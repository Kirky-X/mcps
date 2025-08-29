# LibraryMaster 版本发布记录

## v0.1.1 (2025-08-28)

### 🚀 新功能

#### Context7 API集成
- **search_libraries**: 集成Context7搜索API，支持跨语言库搜索
  - 支持自然语言查询和编程语言过滤
  - 返回相关库、文档和代码示例
  - 包含相关性评分和详细信息
  - 支持结果数量限制（1-50个）
- **get_library_docs**: 集成Context7文档API，获取库文档内容
  - 支持指定库路径（username/library格式）
  - 支持多种文档类型（readme、api、tutorial、examples）
  - 可按主题过滤文档内容
  - 支持token数量限制控制（100-10000）
- **context7_health_check**: Context7 API健康状态检查
  - 实时监控API可用性
  - 提供详细的状态信息和时间戳
- 支持通过环境变量`LIBRARYMASTER_CONTEXT7_API_KEY`配置API密钥
- 自动缓存搜索和文档结果，提升响应速度

#### 缓存系统重构
- 使用`cacheout`库重新实现缓存管理器
- 提升缓存性能和可靠性
- 支持更灵活的TTL（生存时间）配置
- 改进的LRU（最近最少使用）淘汰策略
- 保持完全向后兼容的API接口
- 增强的并发安全性

### 🔧 改进
- 优化错误处理和日志记录
- 增强API响应格式的一致性
- 改进并发处理性能
- 更好的资源管理和内存使用

### 📚 文档更新
- 更新API参考文档，包含Context7工具详细说明
- 添加环境变量配置指南
- 完善集成示例和使用场景
- 新增缓存配置和性能调优指南

### 🧪 测试
- 新增Context7工具完整测试套件
- 添加缓存性能基准测试
- 完善错误场景和边界条件测试覆盖
- 集成测试和端到端测试增强

### ⚙️ 技术细节
- **依赖更新**: 添加`cacheout>=0.16.0`用于缓存管理
- **版本号**: 0.1.0 → 0.1.1
- **Python兼容性**: >=3.10
- **新增环境变量**:
  - `LIBRARYMASTER_CONTEXT7_API_KEY`: Context7 API密钥（必需）
  - `LIBRARYMASTER_CONTEXT7_BASE_URL`: Context7 API基础URL（可选，默认https://context7.com/api/v1）
- **API端点**: 严格按照Context7 API v1规范实现
- **认证方式**: Bearer Token认证
- **请求方式**: RESTful GET请求

### 🔄 兼容性
- ✅ 完全向后兼容
- ✅ 现有MCP工具无变化
- ✅ 现有配置继续有效
- ✅ 无破坏性更改

### 📋 已知问题
- Context7 API需要有效的API密钥才能使用
- 首次使用时缓存为空，响应时间可能较长

---

## v0.1.0 (2025-08-XX)

### 🚀 初始发布

#### 核心功能
- **find_latest_versions**: 批量查询库的最新版本信息
  - 支持多种编程语言
  - 异步批量处理
  - 智能缓存机制
- **find_library_docs**: 批量查询库的官方文档链接
  - 自动识别官方文档源
  - 支持多种文档格式
  - 缓存文档链接信息
- **check_versions_exist**: 批量检查指定版本是否存在
  - 精确版本验证
  - 支持版本范围查询
  - 快速批量检查
- **find_library_dependencies**: 批量查询库的依赖关系
  - 递归依赖分析
  - 依赖版本信息
  - 依赖图构建支持
- **get_cache_stats**: 获取缓存统计信息
  - 缓存命中率统计
  - 内存使用情况
  - 性能指标监控
- **clear_cache**: 清空缓存数据
  - 支持选择性清理
  - 安全的缓存重置

#### 支持的编程语言
- **Rust**: 通过crates.io API
- **Python**: 通过PyPI API
- **Java**: 通过Maven Central API
- **Node.js**: 通过npm API

#### 技术特性
- 基于MCP (Model Context Protocol)协议
- 异步批量处理架构
- 智能缓存机制，提升响应速度
- 完善的错误处理和重试机制
- 全面的测试覆盖（单元测试、集成测试）
- 结构化日志记录

#### 集成支持
- Claude Desktop无缝集成
- 环境变量灵活配置
- Docker容器化部署支持
- 跨平台兼容性

#### 性能特点
- 并发请求处理
- 智能请求去重
- 自适应超时机制
- 内存高效的缓存策略

---

## 版本规划

### v0.1.2 (计划中)
- 性能优化和监控增强
- 更多Context7功能集成
- 用户反馈收集和改进
- 缓存策略优化

### v0.2.0 (计划中)
- 新的编程语言支持（Go、C#、PHP等）
- 高级缓存策略（分层缓存、持久化缓存）
- 分布式部署支持
- Web界面管理工具

### v0.3.0 (计划中)
- AI驱动的库推荐系统
- 安全漏洞检测集成
- 许可证兼容性分析
- 企业级功能支持

---

## 贡献指南

### 如何贡献
1. Fork项目仓库
2. 创建功能分支
3. 提交代码更改
4. 编写测试用例
5. 提交Pull Request

### 开发环境设置
```bash
# 克隆仓库
git clone https://github.com/your-org/LibraryMaster.git
cd LibraryMaster

# 安装依赖
pip install -e .
pip install -e ".[dev]"

# 运行测试
pytest test/

# 代码格式化
black src/
ruff check src/
```

### 发布流程
1. 更新版本号
2. 更新Release.md
3. 运行完整测试套件
4. 创建Git标签
5. 发布到PyPI

---

## 支持与反馈

- **问题报告**: [GitHub Issues](https://github.com/your-org/LibraryMaster/issues)
- **功能请求**: [GitHub Discussions](https://github.com/your-org/LibraryMaster/discussions)
- **文档**: [API Reference](./API_REFERENCE.md)
- **示例**: [Examples Directory](../examples/)

---

## 许可证

本项目采用Apache 2.0许可证。详见[LICENSE](../../LICENSE)文件。

注：本项目是monorepo仓库的一部分，许可证文件位于仓库根目录。