"""Binary-classification metrics for judge calibration (E0), stdlib-only.

Layout mirrors sklearn's `classification_report(digits=3)` + confusion matrix so our
reports are line-comparable with the paper's published `Qwen3-32B_report.txt` files.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Confusion:
    """Rows = true label, cols = predicted label (sklearn order: [[tn fp][fn tp]])."""

    tn: int
    fp: int
    fn: int
    tp: int

    @classmethod
    def from_labels(cls, y_true: list[int], y_pred: list[int]) -> "Confusion":
        if len(y_true) != len(y_pred):
            raise ValueError("y_true and y_pred length mismatch")
        counts = {(0, 0): 0, (0, 1): 0, (1, 0): 0, (1, 1): 0}
        for t, p in zip(y_true, y_pred):
            counts[(t, p)] += 1
        return cls(tn=counts[(0, 0)], fp=counts[(0, 1)], fn=counts[(1, 0)], tp=counts[(1, 1)])

    @property
    def total(self) -> int:
        return self.tn + self.fp + self.fn + self.tp

    @property
    def accuracy(self) -> float:
        return (self.tn + self.tp) / self.total if self.total else 0.0

    def precision(self, label: int) -> float:
        predicted = (self.tp + self.fp) if label == 1 else (self.tn + self.fn)
        hit = self.tp if label == 1 else self.tn
        return hit / predicted if predicted else 0.0

    def recall(self, label: int) -> float:
        actual = (self.tp + self.fn) if label == 1 else (self.tn + self.fp)
        hit = self.tp if label == 1 else self.tn
        return hit / actual if actual else 0.0

    def f1(self, label: int) -> float:
        p, r = self.precision(label), self.recall(label)
        return 2 * p * r / (p + r) if (p + r) else 0.0

    def support(self, label: int) -> int:
        return (self.tp + self.fn) if label == 1 else (self.tn + self.fp)

    def __add__(self, other: "Confusion") -> "Confusion":
        return Confusion(
            tn=self.tn + other.tn,
            fp=self.fp + other.fp,
            fn=self.fn + other.fn,
            tp=self.tp + other.tp,
        )


def report_text(cm: Confusion) -> str:
    """Accuracy + confusion matrix + per-class P/R/F1, mirroring the paper's report files."""
    lines = [
        f"Accuracy: {cm.accuracy:.4f}",
        "",
        "Confusion Matrix:",
        f"[[{cm.tn:>3} {cm.fp:>3}]",
        f" [{cm.fn:>3} {cm.tp:>3}]]",
        "",
        "Classification Report:",
        f"{'':>14}{'precision':>10}{'recall':>10}{'f1-score':>10}{'support':>10}",
        "",
    ]
    for label in (0, 1):
        lines.append(
            f"{label:>14}{cm.precision(label):>10.3f}{cm.recall(label):>10.3f}"
            f"{cm.f1(label):>10.3f}{cm.support(label):>10}"
        )
    lines += ["", f"{'accuracy':>14}{'':>20}{cm.accuracy:>10.3f}{cm.total:>10}"]
    return "\n".join(lines)
