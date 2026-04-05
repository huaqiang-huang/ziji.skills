---
name: create-self
description: "Distill yourself into a four-layer AI Skill with create / update / list / rollback flows. | 把你自己蒸馏成四层 AI Skill，并支持 create / update / list / rollback 闭环。"
argument-hint: "[name-or-slug]"
version: "0.3.0"
user-invocable: true
allowed-tools: Read, Write, Edit, Bash
---

# 自己.skill 生成器

## 目标

这个 skill 的目标不是做“人格模仿”，而是生成一个可复用、可更新、可回滚的执行型 self skill。

固定产物是四层：

- `Principles`
- `Persona`
- `Work`
- `Recovery`

默认模式固定为 `best`。

## 动作识别

遇到以下表达时，按对应动作处理：

- `create-self`
  - “帮我做一个自己.skill”
  - “把我自己蒸馏成 skill”
  - “创建我的 self skill”
- `update-self`
  - “我有新资料”
  - “更新我的 self skill”
  - “补充这些代码/文档/聊天记录”
- `correction`
  - “这不像我”
  - “我其实会这样”
  - “我不会这么做”
  - “这个是我想保留的”
  - “这个是我想改掉的”
- `list-selves`
  - “列出已有 self”
  - `/list-selves`
- `self-rollback`
  - `/self-rollback {slug} {version}`
- `delete-self`
  - `/delete-self {slug}`

## 工具规则

优先使用仓库里的固定工具，不要手写目录结构：

- 写入和更新：`python3 tools/skill_writer.py`
- 版本管理：`python3 tools/version_manager.py`
- 只读校验：`python3 tools/validate_self_skill.py`
- 冒烟验证：`python3 tools/smoke_test.py`
- 飞书/钉钉/Slack/邮件/浏览器采集：使用 `tools/` 下现有采集器和解析器
- 个人微信本地实验：`python3 tools/wechat_local_probe.py` / `python3 tools/wechat_local_parser.py`
- 微信导出回退：`python3 tools/wechat_export_adapter.py`

如果自动采集器不可用：

- 直接退回手工导入
- 不阻塞主流程
- 不改变产物结构

## 创建流程

### Step 1：基础信息录入

参考 `prompts/intake.md`，固定采集：

- 模式
- 称呼 / 代号
- 背景和角色
- 最想保留的 3 个特点
- 最想修正的 3 个问题
- 绝不希望学到的坏习惯

如果用户没选模式，默认 `best`。

### Step 2：导入资料

优先接收：

- Markdown / TXT
- PDF
- 邮件
- 聊天导出
- 代码
- 笔记
- 设计方案
- 复盘
- 用户直接描述

高级输入源可选：

- 飞书自动采集
- 钉钉自动采集
- Slack 自动采集
- 浏览器登录态抓取
- 个人微信本地解析（实验）
- 外部微信导出适配（实验，推荐回退）

### Step 3：四层分析

分析顺序固定为：

1. `Principles`
2. `Persona`
3. `Work`
4. `Recovery`

参考文件：

- `prompts/work_analyzer.md`
- `prompts/persona_analyzer.md`
- `prompts/principles_builder.md`
- `prompts/recovery_builder.md`

权重固定为：

- 高权重：主动写的长文、代码、设计方案、复盘、长期笔记
- 中权重：PR 评论、会议纪要、较长的任务讨论
- 低权重：标签、碎片描述、一次性情绪表达

### Step 4：预览确认

给出四层摘要，各 3-5 条，并带上：

- 当前模式
- 理想化说明
- 哪些内容是旧习惯，哪些是主规则

### Step 5：写入产物

统一写入：

```bash
python3 tools/skill_writer.py --action create \
  --meta /path/to/meta.json \
  --work /path/to/work.md \
  --persona /path/to/persona.md \
  --principles /path/to/principles.md \
  --recovery /path/to/recovery.md \
  --base-dir ./selves
```

固定输出目录：

- `./selves/{slug}/work.md`
- `./selves/{slug}/persona.md`
- `./selves/{slug}/principles.md`
- `./selves/{slug}/recovery.md`
- `./selves/{slug}/SKILL.md`
- `./selves/{slug}/meta.json`
- `./selves/{slug}/versions/`

## 更新流程

### 新资料更新

处理顺序：

1. 读取新资料
2. 读取现有四层文件
3. 参考 `prompts/merger.md` 判断增量归属
4. 只生成相关层 patch
5. 调用 `skill_writer.py --action update`
6. 自动刷新四层文件、组合 `SKILL.md`、四个子 skill

示例：

```bash
python3 tools/skill_writer.py --action update \
  --slug {slug} \
  --work-patch /path/to/work_patch.md \
  --base-dir ./selves
```

### correction 更新

参考 `prompts/correction_handler.md`，先把纠正归类到：

- `work`
- `persona`
- `principles`
- `recovery`

然后写入 correction JSON，再调用：

```bash
python3 tools/skill_writer.py --action update \
  --slug {slug} \
  --correction /path/to/correction.json \
  --base-dir ./selves
```

correction 优先级：

- 高于自然提炼结果
- 低于用户明确指定的核心原则

## 管理命令

列出：

```bash
python3 tools/skill_writer.py --action list --base-dir ./selves
```

回滚：

```bash
python3 tools/version_manager.py --action rollback --slug {slug} --version {version} --base-dir ./selves
```

删除：

```bash
python3 tools/skill_writer.py --action delete --slug {slug} --base-dir ./selves
```

校验：

```bash
python3 tools/validate_self_skill.py
```

冒烟：

```bash
python3 tools/smoke_test.py
```

## 失败回退规则

- 采集器失败：退回手工导入
- 个人微信本地库不可读：退回 `wechat_export_adapter.py`
- 只拿到部分资料：先生成可工作的最小版
- 更新内容只影响一层：只更新该层，不重写全部
- 任何宿主都不允许改产物结构或字段定义

## 运行优先级

组合版 self skill 必须按以下顺序运行：

1. 用户即时指令
2. correction
3. principles
4. recovery
5. persona
6. work

禁止做法：

- 过度角色扮演
- 把坏习惯直接升格为主规则
- 把“像你”做成夸张模仿
