# ML Paper Studio

[English](README.md) | [简体中文](README.zh-CN.md)

An evidence-based writing skill group for computer science and ML/AI papers. One entry point coordinates six stages, from research code and results to a Chinese argument structure, literature positioning, an English manuscript, and a checked LaTeX/PDF deliverable.

**Version:** 1.0.1 · **Skill:** `$ml-paper-studio` · **License:** MIT

## What it does

| Stage | Work | Main outputs |
| --- | --- | --- |
| 0 · Venue | Check the official requirements for the exact venue, year, track, paper type, and submission phase; obtain the template. | Requirements, source links, template provenance. |
| 1 · Evidence and outline | Inspect the supplied code, protocols, and actual results; distinguish observed, planned, synthetic, and incomplete evidence. | Chinese outline, claim–evidence map, terminology, figure plan, gaps. |
| 2 · Literature and positioning | Research prior, closest, and competing work; check citation metadata and the evidence behind claims. | Search record, source and comparison matrices, defensible contribution positioning. |
| 3 · Chinese draft and review | Draft from the confirmed framework, question the argument, simulate review, and make concrete revisions. | Chinese manuscript and review/change record. |
| 4 · Academic English | Translate and polish the manuscript, abstract, introduction, and captions; adapt to the venue. | English manuscript and checks for changes to numbers, equations, citations, and claim strength. |
| 5 · LaTeX and PDF | Build an editable LaTeX project, export the actual PDF, and check its content, references, layout, and submission requirements. | Source project, PDF when build/export tools are available, and a check report. |

For the full workflow, the default author decision point is **after Stage 2**: review the revised Chinese outline, contributions, closest-work comparison, and evidence boundaries. An existing confirmation is reused; explicit delegation to the assistant is also supported. After confirmation, an authorized full workflow continues without asking to start every stage.

Self-review defaults to **two rounds**—evidence/argument review, then simulated peer review—with at most a third round for specific remaining issues. Simulated review is not formal peer review. You can also request a single stage or section without restarting the whole workflow.

Citation checks distinguish three questions: **Does the work exist? Was the relevant text retrieved? Does that text support this particular claim?** A working DOI alone does not answer all three. Literature positioning compares components, their coupling, constraints, and end-to-end evidence; “a complete system” alone is not a novelty argument.

## Install

### Recommended: ask Codex to install the skill

In Codex with `$skill-installer` available, send:

```text
Use $skill-installer to install the skill from
https://github.com/polarskicpl/ml-paper-studio/tree/main/skills/ml-paper-studio
```

Use it on the next turn after installation. To install manually, copy the complete `skills/ml-paper-studio/` directory to a skill directory supported by your client. Current Codex documentation uses `~/.agents/skills/` for personal skills and `.agents/skills/` for project skills. Some older clients and the bundled installer still use `~/.codex/skills/` (or `$CODEX_HOME/skills/`). Follow your client's supported location; preserve existing local changes and avoid duplicate installations. See the [official skills guide](https://learn.chatgpt.com/docs/build-skills).

### Optional: install through a plugin marketplace

This repository also includes a portable `plugin.json` and `.agents/plugins/marketplace.json`. In a supported Codex client, register the repository as a marketplace source:

```bash
codex plugin marketplace add polarskicpl/ml-paper-studio
```

Then select this marketplace in the client's plugin directory and install the plugin. Registering the source **does not install it**. Start a new session after installation. This is a self-hosted marketplace source, not a listing in an official curated directory; client compatibility has not been verified across all clients. See the [official plugin guide](https://developers.openai.com/plugins/build/plugins).

Choose either the direct skill installation or the plugin route to avoid loading duplicate copies.

## Use

Start with your research materials:

```text
Use $ml-paper-studio. Inspect this project's actual code, frozen protocols,
and existing results. Produce a Chinese paper outline, a claim–evidence map,
and a list of gaps. Do not start new experiments. I will specify the venue later.
```

Or request one stage:

```text
Use the literature stage of $ml-paper-studio. Find prior and closest work for
this design, verify the references, and compare component-level ideas with
the overall mechanism. Return the positioning and comparison matrix in English.
Do not draft the full paper or run experiments.
```

```text
使用 $ml-paper-studio，只将这份中文方法与实验章节改成学术英文。
保留数值、公式、引用所支持的句子和结论强度，不重跑其他阶段。
```

The core stage instructions are written in Chinese. You can request English outputs; the default full workflow develops the Chinese framework and draft before English revision. More examples: [usage guide](skills/ml-paper-studio/references/usage-examples.md).

## Requirements and validation

- Bundled helper scripts use the Python standard library. Python **3.10+** is recommended; the current checks ran on **Python 3.14.4**. Additional tools may be needed for the manuscript itself.
- Literature and venue verification require accessible sources. PDF delivery requires an available TeX build/export tool and PDF inspection/rendering tools. The workflow is not tied to a particular desktop tool; missing checks remain explicitly unrun.
- Validation includes **63 regression cases for the workspace-state helper** and a synthetic-material outline trial. Other helper checks retain their documented limits. **A real-paper, end-to-end PDF workflow has not yet been validated.** Structural checks do not establish scientific validity or submission compliance.

See [validation scope and the reproducible check command](docs/VALIDATION.md).

The skill does not authorize new training runs, changes to frozen experiments, or publication of private research materials. Follow the project's own rules and the user's actual authorization.

## Repository and attribution

- [Main skill](skills/ml-paper-studio/SKILL.md): routing and workflow boundaries.
- `skills/ml-paper-studio/stages/`: the six internal stage modules.
- `skills/ml-paper-studio/references/`: artifact contracts, review rubric, examples, and source research.
- `skills/ml-paper-studio/scripts/`: workspace checks, template fetching, translation drift checks, and static TeX auditing.

The original files in this repository are released under the [MIT License](LICENSE). The workflow was informed by research into 16 skill directories across seven repositories; [the source notes](skills/ml-paper-studio/references/upstream-research.md) record what was adopted or omitted. Upstream skill snapshots, scripts, and conference templates are not bundled; links do not change their respective licenses.
