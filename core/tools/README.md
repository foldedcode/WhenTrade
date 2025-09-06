# 工具系统目录结构

## 目录说明

- **legacy/** - 传统工具系统，包含技术分析和情绪分析工具
- **builtin/** - 内置工具（预留）
- **mcp/** - MCP（Model Context Protocol）工具（预留）
- **user/** - 用户自定义工具（预留）

## 当前状态

目前只有 legacy 目录包含实际的工具实现。其他目录为未来扩展预留。

## 工具接口

所有工具都应该继承自相应的基类：
- Legacy 工具：继承自 `core.tools.legacy.base.BaseTool`
- 未来的新工具：可能使用 `core.base.BaseToolInterface`