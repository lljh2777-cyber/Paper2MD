# GROBID claim↔Gold 匹配与严格评分 v0.1

## 目标

人工 claim 标签只能计算 precision；全文 Gold 枚举只能给出 recall 分母。v0.1 在两者之间
加入显式、可重算的 claim↔Gold 映射，并在守恒或标注本体存在冲突时拒绝输出严格分数。
这一阶段不修改冻结机器结果，也不把对齐率、字符覆盖率或文本相似度冒充语义正确率。

## 三个契约

- `paperwright-grobid-gold-match-task-v0.1`：绑定 audit task 与完整 human review；
- `paperwright-grobid-gold-match-review-v0.1`：只保存确定性规则无法决定的 Gold 和 orphan
  claim 裁决；
- `paperwright-grobid-semantic-score-v0.1`：只有 review 完成、无阻塞项时才可生成。

匹配任务保留每个 Gold 的候选 claim、页面、规范化相似度、Gold 字符覆盖率，以及同类型
claim 的 `correct/partial/wrong_role/unsupported/uncertain` 数量。所有输入和输出均以
SHA-256 绑定，工具拒绝覆盖已有目录或分数文件。

## 确定性规则

1. claim 必须先被人工标为 `correct`，才有资格匹配 recall Gold；
2. 同类型、页面有交集、规范化文字完全相等，且 claim 与 Gold 两侧都唯一时，自动
   `matched`；
3. 某类型没有任何人工 `correct` claim 时，该类型的 Gold 自动 `missed`；partial claim
   仍留在标签分布中供审计，但不能充当严格 true positive；
4. 多 claim 合成一个 Gold、一个 claim 可能对应多个 Gold，或存在其他歧义时，必须人工
   裁决；
5. 一个 correct claim 最多分配给一个 Gold。未分配的 correct claim 必须声明原因。

orphan disposition 中，`gold_omission`、`claim_label_error` 和 `uncertain` 会阻塞评分；
`out_of_scope` 与 `duplicate` 不阻塞，但必须写理由。这样可以区分“评审表已填完”和
“数据已经可以评分”，不会靠事后选择有利口径绕过 Gold 缺陷。

## 使用

```bash
PYTHONPATH=src .venv/bin/python tools/prepare_grobid_match_review.py \
  AUDIT_TASK.json HUMAN_REVIEW.json MATCH_REVIEW_DIR

PYTHONPATH=src .venv/bin/python tools/validate_grobid_match_review.py \
  MATCH_REVIEW_DIR/match-task.json EXPORTED.match-review.json \
  --require-complete --require-scoring-ready

PYTHONPATH=src .venv/bin/python tools/score_grobid_human_review.py \
  AUDIT_TASK.json HUMAN_REVIEW.json MATCH_REVIEW_DIR/match-task.json \
  EXPORTED.match-review.json SEMANTIC_SCORE.json
```

离线页面使用 localStorage 保存进度，并支持 task-bound JSON 导入/导出。它只展示需要人工
判断的项目；自动结果仍完整保存在 `match-task.json` 中，可由验证器从上游输入重算。

## g07 首次守恒审计

规范包位于仓库同级评估目录：

```text
paperwright-grobid-semantic-eval-v0.1/runs/baseline-ff8959f/
  human-review-gold-v0.2.1/g07-match-review-v0.1.3/
```

- manifest SHA-256：
  `d225f690b452f9b9ced8ec36c4f79a5b1a4b65d8206fdb63ae8363d4255a14c1`；
- match task SHA-256：
  `33e7c5fba18ebebaf545e1f2430179f81b6638c8b56c29a1f46573f7fef75093`；
- 49 个 Gold：17 个唯一精确匹配、30 个自动 missed、2 个需人工判断；
- 11 个初始 orphan correct claims：其中 6 个是完整摘要的分段候选；其余 5 个是
  `BACKGROUND/AIM/METHODS/RESULTS/CONCLUSION` 结构化摘要标题；
- 两个未决 Gold 是完整跨页摘要和 `REFERENCES` 标题。摘要的六 claim 聚合覆盖率为
  97.8501%；`REFERENCES` 的同页候选已经分别唯一匹配 `FOOTNOTES` 与 `CONCLUSION`，
  不能复用；
- 26 个 reference claims 全被人工标为 `partial`，所以 24 个 reference Gold 是严格
  false negative，而不是“没有任何候选证据”。

首次守恒审计暴露出 human Gold 漏列了上述五个结构化摘要标题，但相应 claims 被人工标为
正确。这是 Gold 本体冲突，不能把它们事后写成 `out_of_scope` 来强行出分。当前应在上游
Gold 中补入这五个 section-heading units，重新导出完整 human review，再重新生成 match
task。故本阶段仍保持 `semantic_accuracy_measured=false`，尚未发布 g07 strict
precision/recall。

## 指标口径

评分器通过阻塞门后才计算：

- strict precision：`correct / (correct + partial + wrong_role + unsupported)`，uncertain
  不进入分母，并同时报告 partial 等原始计数；
- strict recall：`matched Gold / complete Gold`，按六类 Gold 分别报告；
- micro 与单文档 type-macro 分开保存；
- 每个 Gold 的最终 decision、claim IDs 和 deterministic/human 来源均写入分数文件。

单篇通过只代表打通计分链，不代表 GROBID 或 PaperWright 的泛化质量；必须完成其余冻结
论文后才能汇总语料级指标。
