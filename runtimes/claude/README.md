# Claude Code 适配

## 目标

在 Claude Code 中把本项目作为一个可调用 skill 使用，同时保持和其他宿主相同的产物结构。

## 安装

将整个仓库放到：

- 当前项目：`.claude/skills/create-self`
- 或全局：`~/.claude/skills/create-self`

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

## 可用工具

- `Read`
- `Write`
- `Edit`
- `Bash`

## 说明

- Claude 侧不维护单独核心逻辑
- 四层文件、`meta.json`、`versions/` 结构必须与其他宿主一致
- 采集器失败时直接退回手工导入
