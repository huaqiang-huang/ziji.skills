# 四层 Correction 处理 Prompt

## 任务

识别用户的纠正意图，并将其归入四层之一：

- Work
- Persona
- Principles
- Recovery

---

## 常见触发语义

- “这不像我”
- “我其实会这样”
- “我不会这么做”
- “这个是我想保留的”
- “这个是我想改掉的”
- “我遇到这种情况通常会……”

---

## 归属规则

- 工作方法、任务推进、交付规范 → `work`
- 表达方式、互动姿态、风格 → `persona`
- 原则、边界、取舍、优先级 → `principles`
- 遇阻换路、自检、复盘、恢复 → `recovery`

如果一句 correction 同时命中多层：

- 先选最稳定、最上位的一层
- 优先级：`principles > recovery > persona > work`

---

## 输出格式

```text
layer: {work|persona|principles|recovery}
line: - [场景：{场景}] 不应该 {错误行为}，应该 {正确行为}
```

如果用户表达的是“这个是旧习惯，不要放大”，也按相同格式记录，但正确行为写成理想版。

Correction 的执行优先级：

- 低于用户明确指定的核心原则
- 高于自然提炼结果
