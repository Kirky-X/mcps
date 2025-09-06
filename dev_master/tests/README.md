# 测试目录结构

本目录包含MCP DevAgent项目的所有测试文件，按照功能和类型进行了组织。

## 目录结构

```
tests/
├── README.md                    # 本文件，测试目录说明
├── __init__.py                  # Python包初始化文件
├── docs/                        # 测试相关文档
│   ├── test_analysis_report.md  # 测试分析报告
│   └── test_optimization_plan.md # 测试优化计划
├── integration/                 # 集成测试
│   ├── test_code_generation.py  # 代码生成功能集成测试
│   ├── test_cot_functionality.py # 思维链功能集成测试
│   ├── test_database_storage.py # 数据库存储集成测试
│   ├── test_requirement_analysis.py # 需求分析集成测试
│   └── test_search_functionality.py # 搜索功能集成测试
├── test_database.py            # 数据库单元测试
├── test_embedding_service.py   # 嵌入服务单元测试
├── test_export_handler.py      # 导出处理器单元测试
├── test_export_service.py      # 导出服务单元测试
├── test_llm_service.py         # LLM服务单元测试
├── test_mcp_server.py          # MCP服务器单元测试
├── test_search_service.py      # 搜索服务单元测试
├── test_workflow.py            # 工作流单元测试
└── test_workflow_integration.py # 工作流集成测试
```

## 测试类型说明

### 单元测试 (Unit Tests)
位于tests根目录下的`test_*.py`文件，使用pytest框架编写，测试单个模块或类的功能。

**运行单元测试：**
```bash
python -m pytest tests/test_*.py -v
```

### 集成测试 (Integration Tests)
位于`tests/integration/`目录下，测试多个模块协同工作的功能。

**运行集成测试：**
```bash
python tests/integration/test_code_generation.py
python tests/integration/test_cot_functionality.py
# ... 其他集成测试
```

### 测试文档
位于`tests/docs/`目录下，包含测试相关的分析报告和优化计划。

## 运行所有测试

```bash
# 运行所有pytest测试
python -m pytest tests/ -v

# 运行特定测试文件
python -m pytest tests/test_database.py -v

# 运行特定测试方法
python -m pytest tests/test_database.py::TestDatabaseConnection::test_connection -v
```

## 测试覆盖率

```bash
# 生成测试覆盖率报告
python -m pytest tests/ --cov=src/mcp_devagent --cov-report=html
```

## 注意事项

1. 所有测试文件都应该以`test_`开头
2. 单元测试使用pytest框架，集成测试可以是独立的Python脚本
3. 测试数据库使用SQLite，位于`data/mcp_devagent.db`
4. 运行测试前确保已安装所有依赖：`uv sync`