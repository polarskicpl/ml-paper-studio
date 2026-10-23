# 研读来源与取舍

本技能按用户的六阶段工作流原创组织。上游下载到独立研读目录，主 skill 不依赖这些副本运行；未把上游脚本、模板或整套指令复制进本技能。

2026 年 10 月 23 日固定版本下载了 7 个仓库中的 16 个相关技能目录及仓库声明，共 604 个不同文件。逐文件核对 Git blob SHA 与 SHA-256；下载完整不等于对每行实现完成安全审计。研读范围是各目录的主入口、与当前阶段有关的参考材料和有实质影响的实现。

## 写作与论证

| 来源 | 吸收的机制 | 未作为默认的做法 |
| --- | --- | --- |
| [Orchestra ml-paper-writing](https://github.com/Orchestra-Research/AI-Research-SKILLs/tree/773a52944ba4747a18bd4ae9ade53fff041adcbc/20-ml-paper-writing/ml-paper-writing) | 从研究仓库识别主贡献，组织论文论证，引用与模板有出处。 | 静态会议页数/年份、无来源效果统计、靠措辞把组合包装成新颖方法。 |
| [Orchestra systems-paper-writing](https://github.com/Orchestra-Research/AI-Research-SKILLs/tree/773a52944ba4747a18bd4ae9ade53fff041adcbc/20-ml-paper-writing/systems-paper-writing) | 具体问题与适用环境、设计取舍、端到端评价与分解分析的关系。 | 为所有 ML 论文固定系统论文页数或章节比例。 |
| [DELONG paper-writing](https://github.com/DELONG-L/Academic-Paper-Skills/tree/827e13e2299c0a15d397ce095bc548817a2cf3cb/paper-writing) | 实验事实→证据支持→有边界的结论；按实际任务范围改写。 | 为普通段落修改建立整个政策或注册框架。 |
| [DELONG paper-review](https://github.com/DELONG-L/Academic-Paper-Skills/tree/827e13e2299c0a15d397ce095bc548817a2cf3cb/paper-review) | 结构和局部问题分开，意见定位，真实修改与有限复审。 | 把模拟评审写成正式独立审计或录用预测。 |
| [DELONG paper-policy](https://github.com/DELONG-L/Academic-Paper-Skills/tree/827e13e2299c0a15d397ce095bc548817a2cf3cb/paper-policy) | 科学证据、作者要求、投稿合规分开记录。 | 将每个小任务都升级为整篇最终验收。 |
| [SciPilot-writing](https://github.com/Haojae/scipilot-writing-skill/tree/51c5fd39e2a386b7ddca021181b4c8071d3c3da7) | 数值与结论保护，读稿自审，有限轮次修改。 | 反复逐项必问、强制整篇回译、固定报告形式、用文风检测分数推断作者身份或科学质量。 |
| [nature-writing](https://github.com/Yuan1z0825/nature-skills/tree/c6ae86c742705fd968b13c79db1a8518a84089d4/skills/nature-writing) | 稿件类型/章节/语言/期刊按需加载，算法类论文与整体论证。 | 将 Nature 期刊行文格式当成所有计算机会议的要求。 |

## 深度研究与引用

| 来源 | 吸收的机制 | 具体修正 |
| --- | --- | --- |
| [Kalaris citation-verification](https://github.com/KalarisLabs/research-agent-skills/tree/f73da6a491e3cc3417cfe88e1130469e763b1b33/skills/citation-verification) | 题名/作者/年份/标识符核对与失败可见。 | 其脚本 DOI-only 查询可因解析成功给 verified，不能代替身份完整核验，更不能证明所引句子得到支持。 |
| [Kalaris paper-lookup](https://github.com/KalarisLabs/research-agent-skills/tree/f73da6a491e3cc3417cfe88e1130469e763b1b33/skills/paper-lookup) | 先定义检索目标，区分元数据/摘要/全文，记录分页、获取失败和限制。 | 不以 HTTP 200、非空片段或搜索排序证明文献覆盖充分。 |
| [K-Dense research-lookup](https://github.com/K-Dense-AI/scientific-agent-skills/tree/593377bb048752abb0152deab9fbb1083a6087df/skills/research-lookup) | 近期、奠基、近邻、反例多方向检索，证据矩阵、章节资料包与检索日志。 | 不继承固定篇数、付费服务绑定或自引要求；retrieved 与 verified 分开。 |
| [K-Dense literature-review](https://github.com/K-Dense-AI/scientific-agent-skills/tree/593377bb048752abb0152deab9fbb1083a6087df/skills/literature-review) | 版本与来源关系，范围和筛选理由，探索检索与可复现综述的边界。 | 普通 Related Work 不自动套用临床综述全流程，不宣称检索穷尽。 |
| [K-Dense scientific-writing](https://github.com/K-Dense-AI/scientific-agent-skills/tree/593377bb048752abb0152deab9fbb1083a6087df/skills/scientific-writing) | 主张与来源位置绑定、证据范围及报告责任。 | 不对普通写作增加每条引用逐个作者签字、固定插图数量或外部工具硬门禁。 |
| [Kalaris rebuttal](https://github.com/KalarisLabs/research-agent-skills/tree/f73da6a491e3cc3417cfe88e1130469e763b1b33/skills/rebuttal-and-response-to-reviewers) | 将审稿意见分解为问题、实际修改和可核对回应。 | 模拟意见不能自行授权补实验；不存在的修订不能写成已完成。 |

## 投稿与排版

| 来源 | 吸收的机制 | 适用边界 |
| --- | --- | --- |
| [latex-paper-en](https://github.com/bahayonghang/academic-writing-skills/tree/8183f08718ecfbd2200d112f72855ee20d2e4d1c/academic-writing-skills/latex-paper-en) | 现有 LaTeX 的模块化检查、引用与公式保护、局部修订。 | 仅研读其方式，未复制脚本；该仓库 README 标示 Academic Use Only。 |
| [paper-audit](https://github.com/bahayonghang/academic-writing-skills/tree/8183f08718ecfbd2200d112f72855ee20d2e4d1c/academic-writing-skills/paper-audit) | 脚本发现与审稿判断分开，缺陷分级，复审与修订路线。 | 单独运行可能跳过缺失的兄弟技能脚本；退出成功不能当全项通过。 |
| [K-Dense venue-templates](https://github.com/K-Dense-AI/scientific-agent-skills/tree/593377bb048752abb0152deab9fbb1083a6087df/skills/venue-templates) | 完整模板文件结构与体裁差异。 | 仓库内模板只作研究/缓存；正式稿按目标年份、track 和阶段从官方链接获取。 |

## 来源保存和许可

作者本地的下载副本保留了仓库提供的 README、根许可声明与逐文件机器清单；这些研读副本及机器记录不随公开仓库分发。固定提交已记录在上文链接中，主技能运行不依赖本地研读副本。

研读时核实：Orchestra、SciPilot、DELONG、K-Dense 根声明为 MIT；nature-skills 当前为 Apache-2.0；Kalaris 根为 MIT 并提示第三方声明；academic-writing-skills 的 README 为 Academic Use Only / Not for commercial use。不同来源不能一律标成同一种许可。

可移植技能包只包含本技能的原创主入口、阶段规则、接口文档和辅助脚本，不包含上游下载副本或第三方会议模板。本文件链接来源用于追溯，不宣称上游作者背书。
