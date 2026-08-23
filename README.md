# paperwright

paperwright 是一个本地优先、可追溯的 Hybrid 科研 PDF 重建工具。当前版本为
`0.9.0a0` 源码 Alpha。

> **包名与命令**：发布到 PyPI 的发行包名为 **`paperwright`**（`pip install
> paperwright`），但 CLI 命令与 Python 导入仍为 **`paperwright`**。两者均指向
> 同一个官方项目，安装 `paperwright` 后即可使用 `paperwright` 命令。

```text
PDF → evidence → issue routing → L0 + 局部 L1/L2/L3 → validation
    → article-tree.json → article-model.json
    → article.md + reader.json + assets + manifest.json
```

## 当前能力

- PDFium 主后端；
- 标题、段落与基础双栏阅读顺序；
- 跨页重复页眉/页脚/页码自动剔除（`--furniture`，默认 auto）；
- 原生图片、Figure/Caption 分组与保守 region-render；
- 表格无法可靠结构化时明确标记 `degraded`；
- 单文件与确定性批量转换；
- manifest、batch summary、路径安全及原子输出；
- Content ROI、布局候选、结构化复核和最终布局校验；
- `fast`、`standard`、`forensic` 三种布局提取配置；
- 自包含证据包、输出质量报告和无正文训练数据导出；
- 页面完整性门禁：无文字非空页自动保留整页图，孤立 caption/疑似漏图显式降级；
- 面向阅读器的稳定 Markdown 锚点、Figure/图注关系和 `reader.json`；
- 作为规范结构上游的最终 `article-tree.json`，并从它唯一投影
  `article-model.json`、Markdown 和 Reader；
- 受限 `paper-recipe.json`、元素守恒 source-element tree 与确定性重放；
- 确定性内核完全本地运行；Hybrid resolver 按问题接入文本/视觉模型，模型
  **只做受限判断、不转写正文**（产品定位见
  [VISION](docs/VISION.md)）。

region-render 默认关闭，只能显式启用。PDFBox 目前仅保留接口，选择后会明确
报告不可用，不会伪造转换结果。

## 快速安装（推荐）

两种官方安装路径，按场景选择：

**① 只想要 CLI（无需 skills / 无需改代码）** —— 直接从 PyPI 安装：

```bash
pip install paperwright
paperwright --version
```

适合把 `paperwright` 当作转换工具使用、不需要 Agent skills 或源码开发的环境。
如果目标索引尚未收录该 Alpha 版本，请使用下方源码安装路径。
如果下载依赖缓慢，可加 `-i` 指定 PyPI 镜像。

**② 想要完整体验（Agent skills + 自动环境）** —— Linux / macOS 引导安装器
（自动检测 agent harness、安装 Python、复制 4 个 skills）：

```bash
curl -fsSL https://raw.githubusercontent.com/lljh2777-cyber/paperwright/main/install.sh | bash
```

引导安装器会自动：检测当前 agent harness（Claude Code / Codex / Cursor / Gemini
CLI）→ 选择 3.10–3.13 Python（必要时用 uv 自动安装）→ 克隆源码到 `~/.paperwright`
→ 创建隔离虚拟环境 → 安装 CLI 并加入 PATH → 复制 4 个 Agent skills 到 harness
的 skills 目录 → 验证。

子命令与选项：

```bash
bash install.sh update          # 更新源码与依赖
bash install.sh verify          # 校验 CLI 与 skills
bash install.sh uninstall       # 卸载 skills/venv/符号链接
bash install.sh install --harness codex --no-skills   # 指定 harness / 只装 CLI
bash install.sh install --local /path/to/checkout     # 使用本地源码
bash install.sh install --local /path/to/checkout --editable  # 可编辑安装：源码改动即时生效（贡献者推荐）
bash install.sh install --with-vision    # 额外配置 qwen-mm-plugins 视觉 MCP（vision_chat/ocr 等，供 paperwright-vision-qwen 使用）
bash install.sh install --with-vision --yes --local /path/to/checkout --editable   # 可编辑 + 视觉 MCP 一键（贡献者推荐）
```

Windows 用户请使用下方 PowerShell 手动安装流程。

## 手动安装（Windows PowerShell / 无网络一键安装）

## 开始之前

需要：

- 64 位 Python 3.10–3.13；
- Git，或者从 GitHub 下载并解压源码 ZIP；
- 首次安装时能够访问 Python Package Index，以取得锁定依赖；
- born-digital（本身含文字层）的 PDF。

Windows 11 / Python 3.11.2、Linux / Python 3.12 和 Python 3.13 已实测。
macOS、Windows ARM 和 Linux ARM 尚未验证。

## Windows PowerShell 安装

最快路径（不克隆源码）：

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install paperwright

paperwright --version
paperwright --help
```

需要源码或 skills 时再克隆安装：

```powershell
git clone https://github.com/lljh2777-cyber/paperwright.git
cd paperwright

py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install .

paperwright --version
paperwright --help
```

如果没有 Git，可在 GitHub 页面选择 **Code → Download ZIP**，解压后在包含
`pyproject.toml` 的目录打开 PowerShell，再从创建虚拟环境开始执行。

## Linux 安装

某些 Linux 发行版需要先通过系统包管理器安装 `python3-venv` 和
`python3-pip`。

不克隆源码时直接安装发行包：

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install paperwright

paperwright --version
paperwright --help
```

克隆源码手动安装：

```bash
git clone https://github.com/lljh2777-cyber/paperwright.git
cd paperwright

python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install .

paperwright --version
paperwright --help
```

两种方式都会根据 `pyproject.toml` 自动安装
`pypdfium2==5.11.0`、`Pillow==12.2.0` 和 `pdfplumber==0.11.10`，无需提前手动安装。

## 转换单篇科研论文（推荐）

```bash
paperwright hybrid input.pdf output-dir
```

若命令返回 `awaiting_input`，按 `next_action.path` 检查 Content ROI，复制为单独的
确认文件后恢复：

```bash
cp output-dir.paperwright-run/layout-proposal/content-roi.json confirmed-roi.json
# 将 confirmed-roi.json 的 review_status 改为 confirmed，并填写 reviewer
paperwright hybrid input.pdf output-dir \
  --resume --content-roi-json confirmed-roi.json
```

`output-dir.paperwright-run/run.json` 记录阶段、输入/产物哈希、未决动作和失败信息；
不承担 token 预算或费用计算。完整契约见
[HybridPipeline 与 run contract v0.2](docs/HYBRID_RUN_V0.2.md)。

## 旧规则入口（兼容）

```bash
paperwright convert input.pdf output-dir
```

Windows 示例：

```powershell
paperwright convert "C:\Papers\example.pdf" "C:\Papers\example-output"
```

输出目录包含：

```text
output-dir/
├── article.md
├── physical_document.json
├── manifest.json
├── _paperwright/
│   └── completeness-report.json
└── images/
```

输出目录必须尚不存在，paperwright 不会覆盖已有数据。

Hybrid evidence 阶段会生成 `issue-routing.json`：所有页面以 L0 为基础，只把明确的
Figure-caption 绑定、复杂几何、段落续接或证据缺失问题升级到 L1/L2/L3/人工。
旧 `routing.json` 与下列脚本继续作为迁移期兼容产物；新用户应使用 `paperwright hybrid`：
`PYTHONPATH=src python tools/run_routing_plan.py input.pdf review-dir out-dir`
自动执行问题级路由计划。详见
[Issue-level Routing v0.1](docs/ISSUE_ROUTING_V0.1.md)。

L2 默认优先使用候选关系协议：模型只分组候选、判断角色/顺序并建立 caption-of 关系，
最终 bbox 由程序取候选并集生成；无候选时才回退旧画框协议。详见
[Visual Candidate Relations v0.1](docs/VISUAL_RELATIONS_V0.1.md)。当前整体状态见
[CURRENT_STATUS](docs/CURRENT_STATUS.md)。

相邻页的 Figure/Table–caption 关系使用独立的 paired-page task：同一个 issue 会把
视觉页和 caption 页一起送入 L2，接受或拒绝结果进入 ArticleModel/Reader，并覆盖旧
几何猜测。详见 [跨页 caption 关系 v0.1](docs/CROSS_PAGE_CAPTION_V0.1.md)。

关系规则使用仓库外的真实论文标注集校准。标注契约只保存源文件/页面哈希、短 caption
锚点、结构标签和审阅来源，不把 PDF、页面图或正文提交到仓库；`silver` 与人工确认的
`gold` 严格区分。详见
[Caption–visual 关系标注集 v0.1](docs/CAPTION_RELATION_DATASET_V0.1.md)。
首个跨 PLOS、eLife、BMC、Frontiers、Scientific Reports 和 MDPI 的独立基线及规则修正
记录见 [独立出版社 Holdout v0.1](docs/HOLDOUT_V0.1.md)。
后续又冻结 8 篇/171 页自然版式批次，并建立含 7 个出版社显式跨页正例的 marker-selected
挑战集；8 个样本已于 2026-08-17 完成人工复核并形成 gold。抽样边界、基线混淆矩阵和
裸面板标签修正见
[跨页 Caption 挑战集 v0.2](docs/CAPTION_CHALLENGE_V0.2.md)。
首个不按出版社或正例标记选样的随机 holdout 冻结 8 篇/108 页/100 个相邻页对；其
100 个负例已于 2026-08-17 完成人工签署。可重放抽样、零正例统计边界和 gold 记录见
[随机跨页 Caption Holdout v0.3](docs/RANDOM_HOLDOUT_V0.3.md)。
下一批按事前协议沿同一候选顺序再纳入 12 篇/169 页；固定基线路由 0 个跨页候选，
人工复核最终确认 10 个自然正例，均属于“多面板 Figure 跨页且 caption 页仍有后续
面板”的漏召回族；基线 TP=0、FP=0、FN=10、TN=147，现已形成 gold。gold 冻结后该批
明确转为开发/校准集；新增面板连续性证据在本批回放为 TP=10、FP=0、FN=0、TN=147，
仍需新的未见 holdout 验证。见
[随机跨页 Caption Holdout v0.4](docs/RANDOM_HOLDOUT_V0.4.md)及其
[事前协议](docs/RANDOM_HOLDOUT_V0.4_PROTOCOL.md)。
新的未见批次已在查看候选页面前固定基线 `e94cf33`，从冻结候选顺序位置 38 开始按
标签无关停止规则纳入 12 篇；确定性候选与最终 L2 判断分开评估。见
[随机跨页 Caption Holdout v0.5 协议](docs/RANDOM_HOLDOUT_V0.5_PROTOCOL.md)。
该批冻结为 12 篇/158 页/146 个相邻页对；人工复核与 silver 的 146 个页对标签完全一致，
现已形成 gold。固定基线为 TP=4、FP=2、FN=0、TN=140；因只有 4 个正例，结果按事前
协议仍属独立但探索性，不能宣称泛化验收通过。固定 `qwen3.7-plus` 与 paired-page
prompt v0.2 的单次 L2 次指标为候选内 TP=4、FP=1、FN=0、TN=1：消除一个不同 Figure
编号误报，但保留一个中间 continuation marker 误报。见
[随机跨页 Caption Holdout v0.5](docs/RANDOM_HOLDOUT_V0.5.md)。
页面级 L2 桥加固后的首批未见完整链回归按冻结顺序纳入 3 篇/36 页，由
`gpt-5.6-luna` high 代理执行且禁止 task adapter 或人工修补；1 篇五阶段完成，2 篇因
视觉模型输出的 role/content-class 契约冲突在首个 L2 页停止。见
[未见论文 L2 完整生产链回归 v0.1](docs/UNSEEN_L2_FULLCHAIN_V0.1.md)。
随后加入只修正明确 role 与冗余 class/order 自相矛盾的确定性规范化；原失败两篇在新的
开发集 run/output 根中均完成五阶段，28/28 final layout 与 14/14 relation review 有效。
该回放不是新的未见评估，也不证明 role 判断或最终 Markdown 的语义质量。

## 页眉页脚剔除（--furniture）

默认 `auto`：自动检测并剔除跨页重复的页眉、页脚和页码（出现在 ≥45% 页面、
坐标一致的内容，或页面极边缘的全数字短行）。剔除只影响 Markdown 输出，
`physical_document.json` 中保留完整溯源（`markdown_excluded_reason`）。

```bash
paperwright convert input.pdf output-dir                      # 默认 auto
paperwright convert input.pdf output-dir --furniture keep     # 保留全部页眉页脚
paperwright convert input.pdf output-dir --furniture strip    # 追加剔除边缘短行（更激进）
```

`auto` 是保守策略：只剔除高置信的重复家具，正文不会受影响。无法通过重复
检测判定的单页横幅（如期刊分类标签）会保留。

## 批量转换

```bash
paperwright batch output-root --input-dir pdf-directory --continue-on-error
```

`--input-dir` 只读取该目录第一层的 PDF，不递归扫描。每篇论文会写入独立
子目录，并额外生成 `batch_summary.json`。

## 启用保守 region-render

默认关闭。需要时显式启用：

```bash
paperwright convert input.pdf output-dir --region-render-mode auto
```

该模式用于补充部分混合位图/矢量 Figure；启用后还会保守识别并图片化同页表格与
独立公式（渲染失败自动保留原生文字），行内公式不受影响，但可能保守漏检。

## 混合布局复核

复杂双栏、跨栏 Figure/Table 或页面附属内容较多时，可以使用显式复核流程：

```bash
paperwright layout-prepare input.pdf roi-review --extraction-profile fast
paperwright layout-prepare input.pdf layout-review \
  --content-roi-json roi-review/content-roi.json \
  --review-mode visual-direct
paperwright validate-final-layout layout-review/page-0001/final-layout.json \
  --task layout-review/page-0001/layout-task.json
paperwright layout-apply input.pdf layout-review output-dir --evidence standard
```

第一步生成 Content ROI 提案；确认 ROI 后，第二步生成原页预览和复核说明。
`visual-direct` 是默认审核模式：人工或视觉 AI 以干净的 `page.png` 为准，直接绘制
最终正文、Figure/Table、caption 和页眉页脚区块；审核任务不包含规则候选坐标。
`content-roi.png` 只显示一个粗粒度有效内容框。非排除区块必须位于已确认 ROI 内，
paperwright 在回接原始 PDF 元素时也会过滤 ROI 外围内容，避免页眉、页脚和页码中断正文。
ROI 必须包含标题、作者、脚注、Figure/Table 和 caption；提案过窄时应先修正并重新确认。
旧的 `visual-direct` 审核包若没有 `metadata.analysis_roi`，必须重新运行 `layout-prepare`，
不会在 `layout-apply` 时静默放宽或迁移边界。
旧的规则叠加流程可通过 `--review-mode candidate-assisted` 显式启用。审核者只填写
结构化 `final-layout.json`，不转录论文正文。paperwright 随后
重新校验输入、缓存、栅格证据、审核任务完整性和最终区块关系，再确定性生成结果。

混合布局输出的正文包含 `pwwd:block` / `pwwd:slot` 隐藏锚点，
`_paperwright/reader.json` 通过稳定 ID 连接正文块、视觉槽位、图片和图注。阅读器
应以该文件为主索引，不依赖 Markdown 行号、标题 slug 或图注文本匹配。可独立验包：

```bash
paperwright validate-reader output-dir/_paperwright/reader.json
```

`_paperwright/article-model.json` 是复核文章的规范语义模型，保存相同的稳定 ID、
source span、块顺序、Markdown 内容、视觉资产和关系。`article.md` 与
`reader.json` 都由它确定性投影；可同时检查三者及图片资产是否一致：

```bash
paperwright validate-article-model output-dir/_paperwright/article-model.json
```

如需把规范文章交给纯文本模型做受约束整理，先生成不含页面图像、资产清单和
source span 的文本任务，再校验结构化修改并输出一个新的 Article Model：

```bash
paperwright text-prepare output-dir/_paperwright/article-model.json text-task.json
paperwright validate-text-review text-review.json --task text-task.json
paperwright text-apply output-dir/_paperwright/article-model.json text-task.json \
  text-review.json article-model.reviewed.json
paperwright text-package output-dir text-task.json text-review.json reviewed-output-dir
paperwright text-package output-dir text-task.json text-review.json reviewed-output-dir \
  --synthesis-run synthesize-run.json   # L3 程序合成溯源，可选
paperwright validate-text-package reviewed-output-dir
```

`text-apply` 适合只检查新 Article Model；`text-package` 会保留源 v0.9 包不变，
原子写出一个完整的 manifest v0.10 派生包（提供 `--synthesis-run` 时写
manifest v0.11，并绑定脚本重放哈希链），并重新生成 `article.md`、
`reader.json`、Article Model、验证报告及 task/review 哈希链。

文本任务和复核分别使用 v0.2 契约并绑定源 PDF、Article Model 与任务哈希。
允许不改变规范化可见文字的 Markdown 格式整理、严格的断行去连字符，以及
`join-blocks` 跨块段落拼接（纯拼接，由校验器重算并强制：同页、阅读顺序相邻、
同 body 类型、前块不以句末标点结尾、后块以小写开头；重叠块、视觉槽位、参与
Figure/Caption 关系的块会被拒绝）。模型只负责识别与声明"同一段"，不改写文本。
视觉槽位、稳定 ID、source span、资产和关系在拼接中保持；尾部块被移除（物理层
仍可溯源）。`text-apply` 不覆盖原文件，只写出新的规范模型；完整说明见
[文本复核协议](docs/TEXT_REVIEW_PROTOCOL_ZH.md)。

`fast` 使用原生文字坐标和低分辨率栅格证据；`standard` 先在所有页盘点原生
image/vector bounds，再只对高风险页面解码图片资产；`forensic` 对全文执行完整对象
遍历并物化图片。

## 找不到 `paperwright` 命令

确认虚拟环境已激活，或直接使用：

```bash
python -m paperwright --help
python -m paperwright convert input.pdf output-dir
```

关闭终端后，需要重新激活 `.venv`。

## 更多文档

混合布局流程的最终结果采用自包含文档包：顶层只放 `article.md` 和
`images/`，ROI、布局覆盖图、追溯数据与验证报告统一放入 `_paperwright/`。
`_paperwright/article-tree.json`、`_paperwright/article-model.json` 和
`_paperwright/reader.json` 属于所有证据级别都会保留的功能索引，不是调试证据。
`layout-apply` 默认使用 `--evidence standard`；也可选择 `minimal` 或
`full`，并通过 `--include-source-pdf` 显式复制原 PDF。完整结构与命令见
[混合布局设计](docs/HYBRID_LAYOUT_OUTLINE_ZH.md)。

标准与完整证据包会自动检查 Markdown 断词、重复词、短碎片、疑似图内标签、
标题完整性、图片链接、manifest 清单，以及布局对象是否遗漏或重复归属。
启发式文本问题标为 `warning`，不会阻断输出；确定性结构检查单独给出
`PASS/FAIL`。

- [用户指南](docs/USER_GUIDE.md)
- [开发者指南](docs/DEVELOPER_GUIDE.md)
- [产品愿景与架构](docs/VISION.md)
- [Alpha 快速开始](docs/QUICKSTART_ALPHA.md)
- [配置参考](docs/CONFIGURATION.md)
- [GROBID CRF 本地侧车](docs/GROBID_LOCAL.md)
- [GROBID 科研语义证据评估 v0.1 协议](docs/GROBID_SEMANTIC_EVAL_V0.1_PROTOCOL.md)
- [GROBID 科研语义证据评估 v0.1 冻结语料](docs/GROBID_SEMANTIC_EVAL_V0.1_CORPUS.md)
- [GROBID 科研语义证据评估 v0.1 机器结果](docs/GROBID_SEMANTIC_EVAL_V0.1_RESULTS.md)
- [GROBID 人工 Gold 审计 v0.2](docs/GROBID_HUMAN_REVIEW_V0.2.md)
- [GROBID claim↔Gold 匹配与严格评分 v0.2](docs/GROBID_MATCH_SCORING_V0.2.md)
- [架构](docs/ARCHITECTURE.md)
- [粗提取多证据架构 v0.1](docs/EXTRACTION_ENSEMBLE_V0.1.md)
- [PaperRecipe 与 ArticleTree v0.1](docs/PAPER_RECIPE_ARTICLE_TREE_V0.1.md)
- [Final ArticleTree v0.2](docs/FINAL_ARTICLE_TREE_V0.2.md)
- [支持矩阵](docs/SUPPORT_MATRIX.md)
- [故障排查](docs/TROUBLESHOOTING.md)
- [Alpha RC 说明](docs/ALPHA_RC_RELEASE_NOTES.md)
- [文本复核协议](docs/TEXT_REVIEW_PROTOCOL_ZH.md)
- [manifest v0.10 文本复核派生包迁移说明](docs/MANIFEST_MIGRATION_V0.10.md)
- [manifest v0.11 L3 程序合成派生包迁移说明](docs/MANIFEST_MIGRATION_V0.11.md)
- [项目模块导览](docs/PROJECT_MAP.md)
- [契约与兼容性规则](docs/CONTRACTS_AND_COMPATIBILITY.md)
- [贡献验证流程](docs/VALIDATION.md)
- [manifest v0.9 与 Article Model 迁移说明](docs/MANIFEST_MIGRATION_V0.9.md)
- [manifest v0.8 与 Reader 迁移说明](docs/MANIFEST_MIGRATION_V0.8.md)

## AI Agent skills

仓库的 `skills/` 目录提供四个可分发的 Agent skill：

- [`paperwright-install`](skills/paperwright-install/SKILL.md)：下载、安装与 CLI 验证；
- [`paperwright-convert`](skills/paperwright-convert/SKILL.md)：直接转换、批量转换与人工/视觉 AI 混合复核；
- [`paperwright-agent-workflow`](skills/paperwright-agent-workflow/SKILL.md)：由主 Agent 隔离协调视觉布局与纯文本复核子 Agent；
- [`paperwright-vision-qwen`](skills/paperwright-vision-qwen/SKILL.md)（可选）：把视觉复核绑定到
  qwen-mm-plugins 的多模态 MCP 工具（Content ROI 建议、visual-direct 区域、
  join-blocks 断句确认、图注核查）。仅在已安装 qwen-mm-plugins 并配置 DashScope
  key 时可用；未安装不影响核心与其余 skills。MCP 超时时可用直连桥
  `tools/run_visual_review.py` 直接生成并校验 `final-layout.json`。

支持仓库内 skill 发现的 Agent 可以直接加载 `skills/`。其他工具可把对应 skill
目录复制到自身的 skills 目录，或在提示中明确要求参照对应 `SKILL.md`。安装后可使用
`$paperwright-install`、`$paperwright-convert`、
`$paperwright-agent-workflow` 或 `$paperwright-vision-qwen` 显式调用。

这些 skills 只指导 Agent 调用现有命令和遵守项目契约，不会替 paperwright 隐式增加
联网、LLM、OCR 或外部 API 行为。

调用 skill 后，Agent 会先询问尚未明确、且会影响质量、输出范围、存储、隐私或失败
处理的关键选项，并给出推荐设置；已经由用户指定或可从环境安全判断的选项不会重复
询问。用户也可以明确要求使用推荐设置。混合布局中的 Content ROI 和最终布局视觉复核
仍是必须单独完成的确认步骤。

## 已知限制

- 不支持扫描 PDF 的 OCR；
- 不生成语义表格或公式 LaTeX；
- 纯矢量且缺少可靠 Figure 证据时会保守拒绝；
- PDFBox、GUI、Web/API 服务和容器不在当前范围；
- macOS 和 ARM 平台尚未验证。

## 版本与数据契约

包版本与数据契约独立演进。当前包版本为 `0.9.0a0`，PhysicalDocument 使用
v0.2，布局任务使用 v0.1/v0.2，当前混合布局 manifest 使用 v0.9，Article
Model 和 Reader 均使用 v0.1。直接转换的兼容模式仍可能输出 manifest v0.4 或
v0.5；Text Task 与 Text Review 均使用 v0.2（读取旧结果时继续接受 v0.1）；读取旧结果时继续接受混合布局
manifest v0.6–v0.8；`text-package --synthesis-run` 写 manifest v0.11。升级包版本不代表已有
数据契约会被隐式改写。

## 许可证与分发

paperwright 采用 [Apache License 2.0](LICENSE)。任何人都可以在遵守许可证条件的
前提下使用、复制、修改和分发本项目。分发本项目或衍生作品时，请同时保留
`LICENSE` 和 `NOTICE` 中要求保留的声明。

完整的阶段研发记录和历史验证证据保存在
`agent/v2-rebuild` 分支。
