import unittest
from copy import deepcopy

from paperwright.exceptions import ContractValidationError
from paperwright.grobid_evaluation import GROBID_AUDIT_TASK_VERSION
from paperwright.grobid_human_review import (
    RECALL_GOLD_TYPES,
    REVIEW_LABELS,
    build_grobid_human_review_template,
    validate_grobid_human_review,
)
from paperwright.grobid_scoring import (
    GROBID_MATCH_REVIEW_LEGACY_VERSION,
    build_grobid_match_review_template,
    build_grobid_match_task,
    render_grobid_match_review_html,
    score_grobid_human_review,
    validate_grobid_match_review,
    validate_grobid_match_task,
)


def _segment(observation_id: str, text: str, page_index: int = 0):
    return {
        "observation_id": observation_id,
        "page_index": page_index,
        "text": text,
        "paperwright_bbox": {"x": 10, "y": 10, "width": 100, "height": 20},
        "alignments": [
            {
                "physical_element_id": f"p{page_index:04d}-text-00000",
                "native_observation_id": f"native:{observation_id}",
                "native_text": text,
                "native_bbox": {
                    "x": 10,
                    "y": 10,
                    "width": 100,
                    "height": 20,
                },
                "text_score": 1.0,
                "geometry_score": 1.0,
            }
        ],
    }


def _claim(claim_id: str, claim_type: str, text: str):
    return {
        "claim_id": claim_id,
        "claim_type": claim_type,
        "segments": [_segment(f"obs:{claim_id}", text)],
    }


class GrobidSemanticScoringTests(unittest.TestCase):
    def _audit_task(self):
        claims = [
            _claim("c-title", "title", "Journal Name"),
            _claim("c-abstract-1", "abstract", "First abstract sentence."),
            _claim("c-abstract-2", "abstract", "Second abstract sentence."),
            _claim("c-introduction", "section_heading", "INTRODUCTION"),
            _claim("c-background", "section_heading", "BACKGROUND"),
            _claim("c-reference", "reference", "Reference fragment"),
            _claim("c-paragraph", "paragraph", "A correct paragraph."),
        ]
        return {
            "contract_version": GROBID_AUDIT_TASK_VERSION,
            "document_id": "fixture",
            "source_sha256": "a" * 64,
            "review_labels": list(REVIEW_LABELS),
            "downstream_adoption_disclosed": False,
            "claim_count": len(claims),
            "claims": claims,
            "page_images": [
                {
                    "page_index": 0,
                    "path": "page-0001/page.png",
                    "sha256": "b" * 64,
                    "width": 200,
                    "height": 300,
                }
            ],
        }

    def _human_review(self, task):
        response = build_grobid_human_review_template(task)
        labels = {
            "c-title": "wrong_role",
            "c-abstract-1": "correct",
            "c-abstract-2": "correct",
            "c-introduction": "correct",
            "c-background": "correct",
            "c-reference": "partial",
            "c-paragraph": "correct",
        }
        for annotation in response["claim_annotations"]:
            annotation["label"] = labels[annotation["claim_id"]]
        for claim_type in RECALL_GOLD_TYPES:
            response["gold_enumeration"][claim_type]["status"] = "complete"
        response["gold_enumeration"]["title"]["units"] = [
            {
                "gold_unit_id": "fixture:title:0001",
                "claim_type": "title",
                "segments": [
                    {
                        "page_index": 0,
                        "text": "Actual Article Title",
                        "paperwright_bbox": None,
                    }
                ],
                "note": "",
            }
        ]
        response["gold_enumeration"]["abstract"]["units"] = [
            {
                "gold_unit_id": "fixture:abstract:0001",
                "claim_type": "abstract",
                "segments": [
                    {
                        "page_index": 0,
                        "text": "First abstract sentence. Second abstract sentence.",
                        "paperwright_bbox": None,
                    }
                ],
                "note": "",
            }
        ]
        response["gold_enumeration"]["section_heading"]["units"] = [
            {
                "gold_unit_id": "fixture:section_heading:0001",
                "claim_type": "section_heading",
                "segments": [
                    {
                        "page_index": 0,
                        "text": "INTRODUCTION",
                        "paperwright_bbox": None,
                    }
                ],
                "note": "",
            }
        ]
        response["gold_enumeration"]["reference"]["units"] = [
            {
                "gold_unit_id": "fixture:reference:0001",
                "claim_type": "reference",
                "segments": [
                    {
                        "page_index": 0,
                        "text": "Complete reference entry.",
                        "paperwright_bbox": None,
                    }
                ],
                "note": "",
            }
        ]
        response["reviewer"] = "Fixture Reviewer"
        response["completion"] = {
            "claim_count": 7,
            "claims_labeled": 7,
            "gold_types_complete": len(RECALL_GOLD_TYPES),
            "ready_for_scoring": True,
        }
        validate_grobid_human_review(task, response, require_complete=True)
        return response

    def test_builds_conservative_match_task_and_renders_review(self):
        audit_task = self._audit_task()
        human_review = self._human_review(audit_task)
        match_task = build_grobid_match_task(audit_task, human_review)
        self.assertEqual(match_task["gold_unit_count"], 4)
        self.assertEqual(match_task["automatic_match_count"], 1)
        self.assertEqual(match_task["automatic_miss_count"], 2)
        self.assertEqual(match_task["review_gold_unit_count"], 1)
        self.assertEqual(match_task["initial_orphan_correct_claim_count"], 3)
        self.assertEqual(
            match_task["claim_label_counts_by_gold_type"]["reference"][
                "partial"
            ],
            1,
        )
        self.assertEqual(
            next(
                item
                for item in match_task["gold_units"]
                if item["claim_type"] == "reference"
            )["same_type_claim_label_counts"]["correct"],
            0,
        )
        validate_grobid_match_task(audit_task, human_review, match_task)

        response = build_grobid_match_review_template(match_task)
        rendered = render_grobid_match_review_html(match_task, response)
        self.assertIn("GROBID Match Review", rendered)
        self.assertIn("Gold units requiring adjudication", rendered)
        self.assertNotIn("paper-recipe", rendered)

        legacy = deepcopy(response)
        legacy["contract_version"] = GROBID_MATCH_REVIEW_LEGACY_VERSION
        legacy.pop("adjudication_kind")
        validate_grobid_match_review(match_task, legacy)

        invalid_kind = deepcopy(response)
        invalid_kind["adjudication_kind"] = "unattributed"
        with self.assertRaisesRegex(ContractValidationError, "adjudication_kind"):
            validate_grobid_match_review(match_task, invalid_kind)

    def test_blocks_gold_omission_then_scores_resolved_review(self):
        audit_task = self._audit_task()
        human_review = self._human_review(audit_task)
        match_task = build_grobid_match_task(audit_task, human_review)
        response = build_grobid_match_review_template(match_task)
        response["reviewer"] = "Adjudicator"
        response["adjudication_kind"] = "ai"
        response["gold_adjudications"][0].update(
            {
                "decision": "matched",
                "claim_ids": ["c-abstract-1", "c-abstract-2"],
            }
        )
        orphan = {
            item["claim_id"]: item for item in response["orphan_adjudications"]
        }
        orphan["c-background"]["disposition"] = "gold_omission"
        response["completion"] = {
            "gold_review_count": 1,
            "gold_reviews_resolved": 1,
            "orphan_review_count": 3,
            "orphan_reviews_resolved": 3,
            "blocking_issue_count": 1,
            "review_complete": True,
            "ready_for_scoring": False,
        }
        completion = validate_grobid_match_review(
            match_task, response, require_complete=True
        )
        self.assertTrue(completion["review_complete"])
        with self.assertRaisesRegex(ContractValidationError, "阻塞"):
            score_grobid_human_review(
                audit_task, human_review, match_task, response
            )

        orphan["c-background"].update(
            {
                "disposition": "out_of_scope",
                "note": "Structured abstract headings excluded by policy.",
            }
        )
        response["completion"]["blocking_issue_count"] = 0
        response["completion"]["ready_for_scoring"] = True
        score = score_grobid_human_review(
            audit_task, human_review, match_task, response
        )
        self.assertTrue(score["semantic_accuracy_measured"])
        self.assertEqual(score["adjudication_kind"], "ai")
        self.assertEqual(score["strict_recall"]["micro"], 0.5)
        self.assertEqual(score["strict_precision"]["micro"], 0.714286)
        self.assertEqual(
            score["strict_recall"]["by_gold_type"]["abstract"][
                "matched_gold_unit_count"
            ],
            1,
        )
        abstract_match = next(
            item
            for item in score["gold_matches"]
            if item["claim_type"] == "abstract"
        )
        self.assertEqual(abstract_match["decision_source"], "ai_adjudication")

    def test_rejects_reusing_automatic_match_claim(self):
        audit_task = self._audit_task()
        human_review = self._human_review(audit_task)
        match_task = build_grobid_match_task(audit_task, human_review)
        abstract = next(
            item
            for item in match_task["gold_units"]
            if item["claim_type"] == "abstract"
        )
        abstract["candidate_claims"].append(
            {
                "claim_id": "c-introduction",
                "text": "INTRODUCTION",
                "page_indices": [0],
                "page_overlap": True,
                "normalized_similarity": 0.1,
                "gold_char_coverage": 0.1,
            }
        )
        response = build_grobid_match_review_template(match_task)
        response["gold_adjudications"][0].update(
            {"decision": "matched", "claim_ids": ["c-introduction"]}
        )
        with self.assertRaisesRegex(ContractValidationError, "重复分配"):
            validate_grobid_match_review(match_task, response)


if __name__ == "__main__":
    unittest.main()
