# OpenClaw 适配

## 目标

在 OpenClaw 中以 workspace skill 形式运行本项目，并保持与 Claude / Codex 相同的输出结构。

## 安装

将整个仓库放到：

- `~/.openclaw/workspace/skills/create-self`

主入口直接复用仓库根目录的 `SKILL.md`。

## 入口命名

- `/create-self`
- `/list-selves`
- `/self-rollback {slug} {version}`
- `/delete-self {slug}`

## 命令映射

```bash
python3 tools/skill_writer.py --action list --base-dir ./selves
python3 tools/version_manager.py --action rollback --slug {slug} --version {version} --base-dir ./selves
python3 tools/skill_writer.py --action delete --slug {slug} --base-dir ./selves
```

## 说明

- OpenClaw 侧只做薄适配
- 不复制核心 prompts / tools
- 采集器可选，不阻塞生成主流程

保证：

- 四层文件结构一致
- `meta.json` 字段一致
- 组合版 `SKILL.md` 优先级一致
