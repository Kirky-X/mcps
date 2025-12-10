# Prompt Manager MCP

[中文文档](README_ZH.md) | [API Reference](docs/API_REFERENCE.md) | [Release Notes](docs/RELEASE.md)

一个基于 SQLite 构建的企业级 Prompt 版本管理系统，提供全面的 CRUD 接口、语义搜索、版本控制和多客户端适配能力，集成多种 LLM 客户端（OpenAI、Anthropic 等）。

> ⚠️ **注意**：语义搜索功能需要配置正确的 API 密钥以生成 Embedding。

## 版本特性 (v1.0.0)

### 🧹 项目优化与清理

- 🗂️ **代码结构优化**：模块化架构，清晰分离关注点（调用层、业务逻辑层、缓存层、数据访问层、存储层）
- 🧽 **缓存管理**：智能进程内缓存（moka-py），1小时 TTL，实现最佳性能
- ✅ **质量验证**：全面的测试套件，覆盖单元测试、集成测试和端到端场景
- 📁 **目录组织**：遵循 Python 最佳实践的标准化项目布局
- 🚀 **性能增强**：基于 SQLite 的核心，查询响应时间 <500ms

### 🌟 核心特性

- 📦 **版本管理**：完整的 Prompt 版本控制，支持历史追踪和多版本共存
- 🔍 **语义搜索**：基于 sqlite-vec 的向量语义搜索，快速发现 Prompt
- 🔄 **客户端适配**：自动适配不同的 LLM 客户端（OpenAI、Anthropic 等）
- 🧩 **动态组装**：支持占位符替换和动态原则注入
- 📊 **标准输出**：OpenAI 兼容格式，降低集成成本

## 快速开始

### 安装

```bash
# 克隆仓库
git clone https://gitee.com/kirky-x/prompts.git
cd prompts

# 安装 uv (如果尚未安装)
curl -LsSf https://astral.sh/uv/install.sh | sh

# 安装项目依赖
uv sync

# 初始化数据库
uv run python init_db.py
```

### 环境配置

启动服务前配置必要的环境变量：

```bash
# 数据库配置
export PROMPT_MANAGER_DB_PATH="./data/prompts.db"

# 认证密钥 (用于 HTTP Server)
export FASTAPI_USERS_JWT_SECRET="your_jwt_secret"
export FASTAPI_USERS_RESET_SECRET="your_reset_secret"
export FASTAPI_USERS_VERIFY_SECRET="your_verify_secret"

# Embedding 配置 (可选，用于语义搜索)
export OPENAI_API_KEY="your_openai_api_key"

# 缓存配置 (可选)
export PROMPT_MANAGER_CACHE_ENABLED=true
export PROMPT_MANAGER_CACHE_TTL=3600
```

### MCP 服务设置

```bash
# 启动 MCP 服务 (Claude)
uv run -m prompt_manager.mcp_server

# 或者使用自定义配置
PROMPT_MANAGER_DB_PATH=./custom.db uv run -m prompt_manager.mcp_server
```

## 可用 MCP 工具

### 核心 Prompt 管理工具

- **`create_prompt`** - 创建新 Prompt 或版本
- **`search_prompts`** - 通过查询或标签搜索 Prompt
- **`get_prompt`** - 通过名称和版本获取特定 Prompt
- **`update_prompt`** - 更新现有 Prompt 元数据或内容

### Prompt 操作工具

- **`delete_prompt`** - 软删除 Prompt 版本
- **`activate_prompt`** - 激活非活动 Prompt 版本
- **`manage_principles`** - 创建和管理 Prompt 原则

详细 API 文档请参考 [API Reference](docs/API_REFERENCE.md)。

## ⚙️ 配置

### MCP 客户端配置

```json
{
  "mcpServers": {
    "prompt-manager": {
      "command": "uv",
      "args": [
        "run",
        "--with",
        "git+https://gitee.com/kirky-x/prompts.git",
        "prompt-manager"
      ]
    }
  }
}
```

## 测试

Prompt Manager 使用 pytest 进行测试。请在项目根目录运行测试：

```bash
# 运行所有测试
uv run pytest

# 运行带覆盖率的测试
uv run pytest --cov=src/prompt_manager
```

## 许可证

本项目基于 MIT 许可证授权 - 详见 [LICENSE](LICENSE) 文件。

注意：本项目是 monorepo 的一部分，许可证文件位于仓库根目录。
