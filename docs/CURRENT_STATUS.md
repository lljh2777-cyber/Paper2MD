# PaperWright 当前实现状态

更新时间：2026-08-23。

## 产品边界

- 只面向 born-digital 科研论文；扫描 PDF/OCR 不是当前核心范围。
- 只发展 hybrid：L0 确定性内核是流水线基础，不再发展独立 direct 产品语义。
- AI 只处理有证据的未决判断；所有模型输出必须经过确定性契约、守恒和回放校验。
- 路由不使用模型价格、token 预算或供应商身份。

## 质量重评与当前决策

2026-08-21 对未见完整链输出进行人工可读性反查后，确认“契约完成”不等于“论文重建
质量可接受”。U02 漏掉正文 Figure、把 Table 写成数字碎片；U03 把更新提示 logo 与
citation/license 侧栏固化成 Figure-caption。继续调页级候选分类和 prompt 不能修复上游
证据缺失。

根因之一是旧 `standard` 会先生成 text-only PhysicalDocument，再用这份缺少
image/vector 的证据判断是否值得完整枚举。U02/U03 均未升级，最终缓存所有页面都只有
text。E0 已移除这条循环盲区：当前 `standard` 先对所有页枚举 image/vector bounds，再
决定哪些页需要解码图片资产。

因此当前主线暂停新增未见论文批次和视觉关系 prompt 调参，先重建粗提取层。已接受的
目标方案见 [粗提取多证据架构 v0.1](EXTRACTION_ENSEMBLE_V0.1.md)：PDFium 提供全页
原生对象清单，pdfplumber 补充独立字符/图形/表格几何，GROBID 提供科研论文语义骨架，
Docling 只处理局部冲突；各 provider 的观察、主张和最终决定严格分层。

## 已完成

1. 科研论文质量基线：13 篇、305 页，八维标注与失败分类。
2. L0 提取与投影：正文、Figure、同页 Table、独立 Equation、页眉页脚和引用处理。
3. L1 文本判断：只判断验证器允许的相邻 block 是否应 join，不重写正文。
4. L2 视觉判断：DashScope 直连桥、问题级上下文和候选关系协议。
5. L3 程序合成：受限 DSL、守恒校验、重放溯源和 L1 失败降级。
6. Completeness Gate：逐页状态、无文字非空页整页视觉保留、孤立 caption/漏投影回流。
7. Issue-level Routing：所有页面以 L0 为基础，局部问题才升级；布局后精确发现 L1。
8. Visual Candidate Relations：模型只分组/分类/排序/绑定，bbox 由候选并集确定性生成。
9. ArticleModel、Reader、manifest、evidence 和 SHA-256 绑定。
10. HybridPipeline/run contract：唯一 `paperwright hybrid` 入口、ROI 安全暂停/恢复、
    五阶段状态与最终文档包哈希复核。
11. 跨页 Figure/Table–caption：跨页 issue scope、成对页面关系任务、显式接受/拒绝和
    ArticleModel/Reader `caption-of` 投影。
12. Caption–visual 关系标注集：哈希绑定的外部数据契约、silver/gold 分级、16 个真实
    相邻页 seed 样本和确定性校验工具。
13. Hybrid run v0.2：把 resolver 拆成 evidence/layout/projection/text/verification，完成
    阶段逐产物哈希绑定；失败恢复跳过已完成阶段，投影包和文本派生包只在完整校验后复用。
14. 独立出版社 holdout：冻结 6 篇、136 页、6 个版式体系，在 `cf71d02` 首次运行后
    核实 17 个跨页假阳性；以行首锚、页顶方向证据和本页视觉优先规则修正后降为 0，
    旧 16 例 seed 回归仍为 TP=10、FP=0、FN=0、TN=6。
15. 跨页 caption 挑战集 v0.2：冻结 8 篇/171 页自然版式批次与 4 篇/71 页显式标记
    挑战集；后者含 7 个出版社明确正例和 1 个裸面板标签负例。基线 TP=7、FP=1、FN=0，
    收紧裸 `Figure 1A` 锚点后 TP=7、FP=0、FN=0，旧 seed 回归保持不变。
16. 人工 gold：Liao Li 于 2026-08-17 复核挑战集全部 8 张成对页面图，人工标签与 silver
    标签 8/8 一致、无 uncertain；保留 silver 审计输入并生成全量 `human_verified` 的
    `gold-v0.2.json`。
17. 随机 holdout v0.3：从固定的 669 篇 PMC OA 抽样框以可重放随机顺序冻结 8 篇、
    108 页、100 个相邻页对，未按出版社或正例标记换样。`23c7aad` 路由跨页候选为 0，
    全页 silver 审计真实正例也为 0；pair-level prevalence 观察值 0%，双侧 95% 上界
    3.62%，precision/recall 因零正例不可定义。本轮未修改规则。
18. 随机 holdout 人工 gold：Liao Li 于 2026-08-17 复核 8 张全页 contact sheet，结果
    全部为 `none`，与 silver 8/8 文档、100/100 相邻页标签一致，无 uncertain；形成
    `pair-audit-gold-v0.3.json`，仍未修改规则或回填结果。
19. 随机 holdout v0.4 事前协议：固定基线 `6f322ec`，复用 v0.3 的 669 篇抽样框和候选
    顺序，从位置 13 开始，按标签无关的停止规则再纳入 12 篇合格论文；资格、评估流程、
    gold 转换条件和统计边界均在查看新页面前冻结。
20. 随机 holdout v0.4 silver：按协议检查候选位置 13–37，冻结 12 篇/169 页/157 个相邻
    页对。固定基线路由 0 个跨页候选，全页审计发现 9 个 silver 正例（4 篇论文），均为
    多面板 Figure 跨两页、caption 页仍含后续面板；gold 签署前未修改规则。
21. 随机 holdout v0.4 人工 gold：Liao Li 于 2026-08-17 复核全部 12 张 contact sheet，
    确认 9 个 silver 页对并新增 V01 14–15，共 10 个 gold 正例、无 uncertain。文档二元
    判断 12/12 一致、精确页对集合 11/12 一致、相邻页标签 156/157 一致；冻结基线
    TP=0、FP=0、FN=10、TN=147。
22. 跨页面板连续性修正：v0.4 在 gold 后明确转为开发/校准集。路由仅在“前页大型
    raster Figure 到页底 + 后页页顶后续片段紧邻 caption + 前页未被本页 caption 终止”
    时覆盖本地视觉抑制，并拒绝低残余覆盖的整页装饰。v0.4 校准回放为 TP=10、FP=0、
    FN=0、TN=147；v0.3 的 100 个 gold 负页对保持 0 候选，marker challenge 保持
    TP=7、FP=0、FN=0、TN=1。paired-page prompt 升级到 v0.2。
23. 随机 holdout v0.5 事前协议：固定基线 `e94cf33`，沿原冻结候选顺序从位置 38 开始，
    按标签无关停止规则纳入 12 篇合格论文；在查看页面前固定资格、gold 定义、确定性候选
    主指标、最终 L2 分表和“正例少于 5 个不宣称泛化验收”的解释边界。
24. 随机 holdout v0.5 资格冻结：按协议检查候选位置 38–54，纳入 12 篇同行评议原始
    研究、排除 5 篇非目标文章；冻结为 158 页、146 个相邻页对、9 个期刊。资格阶段没有
    运行 PaperWright、生成页面预览或查看跨页标签。
25. 随机 holdout v0.5 silver：固定基线产生 6 个跨页候选，全页审计得到 4 个真实正例，
    TP=4、FP=2、FN=0、TN=140，候选 recall=100%、precision=66.67%、负页对误报率
    1.41%。正例少于事前指定的 5 个，只能作探索性结果；期间未修改规则。
26. 随机 holdout v0.5 人工 gold：Liao Li 于 2026-08-17 复核全部 12 张 contact sheet。
    人工与 silver 的文档二分类、精确评分页对集合和相邻页标签分别为 12/12、12/12、
    146/146 一致。H03 的 `7-9` 是三页 Figure span，按契约评分为 caption 起点边界
    `8-9`。最终基线仍为 TP=4、FP=2、FN=0、TN=140；达到点估计工程目标，但只有 4 个
    gold 正例，因此是独立但探索性的结果，不能宣称泛化验收通过。
27. 随机 holdout v0.5 固定 L2 次指标：`qwen3.7-plus`、temperature 0、paired-page
    prompt v0.2 单次运行覆盖全部 6 个冻结候选，候选内 TP=4、FP=1、FN=0、TN=1，端到端
    为 TP=4、FP=1、FN=0、TN=141。模型拒绝了不同 Figure 6/7 的误报，但仍接受只有
    `Figure 3. Cont.` 的中间边界。前置视觉布局桥在 3 篇首个候选页上均耗尽三次重试且
    被契约拒绝，因此次指标使用透明的 frozen-issue task adapter；该失败与模型语义指标
    分开报告。
28. 视觉布局桥契约加固：关系 prompt 升至 v0.2；temperature 0 重试现在携带上一次精确
    校验错误；程序只规范化 order 这类非语义结构，并对非排除候选并集执行带 warning
    的 confirmed-ROI 求交。候选遗漏、重复、语义角色与父子关系继续由严格校验器拒绝。
    该改动针对 v0.5 暴露的适配层失败族，旧 v0.5 指标与独立性声明保持不变；完整链路
    的独立验收仍需新的未见论文。
29. 未见论文 L2 完整链回归 v0.1：从冻结 PMC 顺序位置 55 起按资格纳入 3 篇/36 页，
    由 `gpt-5.6-luna` high 执行实际流程，固定 `qwen3.7-plus` 视觉模型且禁止 adapter/
    人工修补。1/3 完整通过；另两篇均在第 1 个正式 L2 页耗尽 3 次重试，错误分别是文本
    role 与 `content_class` 不一致、header/margin 未使用 `exclude`。成功文档的五阶段、
    Reader、ArticleModel、文本包、8 个 final layout 和 3 个 relation review 均独立验证
    通过。详见 [UNSEEN_L2_FULLCHAIN_V0.1](UNSEEN_L2_FULLCHAIN_V0.1.md)。
30. Role-derived 冗余字段规范化：明确 `header/footer/margin` role 确定性映射到
    `exclude`，明确文本/视觉 role 的冲突 class 分别映射到 `text`/`visual`，保留
    `unknown`；每项修正写稳定 warning。候选分组、role、caption parent、discard、
    confidence 仍不可自动修复，原始校验器也增加排除 role 的反向一致性约束。原 U01/U03
    在新目录的开发集回放均完成五阶段，28/28 final layout 与 14/14 relation review
    有效；该回放只验证已知停止点，不是独立泛化或语义质量结论。
31. PDFium 全页对象 inventory（E0）：新增不解码位图的 `extract_inventory()`；标准路径
    对每页保留 image/vector 类型与 bbox，图片明确标记 deferred，选择性升级只物化目标
    页。U02/U03 inventory 与 full 的逐页非文字对象计数一致、均无图片解码；U02 第 3、
    6、7 页的 6 个 image 已全部在标准入口可见。
32. SourceEvidenceBundle（E1）：新增 `paperwright-source-evidence-v0.1` 索引、PDFium
    provider snapshot、原始/PaperWright 双坐标、文本 fingerprint 和 observation→
    PhysicalDocument identity alignment。prepare 写入五文件哈希链，apply 重验路径、
    哈希、坐标变换、ID/引用和 alignment 覆盖；claims/conflicts 独立且首版为空。
33. pdfplumber 几何侧车（E2）：`standard/forensic` 默认保存 char/word、line/rect/curve、
    image 独立观察并与 PDFium 对齐；Table finder 只提交无 Markdown 权限的 proposed
    `table_region` claim。U02 唯一命中第 3 页已知表格，U03 为 0 个表格 claim；显式
    `fast` 不运行侧车。
34. GROBID 科研语义侧车（E3）：新增可选本地 HTTP provider、固定 TEI coordinate
    请求、离线 TEI 解析及 title/author/affiliation/abstract/section/paragraph/caption/
    reference/citation proposed claims。claim 必须有坐标 observation，TEI 文本无正文
    权限；未配置或请求失败会保存显式 `unavailable`。2026-08-22 已用 GROBID
    `0.9.0-crf` + OpenJDK 21 完成真实 HTTP 与 PaperWright `layout-prepare` 端到端实测：
    12 个 Wapiti 模型全部加载，示例论文 provider 为 `complete` 并保存 847 个
    observations。该结果只验通集成，不代表语义质量验收。
35. 局部 Docling 专家（E4）：Source Evidence v0.2 新增哈希绑定的 specialist requests 和
    `complete/degraded/conflicted` bundle 状态；确定性发现 Table 边界、reading-order、
    native/raster 三类冲突。Docling 仅在显式启用且有请求时按页运行，接入层再按 ROI 过滤，
    只保存 DoclingDocument 子集、table data、provenance 与 proposed claims，从不采用其
    Markdown。U02 只路由第 3 页已知 Table，U03 为 0 请求；当前本机未安装 Docling，
    离线 JSON 夹具已覆盖解析与溯源。
36. PaperRecipe/ArticleTree 纵向原型（E5）：prepare 写出受限
    `paperwright-paper-recipe-v0.1` 和元素守恒的 `paperwright-article-tree-v0.1`，apply
    校验输入/证据哈希并确定性重放后才投影安全动作。Recipe 不含正文或 Markdown；Tree
    每个物理元素恰有一个叶节点且 `generated_text_count=0`。U02 开发回放把第 3 页 Table
    的 487 个对象从 prose 移入图片区域，并补回第 6、7 页 4 个原生 Figure；U03 首页
    raster-only 更新 logo 被 bbox-scoped furniture action 排除，citation/license 从伪
    caption 降为 margin。模型 producer 尚未开放，这些结果也不是新 holdout 泛化结论。
37. final ArticleTree 规范上游（E6）：新增 `paperwright-article-tree-v0.2`，将最终 block、
    asset、relation 与上游结构哈希编译成 `_paperwright/article-tree.json`。Hybrid
    `layout-apply` 和 `text-package` 均先生成、验证该树，再唯一投影 ArticleModel、Markdown
    与 Reader；prepare 阶段的 v0.1 树在发布包中改称 `source-element-tree.json`，继续负责
    物理元素守恒。旧 v0.9 文本父包没有 final tree 时仍可显式兼容，但新布局包总是保存
    PhysicalDocument 哈希绑定。
38. GROBID 独立机器评估（E7）：在事前冻结的 8 篇/151 页语料上执行 native/CRF 双路径，
    7 对完整并生成 1,944 个 claims 与 7 份盲化审计任务；1 对因两分支共有的 436 个
    pdfplumber 越界字符而失败，按协议保留失败且不换样。逐类型 micro/document-macro
    alignment、字符覆盖和文本相似度加权覆盖已固化；这些指标不等于语义正确率。
39. GROBID 人工 gold 工作台：audit task 升级到 v0.2，补齐 PDFium 原生文字/bbox 和成功
    论文全部 143 页；新增无外部前端依赖的浏览器审阅器、localStorage 恢复、JSON 导入/
    导出、六类 recall gold 全文枚举及 task-bound response 完整性验证。初始空白包覆盖
    7 篇、1,944 个 claims。
40. GROBID 多页 gold 单元：人工 `g07` 暴露出 v0.1 会把跨页摘要/参考文献拆成两个 recall
    单元；response/manifest 升级到 v0.2，以一个 semantic unit 下的多个 page segments 保持
    分母守恒，并新增显式迁移/合并工具。`g07` 的 141 条标签已无损迁移并严格验证；摘要
    为 1 unit/2 segments，参考文献为 24 units/25 segments。该提交当时尚未建立
    claim↔Gold 显式匹配，后续状态见第 41 项。
41. GROBID claim↔Gold 守恒评分门与首个严格试算：新增哈希绑定的 match task/review/score
    三个契约；
    唯一规范化文字+页面交集自动匹配，无同类型 correct claim 自动 missed，其余情况由离线
    页面显式裁决；正确 claim 不得复用，Gold omission、claim label error 和 uncertain 会
    阻塞评分。`g07` 首次检查暴露五个已标 correct 的结构化摘要标题未进入 Gold；明确
    口径后保留原响应并生成修正版，得到 22 个自动匹配、30 个自动 missed 和 2 个 AI
    裁决项。review/score v0.2 显式区分 human/AI/mixed 来源；首个单文档 strict precision
    micro 为 60.28%，strict recall micro 为 42.59%，只作链路验通与失败族诊断。详见
    [GROBID_MATCH_SCORING_V0.2](GROBID_MATCH_SCORING_V0.2.md)。

## 当前主链

```text
PDF
 → PDFium 全页 object inventory + raster evidence
 → issue-routing.json
 → L0 layout
 → L2 candidate relation review（仅局部视觉 issue）
 → deterministic FinalLayout compiler
 → paired-page caption relation review（仅跨页候选）
 → final ArticleTree v0.2
 → ArticleModel + Markdown + Reader + assets
 → Completeness Gate
 → exact L1 block-pair discovery
 → L1，失败时 L3
 → resolve-issues.json（若仍有局部问题）
```

## 真实论文校准结果

- 基线：13 篇、305 页。
- A06 Completeness：原空白输出的第 31–32 页改为整页视觉保留。
- A06 issue routing：32 页均以 L0 为基础，仅 7 页需要视觉关系判断。
- A06 visual relations：6 个 Figure 页均有 caption + visual 候选，第 28 页保留 24 个复杂
  候选；真实第 8 页任务已通过关系编译与最终布局校验。
- Hybrid run v0.1 在真实论文 *Attention Is All You Need*（15 页）完成过历史离线 evidence
  检查点：发现 15 个 L2 局部 issue（覆盖 14 页），15 页关系任务共保留 160 个候选；
  `run.json` 正确停在 `confirm_content_roi`，且通过公开契约校验。该检查未调用模型。
- Caption relation seed v0.1：9 篇、16 个真实相邻页样本，含 10 正例和 6 困难负例。
  新鲜 standard evidence 校准得到 TP=10、FP=0、FN=0、TN=6；这是调参集结果，不是
  holdout 泛化结论。合成正例仍覆盖 task/review/writer/Reader 全链。
- Caption challenge v0.2：自然抽取的 8 篇/171 页未出现正例；marker-selected 的 4 篇/
  71 页含 7 个显式正例，调整后全部召回且 1 个裸面板标签误报被消除。该集合已参与修正，
  8 个样本已完成人工复核并形成 gold，但仍不能估计自然分布指标，详见
  [CAPTION_CHALLENGE_V0.2](CAPTION_CHALLENGE_V0.2.md)。
- Random holdout v0.3：随机冻结的 8 篇/108 页形成 100 个相邻页对，当前 silver 审计没有
  正例；100 个负例已人工复核并形成 gold，规则未因结果修改。它提供自然 prevalence 的
  初步上界，但不能估计候选 precision/recall，详见
  [RANDOM_HOLDOUT_V0.3](RANDOM_HOLDOUT_V0.3.md)。
- Random holdout v0.4：事前冻结后新增 12 篇/169 页/157 个相邻页对；0 个路由候选下
  人工确认 10 个 gold 漏召回，集中为“caption 页存在同一 Figure 后续面板”的系统失败族。
  规则在 gold 签署前保持冻结；转为开发/校准集后的面板连续性路由已召回 10/10，且
  没有命中其余 147 个页对。该数字不能作为独立泛化结果，详见
  [RANDOM_HOLDOUT_V0.4](RANDOM_HOLDOUT_V0.4.md)。
- Random holdout v0.5：固定基线在 12 篇/158 页/146 个相邻页对中产生 6 个候选；人工
  gold 确认 4 个正例，得到 TP=4、FP=2、FN=0、TN=140。全部人工标签与 silver 一致，
  但 review 是 silver-informed，且正例少于预注册的 5 个，故只支持探索性结论，详见
  [RANDOM_HOLDOUT_V0.5](RANDOM_HOLDOUT_V0.5.md)。固定 L2 单次判断在候选内得到
  TP=4、FP=1、FN=0、TN=1；它保留全部正例并消除一个误报，但前置视觉布局桥的契约失败
  说明当前完整生产链仍不能据此视为通过。

## 仍是兼容层的部分

- `routing.json` 的页级单标签语义；主语义已经是 `issue-routing.json`。
- 旧 visual-direct 自由画框协议；仅在没有候选时回退。
- `tools/run_routing_plan.py` 仍是默认过渡 resolver；v0.2 已把它按 layout/projection/text
  分阶段调用，但各阶段的具体执行实现尚未全部迁入核心包。
- direct CLI/manifest 仍保留兼容，但不应继续增加新能力。

## 下一阶段

冻结 v0.5 gold、原 unseen v0.1 和本次开发回放，不再使用这些样本修改路由、prompt 或
规范化规则，也暂不从位置 65 之后扩展新 holdout。按
[粗提取多证据架构 v0.1](EXTRACTION_ENSEMBLE_V0.1.md)的 E0–E5 纵向原型和
final ArticleTree v0.2 的规范上游迁移均已完成。GROBID HTTP 集成已经用真实 CRF 服务
验通，但尚未证明其 claims 正确；已冻结
[GROBID 科研语义证据评估 v0.1 协议](GROBID_SEMANTIC_EVAL_V0.1_PROTOCOL.md)及
[8 篇/151 页独立语料](GROBID_SEMANTIC_EVAL_V0.1_CORPUS.md)。语料沿既有 PMC OA 随机
顺序取位置 65–72，冻结前没有运行 PaperWright/GROBID 或查看页面标签。冻结批次现已完成
7/8 对；机器结果见
[GROBID 科研语义证据评估 v0.1 机器结果](GROBID_SEMANTIC_EVAL_V0.1_RESULTS.md)。盲化
[人工 gold 工作台 v0.2](GROBID_HUMAN_REVIEW_V0.2.md)也已生成，且首篇 `g07` 已完成。
[claim↔Gold 匹配与严格评分门](GROBID_MATCH_SCORING_V0.2.md)已经实现，`g07` Gold
本体冲突已经显式修正并完成首个严格试算。下一步继续其余 6 份 response，逐类
测量 front matter、摘要、章节、caption、引用和参考文献
的严格 precision/recall 与 ArticleTree 决策贡献。同时测量首页家具排除、Table
图片回退和原生 Figure 补全的误伤/漏召回，据此决定哪些 E5 baseline 动作可以保留、收紧
或必须回到局部 resolver。Docling 本地模型仍受可选依赖缺失限制，不能把离线适配测试
表述为真实模型质量验收。
