### 技术栈

| 技术组件 | 版本 | 用途 | 选择原因 |
|---------|------|------|----------|
| **LangGraph** | 0.6.6 | AI工作流引擎 | 提供结构化的AI代理编排能力，支持复杂的多步骤推理流程 |
| **Python** | 3.11+ | 核心开发语言 | 丰富的AI生态系统，与LangGraph完美集成 |
| **SQLite** | 3.45+ | 本地数据存储 | 轻量级、无服务器、支持复杂查询的嵌入式数据库 |
| **sqlite-vss** | 0.1.2 | 向量搜索扩展 | SQLite向量搜索扩展，支持语义搜索 |
| **LangChain** | 0.3.27 | LLM框架核心 | 统一LLM接口抽象，支持多种模型提供商 |
| **LangChain-Community** | 0.3.29 | 社区集成包 | 丰富的第三方LLM和工具集成 |
| **LangChain-OpenAI** | 0.3.32 | OpenAI集成 | GPT模型和嵌入服务的官方集成 |
| **LangChain-Anthropic** | 0.3.19 | Anthropic集成 | Claude模型的官方集成支持 |
| **LangChain-Ollama** | 0.3.7 | Ollama集成 | 本地模型部署和嵌入生成支持 |
| **MCP Python SDK** | 1.13.1 | MCP协议实现 | 最新版本的MCP Python SDK，提供标准化的MCP服务器和客户端实现 |
| **FastAPI** | 0.116.1 | Web框架 | 高性能异步Web框架，用于构建API服务 |
| **Uvicorn** | 0.35.0 | ASGI服务器 | 高性能ASGI服务器，支持异步Web应用 |
| **Pydantic** | 2.11.7 | 数据验证 | 强类型数据验证和序列化库 |
| **Pytest** | 8.4.1 | 测试框架 | Python生态系统中最流行的测试框架 |

### 开发指导

- 严格按照《MCP-DevAgent-技术架构文档.md》文档进行开发。

### 开发环境

- 使用conda创建虚拟环境进行开发
- 使用uv作为包管理器
- 使用pytest作为测试框架
