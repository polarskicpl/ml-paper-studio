# Validation / 验证范围

Version 1.0.1 changes distribution metadata, bilingual documentation and the conditional desktop-tool route. The helper implementations are unchanged from the tested local 1.0.0 revision.

1.0.1 调整分发清单、中英文说明及桌面工具的条件分支，辅助脚本实现沿用已检查的本地 1.0.0 版本。

## Reproduce the workspace regression checks / 复跑工作区检查

From the repository root / 在仓库根目录运行：

```bash
python3 tests/test_workspace.py
```

This uses only temporary, synthetic fixtures and Python's standard library. It checks 63 cases, including missing citation bindings, stale evidence/PDF inputs, confirmation versions, review metadata, malformed JSON, and path boundaries. It prints the results location. Synthetic pass fields and the dummy PDF header in these fixtures exercise interface validation; they are not real author approval, compilation, visual review or research results.

测试仅使用临时合成样例和 Python 标准库，覆盖 63 个行为场景，并输出结果位置。样例中的通过字段和 PDF 文件头只用于检查接口，不能视为真实作者批准、编译、视觉检查或研究结论。

## Other observed checks / 其他已做检查

- Four helpers parse and expose command help; the master skill passes the bundled skill format validator.
- A separate agent used a tiny EMA code sketch and explicitly synthetic metrics to produce a Chinese outline. It retained the missing implementation, real-experiment and literature boundaries.
- Template fetching previously passed 24 offline/mocked cases; no live HTTPS/TLS integration download was performed.
- Translation drift checking previously passed 12 mechanical/error-path cases; it does not validate semantic equivalence.
- Static TeX checking passed targeted include/reference/asset, output-alias and unbraced-input checks. It is not a TeX engine.

The historical helper checks did not all record source fingerprints or complete per-case logs at execution time. This repository does not describe them as a new, fully version-bound validation run. Real-paper drafting, actual final-PDF export/visual review, and venue compliance remain unvalidated end to end. Plugin metadata has local structural checks; installation across client versions and official-directory acceptance are not established.

此前部分辅助工具检查没有在执行当时保存源码指纹或逐项完整日志，不能把它们描述为重新执行、完整绑定版本的验收。真实论文到最终 PDF、视觉检查及投稿合规尚未做全链路验证；插件清单的本地结构检查也不等于所有客户端安装通过或官方目录审核通过。
