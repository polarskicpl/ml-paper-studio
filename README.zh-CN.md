# ML Paper Studio · ML 论文写作工作室

[English](README.md) | [简体中文](README.zh-CN.md)

面向计算机与 ML/AI 论文的证据驱动写作技能组。一个入口协调六个阶段，从研究代码和实验结果出发，组织中文论证框架、研究文献定位，再完成英文稿与经过检查的 LaTeX/PDF 交付物。

**版本：** 1.0.1 · **技能入口：** `$ml-paper-studio` · **许可证：** MIT

## 能做什么

| 阶段 | 工作内容 | 主要交付物 |
| --- | --- | --- |
| 0 · 投稿要求 | 核对指定会议、年份、track、稿件类型及投稿阶段的官方要求，获取模板。 | 投稿规则、来源链接、模板来源记录。 |
| 1 · 证据与框架 | 检查给定代码、协议和实际结果，区分实际观测、计划、合成及未完成证据。 | 中文框架、主张与证据映射、术语、图表计划、证据缺口。 |
| 2 · 文献与定位 | 深度研究前置、最接近及竞争工作，核验引用元数据与论断依据。 | 检索记录、文献及比较矩阵、有依据的贡献定位。 |
| 3 · 中文稿与自审 | 根据已确认框架写稿，自问论证问题、模拟审稿并实际修订。 | 中文正文、自审意见及修改记录。 |
| 4 · 学术英文 | 翻译润色正文、摘要、引言和图表标题，适配投稿要求。 | 英文稿，以及数值、公式、引用和结论强度的变动检查。 |
| 5 · LaTeX 与 PDF | 建立可编辑 LaTeX 工程，导出实际 PDF，检查内容、引用、排版及投稿要求。 | 源码工程、构建与导出工具可用时生成的 PDF、检查报告。 |

完整流程默认在**阶段 2 后**保留一个作者决策点：审阅修订后的中文框架、贡献、最接近工作比较和证据边界。已有确认会复用，也支持作者明确授权模型自行确定框架。确认后，在已授权的完整流程内连续推进，无需每个阶段重新要求“开始”。

自审默认**两轮**：先核对证据与论证，再模拟审稿；只有仍存在具体问题时才增加第三轮。模拟审稿不等于正式同行评议。也可以只做一个阶段或章节，不必重走全流程。

引用核验区分三个问题：**文献是否真实存在？是否取得了相关原文？原文是否支持当前这条论断？** DOI 能打开不能同时回答这三个问题。贡献定位会比较组件、机制耦合、约束及端到端证据；“整套系统完整”本身不能证明新颖性。

## 安装

### 推荐：让 Codex 安装技能

在提供 `$skill-installer` 的 Codex 中发送：

```text
使用 $skill-installer 安装这个技能：
https://github.com/polarskicpl/ml-paper-studio/tree/main/skills/ml-paper-studio
```

安装后下一轮即可使用。手动安装时，将完整的 `skills/ml-paper-studio/` 文件夹复制到客户端支持的技能目录。当前 Codex 文档使用 `~/.agents/skills/` 放个人技能、`.agents/skills/` 放项目技能；部分旧客户端和内置安装器仍使用 `~/.codex/skills/`（或 `$CODEX_HOME/skills/`）。请按所用客户端支持的位置安装，保留已有本地修改，避免重复安装。参见[官方技能指南](https://learn.chatgpt.com/docs/build-skills)。

### 可选：通过插件市场安装

仓库还提供便携的 `plugin.json` 和 `.agents/plugins/marketplace.json`。在支持此功能的 Codex 客户端中，先注册仓库作为插件市场来源：

```bash
codex plugin marketplace add polarskicpl/ml-paper-studio
```

随后在客户端的插件目录中选择此市场并安装插件。注册来源**不等于已经安装**，安装后请开始新会话。这是自行托管的市场来源，并非官方精选目录收录；尚未在所有客户端中验证兼容性。参见[官方插件指南](https://developers.openai.com/plugins/build/plugins)。

直接安装技能与插件方式二选一即可，避免加载两份相同技能。

## 使用

从研究材料开始：

```text
使用 $ml-paper-studio。根据这个项目的实际代码、冻结协议和已有结果，
先给出中文论文框架、主张与证据映射和证据缺口，不启动新实验。
具体投稿会议稍后确定。
```

也可以只做一个阶段：

```text
使用 $ml-paper-studio 的文献阶段。围绕这个设计查找前置和最接近工作，
核验引用，比较组件层面的想法与整体机制。用英文输出定位和比较矩阵，
不要撰写全文或运行实验。
```

```text
Use $ml-paper-studio to translate only these Chinese methods and experiments
sections into academic English. Preserve numbers, equations, citation attachment,
and claim strength. Do not rerun the other stages.
```

核心阶段指令使用中文编写，也可以要求英文输出；完整流程默认先形成中文框架和中文稿，再做英文修订。更多例子见[调用示例](skills/ml-paper-studio/references/usage-examples.md)。

## 依赖与验证范围

- 内置辅助脚本仅使用 Python 标准库，建议 **Python 3.10+**；本次检查实际使用 **Python 3.14.4**。论文本身可能需要其他工具。
- 文献与投稿要求核实需要能够访问来源；PDF 交付需要可用的 TeX 构建、导出及 PDF 检查和渲染工具。流程不绑定某款桌面专属工具，缺失的检查会明确记为未执行。
- 已完成**工作区状态辅助脚本的 63 项回归检查**和一次合成材料框架试用；其他辅助工具保留各自记录的检查边界。**真实论文到 PDF 的完整流程尚未验收。** 结构检查通过不能证明科学真实性或投稿合规。

检查范围和复跑命令见[验证说明](docs/VALIDATION.md)。

技能本身不授权新增训练、修改冻结实验或公开私人研究材料；执行时仍遵循项目规则与用户实际授权。

## 目录与来源

- [主技能](skills/ml-paper-studio/SKILL.md)：阶段调度与工作边界。
- `skills/ml-paper-studio/stages/`：六个内部阶段模块。
- `skills/ml-paper-studio/references/`：交付接口、自审标准、示例与来源研究。
- `skills/ml-paper-studio/scripts/`：工作区检查、模板获取、翻译漂移检查及 TeX 静态审查。

本仓库原创文件按 [MIT 许可证](LICENSE) 发布。设计参考了七个仓库中的 16 个技能目录；[来源记录](skills/ml-paper-studio/references/upstream-research.md)说明了吸收与舍弃的做法。仓库不打包上游技能快照、脚本或会议模板；引用链接不改变这些材料各自的许可证。
