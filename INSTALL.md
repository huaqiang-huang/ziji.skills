# 安装与宿主适配

本项目共享一套核心逻辑，按宿主做薄适配。

当前宿主目标：

- Claude Code
- OpenClaw
- Codex

## 依赖

```bash
pip3 install -r requirements.txt
```

如果需要浏览器采集：

```bash
playwright install chromium
```

## 通用命令

```bash
python3 tools/skill_writer.py --action list --base-dir ./selves
python3 tools/version_manager.py --action list --slug {slug} --base-dir ./selves
python3 tools/validate_self_skill.py
python3 tools/smoke_test.py
```

## 个人微信实验能力

当前仅作为实验能力提供：

- 本地探测：`python3 tools/wechat_local_probe.py --platform auto --output /tmp/wechat_manifest.json`
- 本地解析：`python3 tools/wechat_local_parser.py --manifest /tmp/wechat_manifest.json --output-dir /tmp/wechat_out`
- 导出适配：`python3 tools/wechat_export_adapter.py --input /path/to/export --format auto --output-dir /tmp/wechat_out`
- 统一入口：`python3 tools/wechat_pipeline.py --mode local --platform auto --output-dir /tmp/wechat_out`
- 冒烟验证：`python3 tools/wechat_smoke_test.py`

注意：

- 这条线不承诺稳定，优先作为研究和实验使用
- 不支持 iPhone / Android 端本机直读
- 不会写回微信目录，只会复制候选库到临时目录后尝试解析
- 如果本地库不可读，推荐先用留痕 / WeChatMsg / PyWxDump 导出后再适配

## 宿主说明

- `runtimes/claude/README.md`
- `runtimes/openclaw/README.md`
- `runtimes/codex/README.md`

共同约束：

- 四层结构固定
- 默认模式固定为 `best`
- 采集器是可选高级输入源，不阻塞主流程
- 不允许不同宿主产出不同字段和不同目录结构
