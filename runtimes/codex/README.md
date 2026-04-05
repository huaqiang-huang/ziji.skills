# Codex 适配

## 目标

让 Codex 使用与 Claude / OpenClaw 相同的核心生成逻辑。

## 入口策略

Codex 侧不假设一定存在 Claude 式原生 slash skill 机制。

第一版可用方案：

- 复用同一套 prompts
- 复用同一套 tools
- 复用同一套产物结构
- 通过仓库根 `SKILL.md` 约束行为
- 通过本地命令映射完成 create / update / list / rollback

## 安装建议

如果你的 Codex 环境支持本地 skills 目录：

- 将本仓库软链接或复制到对应目录
- 入口名使用 `create-self`

如果没有本地 skills 目录：

- 直接在本仓库内工作
- 把根 `SKILL.md` 当作入口契约
- 用下面的命令映射执行

## 命令映射

```bash
python3 tools/skill_writer.py --action create --meta ... --work ... --persona ... --principles ... --recovery ... --base-dir ./selves
python3 tools/skill_writer.py --action update --slug {slug} --work-patch ... --correction ... --base-dir ./selves
python3 tools/skill_writer.py --action list --base-dir ./selves
python3 tools/version_manager.py --action rollback --slug {slug} --version {version} --base-dir ./selves
python3 tools/skill_writer.py --action delete --slug {slug} --base-dir ./selves
```

## 当前约束

Codex 适配的重点是：

- 共享核心逻辑
- 不引入不同的产物格式
- 不要求第一版与 Claude/OpenClaw 体验完全同构
- 采集器不可用时退回手工导入
