#!/usr/bin/env python3
"""infra_up — bring the DECLARED infra up in the sandbox and demand a proof USES it (E1, DES-9).

PORTED (V3-INC7-MIGRATE-DUMMY) — the body behind the argv INC-4 resolved.

The substrate ORCHESTRATES, it does NOT verify (the same doctrine as the `generate` slot and the
`product_env` proof, ADR-013/012): this helper LAUNCHES a DECLARED `up` (the service — docker compose up,
pg_ctl start, a stdlib socket server) in the BACKGROUND, RETRIES a DECLARED `proof` against it (a client
that connects + asserts) until it passes, and ALWAYS tears the service down. All of `up`/`proof`/`down`
are raw argv passed in as DATA; the substrate NAMES NO TECH — a new infra is new data, never an engine
branch. This is what makes `runs_in: <sandbox>` executable instead of descriptive: a render-green compose
file does NOT pass — the service must actually COME UP and be REACHABLE by the proof.

An optional `bootstrap` (run ONCE, in `workdir`, with the same scrubbed env, BEFORE the service starts)
prepares the PRODUCT's own toolchain so the `proof` can be the product's OWN test (DES-8) running against
the LIVE declared infra. It runs before `up` so a failing bootstrap costs no container, and it is NOT
re-run in the negative phase (only the proof is).

Two non-negotiables make this an honest realization and not a façade:

  1. cwd == the infra `workdir` (where the emitted glue / compose / sources live), and the env is SCRUBBED
     of the platform's PYTHONPATH / VIRTUAL_ENV / PYTHONHOME (DES-8/9): the infra stands on its own, it
     cannot borrow the factory's interpreter. `up` runs in its own process group so teardown reaches the
     whole tree (a leaked server would poison the next run's port).
  2. an EMBEDDED, two-sided negative: after the proof passes and the service is torn down, the SAME proof
     is re-run with the service DOWN and must FAIL. If a proof passes with nothing up, it does not
     actually use the live infra — the gate is decorative (red). This single step doubles as teardown
     verification: it can only fail-to-connect if teardown truly freed the resource.

THAT EMBEDDED NEGATIVE IS WHY THIS EXECUTOR IS NOT HOLLOW. `proof_sha` hashes check names and exit codes
(§11.2), so a port that returned 0 without standing anything up would reproduce the pin perfectly. Here
the 0 is only reachable by passing against a live service AND failing against a dead one — two opposite
observations of the same command, which no amount of returning 0 can fake.

Exit 0 iff the proof reaches the live service AND fails once it is gone. It never raises past the verdict
(fail-safe, like the seed verifier): a workdir that does not exist is exit 2 (nothing built to stand up),
a command that cannot even launch is exit 127, a proof that never connects within the timeout is exit 1.
"""
from __future__ import annotations

import json
import os
import shutil
import signal
import subprocess
import sys
import tempfile
import time
from pathlib import Path

#: env keys that would let the infra/proof borrow the platform's toolchain (DES-8/9).
_LEAKY_ENV = ("PYTHONPATH", "VIRTUAL_ENV", "PYTHONHOME")
#: how long the proof may take to reach a healthy service before we call it dead (seconds).
_READY_TIMEOUT = 10.0
#: how long the proof gets to FAIL against a torn-down service (the decorative-proof tooth).
_DOWN_TIMEOUT = 2.0
#: poll cadence while retrying the proof against a starting service.
_POLL = 0.15


def _sandbox_env() -> dict:
    env = dict(os.environ)
    for leak in _LEAKY_ENV:
        env.pop(leak, None)
    return env


def _short_cwd(wd: Path):
    """Give the check a SHORT logical cwd aliasing `wd`, so a service that derives a Unix-socket path from
    `$PWD` stays under sun_path's ~108-byte budget even when the re-derivable workdir nests deep. A short
    symlink in /tmp points at `wd`; running with cwd=link AND env PWD=link keeps `$PWD` short, while the
    bound socket FILE still lands in the real `wd` (the link resolves there). Tech-AGNOSTIC: the substrate
    only shortens the path — it never knows a socket is bound (ADR-012). Falls back to `wd` itself if the
    alias cannot be made. Returns (cwd, pwd, cleanup).

    This matters MORE in v3 than it did in v2: `v3.verify.rederive` runs the line inside a temporary
    copy under the system temp dir, so the workdir is deeper than the in-place one v2 measured against.
    """
    try:
        holder = tempfile.mkdtemp(prefix="mfu-", dir=tempfile.gettempdir())
        link = Path(holder) / "w"
        link.symlink_to(wd)
        return link, str(link), lambda: shutil.rmtree(holder, ignore_errors=True)
    except OSError:
        return wd, str(wd), lambda: None


def _run(argv: list, cwd: Path, env: dict) -> int:
    """Run one argv to completion; OSError (cannot launch) surfaces as 127, never raises."""
    try:
        proc = subprocess.run(list(argv), cwd=str(cwd), env=env, capture_output=True, text=True)
    except OSError as exc:
        print(f"infra_up: could not launch {argv[0] if argv else '?'}: {type(exc).__name__}: {exc}",
              file=sys.stderr)
        return 127
    return proc.returncode


def _retry_proof(proof: list, cwd: Path, env: dict, deadline: float, up) -> int:
    """Retry the proof until it exits 0 or the deadline passes. If the background `up` dies with a
    non-zero code before the proof passes, fail fast with that code (the service never came up)."""
    last = 1
    while time.monotonic() < deadline:
        if up is not None and up.poll() is not None and up.returncode not in (0, None):
            print(f"infra_up: the infra (`up`) died with code {up.returncode} before the proof",
                  file=sys.stderr)
            return up.returncode or 1
        last = _run(proof, cwd, env)
        if last == 0:
            return 0
        time.sleep(_POLL)
    return last if last != 0 else 1


def _teardown(down: list, up, cwd: Path, env: dict) -> None:
    """ALWAYS free the resource: run the declared `down` (if any), then signal the `up` process group
    (SIGTERM, then SIGKILL) so no server is left holding the port for the next run."""
    if down:
        _run(down, cwd, env)
    if up is None:
        return
    if up.poll() is None:
        for sig in (signal.SIGTERM, signal.SIGKILL):
            try:
                os.killpg(up.pid, sig)
            except (ProcessLookupError, PermissionError, OSError):
                try:
                    up.send_signal(sig)
                except (ProcessLookupError, OSError):
                    pass
            try:
                up.wait(timeout=3)
                break
            except subprocess.TimeoutExpired:
                continue
    try:
        up.wait(timeout=1)
    except subprocess.TimeoutExpired:
        pass


def run(workdir: str, up: list, proof: list, down: list, bootstrap: list | None = None,
        ready_timeout: float = _READY_TIMEOUT, down_timeout: float = _DOWN_TIMEOUT) -> int:
    wd = Path(workdir).resolve()
    if not wd.is_dir():
        print(f"infra_up: workdir {wd} does not exist (nothing built to stand up)", file=sys.stderr)
        return 2
    if not proof:
        print("infra_up: no `proof` argv (a proof must USE the live infra)", file=sys.stderr)
        return 2
    env = _sandbox_env()
    cwd, env["PWD"], cleanup = _short_cwd(wd)
    try:
        return _run_phases(cwd, up, proof, down, bootstrap, env, ready_timeout, down_timeout)
    finally:
        cleanup()   # always remove the short alias (a symlink in /tmp; the real wd is untouched)


def _run_phases(cwd: Path, up: list, proof: list, down: list, bootstrap: list | None,
                env: dict, ready_timeout: float, down_timeout: float) -> int:
    # 0. BOOTSTRAP (optional): prepare the PRODUCT's toolchain once, BEFORE standing the infra up (a
    #    broken bootstrap costs no container). Same scrubbed env (DES-8). Not re-run in the negative phase.
    if bootstrap:
        rc = _run(bootstrap, cwd, env)
        if rc != 0:
            print(f"infra_up: the product bootstrap failed (exit {rc}) before the infra came up",
                  file=sys.stderr)
            return rc

    proc = None
    try:
        if up:
            try:
                proc = subprocess.Popen(list(up), cwd=str(cwd), env=env, start_new_session=True,
                                        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            except OSError as exc:
                print(f"infra_up: the infra (`up`) could not launch ({up[0]}): "
                      f"{type(exc).__name__}: {exc}", file=sys.stderr)
                return 127
        # 1. POSITIVE: the proof reaches the live service (retried while it boots).
        rc = _retry_proof(proof, cwd, env, time.monotonic() + ready_timeout, proc)
        if rc != 0:
            print(f"infra_up: the proof did not reach the live infra in {ready_timeout:.0f}s (exit {rc})",
                  file=sys.stderr)
            return rc
    finally:
        _teardown(down, proc, cwd, env)

    # 2. EMBEDDED NEGATIVE (not decorative): with the infra ALREADY down, the SAME proof must FAIL. A
    #    proof that passes with no live service does not use the infra (it would be prose). Double duty:
    #    it proves teardown freed the resource — it can only fail to connect if the service really went.
    deadline = time.monotonic() + down_timeout
    neg = 1
    while time.monotonic() < deadline:
        neg = _run(proof, cwd, env)
        if neg != 0:
            break
        time.sleep(_POLL)
    if neg == 0:
        print("infra_up: GATE DECORATIVO — the proof passed with the infra DOWN (it does not use the "
              "live service, or teardown did not free the resource)", file=sys.stderr)
        return 1

    print("OK infra_up: the declared infra came up and the proof used it (exit 0); with the infra down "
          "the proof goes red (not decorative, teardown verified)")
    return 0


def main(argv: list[str]) -> int:
    # argv: <workdir> <up-json> <proof-json> <down-json> <bootstrap-json> [ready-timeout]. up/proof/down/
    # bootstrap arrive JSON-encoded so arbitrary argv (spaces, flags) survive transport unambiguously; they
    # are free DATA the plan chose (ADR-012). The optional readiness timeout is DATA too: real infra (a
    # container) declares its own boot window, the substrate hardcodes none.
    if len(argv) not in (5, 6):
        print("usage: infra_up <workdir> <up-json> <proof-json> <down-json> <bootstrap-json> [ready-timeout]",
              file=sys.stderr)
        return 2
    kwargs = {}
    if len(argv) == 6 and argv[5]:
        kwargs["ready_timeout"] = float(argv[5])
    return run(argv[0], json.loads(argv[1]), json.loads(argv[2]), json.loads(argv[3]),
               bootstrap=json.loads(argv[4]), **kwargs)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
