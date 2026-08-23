# Project map

Read the actual source before editing; this map only routes investigation.

| Area | Primary modules | Primary tests |
|---|---|---|
| CLI and orchestration | `src/paperwright/cli.py`, `api.py`, `hybrid.py`, `batch.py` | `test_cli.py`, `test_hybrid_pipeline.py`, `test_routing_plan.py`, `test_paths_api.py`, `test_phase5_alpha.py` |
| Physical model and PDFium | `models.py`, `backends/base.py`, `backends/pdfium.py` | `test_models.py`, `test_pdfium_degenerate.py`, `test_mvp_pipeline.py` |
| Source evidence and provider alignment | `source_evidence.py`, `pdfplumber_provider.py`, `grobid_provider.py`, `specialist_routing.py`, `docling_provider.py`, `schemas/source_evidence.schema.json` | `test_source_evidence.py`, `test_grobid_provider.py`, `test_specialist_routing.py`, `test_docling_provider.py`, `test_layout_stage_d.py` |
| GROBID evaluation and human Gold | `grobid_evaluation.py`, `grobid_human_review.py`, `grobid_scoring.py`, `tools/*grobid*` | `test_grobid_evaluation.py`, `test_grobid_human_review.py`, `test_grobid_scoring.py` |
| Paper-level decisions and structural compilation | `paper_recipe.py`, `article_tree.py`, `schemas/paper_recipe.schema.json`, `schemas/article_tree.schema.json`, `schemas/final_article_tree.schema.json` | `test_paper_recipe.py`, `test_reader.py`, `test_layout_stage_d.py`, `test_text_package.py` |
| Direct reconstruction | `text_reconstruction.py`, `figures.py`, `region_render.py`, `content_render.py`, `writer.py` | `test_text_reconstruction.py`, `test_phase3_figures.py`, `test_phase4_region_render.py`, `test_content_render.py` |
| Hybrid candidate generation | `layout_roi.py`, `layout_candidates.py`, `layout_candidate_features.py`, `raster_layout.py`, `layout_risk.py`, `layout_export.py` | `test_layout_stage_a.py`, `test_layout_stage_b.py`, `test_layout_risk.py`, `test_raster_layout.py` |
| Routing | `issue_routing.py`, `routing.py`, `auto_layout.py`, `tools/run_routing_plan.py` | `test_routing.py`, `test_routing_plan.py` |
| Review and layout application | `layout_models.py`, `layout_review.py`, `layout_writer.py`, `layout_caption.py`, `cross_page_caption.py`, `layout_continuation.py` | `test_layout_stage_c.py`, `test_layout_stage_d.py`, `test_cross_page_caption.py`, `test_realworld_text_rules.py` |
| Evidence and quality | `manifest.py`, `evidence.py`, `quality.py`, `layout_dataset.py`, `relation_dataset.py` | `test_manifest.py`, `test_evidence.py`, `test_quality.py`, `test_relation_dataset.py`, `test_layout_stage_f.py` |
| Reader and text review | `reader.py`, `reader_contract.py`, `article_model.py`, `text_review.py` | `test_reader.py`, `test_text_review.py` |
| L3 synthesis bridge | `synthesize.py`, `tools/run_text_synthesize.py` | `test_synthesize.py` |
| LLM cost accounting | `llm_cost.py`, `tools/run_*` bridges | `test_llm_cost.py` |
| Public onboarding | `README.md`, `docs/`, `pyproject.toml` | `test_public_onboarding.py` |

The `schemas/` directory contains shipped JSON schemas. `config/defaults.json` is the built-in configuration source. `tools/` contains repository validation/packaging checks and the optional
model bridges (`run_text_review.py`, `run_text_synthesize.py`); their
deterministic logic lives in `src/paperwright/`.
