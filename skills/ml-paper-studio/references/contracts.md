# 工作区与阶段接口

本文件是六个阶段的共享接口。已有项目可把实际文件映射到这些角色，不为迁就默认路径复制整份研究仓库。`paper-state.json` 记录实际路径；内部阶段文档中的路径均相对论文工作区。

## 目录和状态

```text
paper-state.json
venue/requirements.json                 官方规则与目标
venue/requirements.md                   可读规则摘要
venue/template-bundles/<id>/             下载原件与安全提取目录
venue/template-manifest.json             可选的当前模板索引
evidence/inventory.md                    实际实现和实验清单
evidence/evidence-map.json               主张与本地证据绑定
evidence/draft-declaration.json          并行模式的内部声明与待填账本（按需）
evidence/terms-and-symbols.md
outline/outline.zh.md
literature/sources.json
literature/search-ledger.jsonl
literature/evidence-matrix.csv
literature/prior-art-matrix.csv
literature/positioning.zh.md
literature/related-work.zh.md
literature/unresolved.md
manuscript/manuscript.zh.md
manuscript/manuscript.en.md
review/review-log.json
checks/translation-map.json
checks/invariants.json
checks/build-inputs.json
checks/build.json
checks/pdf-check.json
checks/final-report.md
paper/main.tex, sections/, figures/, references.bib, paper.pdf
```

初始化只创建状态，不预填证据、不生成“已通过”的检查报告。文件按实际阶段需要产生。

`paper-state.json` 的 schema 为 `ml-paper-studio.state/1`。包含 `paper_id`、`project_root`、`requested_scope`（full/stage/section）、`current_stage`、`stages`、`artifact_paths`、`framework_confirmation`、`open_decisions`、`unresolved_evidence` 和 `history`。

阶段键为 `00-venue`、`01-evidence-outline`、`02-literature`、`03-draft-review-zh`、`04-english`、`05-latex-pdf`。可用状态：`not_started`、`in_progress`、`waiting_author`、`blocked`、`drafted`、`complete`、`stale`。`complete` 是指定阶段产物的真实完成，不代表整篇论文可投。静态检查脚本从不自动写 `complete`。

工具字段里的单项检查状态为 `pass`、`fail`、`not_run`、`manual_required`、`not_applicable`。`not_applicable` 附理由；无法检查不用该状态掩盖。

## 阶段 0 投稿规则

```json
{
  "schema": "ml-paper-studio.venue/1",
  "target": {"venue": null, "year": null, "track": null, "paper_type": null, "phase": null},
  "status": "target_unconfirmed",
  "sources": [],
  "rules": [],
  "conflicts": [],
  "template": {"status": "not_downloaded", "manifest_path": null}
}
```

确认目标后填 `target`。`status` 为 `verified`、`provisional`、`target_unconfirmed` 或 `conflict`。每条 `rules` 至少有 `id`、`requirement`、`mandatory`、`source_url`、`locator`、`checked_at`、`status`；另记录适用阶段、计页口径等实际规则。`verified` 仅指来源和适用性被核对，不能推出稿件满足规则。

模板 helper 输出原 manifest 在实际新建 bundle 内；`template.manifest_path` 指向该文件。`venue/template-manifest.json` 如使用则只保存 `active_manifest_path` 等索引，不能把复制后的相对路径误当原 manifest 根。下载器的 `provenance_not_established` 需要模型根据官方页面核实，不能自动升级为官方模板已认证。

## 阶段 1 本地证据

```json
{
  "schema": "ml-paper-studio.evidence/1",
  "records": [{
    "id": "EV-001", "root": "project", "path": "outputs/real-run/metrics.json",
    "sha256": "<实际文件SHA256>", "locator": "test.metrics.ndcg_at_10",
    "kind": "result", "status": "observed",
    "conditions": {"dataset": "实际值", "split": "TEST", "seed": "实际值"},
    "interpretation": "实际查看后能支持什么、不能支持什么"
  }],
  "claims": [{
    "id": "C-001", "text": "待写的具体主张", "claim_type": "empirical",
    "evidence_ids": ["EV-001"], "source_ids": [],
    "status": "supported", "use_in_manuscript": true,
    "scope": "明确比较对象、条件和结论范围"
  }]
}
```

此示例是字段说明，不能复制占位值冒充真实记录。

- 记录 `root` 为 `project` 或 `workspace`；`path` 是相对相应根的路径。越界或符号链接逃逸须显式处理，不能自动扩大根。
- `kind` 可为 code/result/protocol/log/theory/data/figure；`status` 为 observed/author_reported/planned/synthetic/partial/failed。文件哈希只证明当前字节与记录一致，不证明实验合法或内容真实。
- 主张 `claim_type` 为 empirical/implementation/theory/positioning；`status` 为 supported/bounded/unresolved/contradicted。`bounded` 说明具体限制；没有证据的主张不能靠该标签放行。
- 外部论文作为背景或理论支持不能冒充本研究结果。经验性结果至少要有相符条件下的实际结果记录；`partial` 仅能支持明确写出的部分范围。
- `use_in_manuscript:false` 表示本轮不使用的候选主张，不要求为了凑齐它们去补实验。

## 并行写作的可选接口

按 [兼容模式](parallel-drafting.md) 启用，不改变原证据枚举或默认严格检查。完整工作区的状态可补：

```json
{"drafting": {"mode": "parallel", "declaration_path": "evidence/draft-declaration.json"}}
```

声明文件示例：

```json
{
  "schema": "ml-paper-studio.draft-declaration/1",
  "authorization": {
    "user_message_ref": "实际用户消息引用",
    "quote": "实际授权原话",
    "scope": "允许先写的具体范围；不代表批准结果或投稿"
  },
  "design_basis": ["按实际说明整理的算法、协议及内部实现差异"],
  "pending": [{
    "id": "R1", "claim_id": "C-RESULT-1",
    "locations": ["manuscript/manuscript.zh.md 的实际结果位置"],
    "required_evidence": "实际需要补齐并核验的结果及比较条件",
    "status": "pending", "placeholder": "[[RESULT:R1]]"
  }]
}
```

此示例不是授权或结果。`authorization` 只记录实际消息，脚本不能鉴别消息身份；`design_basis` 是可选说明，不是实测证明。`pending` 中每条都有唯一 id、实际 claim_id、非空位置与待补依据、状态和占位；id 用字母数字开头及字母数字/下划线/短横线，占位必须是 `[[RESULT:<id>]]`。`locations` 为调用方定位说明，脚本不做语义认证。

状态为 pending/resolved/dropped。pending 只对应仍在稿件范围内的 unresolved 主张，占位保留在中文及已生成的对应英文中；使用中的每条 unresolved 主张须有登记。contradicted 不能靠声明放行。resolved 仍须对应有实际支持的 supported/bounded 主张；dropped 须移出本轮主张范围。真实证据到达前不改状态，不删除占位冒充问题解决。

例如 `paper_workspace.py check --stage 3 --purpose draft`，仅限阶段 3、4、5，使用独立报告 schema `ml-paper-studio.draft-check/1`，状态为 draft_consistent/needs_review，`submission_readiness` 固定 not_assessed。它检查声明、主张关联、文本占位与当前字节绑定；英文仍核对翻译保真记录，内部 PDF 仍核对构建/PDF/输入绑定。未做的审稿、语义支持、作者身份、视觉及投稿检查不升级为通过；不会自动确认框架、标阶段 complete 或修改证据。

未指定 `--purpose` 或指定 strict 时仍用原严格行为；0–2 阶段不接受 draft。正常中文草稿可带登记缺口交接，但原严格检查中的 open_core_claim 等问题继续存在。一个阶段返回 consistent 也不是完整投稿验收；最终提交需相关内容、引用、翻译、PDF 及会议要求分别通过实际核对。

## 阶段 2 文献证据

`sources.json`：

```json
{
  "schema": "ml-paper-studio.sources/1",
  "entries": [{
    "id": "S-001", "title": "实际题名", "authors": ["实际作者"], "year": 2026,
    "identifiers": {"doi": null, "arxiv": null, "url": "原始来源URL"},
    "canonical_url": "可追溯的论文原始来源URL",
    "identity_status": "unverified",
    "retrieval_status": "metadata_only", "checked_at": null,
    "version_notes": "预印本/会议版/更正等关系"
  }]
}
```

`identity_status` 为 verified/mismatch/uncertain/unverified。`verified` 必须有实际题名、作者、年份匹配及检查依据，DOI 能解析本身不够。`retrieval_status` 为 full_text/abstract_only/metadata_only/unavailable。

`evidence-matrix.csv` 至少有 `claim_id,source_id,locator,relation,support_status`；按需补 `source_version,proposition,scope,caveat,checked_at,check_method`。relation 为 supports/contradicts/partial/context/unclear；support_status 为 supported/partial/contradicted/context_only/unverified。metadata_only 和 unavailable 不可支持技术主张；摘要只能支持其中明确写出的有限结论，并标明摘要位置与限制，不能支持精细方法/不存在性比较。

允许的 relation/support_status 配对：supports 对应 supported/partial/unverified，partial 对应 partial/unverified，contradicts 对应 contradicted/unverified，context 对应 context_only/unverified，unclear 仅对应 unverified。使用中的 supported/bounded 主张，其每个 `source_id` 都须存在，并有相同 claim/source 的支持行、已核实身份、可用原文或有范围限制的摘要及非空定位。反证和背景引用保留在矩阵中，不用它们代替核心主张的支持证据。阶段 1 尚未核实的候选引用可随 unresolved 主张暂存，不能提前标为 supported。

`prior-art-matrix.csv` 说明 foundational/component/closest/competitor/negative 关系、问题与假设、组件及耦合、反馈时序和评价条件、相同/不同点、区别的证据及比较局限。`search-ledger.jsonl` 保存问题、检索式、平台、日期、筛选、失败与限制。不把下载数量当覆盖完成标准。

## 框架确认

确认绑定 `outline/outline.zh.md`、`literature/positioning.zh.md`、`evidence/evidence-map.json` 三份文件的哈希，并记录实际用户消息引用、原话、确认范围和时间。默认 `mode=human_confirmed`；只有用户明确委托模型自主决定框架才可记 `delegated_to_agent`。

同版确认复用；核心贡献或证据边界改变后重新确认受影响范围。格式、标点等不改研究立场的微调可以先解释变更并由模型记录非实质修订，不能用机械哈希变动逼用户反复批准。工具发现哈希变化只提示重新核对，不判断变化是否实质。

## 阶段 3 自审

`review-log.json` 的 schema 为 `ml-paper-studio.review/1`，顶层 `rounds`、`unresolved`。每轮记录唯一的 `round`、`type`（evidence_self_review/simulated_review/targeted_fix）、`reviewer_mode`（same_model/independent_agent）、`findings`、`changes`。默认两轮需分别包含 evidence_self_review 和 simulated_review；空 findings 只表示确实没有发现问题，不能伪造发现凑数。每个 finding 有 `id,severity,location,issue,evidence,status,resolution`；severity 为 critical/major/minor/style，status 为 fixed/unresolved/deferred。未实际核对的修订不记 fixed。

默认两轮、最多第三轮，每轮针对不同目的；事实性核心缺陷未解则保持 drafted 或 blocked。仅剩可选风格意见时停止；不以虚构评分、AI 文风分数或录用概率证明质量。

## 阶段 4 英文保真

`translation-map.json` 的 schema 为 `ml-paper-studio.translation/1`，含 `source_sha256`、`target_sha256`、`checks` 和段落对应 `entries`。checks 按 numbers/formulas/citation_attachment/claim_strength/terminology 分别记状态和检查依据。对风险段落回译，不强制整篇逐句回译。

`check_fidelity.py` 只发现数字、引用键或显示公式变化候选。数学等价改写、百分比换算、中文数量词和编号会产生差异，须根据实际内容判断；没有机械差异也不能证明语义相同。

## 阶段 5 构建与 PDF

`build.json` 至少记录：

```json
{
  "schema": "ml-paper-studio.build/1", "status": "not_run",
  "engine": null, "command_or_tool": null, "built_at": null,
  "source_manifest": [], "pdf_path": "paper/paper.pdf", "pdf_sha256": null,
  "diagnostics": [], "log_path": null
}
```

实际构建成功后才用 `status=success`；失败为 failed，没有运行保持 not_run。`source_manifest` 是 `snapshot-inputs` 生成的列表，`path` 相对工作区、`sha256` 绑定实际构建输入；构建前后核对期间输入未变。下载 PDF 与编译器成功各有真实证据，不填凭想象的命令结果。

快照覆盖 `paper/` 下全部普通文件，排除当前目标 PDF、`.git` 和已知 TeX 构建中间产物；不能只追踪固定后缀。脚本拒绝目录符号链接及越界文件链接；项目确实依赖外部构建输入时需显式迁入授权论文工程或补充独立绑定，静态快照不能发现任意 TeX 宏运行时读取。

`pdf-check.json` schema 为 `ml-paper-studio.pdf-check/1`，含 `pdf_sha256`、`checks`。检查项：content_fidelity, references, math, layout_visual, page_limit, anonymity, fonts；每项为 `{status,evidence,reason}`。所有必查项须有实际依据的 pass，manual_required/not_run 不算通过；只有非匿名稿的 anonymity 可记有理由的 not_applicable。所有实际页面需要视觉查看。未知目标时 page_limit 保持 manual_required，不能宣称完整投稿合规。

最后分别报告内容、引用、构建、视觉及投稿合规。脚本状态 `consistent` 只表示已检查的静态接口与哈希一致，不是科学真实性、作者批准或录用保证。
