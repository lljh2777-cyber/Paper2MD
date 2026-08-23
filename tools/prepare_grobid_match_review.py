#!/usr/bin/env python3
"""Prepare an offline claim-to-Gold adjudication package."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from paperwright.grobid_evaluation import canonical_grobid_evaluation_json
from paperwright.grobid_scoring import (
    build_grobid_match_review_template,
    build_grobid_match_task,
    grobid_match_task_sha256,
    render_grobid_match_review_html,
)


def _load(path: Path) -> dict[str, object]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise SystemExit(f"JSON 顶层必须是 object: {path}")
    return value


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("audit_task", type=Path)
    parser.add_argument("human_review", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    output = args.output.resolve()
    if output.exists():
        raise SystemExit(f"match review 输出已存在，拒绝覆盖: {output}")
    audit_task = _load(args.audit_task.resolve())
    human_review = _load(args.human_review.resolve())
    match_task = build_grobid_match_task(audit_task, human_review)
    response = build_grobid_match_review_template(match_task)
    task_payload = canonical_grobid_evaluation_json(match_task)
    response_payload = canonical_grobid_evaluation_json(response)
    html_payload = render_grobid_match_review_html(match_task, response)
    readme = """# GROBID Match Review

Open `index.html`. Review only the Gold units and human-correct claims that the
deterministic matcher could not conserve. Export JSON after each session.

`gold_omission`, `claim_label_error`, and `uncertain` are deliberate blockers:
fix the upstream human Gold/claim review, regenerate this package, and do not
force a strict score through unresolved ontology errors.
"""
    manifest = {
        "contract_version": "paperwright-grobid-match-review-package-v0.1",
        "document_id": match_task["document_id"],
        "match_task": {
            "path": "match-task.json",
            "sha256": grobid_match_task_sha256(match_task),
        },
        "response_template": {
            "path": "match-review-template.json",
            "sha256": _sha256_text(response_payload),
        },
        "html": {"path": "index.html", "sha256": _sha256_text(html_payload)},
        "automatic_match_count": match_task["automatic_match_count"],
        "automatic_miss_count": match_task["automatic_miss_count"],
        "review_gold_unit_count": match_task["review_gold_unit_count"],
        "initial_orphan_correct_claim_count": match_task[
            "initial_orphan_correct_claim_count"
        ],
    }
    output.mkdir(parents=True)
    (output / "match-task.json").write_text(
        task_payload, encoding="utf-8", newline="\n"
    )
    (output / "match-review-template.json").write_text(
        response_payload, encoding="utf-8", newline="\n"
    )
    (output / "index.html").write_text(
        html_payload, encoding="utf-8", newline="\n"
    )
    (output / "README.md").write_text(readme, encoding="utf-8", newline="\n")
    manifest_payload = canonical_grobid_evaluation_json(manifest)
    (output / "manifest.json").write_text(
        manifest_payload, encoding="utf-8", newline="\n"
    )
    print(manifest_payload, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
