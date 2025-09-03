# LibraryMaster 版本发布记录

## v0.1.3 (2025-09-20)

### 🚀 新功能

#### 镜像源配置与故障转移系统
- **多镜像源支持**: 为所有支持的语言配置镜像源
  - Rust: 支持中科大、清华、上海交大等镜像源
  - Python: 支持阿里云、清华、豆瓣等镜像源
  - Java: 支持阿里云、华为云等Maven镜像源
  - Node.js: 支持淘宝、华为云等npm镜像源
  - Go: 支持七牛云、阿里云等Go模块代理
  - C++: 支持vcpkg和Conan镜像源
- **智能故障转移**: 自动检测镜像源健康状态，故障时自动切换
- **镜像源健康监控**: 实时监控镜像源可用性和响应时间
- **配置灵活性**: 通过环境变量轻松配置镜像源优先级

#### 增强网络重试机制
- **指数退避重试**: 实现智能重试策略，避免网络拥塞
- **熔断器模式**: 防止级联故障，提升系统稳定性
- **自适应超时**: 根据网络状况动态调整请求超时时间
- **请求去重**: 避免重复请求，提升性能

#### 扩展语言支持
- **C++语言支持**: 通过vcpkg和Conan API获取包信息
  - 支持vcpkg包管理器
  - 集成Conan包仓库

#### 实时健康监控
- **系统健康检查**: 全面监控各组件健康状态
- **性能指标收集**: 实时收集响应时间、成功率等指标
- **告警机制**: 异常情况自动告警

### 🔧 改进
- 优化缓存策略，提升命中率
- 增强并发处理能力
- 改进错误处理和日志记录
- 提升API响应一致性
- 优化内存使用和资源管理

### 📚 文档更新
- 更新API参考文档，包含新增语言支持
- 添加镜像源配置详细指南
- 完善故障转移和监控文档
- 新增Go和C++集成示例

### 🧪 测试增强
- 新增镜像源故障转移测试
- 添加网络重试机制测试
- 完善Go和C++语言支持测试
- 增强性能基准测试

### ⚙️ 技术细节
- **版本号**: 0.1.2 → 0.1.3
- **新增环境变量**:
  - 镜像源配置: `LIBRARYMASTER_*_MIRROR_URLS`
  - 网络配置: `LIBRARYMASTER_MIRROR_FALLBACK_ENABLED`、`LIBRARYMASTER_MAX_RETRIES`等
- **依赖更新**: 优化网络请求库配置
- **性能优化**: 减少内存占用，提升响应速度

### 🔄 兼容性
- ✅ 完全向后兼容
- ✅ 现有配置继续有效
- ✅ 无破坏性更改
- ✅ 平滑升级支持

---

## v0.1.2 (2025-01-22)

### 🚀 新功能

#### 镜像源配置与故障转移系统
- **镜像源配置管理器(MirrorConfigManager)**: 支持通过环境变量配置多个镜像源
  - 支持Python、Node.js、Java、Rust、Go、C++等多种语言的镜像源配置
  - 自动从环境变量读取镜像源列表（如`LIBRARYMASTER_PYTHON_MIRRORS`）
  - 支持主URL和备用镜像源的灵活配置
  - 提供镜像源健康状态监控和管理

- **故障转移管理器(FailoverManager)**: 实现熔断器模式和健康检查
  - 智能故障检测和自动切换机制
  - 熔断器模式防止级联故障
  - 自动健康检查和恢复机制
  - 可配置的故障阈值和恢复超时
  - 支持异步健康检查和状态监控

- **BaseWorker镜像源支持**: 所有Worker类现在支持镜像源配置
  - 自动故障转移到可用镜像源
  - 智能重试机制和请求分发
  - 实时镜像源健康状态监控
  - 支持动态镜像源切换和恢复

#### 环境变量配置支持
- `LIBRARYMASTER_PYTHON_MIRRORS`: Python包镜像源列表
- `LIBRARYMASTER_NODE_MIRRORS`: Node.js包镜像源列表
- `LIBRARYMASTER_JAVA_MIRRORS`: Java包镜像源列表
- `LIBRARYMASTER_RUST_MIRRORS`: Rust包镜像源列表
- `LIBRARYMASTER_GO_MIRRORS`: Go包镜像源列表
- `LIBRARYMASTER_CPP_MIRRORS`: C++包镜像源列表
- `LIBRARYMASTER_MIRROR_FAILURE_THRESHOLD`: 故障阈值配置
- `LIBRARYMASTER_MIRROR_RECOVERY_TIMEOUT`: 恢复超时配置

### 🔧 改进
- 大幅提升网络请求的可靠性和稳定性
- 优化在网络不稳定环境下的表现
- 增强错误处理和故障恢复能力
- 改进日志记录，提供更详细的故障诊断信息
- 提升并发处理性能和资源利用率

### 🧪 测试
- 新增完整的镜像源配置和故障转移测试套件
- 添加故障模拟和恢复机制测试
- 完善网络异常和边界条件测试覆盖
- 集成pytest测试框架，提供更好的测试体验

### ⚙️ 技术细节
- **版本号**: 0.1.1 → 0.1.2
- **新增核心模块**:
  - `library_master.core.mirror_config`: 镜像源配置管理
  - `library_master.core.failover`: 故障转移和健康检查
- **增强模块**:
  - `library_master.workers.base`: 基础Worker类镜像源支持
  - 所有语言特定Worker类的镜像源集成
- **配置系统**: 支持环境变量和配置文件的镜像源配置
- **监控系统**: 实时镜像源状态监控和健康检查

### 🔄 兼容性
- ✅ 完全向后兼容
- ✅ 现有配置继续有效
- ✅ 无破坏性更改
- ✅ 可选的镜像源配置，不影响现有功能

### 📋 使用示例
```bash
# 配置Python镜像源
export LIBRARYMASTER_PYTHON_MIRRORS="https://pypi.tuna.tsinghua.edu.cn/pypi,https://mirrors.aliyun.com/pypi"

# 配置Node.js镜像源
export LIBRARYMASTER_NODE_MIRRORS="https://registry.npmmirror.com,https://registry.npm.taobao.org"

# 配置故障阈值
export LIBRARYMASTER_MIRROR_FAILURE_THRESHOLD="5"
export LIBRARYMASTER_MIRROR_RECOVERY_TIMEOUT="300"
```

---

## v0.1.1 (2025-09-01)

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
- 支持通过环境变量`LIBRARYMASTER_CONTEXT7_API_KEY`配置API密钥
- 自动缓存搜索和文档结果，提升响应速度

#### 扩展语言支持
- **Go语言支持**: 通过Go模块代理API获取包信息
  - 支持go.mod解析和版本查询
  - 集成主流Go模块代理服务

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

### v0.1.4 (计划中)
- 镜像源配置的Web管理界面
- 更多Context7功能集成
- 用户反馈收集和改进
- 高级缓存策略优化
- 性能监控仪表板

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