# Validation / 验证范围

Version 1.1.0 adds an explicit draft-purpose path while preserving the default strict checks. The original 63 workspace cases and 35 additional draft-mode boundary cases pass on the updated helper.

1.1.0 增加显式草稿用途分支，默认严格检查保留。更新脚本通过原 63 项工作区检查和新增 35 项草稿边界检查。

## Reproduce the workspace regression checks / 复跑工作区检查

From the repository root / 在仓库根目录运行：

```bash
python3 tests/test_workspace.py
python3 tests/test_draft_mode.py
```

These use only temporary, synthetic fixtures and Python's standard library, and print the results locations. The original 63 cases cover evidence, references and version boundaries; 35 draft cases additionally cover authorization records, pending claims/placeholders, translation and PDF bindings, and preservation of strict behavior. Synthetic pass fields and dummy PDF headers exercise interface validation; they are not real author approval, compilation, visual review or research results.

测试仅使用临时合成样例与标准库，并打印结果位置。原 63 项覆盖证据和版本等边界；新增 35 项覆盖声明、待补主张/占位、翻译与 PDF 绑定以及严格分支保留。样例通过字段与 PDF 文件头只用于接口检查，不是真实作者批准、编译、视觉检查或研究结论。

## Other observed checks / 其他已做检查

- Four helpers parse and expose command help; the master skill passes the bundled skill format validator.
- A separate agent used a tiny EMA code sketch and explicitly synthetic metrics to produce a Chinese outline. It retained the missing implementation, real-experiment and literature boundaries.
- Template fetching previously passed 24 offline/mocked cases; no live HTTPS/TLS integration download was performed.
- Translation drift checking previously passed 12 mechanical/error-path cases; it does not validate semantic equivalence.
- Static TeX checking passed targeted include/reference/asset, output-alias and unbraced-input checks. It is not a TeX engine.

The historical helper checks did not all record source fingerprints or complete per-case logs at execution time. This repository does not describe them as a new, fully version-bound validation run. Real-paper drafting, actual final-PDF export/visual review, and venue compliance remain unvalidated end to end. Plugin metadata has local structural checks; installation across client versions and official-directory acceptance are not established.

此前部分辅助工具检查没有在执行当时保存源码指纹或逐项完整日志，不能把它们描述为重新执行、完整绑定版本的验收。真实论文到最终 PDF、视觉检查及投稿合规尚未做全链路验证；插件清单的本地结构检查也不等于所有客户端安装通过或官方目录审核通过。
