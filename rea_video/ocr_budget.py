"""Shared, per-analysis OCR call budget; cache reuse does not spend a call."""
from dataclasses import dataclass

@dataclass
class OCRBudget:
    limit: int = 240
    used: int = 0
    failed: int = 0
    scanned: int = 0
    reused: int = 0
    unavailable: bool = False
    skipped: int = 0

    def __post_init__(self):
        if isinstance(self.limit, bool) or not isinstance(self.limit, int) or self.limit < 0:
            raise ValueError("OCR budget must be a non-negative integer")

    def take(self):
        if self.used >= self.limit:
            self.skipped += 1
            return False
        self.used += 1
        return True

    def summary(self, enabled=True):
        status = ("off" if not enabled else "unavailable" if self.unavailable else
                  "failed" if self.used and self.failed == self.used else
                  "partial" if self.failed or self.skipped else "ok" if self.used else "not_run")
        return {"status": status, "max_calls": self.limit, "calls": self.used,
                "failed_calls": self.failed, "scanned_frames": self.scanned, "reused_frames": self.reused,
                "skipped_requests": self.skipped, "budget_exhausted": self.used >= self.limit,
                "coverage": "sampled_times_only"}
