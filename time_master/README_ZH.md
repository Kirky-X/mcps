# TimeMaster v0.1.3 - 时间助手

[English Documentation](README.md) | [API参考文档](API_REFERENCE.md) | [版本说明](Release.md)

一个强大的 MCP（模型上下文协议）时间管理服务，提供统一的中国历法接口和全面的时间、时区操作功能。

## 项目介绍

TimeMaster 是一个专为 AI 应用程序设计的时间管理服务，通过标准化的 MCP 接口提供：

- **统一中国历法接口**：通过单一方法获取完整的农历、干支、节气、生肖、黄历等信息
- **智能时间管理**：时区转换、时间计算、节假日查询
- **AI 就绪集成**：标准化 MCP 协议，无缝 AI 应用程序集成
- **多语言支持**：中英文双语界面和文档

## v0.1.3 版本特性

### 🎯 中国历法功能
- **统一接口**：`get_chinese_calendar_info()` 一次调用获取所有中国历法信息
- **农历转换**：公历与农历日期互转，支持闰月处理
- **天干地支**：完整的四柱八字计算
- **二十四节气**：精确的节气时间查询
- **生肖查询**：十二生肖及相关信息
- **黄历信息**：宜忌事项、吉凶等级等传统信息

### 🌐 时间管理功能
- **统一时间接口**：`get_time` 工具支持当前时间获取和时区转换
- **智能时区管理**：自动检测、搜索和转换功能
- **节假日查询**：按名称、国家和日期范围查询节假日
- **离线模式支持**：无需互联网连接，使用系统数据

## 安装

```bash
pip install time-master
```

## 使用方法

### MCP 服务启动

```bash
# 启动 MCP 服务
python -m time_master.mcp_service

# 使用离线模式
TIMEMASTER_OFFLINE_MODE=true python -m time_master.mcp_service
```

### 主要 MCP 工具

**中国历法工具**
- `get_chinese_calendar_info` - 获取完整的中国历法信息

**时间管理工具**
- `get_time` - 统一时间接口，获取当前时间或进行时区转换
- `search_timezones` - 搜索时区
- `search_holiday` - 搜索节假日
- `list_holidays` - 列出节假日
- `calculate_time_difference` - 计算时间差

### 与 MCP 客户端集成

```json
{
  "mcpServers": {
    "time-master": {
      "command": "uv",
      "args": [
        "run",
        "-m",
        "time_master.mcp_service"
      ],
      "cwd": "/path/to/time-master"
    }
  }
}
```

## 配置

### 环境变量

```bash
# 离线模式
export TIMEMASTER_OFFLINE_MODE=true

# 默认时区
export TIMEMASTER_DEFAULT_TIMEZONE="Asia/Shanghai"

# 默认国家
export TIMEMASTER_DEFAULT_COUNTRY="CN"
```

## 开发

```bash
# 安装依赖
pip install -e ".[dev]"

# 运行测试
python -m pytest

# 启动服务
python -m time_master.mcp_service
```

## 文档

- [API 参考文档](API_REFERENCE.md) - 详细的接口说明
- [版本说明](Release.md) - 版本历史和兼容性信息
- [English Documentation](README.md) - 英文文档

## 许可证

本项目采用 Apache 2.0 许可证 - 详情请参阅 [LICENSE](../../LICENSE) 。

注：本项目是 monorepo 仓库的一部分，许可证文件位于仓库根目录。