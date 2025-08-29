# TimeMaster MCP

[English Documentation](README.md) | [API参考文档](API_REFERENCE.md) | [版本说明](RELEASE_NOTES.md)

一个强大的 MCP（模型上下文协议）时间管理和时区操作服务。TimeMaster 通过标准化的 MCP 接口为 AI 应用程序提供全面的时间、时区和节假日查询功能。

## 核心 MCP 功能

- **统一时间操作**：通过单一接口获取当前时间、时区转换
- **智能时区管理**：自动检测、搜索和转换功能
- **全面节假日支持**：按名称、国家和日期范围查询节假日
- **AI 就绪集成**：标准化 MCP 协议，无缝 AI 应用程序集成
- **灵活配置**：支持环境变量和配置文件
- **离线模式支持**：无需互联网连接，使用系统数据
- **多语言支持**：跨不同语言环境的一致功能

## 安装

```bash
pip install time-master
```

## v0.1.2 版本新特性

- **🔄 统一时间接口**：新的 `get_time` MCP 工具通过可选参数替代 `get_current_time` 和 `convert_time`
- **🌐 自动时区检测**：MCP 服务自动检测时区（网络优先，系统回退）
- **🔧 环境变量控制**：使用 `TIMEMASTER_OFFLINE_MODE=true` 进行离线模式配置
- **🔍 增强搜索**：`search_timezones` 工具现在支持空查询以列出所有时区
- **🎉 节假日搜索**：新的 `search_holiday` 工具按名称查找节假日
- **📋 统一节假日格式**：所有节假日工具现在返回一致的字典格式
- **⚠️ 向后兼容性**：已弃用的工具仍然有效，但显示迁移警告

## 使用方法

TimeMaster 主要通过 MCP（模型上下文协议）服务为 AI 应用程序提供时间管理功能。

### MCP 服务用于 AI 集成

TimeMaster 提供了一个 [MCP（模型上下文协议）](https://modelcontextprotocol.io/) 服务，用于使用标准 STDIO 传输进行 AI 集成。

```bash
# 启动 MCP 服务
python -m time_master.mcp_service

# 或使用自定义配置
TIMEMASTER_OFFLINE_MODE=true python -m time_master.mcp_service
```

### 可用的 MCP 工具

**核心时间工具 (v0.1.2+)**

- **`get_time`** - 统一时间接口，获取当前时间或进行时区转换
- **`get_local_timezone`** - 获取本地系统时区
- **`search_timezones`** - 搜索匹配的时区，支持空查询列出所有时区
- **`calculate_time_difference`** - 计算两个不同时区时间之间的差值

**节假日工具 (v0.1.2+)**

- **`search_holiday`** - 按名称搜索节假日，返回日期、剩余天数和假期时长
- **`list_holidays`** - 列出特定国家和年份的所有节假日

**已废弃的工具 (Deprecated)**
- `get_next_holiday` - ⚠️ 请使用 `search_holiday("")` 替代
- `calculate_days_to_holiday` - ⚠️ 请使用 `search_holiday(holiday_name)` 替代
- `get_current_time` - ⚠️ 请使用 `get_time()` 替代
- `convert_time` - ⚠️ 请使用 `get_time()` 带参数替代

### MCP 工具参数

**`get_time`**
- `timezone` (可选): 目标时区，默认为本地时区
- `time_str` (可选): 要转换的时间字符串，如果不提供则获取当前时间
- `from_tz` (可选): 源时区，当提供time_str时必需
- `format` (可选): 输出格式，'iso'或'friendly_cn'，默认'iso'

**`search_timezones`**
- `query` (可选): 时区名称搜索查询，空字符串返回所有时区
- `limit` (可选): 最大返回结果数，默认20

**`search_holiday`**
- `query` (可选): 节假日名称搜索查询，空字符串返回下一个节假日
- `country` (可选): ISO国家代码 (如 'US', 'GB', 'FR')
- `timezone` (可选): 用于推断国家的时区
- `year` (可选): 年份，默认当前年份
- `limit` (可选): 最大返回结果数，默认10

**`list_holidays`**
- `country` (可选): ISO国家代码
- `timezone` (可选): 用于推断国家的时区
- `year` (可选): 年份，默认当前年份

**`calculate_time_difference`**
- `time1` (必需): 第一个时间字符串
- `tz1` (必需): 第一个时间的时区
- `time2` (必需): 第二个时间字符串
- `tz2` (必需): 第二个时间的时区

### 与 MCP 客户端集成
```json
{
  "mcpServers": {
    "time-master": {
      "command": "uv",
      "args": ["run", "-m", "time_master.mcp_service"],
      "cwd": "/path/to/time-master"
    }
  }
}
```

## 配置

### 环境变量配置

```bash
# 设置离线模式（禁用网络节假日数据）
export TIMEMASTER_OFFLINE_MODE=true

# 设置默认时区
export TIMEMASTER_DEFAULT_TIMEZONE="Asia/Shanghai"

# 设置默认国家（用于节假日查询）
export TIMEMASTER_DEFAULT_COUNTRY="CN"
```

### MCP 服务启动

```bash
# 使用默认配置启动
python -m time_master.mcp_service

# 使用环境变量配置启动
TIMEMASTER_OFFLINE_MODE=true TIMEMASTER_DEFAULT_TIMEZONE="Asia/Shanghai" python -m time_master.mcp_service
```

详细的 Python API 配置和使用方法，请参考 [API 参考文档](API_REFERENCE.md)。

## 开发设置

```bash
# 安装依赖
pip install -e ".[dev]"

# 格式化代码
black time-master/
ruff check time-master/

# 运行 MCP 服务进行测试
python -m time_master.mcp_service
```

## 许可证

本项目采用 Apache 2.0 许可证 - 详情请参阅 [LICENSE](../../LICENSE) 。

注：本项目是 monorepo 仓库的一部分，许可证文件位于仓库根目录。