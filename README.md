# MCP 仓库总览

本仓库为 MCP（Model Context Protocol）多服务模块的单体仓库，当前已包含 Git 服务模块 `mcp-git`（位于 `services/git`）。

主要目标：
- 提供可复用、可观测、生产级的 MCP 服务器实现
- 通过统一的协议向 AI 代理暴露工具能力
- 按模块划分服务，统一版本与发布流程

目录结构：
- `services/git`：Git 操作 MCP 服务模块（基于 `pygit2`/`libgit2`）
- `.github/workflows`：CI/CD 工作流（包含 `mcp-git` 发布流程）

快速开始：
- 安装：`uv pip install mcp-git`
- 运行：`uv run mcp-git --debug`

发布约定：
- 使用带前缀的标签进行发布：`mcp-git-vX.Y.Z`
- GitHub Action 会在推送上述标签后自动构建并创建 Release，附带 `wheel` 与 `sdist` 构件

版本策略：
- 统一遵循语义化版本
- 当前 `mcp-git` 版本：`0.1.0`

更多信息：
- 模块文档参见 `services/git/README.md`
