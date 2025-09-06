# MCP-DevAgent

> 🤖 基于模型上下文协议(MCP)的智能AI开发助手

一个专为现代软件开发工作流程设计的智能AI助手，结合先进的AI能力与强大的代码分析、搜索和生成功能。

## ✨ 功能特性

- **AI代码分析**: 智能代码理解和语义分析
- **混合搜索**: 结合全文搜索和向量相似性搜索
- **MCP协议**: 完全兼容模型上下文协议标准
- **多模型支持**: 支持OpenAI、Anthropic、Ollama等多种AI模型

## 🚀 快速开始

### 先决条件
- Python 3.11+
- SQLite 3.45+
- 4GB+ RAM

### 安装
```bash
# 克隆仓库
git clone <repository-url>
cd dev_master

# 创建虚拟环境
python -m venv .venv
source .venv/bin/activate

# 安装依赖
pip install -r requirements.txt
```

### 配置
```bash
# 设置API密钥
export OPENAI_API_KEY="your-api-key"
```

### 运行
```bash
# 启动服务器
python -m mcp_devagent.main

# 测试连接
curl http://localhost:8000/health
```

## 📖 使用方法

### 代码搜索
```python
from mcp_devagent import DevAgent

agent = DevAgent()
results = agent.search("function definition")
```

### 代码分析
```python
analysis = agent.analyze_file("src/main.py")
print(analysis.summary)
```

---

## 项目信息

- **许可证**: [MIT](../LICENSE) (monorepo)
- **最后更新**: 2025年9月6日
- **所属项目**: MCP工具集合仓库