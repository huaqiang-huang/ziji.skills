# Contributing

欢迎贡献。

## 开始前

- Python 3.9+
- `pip3 install -r requirements.txt`

建议先跑：

```bash
python3 tools/validate_self_skill.py
python3 tools/smoke_test.py
python3 tools/wechat_smoke_test.py
```

## 提交方向

优先欢迎这些贡献：

- 新的数据输入源
- 解析器兼容性修复
- 微信导出工具适配增强
- 文档和示例完善
- CI / 测试补充

## 约定

- 不要改动 `selves/{slug}/` 产物结构
- 不要新增与现有 `meta.json` 不兼容的字段
- 微信本地解析相关能力默认按“实验能力”处理
- 优先保持只读，不要对原始聊天目录做写操作

## PR 建议

- 描述变更目标
- 说明影响范围
- 附上验证命令和结果
