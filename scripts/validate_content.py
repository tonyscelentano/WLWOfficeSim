from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from tools.content_validation import validate_content  # noqa: E402


def main() -> int:
    report = validate_content()
    for warning in report.warnings:
        print(f"WARN: {warning}")
    for error in report.errors:
        print(f"ERROR: {error}")
    if report.ok:
        print("Content validation passed.")
        return 0
    print(f"Content validation failed with {len(report.errors)} error(s).")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
