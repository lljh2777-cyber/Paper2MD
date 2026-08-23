# PaperWright 开发者指南

本文面向**修改 paperwright 源码、契约或桥工具的开发者**。用户流程见
[用户指南](USER_GUIDE.md)，产品定位见 [VISION](VISION.md)。

## 1. 架构分层

| 层 | 模块 | 职责 |
|---|---|---|
| L0 确定性内核 | `backends/pdfium.py`, `models.py`, `source_evidence.py`, `pdfplumber_provider.py`, `grobid_provider.py`, `specialist_routing.py`, `docling_provider.py`, `figures.py`, `content_render.py`, `region_render.py`, `writer.py` | PDFium inventory/materialization、多源侧车、局部专家请求、provider 证据快照、Figure/Table/Equation 图片化、Markdown/manifest 写出 |
| L1 文本判断 | `text_review.py`, `tools/run_text_review.py` | 只判断格式整理与 join-blocks，写 `text-review.json` |
| L2 视觉判断 | `visual_relations.py`, `cross_page_caption.py`, `layout_models.py`, `layout_review.py`, `layout_writer.py`, `tools/run_visual_review.py` | 页内候选关系 + 相邻页 caption-of，确定性编译/投影 |
| L3 程序合成 | `synthesize.py`, `tools/run_text_synthesize.py` | 受限 DSL + 守恒校验 + 重放溯源 |
| 路由/编排 | `hybrid.py`, `issue_routing.py`, `routing.py`, `auto_layout.py`, `tools/run_routing_plan.py` | Hybrid v0.2 五阶段状态机 + 局部 issue 路由；后两者为过渡执行适配层 |
| Bridge 兼容观测 | `llm_cost.py` | 保留旧 bridge usage/估算报告；不进入 Hybrid 路由、预算或 run contract |

核心原则：
- 校验器是唯一真值源；模型产物全部过 `validate-*`
- 核心不 import `openai`、不联网
- 坐标与契约可回放：PhysicalDocument v0.2、Source Evidence v0.2（兼容读 v0.1）、Article Model v0.1、Reader v0.1

## 2. 目录地图

```text
src/paperwright/      核心包（确定性逻辑）
  schemas/            JSON Schema（随包发布）
  hybrid.py           唯一 HybridPipeline API 与 run contract
tools/                仓库工具 + 可选模型桥
  run_text_review.py  L1 桥
  run_text_synthesize.py  L3 桥
  run_visual_review.py    L2 桥（直连 DashScope）
  run_routing_plan.py     路由执行器
tests/                单测；fixtures 自生成，不提交真实 PDF
docs/                 用户/开发/契约文档
skills/               4 个可分发 Agent skills
```

详细模块路由见 [PROJECT_MAP](PROJECT_MAP.md)。

## 3. 数据契约与兼容性

- 包版本与数据契约独立演进。
- 改动任何契约前先读 [契约与兼容性规则](CONTRACTS_AND_COMPATIBILITY.md)。
- 新增 manifest 版本必须有迁移文档；现有：
  - v0.4 直接转换
  - v0.5 直接转换 + region-render
  - v0.9 混合布局
  - v0.10 文本复核派生包
  - v0.11 L3 合成派生包
- 对应 schema 在 `src/paperwright/schemas/`，随包发布；修改后更新
  `tools/run_install_checks.py` 的必需 schema 清单（如新增文件）。

## 4. 如何新增一个文本操作（以 reorder 为例）

1. 在 `text_review.py`：
   - 定义操作字段与守恒校验函数
   - 在 `validate_text_review` 中接受该 op
   - 在 `apply_text_review` 中实现模型投影
2. 更新 `schemas/text_review.schema.json`
3. 更新 `docs/TEXT_REVIEW_PROTOCOL_ZH.md`
4. 若要 L3 也能产出：
   - 在 `synthesize.py` 的 `ReviewAPI` 增加 `emit_*`
   - 增加守恒校验与 AST 白名单测试
5. 加单测覆盖合法/非法/守恒破坏三种情况

## 5. 如何新增一个 L2 桥或路由信号

- 桥工具放 `tools/`，薄封装模型调用；
- 确定性逻辑放 `src/paperwright/`；
- 新路由信号在 `issue_routing.py` 中表达，必须定位到 page + bbox/element/candidate/block，
  并只用 PhysicalDocument、LayoutTask、LayoutRiskAssessment、ArticleModel 或验证结果；
- 不再增加新的页级单标签语义；`routing.py` 只维护兼容行为；
- provider 接入 HybridPipeline resolver；v0.2 的 resolver 每次只接收
  `layout/projection/text` 之一，核心在返回后验证并绑定阶段产物；
  `tools/run_routing_plan.py` 是默认过渡适配器，不能成为新的产品契约。详见
  [Hybrid run v0.2](HYBRID_RUN_V0.2.md)。

## 6. 如何跑测试与验证

```bash
# 定点单测
PYTHONPATH=src:. python -m unittest tests.test_routing -v

# 全量
PYTHONPATH=src python -m unittest discover -s tests

# 仓库检查
python tools/generate_fixtures.py --check
python -m compileall -q src tests tools
python tools/check_repo_policy.py --root .
git diff --check

# 内容冒烟（重建/布局/manifest 变更必跑）
PYTHONPATH=src:tests python tools/run_content_smoke.py

# 安装/打包（依赖/入口/发布相关）
python tools/run_install_checks.py --repo . --output-root /tmp/pw-install-check --summary /tmp/pw-install-summary.json
```

完整清单见 [VALIDATION](VALIDATION.md)。

页面级投影守恒、无文字页整页兜底及 manifest 哈希绑定见
[Completeness Gate v0.1](COMPLETENESS_GATE_V0.1.md)。
局部问题契约、两阶段发现和桥接适配见
[Issue-level Routing v0.1](ISSUE_ROUTING_V0.1.md)。
候选关系审查与最终布局编译见
[Visual Candidate Relations v0.1](VISUAL_RELATIONS_V0.1.md)。
跨页 scope、paired-page review 与 Reader 投影见
[跨页 caption 关系 v0.1](CROSS_PAGE_CAPTION_V0.1.md)。
真实关系样本的哈希绑定、silver/gold 分级与校准边界见
[Caption–visual 关系标注集 v0.1](CAPTION_RELATION_DATASET_V0.1.md)。

## 7. 仓库政策

- 禁止提交 PDF、渲染产物、真实论文输出、二进制、凭据；
- 禁止超过 5 MiB 的源码交付内容；
- `tools/check_repo_policy.py` 是防误提交，不替代正式安全扫描；
- 提交前保持工作区只含有意变更，`git status --short` 确认。

## 8. 提交与推送

- 提交信息格式：`feat:` / `fix:` / `docs:` / `test:` / `refactor:`
- 说明行为、影响文件、验证结果
- 推送前跑相关测试；不要声称只跑定向测试为“全量通过”

## 9. 当前路线图

见 [VISION](VISION.md) §7。已完成：

- L0 内核、L1/L2/L3 桥
- L3 落盘溯源与 manifest v0.11
- 表格/公式图片化第一版
- 旧 bridge usage/成本报告兼容层（非 Hybrid 核心策略）
- 确定性路由 + 自动编排 + L1→L3 降级
- issue-level routing、布局后精确 L1 发现与 Completeness 回流
- 候选关系式视觉协议与确定性 FinalLayout 编译
- 唯一 `paperwright hybrid` 入口、五阶段 run contract、ROI 暂停/恢复和逐阶段产物复核
- 跨页 Figure/Table–caption issue、paired-page review、显式拒绝与 ArticleModel/Reader 投影
- 多页 Figure panel-continuity 候选、拆分 caption 首行重建与 prompt v0.2
- SourceEvidence E0–E4、多源局部冲突路由、PaperRecipe v0.1、元素守恒 ArticleTree
  v0.1，以及 ArticleModel 的规范上游 final ArticleTree v0.2
- `paperwright.grobid_evaluation`：冻结 corpus 校验、GROBID claim 分类型证据统计和盲化
  人工 audit task；`tools/run_grobid_semantic_eval.py` 负责成对 native/CRF 采集，
  `tools/summarize_grobid_semantic_eval.py` 可从不可变 run 重算 micro/document-macro 汇总且
  拒绝覆盖；`tools/prepare_grobid_human_review.py` 生成无依赖盲审页面，
  `tools/migrate_grobid_human_review.py` 将 v0.1 单页 gold 迁移为 v0.2 多片段单元，
  `tools/validate_grobid_human_review.py` 校验 task-bound 人工 response；
  `paperwright.grobid_scoring` 确定性重算 claim↔Gold 匹配、守恒 orphan correct claims，
  `tools/prepare_grobid_match_review.py`/`validate_grobid_match_review.py` 提供离线裁决和阻塞门，
  match-review/score v0.2 显式保存 `human/ai/mixed` 裁决来源；
  `tools/score_grobid_human_review.py` 只在完整且无 Gold/标签冲突时输出 strict
  precision/recall（旧 match-review v0.1 仍可读）

未完成：

- L3 操作集扩展与规则回填
- 把默认过渡 resolver 的阶段实现逐步迁入核心包，消除脚本级编排分叉
- 用新的未见随机 holdout 验证跨页面板连续性修正
- 用新冻结论文校准 Recipe 家具/Table/Figure 决策，并扩展 final ArticleTree 的 section、
  split/merge 与正文引用表达
