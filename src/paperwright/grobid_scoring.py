"""Auditable matching and strict semantic scoring for GROBID human reviews."""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from collections import Counter
from difflib import SequenceMatcher
from typing import Any, Mapping

from .exceptions import ContractValidationError
from .grobid_human_review import (
    RECALL_GOLD_TYPES,
    REVIEW_LABELS,
    grobid_audit_task_sha256,
    validate_grobid_audit_task,
    validate_grobid_human_review,
)

GROBID_MATCH_TASK_VERSION = "paperwright-grobid-gold-match-task-v0.1"
GROBID_MATCH_REVIEW_VERSION = "paperwright-grobid-gold-match-review-v0.1"
GROBID_SEMANTIC_SCORE_VERSION = "paperwright-grobid-semantic-score-v0.1"
MATCH_DECISIONS = ("matched", "missed", "uncertain")
ORPHAN_DISPOSITIONS = (
    "out_of_scope",
    "duplicate",
    "gold_omission",
    "claim_label_error",
    "uncertain",
)
BLOCKING_ORPHAN_DISPOSITIONS = {
    "gold_omission",
    "claim_label_error",
    "uncertain",
}


def _fail(message: str) -> None:
    raise ContractValidationError(message)


def _canonical_json(value: Mapping[str, Any]) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        indent=2,
        sort_keys=True,
        allow_nan=False,
    ) + "\n"


def _sha256(value: Mapping[str, Any]) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def grobid_human_review_sha256(response: Mapping[str, Any]) -> str:
    return _sha256(response)


def grobid_match_task_sha256(task: Mapping[str, Any]) -> str:
    return _sha256(task)


def _normalized_text(value: str) -> str:
    value = unicodedata.normalize("NFKC", value).casefold().replace("\u00ad", "")
    return re.sub(r"[^\w]+", "", value)


def _unique_claim_text(claim: Mapping[str, Any]) -> str:
    values: list[str] = []
    seen: set[str] = set()
    for segment in claim["segments"]:
        text = segment["text"].strip()
        if text and text not in seen:
            seen.add(text)
            values.append(text)
    return " ".join(values)


def _gold_text(unit: Mapping[str, Any]) -> str:
    return " ".join(segment["text"].strip() for segment in unit["segments"])


def _claim_pages(claim: Mapping[str, Any]) -> list[int]:
    return sorted({segment["page_index"] for segment in claim["segments"]})


def _gold_pages(unit: Mapping[str, Any]) -> list[int]:
    return sorted({segment["page_index"] for segment in unit["segments"]})


def _similarity(left: str, right: str) -> float:
    if not left or not right:
        return 0.0
    return round(SequenceMatcher(None, left, right, autojunk=False).ratio(), 6)


def _gold_coverage(gold: str, candidate: str) -> float:
    if not gold:
        return 0.0
    matcher = SequenceMatcher(None, gold, candidate, autojunk=False)
    matched = sum(block.size for block in matcher.get_matching_blocks())
    return round(min(1.0, matched / len(gold)), 6)


def build_grobid_match_task(
    audit_task: Mapping[str, Any],
    human_review: Mapping[str, Any],
) -> dict[str, Any]:
    """Build conservative exact matches and explicit adjudication candidates."""

    validate_grobid_audit_task(audit_task)
    validate_grobid_human_review(audit_task, human_review, require_complete=True)
    annotations = {
        item["claim_id"]: item for item in human_review["claim_annotations"]
    }
    claims = {claim["claim_id"]: claim for claim in audit_task["claims"]}
    claim_order = {
        claim["claim_id"]: index
        for index, claim in enumerate(audit_task["claims"])
    }
    eligible = {
        claim_id: claim
        for claim_id, claim in claims.items()
        if claim["claim_type"] in RECALL_GOLD_TYPES
        and annotations[claim_id]["label"] == "correct"
    }
    gold_units = [
        unit
        for claim_type in RECALL_GOLD_TYPES
        for unit in human_review["gold_enumeration"][claim_type]["units"]
    ]
    exact_by_gold: dict[str, list[str]] = {}
    exact_by_claim: dict[str, list[str]] = {}
    for unit in gold_units:
        gold_id = unit["gold_unit_id"]
        gold_normalized = _normalized_text(_gold_text(unit))
        gold_pages = set(_gold_pages(unit))
        exact_ids = []
        for claim_id, claim in eligible.items():
            if claim["claim_type"] != unit["claim_type"]:
                continue
            if not gold_pages.intersection(_claim_pages(claim)):
                continue
            if _normalized_text(_unique_claim_text(claim)) == gold_normalized:
                exact_ids.append(claim_id)
                exact_by_claim.setdefault(claim_id, []).append(gold_id)
        exact_by_gold[gold_id] = exact_ids

    matched_claim_ids: set[str] = set()
    items = []
    correct_type_counts = Counter(claim["claim_type"] for claim in eligible.values())
    label_counts_by_type: dict[str, Counter[str]] = {
        claim_type: Counter() for claim_type in RECALL_GOLD_TYPES
    }
    for claim_id, claim in claims.items():
        if claim["claim_type"] in label_counts_by_type:
            label_counts_by_type[claim["claim_type"]][
                annotations[claim_id]["label"]
            ] += 1
    for unit in gold_units:
        gold_id = unit["gold_unit_id"]
        claim_type = unit["claim_type"]
        gold_text = _gold_text(unit)
        normalized_gold = _normalized_text(gold_text)
        gold_pages = _gold_pages(unit)
        candidate_claims = []
        for claim_id, claim in eligible.items():
            if claim["claim_type"] != claim_type:
                continue
            claim_text = _unique_claim_text(claim)
            normalized_claim = _normalized_text(claim_text)
            pages = _claim_pages(claim)
            candidate_claims.append(
                {
                    "claim_id": claim_id,
                    "text": claim_text,
                    "page_indices": pages,
                    "page_overlap": bool(set(gold_pages).intersection(pages)),
                    "normalized_similarity": _similarity(
                        normalized_gold, normalized_claim
                    ),
                    "gold_char_coverage": _gold_coverage(
                        normalized_gold, normalized_claim
                    ),
                }
            )
        candidate_claims.sort(
            key=lambda item: (
                item["page_overlap"],
                item["gold_char_coverage"],
                item["normalized_similarity"],
                item["claim_id"],
            ),
            reverse=True,
        )
        exact_ids = exact_by_gold[gold_id]
        if (
            len(exact_ids) == 1
            and len(exact_by_claim.get(exact_ids[0], [])) == 1
        ):
            automatic_decision = "matched"
            automatic_claim_ids = exact_ids
            reason = "unique_exact_normalized_text_and_page_overlap"
            matched_claim_ids.update(exact_ids)
        elif correct_type_counts[claim_type] == 0:
            automatic_decision = "missed"
            automatic_claim_ids = []
            reason = "no_human_correct_claim_of_same_type"
        else:
            automatic_decision = None
            automatic_claim_ids = []
            reason = "requires_human_adjudication"
        overlapping = [item for item in candidate_claims if item["page_overlap"]]
        aggregate_ids = sorted(
            (item["claim_id"] for item in overlapping),
            key=claim_order.__getitem__,
        )
        aggregate_text = " ".join(
            _unique_claim_text(claims[claim_id]) for claim_id in aggregate_ids
        )
        items.append(
            {
                "gold_unit_id": gold_id,
                "claim_type": claim_type,
                "text": gold_text,
                "page_indices": gold_pages,
                "automatic_decision": automatic_decision,
                "automatic_claim_ids": automatic_claim_ids,
                "reason": reason,
                "same_type_claim_label_counts": {
                    label: label_counts_by_type[claim_type][label]
                    for label in REVIEW_LABELS
                },
                "aggregate_candidate_claim_ids": aggregate_ids,
                "aggregate_normalized_similarity": _similarity(
                    normalized_gold,
                    _normalized_text(aggregate_text),
                ),
                "aggregate_gold_char_coverage": _gold_coverage(
                    normalized_gold,
                    _normalized_text(aggregate_text),
                ),
                "candidate_claims": candidate_claims,
            }
        )
    orphan_claims = []
    for claim_id, claim in eligible.items():
        if claim_id in matched_claim_ids:
            continue
        orphan_claims.append(
            {
                "claim_id": claim_id,
                "claim_type": claim["claim_type"],
                "text": _unique_claim_text(claim),
                "page_indices": _claim_pages(claim),
                "exact_gold_unit_ids": exact_by_claim.get(claim_id, []),
            }
        )
    return {
        "contract_version": GROBID_MATCH_TASK_VERSION,
        "document_id": audit_task["document_id"],
        "source_sha256": audit_task["source_sha256"],
        "audit_task_sha256": grobid_audit_task_sha256(audit_task),
        "human_review_sha256": grobid_human_review_sha256(human_review),
        "policy": {
            "strict_true_positive_label": "correct",
            "uncertain_claims_excluded_from_precision_denominator": True,
            "automatic_match": "unique normalized-text equality with page overlap",
            "automatic_miss": "no human-correct claim of the same type",
            "many_claims_to_one_gold_requires_adjudication": True,
            "blocking_orphan_dispositions": sorted(
                BLOCKING_ORPHAN_DISPOSITIONS
            ),
        },
        "gold_unit_count": len(items),
        "automatic_match_count": sum(
            item["automatic_decision"] == "matched" for item in items
        ),
        "automatic_miss_count": sum(
            item["automatic_decision"] == "missed" for item in items
        ),
        "review_gold_unit_count": sum(
            item["automatic_decision"] is None for item in items
        ),
        "claim_label_counts_by_gold_type": {
            claim_type: {
                label: label_counts_by_type[claim_type][label]
                for label in REVIEW_LABELS
            }
            for claim_type in RECALL_GOLD_TYPES
        },
        "gold_units": items,
        "initial_orphan_correct_claim_count": len(orphan_claims),
        "initial_orphan_correct_claims": orphan_claims,
    }


def validate_grobid_match_task(
    audit_task: Mapping[str, Any],
    human_review: Mapping[str, Any],
    match_task: Mapping[str, Any],
) -> None:
    """Validate provenance and conservation of a generated match task."""

    expected = build_grobid_match_task(audit_task, human_review)
    if match_task != expected:
        _fail("GROBID match task 与确定性重算结果不一致")


def build_grobid_match_review_template(
    match_task: Mapping[str, Any],
) -> dict[str, Any]:
    """Create an empty response only for decisions deterministic rules cannot make."""

    gold = [
        {
            "gold_unit_id": item["gold_unit_id"],
            "decision": None,
            "claim_ids": [],
            "note": "",
        }
        for item in match_task["gold_units"]
        if item["automatic_decision"] is None
    ]
    orphan = [
        {"claim_id": item["claim_id"], "disposition": None, "note": ""}
        for item in match_task["initial_orphan_correct_claims"]
    ]
    return {
        "contract_version": GROBID_MATCH_REVIEW_VERSION,
        "match_task_sha256": grobid_match_task_sha256(match_task),
        "document_id": match_task["document_id"],
        "reviewer": "",
        "gold_adjudications": gold,
        "orphan_adjudications": orphan,
        "completion": {
            "gold_review_count": len(gold),
            "gold_reviews_resolved": 0,
            "orphan_review_count": len(orphan),
            "orphan_reviews_resolved": 0,
            "blocking_issue_count": 0,
            "review_complete": False,
            "ready_for_scoring": False,
        },
    }


def validate_grobid_match_review(
    match_task: Mapping[str, Any],
    response: Mapping[str, Any],
    *,
    require_complete: bool = False,
    require_scoring_ready: bool = False,
) -> dict[str, Any]:
    """Validate adjudications and enforce gold/claim conservation."""

    if (
        match_task.get("contract_version") != GROBID_MATCH_TASK_VERSION
        or not isinstance(match_task.get("gold_units"), list)
        or not isinstance(match_task.get("initial_orphan_correct_claims"), list)
    ):
        _fail("GROBID match task 顶层字段非法")
    if (
        response.get("contract_version") != GROBID_MATCH_REVIEW_VERSION
        or response.get("match_task_sha256")
        != grobid_match_task_sha256(match_task)
        or response.get("document_id") != match_task.get("document_id")
        or not isinstance(response.get("reviewer"), str)
    ):
        _fail("GROBID match review 与 task 绑定不匹配")
    review_gold = [
        item
        for item in match_task["gold_units"]
        if item["automatic_decision"] is None
    ]
    adjudications = response.get("gold_adjudications")
    if not isinstance(adjudications, list) or len(adjudications) != len(
        review_gold
    ):
        _fail("GROBID match review gold adjudications 不守恒")
    correct_claims = {
        item["claim_id"]: item
        for item in match_task["initial_orphan_correct_claims"]
    }
    assigned: set[str] = {
        claim_id
        for item in match_task["gold_units"]
        for claim_id in item["automatic_claim_ids"]
    }
    gold_resolved = 0
    blocking = 0
    for adjudication, gold in zip(adjudications, review_gold, strict=True):
        decision = (
            adjudication.get("decision")
            if isinstance(adjudication, dict)
            else None
        )
        claim_ids = (
            adjudication.get("claim_ids")
            if isinstance(adjudication, dict)
            else None
        )
        if (
            not isinstance(adjudication, dict)
            or adjudication.get("gold_unit_id") != gold["gold_unit_id"]
            or decision not in {*MATCH_DECISIONS, None}
            or not isinstance(claim_ids, list)
            or len(claim_ids) != len(set(claim_ids))
            or not isinstance(adjudication.get("note"), str)
        ):
            _fail("GROBID match review gold adjudication 非法或乱序")
        allowed = {
            item["claim_id"]
            for item in gold["candidate_claims"]
            if item["page_overlap"]
        }
        if any(claim_id not in allowed for claim_id in claim_ids):
            _fail("GROBID match review 使用了非候选 claim")
        if decision == "matched" and assigned.intersection(claim_ids):
            _fail("GROBID match review claim 被重复分配给多个 gold units")
        if decision == "matched" and not claim_ids:
            _fail("matched gold unit 必须绑定至少一个 claim")
        if decision in {"missed", "uncertain", None} and claim_ids:
            _fail("非 matched gold unit 不得绑定 claims")
        if decision is not None:
            gold_resolved += 1
        if decision == "uncertain":
            blocking += 1
        assigned.update(claim_ids)
    orphan_items = response.get("orphan_adjudications")
    if not isinstance(orphan_items, list) or len(orphan_items) != len(
        correct_claims
    ):
        _fail("GROBID match review orphan adjudications 不守恒")
    orphan_resolved = 0
    for adjudication, (claim_id, _claim) in zip(
        orphan_items, correct_claims.items(), strict=True
    ):
        disposition = (
            adjudication.get("disposition")
            if isinstance(adjudication, dict)
            else None
        )
        if (
            not isinstance(adjudication, dict)
            or adjudication.get("claim_id") != claim_id
            or disposition not in {*ORPHAN_DISPOSITIONS, None}
            or not isinstance(adjudication.get("note"), str)
        ):
            _fail("GROBID match review orphan adjudication 非法或乱序")
        if claim_id in assigned:
            if disposition is not None:
                _fail("已匹配 claim 不得再设置 orphan disposition")
            orphan_resolved += 1
            continue
        if disposition is not None:
            orphan_resolved += 1
        if disposition in BLOCKING_ORPHAN_DISPOSITIONS:
            blocking += 1
        if disposition in {"out_of_scope", "duplicate"} and not adjudication[
            "note"
        ].strip():
            _fail("out_of_scope/duplicate orphan 必须说明理由")
    review_complete = (
        gold_resolved == len(review_gold)
        and orphan_resolved == len(correct_claims)
    )
    completion = {
        "gold_review_count": len(review_gold),
        "gold_reviews_resolved": gold_resolved,
        "orphan_review_count": len(correct_claims),
        "orphan_reviews_resolved": orphan_resolved,
        "blocking_issue_count": blocking,
        "review_complete": review_complete,
        "ready_for_scoring": review_complete and blocking == 0,
    }
    if response.get("completion") != completion:
        _fail("GROBID match review completion 与内容不一致")
    if require_complete and (
        not review_complete or not response["reviewer"].strip()
    ):
        _fail("GROBID match review 尚未完成或缺少 reviewer")
    if require_scoring_ready and not completion["ready_for_scoring"]:
        _fail("GROBID match review 存在阻塞问题，拒绝评分")
    return completion


_MATCH_REVIEW_HTML = r'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>GROBID Match Review</title>
<style>
:root{--bg:#f3f6fa;--surface:#fff;--text:#172033;--muted:#647087;--line:#d9e0ea;--blue:#1268dc;--blue-soft:#eaf3ff;--amber:#d88900;--amber-soft:#fff6e3;--green:#138a62;--red:#c93c46;--radius:6px;--header:60px}
*{box-sizing:border-box}html,body{height:100%;margin:0}body{display:grid;grid-template-rows:var(--header) minmax(0,1fr) 34px;background:var(--bg);color:var(--text);font:14px Inter,ui-sans-serif,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}button,input,textarea,select{font:inherit;color:inherit}.topbar{display:grid;grid-template-columns:310px 1fr auto;align-items:center;gap:20px;padding:0 22px;background:#fff;border-bottom:1px solid var(--line)}.brand{font-size:20px;font-weight:780}.document{font-weight:680}.actions{display:flex;gap:8px}.button{height:38px;padding:0 14px;border:1px solid var(--line);border-radius:var(--radius);background:#fff;font-weight:680;cursor:pointer}.button.primary{background:var(--blue);border-color:var(--blue);color:#fff}.workspace{min-height:0;overflow:auto;padding:22px}.summary{max-width:1380px;margin:0 auto 16px;display:grid;grid-template-columns:repeat(5,1fr);background:#fff;border:1px solid var(--line)}.metric{padding:13px 15px;border-right:1px solid var(--line)}.metric:last-child{border-right:0}.metric strong{display:block;font-size:19px}.metric span{font-size:12px;color:var(--muted)}.reviewer-row{max-width:1380px;margin:0 auto 16px;display:flex;align-items:center;gap:12px}.reviewer-row label{font-weight:720}.reviewer-row input{width:280px;height:38px;border:1px solid var(--line);border-radius:var(--radius);padding:0 10px;background:#fff}.columns{max-width:1380px;margin:0 auto;display:grid;grid-template-columns:minmax(0,1.1fr) minmax(420px,.9fr);gap:18px;align-items:start}.panel{background:#fff;border:1px solid var(--line);border-radius:var(--radius)}.panel-head{padding:18px 20px;border-bottom:1px solid var(--line)}.panel-head h1{font-size:19px;margin:0 0 6px}.panel-head p{margin:0;color:var(--muted);line-height:1.5}.item{padding:18px 20px;border-bottom:1px solid var(--line)}.item:last-child{border-bottom:0}.item-head{display:flex;justify-content:space-between;gap:14px;align-items:start}.item-title{font-weight:760}.meta{color:var(--muted);font-size:12px;margin-top:3px}.gold-text,.claim-text{margin-top:11px;padding:10px 11px;border:1px solid #8abaff;background:#f8fbff;border-radius:var(--radius);line-height:1.48;white-space:pre-wrap}.claim-text{border-color:#efbc5c;background:#fffaf0}.evidence{margin-top:12px}.candidate{display:grid;grid-template-columns:22px 1fr;gap:8px;padding:9px 0;border-top:1px solid #e8edf3}.candidate input{margin-top:3px}.candidate.disabled{opacity:.55}.score{font-size:12px;color:var(--muted);margin-top:4px}.decision{height:36px;border:1px solid var(--line);border-radius:5px;background:#fff;padding:0 8px}.note{width:100%;min-height:62px;margin-top:10px;padding:8px 9px;border:1px solid var(--line);border-radius:var(--radius);resize:vertical;line-height:1.4}.resolved{color:var(--green);font-weight:720}.blocked{color:var(--red);font-weight:720}.statusbar{display:flex;align-items:center;justify-content:space-between;padding:0 18px;background:#fff;border-top:1px solid var(--line);font-size:12px;color:var(--muted)}.dot{display:inline-block;width:8px;height:8px;border-radius:50%;background:var(--green);margin-right:7px}.hidden{display:none}@media(max-width:960px){body{height:auto;display:block}.topbar{min-height:60px;grid-template-columns:1fr auto}.document{display:none}.summary{grid-template-columns:repeat(2,1fr)}.columns{grid-template-columns:1fr}.workspace{overflow:visible}.statusbar{position:sticky;bottom:0;height:34px}}
</style></head><body>
<header class="topbar"><div class="brand">GROBID Match Review</div><div class="document" id="documentName"></div><div class="actions"><button class="button" id="importButton">Import JSON</button><button class="button primary" id="exportButton">Export JSON</button><input class="hidden" id="importFile" type="file" accept="application/json"></div></header>
<main class="workspace"><section class="summary" id="summary"></section><div class="reviewer-row"><label for="reviewer">Reviewer</label><input id="reviewer" placeholder="Required for completed review"></div><div class="columns"><section class="panel"><div class="panel-head"><h1>Gold units requiring adjudication</h1><p>Only deterministic rules’ unresolved cases appear here. “Matched” requires selecting every correct claim that jointly covers the Gold unit.</p></div><div id="goldItems"></div></section><section class="panel"><div class="panel-head"><h1>Unassigned correct claims</h1><p>A claim selected in a Gold match resolves automatically. Otherwise classify why a human-correct claim has no Gold counterpart; gold omissions and label errors block scoring.</p></div><div id="orphanItems"></div></section></div></main>
<footer class="statusbar"><div><span class="dot"></span>Changes are saved locally.</div><div id="completion"></div></footer>
<script>
const task=__TASK_JSON__;const initialResponse=__RESPONSE_JSON__;const taskHash=__TASK_HASH_JSON__;const storageKey=`paperwright-grobid-match:${taskHash}`;const blocking=new Set(["gold_omission","claim_label_error","uncertain"]);let response=load();const $=id=>document.getElementById(id);
function load(){try{const saved=localStorage.getItem(storageKey);if(saved){const value=JSON.parse(saved);if(value.match_task_sha256===taskHash)return value}}catch(error){}return structuredClone(initialResponse)}
function assignedClaims(){const result=new Set(task.gold_units.flatMap(item=>item.automatic_claim_ids));response.gold_adjudications.forEach(item=>{if(item.decision==="matched")item.claim_ids.forEach(id=>result.add(id))});return result}
function calculate(){const assigned=assignedClaims();const goldResolved=response.gold_adjudications.filter(item=>item.decision!==null&&(item.decision!=="matched"||item.claim_ids.length>0)).length;let orphanResolved=0;let blockers=response.gold_adjudications.filter(item=>item.decision==="uncertain").length;response.orphan_adjudications.forEach(item=>{if(assigned.has(item.claim_id)){item.disposition=null;orphanResolved++}else if(item.disposition!==null&&!(["out_of_scope","duplicate"].includes(item.disposition)&&!item.note.trim())){orphanResolved++;if(blocking.has(item.disposition))blockers++}});const reviewComplete=goldResolved===response.gold_adjudications.length&&orphanResolved===response.orphan_adjudications.length;return{gold_review_count:response.gold_adjudications.length,gold_reviews_resolved:goldResolved,orphan_review_count:response.orphan_adjudications.length,orphan_reviews_resolved:orphanResolved,blocking_issue_count:blockers,review_complete:reviewComplete,ready_for_scoring:reviewComplete&&blockers===0}}
function save(){response.reviewer=$("reviewer").value;response.completion=calculate();localStorage.setItem(storageKey,JSON.stringify(response));renderStatus()}
function pages(values){return values.map(value=>value+1).join(", ")}
function automaticAssigned(){return new Set(task.gold_units.flatMap(item=>item.automatic_claim_ids))}
function renderGold(){const root=$("goldItems");root.innerHTML="";const auto=automaticAssigned();const reviews=task.gold_units.filter(item=>item.automatic_decision===null);reviews.forEach((item,index)=>{const adjudication=response.gold_adjudications[index];const section=document.createElement("section");section.className="item";section.innerHTML='<div class="item-head"><div><div class="item-title"></div><div class="meta"></div></div><select class="decision"><option value="">Choose decision</option><option value="matched">Matched</option><option value="missed">Missed</option><option value="uncertain">Uncertain</option></select></div><div class="gold-text"></div><div class="evidence"></div><textarea class="note" placeholder="Optional adjudication note"></textarea>';section.querySelector(".item-title").textContent=item.claim_type.replaceAll("_"," ");const labels=item.same_type_claim_label_counts;section.querySelector(".meta").textContent=`Gold ${item.gold_unit_id} · p. ${pages(item.page_indices)} · aggregate coverage ${(item.aggregate_gold_char_coverage*100).toFixed(1)}% · same-type claims: ${labels.correct} correct / ${labels.partial} partial / ${labels.wrong_role} wrong role / ${labels.unsupported} unsupported / ${labels.uncertain} uncertain`;section.querySelector(".gold-text").textContent=item.text;const select=section.querySelector("select");select.value=adjudication.decision||"";select.onchange=()=>{adjudication.decision=select.value||null;if(adjudication.decision!=="matched")adjudication.claim_ids=[];save();renderAll()};const evidence=section.querySelector(".evidence");item.candidate_claims.filter(candidate=>candidate.page_overlap).forEach(candidate=>{const label=document.createElement("label");const used=auto.has(candidate.claim_id);label.className=`candidate ${used?"disabled":""}`;label.innerHTML='<input type="checkbox"><div><div class="claim-text"></div><div class="score"></div></div>';const checkbox=label.querySelector("input");checkbox.checked=adjudication.claim_ids.includes(candidate.claim_id);checkbox.disabled=used||adjudication.decision!=="matched";checkbox.onchange=()=>{if(checkbox.checked)adjudication.claim_ids.push(candidate.claim_id);else adjudication.claim_ids=adjudication.claim_ids.filter(id=>id!==candidate.claim_id);save();renderAll()};label.querySelector(".claim-text").textContent=candidate.text;label.querySelector(".score").textContent=`${candidate.claim_id} · p. ${pages(candidate.page_indices)} · coverage ${(candidate.gold_char_coverage*100).toFixed(1)}%${used?" · already assigned by exact match":""}`;evidence.append(label)});const note=section.querySelector("textarea");note.value=adjudication.note;note.oninput=()=>{adjudication.note=note.value;save()};root.append(section)});if(!reviews.length)root.innerHTML='<div class="item resolved">All Gold units were decided deterministically.</div>'}
function renderOrphans(){const root=$("orphanItems");root.innerHTML="";const assigned=assignedClaims();task.initial_orphan_correct_claims.forEach((claim,index)=>{const adjudication=response.orphan_adjudications[index];const section=document.createElement("section");section.className="item";const covered=assigned.has(claim.claim_id);section.innerHTML='<div class="item-head"><div><div class="item-title"></div><div class="meta"></div></div><select class="decision"><option value="">Choose disposition</option><option value="out_of_scope">Out of scope</option><option value="duplicate">Duplicate</option><option value="gold_omission">Gold omission</option><option value="claim_label_error">Claim label error</option><option value="uncertain">Uncertain</option></select></div><div class="claim-text"></div><textarea class="note" placeholder="Required for out-of-scope or duplicate"></textarea>';section.querySelector(".item-title").textContent=claim.claim_type.replaceAll("_"," ");section.querySelector(".meta").textContent=`${claim.claim_id} · p. ${pages(claim.page_indices)}`;section.querySelector(".claim-text").textContent=claim.text;const select=section.querySelector("select");if(covered){select.innerHTML='<option>Covered by Gold mapping</option>';select.disabled=true;adjudication.disposition=null}else{select.value=adjudication.disposition||"";select.onchange=()=>{adjudication.disposition=select.value||null;save();renderStatus()}}const note=section.querySelector("textarea");note.value=adjudication.note;note.disabled=covered;note.oninput=()=>{adjudication.note=note.value;save()};root.append(section)})}
function renderStatus(){const c=calculate();response.completion=c;$("completion").textContent=`Gold ${c.gold_reviews_resolved}/${c.gold_review_count} · claims ${c.orphan_reviews_resolved}/${c.orphan_review_count} · blockers ${c.blocking_issue_count}${c.ready_for_scoring?" · Ready for scoring":c.review_complete?" · Review complete, scoring blocked":""}`;$("summary").innerHTML=`<div class="metric"><strong>${task.automatic_match_count}</strong><span>automatic matches</span></div><div class="metric"><strong>${task.automatic_miss_count}</strong><span>automatic misses</span></div><div class="metric"><strong>${task.review_gold_unit_count}</strong><span>Gold decisions</span></div><div class="metric"><strong>${task.initial_orphan_correct_claim_count}</strong><span>initial orphan claims</span></div><div class="metric"><strong class="${c.blocking_issue_count?"blocked":"resolved"}">${c.blocking_issue_count}</strong><span>scoring blockers</span></div>`}
function renderAll(){renderGold();renderOrphans();renderStatus()}
function exportResponse(){save();const blob=new Blob([JSON.stringify(response,null,2)+"\n"],{type:"application/json"});const link=document.createElement("a");link.href=URL.createObjectURL(blob);link.download=`${task.document_id}.match-review.json`;link.click();setTimeout(()=>URL.revokeObjectURL(link.href),1000)}
function importResponse(file){const reader=new FileReader();reader.onload=()=>{try{const value=JSON.parse(reader.result);if(value.match_task_sha256!==taskHash||value.document_id!==task.document_id)throw new Error("Response is bound to another match task");response=value;localStorage.setItem(storageKey,JSON.stringify(response));$("reviewer").value=response.reviewer||"";renderAll();alert("Match review imported.")}catch(error){alert(`Import failed: ${error.message}`)}};reader.readAsText(file)}
$("documentName").textContent=task.document_id;$("reviewer").value=response.reviewer||"";$("reviewer").oninput=save;$("exportButton").onclick=exportResponse;$("importButton").onclick=()=>$("importFile").click();$("importFile").onchange=event=>event.target.files[0]&&importResponse(event.target.files[0]);renderAll();
</script></body></html>'''


def _safe_script_json(value: object) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).replace("</", "<\\/")


def render_grobid_match_review_html(
    match_task: Mapping[str, Any],
    response: Mapping[str, Any],
) -> str:
    """Render a dependency-free adjudication surface for unresolved matches."""

    validate_grobid_match_review(match_task, response)
    return (
        _MATCH_REVIEW_HTML.replace("__TASK_JSON__", _safe_script_json(match_task))
        .replace("__RESPONSE_JSON__", _safe_script_json(response))
        .replace(
            "__TASK_HASH_JSON__",
            _safe_script_json(grobid_match_task_sha256(match_task)),
        )
    )


def _rate(numerator: int, denominator: int) -> float | None:
    return round(numerator / denominator, 6) if denominator else None


def score_grobid_human_review(
    audit_task: Mapping[str, Any],
    human_review: Mapping[str, Any],
    match_task: Mapping[str, Any],
    match_review: Mapping[str, Any],
) -> dict[str, Any]:
    """Score one document only after all matching conflicts are resolved."""

    validate_grobid_match_task(audit_task, human_review, match_task)
    validate_grobid_match_review(
        match_task,
        match_review,
        require_complete=True,
        require_scoring_ready=True,
    )
    labels_by_claim = {
        item["claim_id"]: item["label"]
        for item in human_review["claim_annotations"]
    }
    claim_types = sorted({claim["claim_type"] for claim in audit_task["claims"]})
    precision_by_type = {}
    precision_correct = precision_denominator = 0
    for claim_type in claim_types:
        labels = [
            labels_by_claim[claim["claim_id"]]
            for claim in audit_task["claims"]
            if claim["claim_type"] == claim_type
        ]
        counts = Counter(labels)
        evaluated = len(labels) - counts["uncertain"]
        correct = counts["correct"]
        precision_correct += correct
        precision_denominator += evaluated
        precision_by_type[claim_type] = {
            "claim_count": len(labels),
            **{label: counts[label] for label in REVIEW_LABELS},
            "evaluated_claim_count": evaluated,
            "strict_precision": _rate(correct, evaluated),
        }
    adjudication_by_gold = {
        item["gold_unit_id"]: item for item in match_review["gold_adjudications"]
    }
    recall_by_type = {}
    recall_matched = recall_denominator = 0
    match_records = []
    for claim_type in RECALL_GOLD_TYPES:
        units = [
            item
            for item in match_task["gold_units"]
            if item["claim_type"] == claim_type
        ]
        matched = 0
        for unit in units:
            if unit["automatic_decision"] is not None:
                decision = unit["automatic_decision"]
                claim_ids = unit["automatic_claim_ids"]
                source = "deterministic"
            else:
                adjudication = adjudication_by_gold[unit["gold_unit_id"]]
                decision = adjudication["decision"]
                claim_ids = adjudication["claim_ids"]
                source = "human"
            matched += decision == "matched"
            match_records.append(
                {
                    "gold_unit_id": unit["gold_unit_id"],
                    "claim_type": claim_type,
                    "decision": decision,
                    "claim_ids": claim_ids,
                    "decision_source": source,
                }
            )
        recall_matched += matched
        recall_denominator += len(units)
        recall_by_type[claim_type] = {
            "gold_unit_count": len(units),
            "matched_gold_unit_count": matched,
            "false_negative_count": len(units) - matched,
            "strict_recall": _rate(matched, len(units)),
        }
    precision_rates = [
        item["strict_precision"]
        for item in precision_by_type.values()
        if item["strict_precision"] is not None
    ]
    recall_rates = [
        item["strict_recall"]
        for item in recall_by_type.values()
        if item["strict_recall"] is not None
    ]
    return {
        "contract_version": GROBID_SEMANTIC_SCORE_VERSION,
        "document_id": audit_task["document_id"],
        "source_sha256": audit_task["source_sha256"],
        "audit_task_sha256": grobid_audit_task_sha256(audit_task),
        "human_review_sha256": grobid_human_review_sha256(human_review),
        "match_task_sha256": grobid_match_task_sha256(match_task),
        "match_review_sha256": _sha256(match_review),
        "semantic_accuracy_measured": True,
        "scope": "single_document",
        "strict_precision": {
            "micro": _rate(precision_correct, precision_denominator),
            "document_type_macro": (
                round(sum(precision_rates) / len(precision_rates), 6)
                if precision_rates
                else None
            ),
            "by_claim_type": precision_by_type,
        },
        "strict_recall": {
            "micro": _rate(recall_matched, recall_denominator),
            "document_type_macro": (
                round(sum(recall_rates) / len(recall_rates), 6)
                if recall_rates
                else None
            ),
            "by_gold_type": recall_by_type,
        },
        "gold_matches": match_records,
    }


__all__ = [
    "BLOCKING_ORPHAN_DISPOSITIONS",
    "GROBID_MATCH_REVIEW_VERSION",
    "GROBID_MATCH_TASK_VERSION",
    "GROBID_SEMANTIC_SCORE_VERSION",
    "MATCH_DECISIONS",
    "ORPHAN_DISPOSITIONS",
    "build_grobid_match_review_template",
    "build_grobid_match_task",
    "grobid_human_review_sha256",
    "grobid_match_task_sha256",
    "render_grobid_match_review_html",
    "score_grobid_human_review",
    "validate_grobid_match_review",
    "validate_grobid_match_task",
]
