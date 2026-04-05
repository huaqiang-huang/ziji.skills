# WeChat Experimental Samples

这个目录放的是**脱敏样例**，用于说明微信实验能力的输入输出长什么样。

包含：

- `manifest.sample.json`
  - 本地探测器的示例输出
- `messages.sample.json`
  - 统一标准化后的消息输出样例
- `parse_report.sample.json`
  - 本地解析或导出适配后的解析报告样例
- `export/messages.txt`
  - 一个最小导出文本样例，适合喂给 `wechat_export_adapter.py`

这些文件都不包含真实聊天记录，只用于：

- README 展示
- CI / smoke test 参考
- 第三方开发者理解输出结构
