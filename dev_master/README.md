# MCP-DevAgent

**AI-Powered Development Assistant**

MCP-DevAgent is an AI development assistant built on the Model Context Protocol (MCP). It provides intelligent code understanding, semantic search, and AI-powered development assistance for modern development workflows.

## Features

- **AI Code Analysis**: Semantic understanding of code structure and relationships
- **Hybrid Search**: Combines full-text search (FTS5) with vector similarity search (VSS)
- **MCP Protocol**: Full compliance with Model Context Protocol 1.0
- **Multi-Model Support**: Works with OpenAI, Anthropic, and local Ollama models

## Quick Start

### Prerequisites
- Python 3.11+
- Git

### Installation

```bash
# Clone repository
git clone https://github.com/mcp-devagent/mcp-devagent.git
cd mcp-devagent

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Install dependencies
pip install -e .
```

### Configuration

1. Copy environment file:
   ```bash
   cp .env.example .env
   ```

2. Configure API key (choose one):
   ```env
   OPENAI_API_KEY=sk-your-openai-key
   # OR
   ANTHROPIC_API_KEY=your-anthropic-key
   # OR
   OLLAMA_BASE_URL=http://localhost:11434
   ```

### Run

```bash
# Start the server
python -m mcp_devagent.main

# Test connection
curl http://localhost:8000/health
```

## Usage

### Code Search
```python
import asyncio
from mcp_devagent import MCPClient

async def search_code():
    client = MCPClient("http://localhost:8000")
    results = await client.search(query="authentication middleware")
    for result in results:
        print(f"File: {result.file_path}")
        print(f"Context: {result.context}")

asyncio.run(search_code())
```

### Code Analysis
```python
async def analyze_code():
    client = MCPClient("http://localhost:8000")
    analysis = await client.analyze_code(file_path="src/main.py")
    print(f"Quality Score: {analysis.quality_score}")
    print(f"Suggestions: {analysis.suggestions}")

asyncio.run(analyze_code())
```

---

## Project Info

- **License**: [MIT](../LICENSE) (monorepo)
- **Last Updated**: September 6, 2025
- **Part of**: MCP Tools Monorepo