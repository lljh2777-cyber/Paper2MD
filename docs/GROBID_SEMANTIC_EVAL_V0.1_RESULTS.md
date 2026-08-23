# GROBID 科研语义证据评估 v0.1：机器结果

运行日期：2026-08-22

冻结基线：`ff8959f714262bef0ac8401cff0ed9d092a1d1a2`

事前协议：[`GROBID_SEMANTIC_EVAL_V0.1_PROTOCOL.md`](GROBID_SEMANTIC_EVAL_V0.1_PROTOCOL.md)

冻结语料：[`GROBID_SEMANTIC_EVAL_V0.1_CORPUS.md`](GROBID_SEMANTIC_EVAL_V0.1_CORPUS.md)

## 运行完整性

固定 runner 在 8 篇/151 页冻结语料上完成了 native 与 GROBID `0.9.0-crf` 成对运行。
7 对完整，1 对失败；失败仍保留在分母，没有换样或重跑。7 篇成功论文共生成 1,944 个
GROBID claims 和 7 份盲化人工审计任务。

冻结输出位于仓库同级目录：

```text
paperwright-grobid-semantic-eval-v0.1/runs/baseline-ff8959f/
```

- `report.json` SHA-256：
  `3aa268d301782a7d1abffeee32e1cf27c8f1f44d4ebd045b59277e578949787f`；
- `machine-summary.json` SHA-256：
  `8b6405b9ba7864cdb7b014dbc39ea487dff9d8ce211faae83e65454f32393e75`。

`machine-summary.json` 由只读重汇总工具从既有证据包生成，不修改 `report.json`、论文输出或
审计任务。工具与原 runner 均拒绝覆盖已有结果。

## Claims 与原生证据对齐

下表只报告 7 篇完整论文。`support` 是具有 PDFium alignment 的 claim observation 比例；
`字符覆盖` 是这些 observation 的字符占比；`加权覆盖` 再乘最佳 alignment 的文本相似度。
三者都不是语义准确率。

| Claim type | 文档 | Claims | Support micro | 字符覆盖 micro | 加权覆盖 micro |
|---|---:|---:|---:|---:|---:|
| title | 7 | 7 | 93.55% | 96.38% | 26.61% |
| author | 7 | 61 | 88.52% | 90.75% | 1.98% |
| affiliation | 7 | 64 | 95.10% | 94.17% | 53.80% |
| abstract | 7 | 14 | 76.15% | 82.98% | 7.56% |
| section_heading | 7 | 187 | 99.52% | 99.97% | 64.58% |
| paragraph | 7 | 444 | 81.85% | 82.18% | 4.71% |
| inline_citation | 7 | 791 | 90.44% | 92.22% | 60.10% |
| reference | 7 | 368 | 80.99% | 80.54% | 15.07% |
| table | 3 | 8 | 12.50% | 2.58% | 1.52% |

完整 JSON 同时保存 document-macro 指标，避免大文档或高频 paragraph/reference 淹没
低频类型。当前结果支持三个工程判断：

1. 章节标题、行内引文和单位是较强的可定位语义候选，但仍须人工确认角色和边界；
2. paragraph、author、abstract 与 reference 的“找到原生位置”和“文本边界相似”差距很大，
   不能因为几何命中就取得正文事实权限；
3. GROBID table claim 的原生支撑在本批明显不足，不能作为确定性 Table 边界或 Markdown
   表格来源。

本批没有产生 Figure caption claim，因此不能据此评价 Figure caption；缺失本身将在人工
gold 枚举中体现为召回问题，不能用现有 claim 精度替代。

## 失败样本

`g06-athlete-mental-health` 的 native 与 grobid-crf 分支均以同一契约错误退出：

```text
provider observation 坐标映射非法
```

只读复现确认 PDFium 的 3,997 个 observations 均合法；pdfplumber 的 48,393 个
observations 中有 436 个字符越过页面右边界，分布在 PDF 页 2、4、6、8，每页 109 个，
最大超出约 350.54 PDF point。故障发生在两分支共享的 pdfplumber SourceEvidence
规范化阶段，不是 GROBID HTTP、TEI 或 CRF 模型失败。

按事前协议，本轮不修复后重跑。后续把该文档转为开发回归样本，设计“保留原始 bbox、
对规范 bbox 裁剪或拒绝、记录 diagnostics”的明确契约；修复后的回放不能冒充本次独立结果。

## 结论边界与下一步

当前只完成机器可计算的证据对齐审计，`semantic_accuracy_measured=false`。因此尚不能声称
GROBID 改善了 Markdown，也不能将任何 claim type 升级为确定性采用规则。

盲化人工审计工具和 7 份 task-bound 空白 response 已生成，见
[GROBID 人工 Gold 审计 v0.2](GROBID_HUMAN_REVIEW_V0.2.md)。v0.2 将跨页语义单元表示为
一个 unit 下的多个 page segments，避免错误增大 recall 分母。`g07` 已完成逐 claim 标注和
全文 gold 枚举，其余 6 篇尚待处理。claim↔Gold 的确定性匹配、人工裁决和严格评分门已经
实现，见 [`GROBID_MATCH_SCORING_V0.1.md`](GROBID_MATCH_SCORING_V0.1.md)。`g07`
重算得到 17 个自动匹配、30 个自动 missed 和 2 个需人工判断的 Gold；同时发现 Gold 漏列
五个已标 correct 的结构化摘要标题。该本体冲突按契约阻塞评分，所以本报告仍维持
`semantic_accuracy_measured=false`。修复并重新签署上游 Gold 后，才能发布 strict
precision/recall，再决定哪些 GROBID claims 只用于路由、哪些能进入受限 Recipe 动作。
