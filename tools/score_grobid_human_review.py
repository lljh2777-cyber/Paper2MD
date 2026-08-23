#!/usr/bin/env python3
"""Write a strict single-document GROBID semantic score after adjudication."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from paperwright.grobid_evaluation import canonical_grobid_evaluation_json
from paperwright.grobid_scoring import score_grobid_human_review


def _load(path: Path) -> dict[str, object]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise SystemExit(f"JSON 顶层必须是 object: {path}")
    return value


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("audit_task", type=Path)
    parser.add_argument("human_review", type=Path)
    parser.add_argument("match_task", type=Path)
    parser.add_argument("match_review", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    output = args.output.resolve()
    if output.exists():
        raise SystemExit(f"semantic score 输出已存在，拒绝覆盖: {output}")
    score = score_grobid_human_review(
        _load(args.audit_task.resolve()),
        _load(args.human_review.resolve()),
        _load(args.match_task.resolve()),
        _load(args.match_review.resolve()),
    )
    payload = canonical_grobid_evaluation_json(score)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(payload, encoding="utf-8", newline="\n")
    print(payload, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
