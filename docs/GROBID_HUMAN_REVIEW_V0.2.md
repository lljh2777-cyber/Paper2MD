# GROBID 人工 Gold 审计 v0.2

## 修复目标

v0.1 把一个 gold unit 固定为单页记录。实际标注 `g07` 时，跨页摘要和跨页参考文献只能被
拆成两个单元，会错误增大 recall 分母。v0.2 将**语义单元**与**页内片段**分开：

```text
gold unit
  ├─ segment: page 8 continuation start
  └─ segment: page 9 continuation end
```

一个 unit 表示一个 title、abstract、section heading、Figure/Table caption 或 reference；
`segments` 表示该单元在一页或多页上的可见片段。bbox 仍可为空。

## 契约

- audit task：`paperwright-grobid-claim-audit-task-v0.2`；
- response：`paperwright-grobid-human-review-v0.2`；
- manifest：`paperwright-grobid-human-review-manifest-v0.2`。

验证器要求每个 unit 至少含一个 segment，并逐片段检查 page index、非空文字及可选 bbox。
response 仍与 task SHA-256、document ID、PDF SHA-256 和完整 claim 顺序绑定。

## 标注方式

在 `Gold units` 中：

1. 首次遇到一个语义单元时选择 `New semantic unit`，填写当前页可见文字并添加片段；
2. 同一单元延续到另一页时，在 `Attach to` 选择已有 unit，再添加下一页片段；
3. 如果旧版中已经拆成相邻单元，使用 `Merge into previous` 合并；
4. 修改后重新将该 gold type 标记为 `Complete`；
5. 每次会话结束导出 JSON。

Claim 标签口径没有变化。`Reviewer` 仍是整篇论文级字段，只填写一次。

## v0.1 迁移

迁移器拒绝覆盖输出，也不会自行猜测哪些单元应合并：

```bash
PYTHONPATH=src .venv/bin/python tools/migrate_grobid_human_review.py \
  TASK.json LEGACY_RESPONSE.json RESPONSE.v0.2.json \
  --merge-gold 'SOURCE_UNIT_ID=TARGET_UNIT_ID' \
  --require-complete
```

每个 v0.1 unit 会先无损变成一个含单 segment 的 v0.2 unit；只有显式 `--merge-gold` 的
source 才会并入 target。原响应保持不变。

## 本批规范产物

新入口为：

```text
paperwright-grobid-semantic-eval-v0.1/runs/baseline-ff8959f/
  human-review-gold-v0.2.1/index.html
```

它覆盖 7 篇成功论文、143 页和 1,944 个 claims。`manifest.json` SHA-256：
`f872ff78b395c370a5ba169b51d1725ad9c5f0d6efd5bd009cbaa93415a8d3a2`。

已完成的 `g07` 在新目录中保留为：

```text
g07-diabetic-sudden-deafness.human-review.json
```

其 141 条 claim 和六类 gold 均通过严格验证；摘要为 1 个语义单元/2 个页片段，参考文献为
24 个语义单元/25 个页片段。v0.1 原始人工响应继续保留，作为不可覆盖的原始记录。
同级 `human-review-gold-v0.2` 是浏览器 QA 迭代，不是后续标注入口。

## 后续匹配审计

当前只有 `g07` 完成人工标注。v0.2 修复了 recall 分母的跨页守恒；后续的可审计
claim↔Gold 匹配和严格评分门见
[`GROBID_MATCH_SCORING_V0.2.md`](GROBID_MATCH_SCORING_V0.2.md)。首次守恒审计发现
`g07` 的 Gold 漏列五个已被标为 correct 的结构化摘要标题；在明确确认它们属于
section-heading Gold 后，原响应保持不变，修正版另行保存并完成首个严格试算。
