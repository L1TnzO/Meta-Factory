"""Ephemeral PostgreSQL cluster (initdb + pg_ctl in a temp dir, unix socket only).

Gives the store tests — and self-contained council runs — a REAL Postgres without a
server install or docker: TCP is disabled (`listen_addresses=''`), the cluster lives
behind a private unix socket in tmp and is destroyed on exit. This is the tooth that
docs/work/H3 promised for `store/schema.sql`: round-trips run against Postgres 18,
never against a mock.
"""

from __future__ import annotations

import shutil
import socket
import subprocess
import tempfile
from contextlib import contextmanager
from pathlib import Path

PG_USER = "reqcouncil"


class PgUnavailable(RuntimeError):
    """Raised when the PostgreSQL binaries are not on PATH."""


def binaries_available() -> bool:
    return shutil.which("initdb") is not None and shutil.which("pg_ctl") is not None


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _run(cmd: list[str]) -> None:
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(f"{cmd[0]} failed:\n{proc.stdout}\n{proc.stderr}")


@contextmanager
def ephemeral_postgres():
    """Yield a psycopg DSN for a throwaway cluster; always torn down on exit."""
    if not binaries_available():
        raise PgUnavailable("initdb/pg_ctl not on PATH — install postgresql to run this")
    tmp = Path(tempfile.mkdtemp(prefix="reqc-pg-"))
    data_dir, sock_dir = tmp / "data", tmp / "sock"
    sock_dir.mkdir()
    started = False
    try:
        _run(["initdb", "-D", str(data_dir), "-A", "trust", "-U", PG_USER, "--no-sync"])
        port = _free_port()  # names the socket file only; TCP stays off
        _run(
            [
                "pg_ctl", "-D", str(data_dir), "-l", str(tmp / "pg.log"), "-w",
                "-o", f"-p {port} -k {sock_dir} -c listen_addresses=''",
                "start",
            ]
        )
        started = True
        yield f"host={sock_dir} port={port} user={PG_USER} dbname=postgres"
    finally:
        if started:
            subprocess.run(
                ["pg_ctl", "-D", str(data_dir), "-m", "immediate", "stop"],
                capture_output=True,
            )
        shutil.rmtree(tmp, ignore_errors=True)
