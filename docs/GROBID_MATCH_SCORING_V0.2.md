# GROBID claim↔Gold 匹配与严格评分 v0.2

## 目标

人工 claim 标签只能计算 precision；全文 Gold 枚举只能给出 recall 分母。本模块在两者之间
加入显式、可重算的 claim↔Gold 映射，并在守恒或标注本体存在冲突时拒绝输出严格分数。
它不把对齐率、字符覆盖率或文本相似度冒充语义正确率。

## 契约

- `paperwright-grobid-gold-match-task-v0.1`：绑定 audit task 与完整 human review；
- `paperwright-grobid-gold-match-review-v0.2`：保存确定性规则无法决定的 Gold 和 orphan
  claim 裁决，并显式记录 `adjudication_kind=human|ai|mixed`；
- `paperwright-grobid-semantic-score-v0.2`：只有 review 完成、无阻塞项时才可生成，并把
  deterministic 与 human/AI/mixed adjudication 分开记录。

v0.2 修复了 v0.1 将所有裁决笼统写成 `decision_source=human` 的溯源歧义；验证器仍兼容
旧 v0.1 response，并按其原始语义解释为 human。匹配任务本身未改变。

匹配任务保留每个 Gold 的候选 claim、页面、规范化相似度、Gold 字符覆盖率，以及同类型
claim 的 `correct/partial/wrong_role/unsupported/uncertain` 数量。所有输入和输出均以
SHA-256 绑定，工具拒绝覆盖已有目录或分数文件。

## 确定性规则

1. claim 必须先被人工标为 `correct`，才有资格匹配 recall Gold；
2. 同类型、页面有交集、规范化文字完全相等，且 claim 与 Gold 两侧都唯一时，自动
   `matched`；
3. 某类型没有任何人工 `correct` claim 时，该类型的 Gold 自动 `missed`；partial claim
   仍留在标签分布中供审计，但不能充当严格 true positive；
4. 多 claim 合成一个 Gold、一个 claim 可能对应多个 Gold，或存在其他歧义时，必须裁决；
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

离线页面使用 localStorage 保存进度，并支持 task-bound JSON 导入/导出。页面生成的模板默认
是 `adjudication_kind=human`；程序或混合裁决必须在响应中如实改为 `ai` 或 `mixed`。

## g07 Gold 修正

首次守恒审计发现，`BACKGROUND/AIM/METHODS/RESULTS/CONCLUSION` 五个结构化摘要标题的
GROBID claims 已被人工标为 correct，但没有进入 section-heading Gold。Liao Li 于
2026-08-23 明确确认结构化摘要小标题应计入 section heading。原始响应保持不变，修正版为：

```text
human-review-gold-v0.2.1/
  g07-diabetic-sudden-deafness.human-review.gold-fixed-v0.2.json
```

修正版 SHA-256：
`54c6c8f6186b94ff9769dd5d99a472e38007ef0ea0c0d73e7954a8772e89488e`。
五个新增单元都带有确认 note；修正后 54 个 Gold 中有 22 个唯一精确匹配、30 个自动
missed、2 个需裁决，初始 orphan correct claims 从 11 降为 6。

## g07 首个严格分数

规范输出位于仓库同级评估目录：

```text
paperwright-grobid-semantic-eval-v0.1/runs/baseline-ff8959f/
  human-review-gold-v0.2.1/g07-match-review-v0.2.0/
```

- package manifest SHA-256：
  `70e35b2c3e312e921bb5410bb6bb5319f5d7350b0400644f37a4d75d76403086`；
- match task SHA-256：
  `e7aa81399199dae871791ab98760c2a787eb3e65644446942761d1ae55d87470`；
- AI adjudication response SHA-256：
  `8de8ba9495d203c34a3fd036c715d6ff60ad153c51d03fc5b78069dfad5c01a9`；
- semantic score SHA-256：
  `64420e3af9ce21d206b3015283143410c405f97fafce24106336125e56169b58`。

两项非确定性裁决透明记录为 `adjudication_kind=ai`：六个 human-correct abstract claims
共同匹配一个跨页 abstract Gold；没有 correct claim 对应 `REFERENCES` 标题，因此它是
section-heading false negative。最终无阻塞，单文档 score 才写
`semantic_accuracy_measured=true`。

### Strict precision

| Claim type | Correct / evaluated | Precision |
|---|---:|---:|
| title | 0 / 1 | 0.00% |
| author | 2 / 2 | 100.00% |
| affiliation | 0 / 4 | 0.00% |
| abstract | 6 / 6 | 100.00% |
| section_heading | 22 / 29 | 75.86% |
| paragraph | 34 / 42 | 80.95% |
| inline_citation | 21 / 31 | 67.74% |
| reference | 0 / 26 | 0.00% |
| **Micro** | **85 / 141** | **60.28%** |

单文档 type-macro precision 为 53.07%。`partial` 严格按错误计入分母，uncertain 才排除。

### Strict recall

| Gold type | Matched / Gold | Recall |
|---|---:|---:|
| title | 0 / 1 | 0.00% |
| abstract | 1 / 1 | 100.00% |
| section_heading | 22 / 23 | 95.65% |
| figure_caption | 0 / 2 | 0.00% |
| table_caption | 0 / 3 | 0.00% |
| reference | 0 / 24 | 0.00% |
| **Micro** | **23 / 54** | **42.59%** |

单文档 type-macro recall 为 32.61%。结果说明这一篇中 GROBID CRF 对摘要和章节骨架有用，
但不能独立承担题名、caption、参考文献完整单元；paragraph 与 inline citation 的 precision
也不足以取得正文事实权限。

这是首篇、且 claim↔Gold 的两个组合判断由 AI 裁决，只能作为链路打通和失败族诊断，不能
代表七篇冻结语料或 GROBID 的泛化质量。其余六篇必须继续独立人工 Gold 标注，并分别公开
裁决来源，之后才能汇总 corpus-level 指标。
