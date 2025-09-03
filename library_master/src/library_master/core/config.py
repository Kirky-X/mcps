"""配置管理模块"""

from typing import Optional
from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """应用配置"""
    
    # 服务器配置
    server_name: str = Field(default="LibraryMaster", description="MCP服务器名称")
    log_level: str = Field(default="INFO", description="日志级别")
    
    # 并发配置
    max_workers: int = Field(default=10, description="最大工作线程数")
    request_timeout: float = Field(default=30.0, description="请求超时时间(秒)")
    
    # 缓存配置
    cache_ttl: int = Field(default=3600, description="缓存TTL(秒)")
    cache_max_size: int = Field(default=1000, description="缓存最大条目数")
    
    # API配置
    rust_api_base: str = Field(default="https://crates.io/api/v1", description="Rust API基础URL")
    python_api_base: str = Field(default="https://pypi.org/pypi", description="Python API基础URL")
    java_api_base: str = Field(default="https://search.maven.org/solrsearch/select", description="Java API基础URL")
    node_api_base: str = Field(default="https://registry.npmjs.org", description="Node.js API基础URL")
    go_api_base: str = Field(default="https://proxy.golang.org", description="Go API基础URL")
    cpp_api_base: str = Field(default="https://center.conan.io", description="C++ API基础URL")
    
    # Context7 API配置
    context7_api_key: Optional[str] = Field(
        default=None,
        description="Context7 API密钥"
    )
    context7_base_url: str = Field(
        default="https://context7.com/api/v1",
        description="Context7 API基础URL"
    )
    
    # 镜像源配置
    # Python镜像源
    python_mirrors: str = Field(
        default="https://pypi.org/simple,https://pypi.tuna.tsinghua.edu.cn/simple,https://mirrors.aliyun.com/pypi/simple",
        description="Python镜像源列表，用逗号分隔"
    )
    
    # Node.js镜像源
    node_mirrors: str = Field(
        default="https://registry.npmjs.org,https://registry.npmmirror.com,https://registry.npm.taobao.org",
        description="Node.js镜像源列表，用逗号分隔"
    )
    
    # Rust镜像源
    rust_mirrors: str = Field(
        default="https://crates.io,https://rsproxy.cn,https://mirrors.ustc.edu.cn/crates.io-index",
        description="Rust镜像源列表，用逗号分隔"
    )
    
    # Java镜像源
    java_mirrors: str = Field(
        default="https://repo1.maven.org/maven2,https://maven.aliyun.com/repository/public,https://mirrors.huaweicloud.com/repository/maven",
        description="Java镜像源列表，用逗号分隔"
    )
    
    # Go镜像源
    go_mirrors: str = Field(
        default="https://proxy.golang.org,https://goproxy.cn,https://goproxy.io",
        description="Go镜像源列表，用逗号分隔"
    )
    
    # C++镜像源
    cpp_mirrors: str = Field(
        default="https://center.conan.io,https://conan.bintray.com",
        description="C++镜像源列表，用逗号分隔"
    )
    
    # 故障转移配置
    mirror_failure_threshold: int = Field(
        default=3,
        description="镜像源故障阈值"
    )
    mirror_recovery_timeout: int = Field(
        default=300,
        description="镜像源恢复超时时间(秒)"
    )
    mirror_health_check_interval: int = Field(
        default=60,
        description="镜像源健康检查间隔(秒)"
    )
    mirror_request_timeout: float = Field(
        default=10.0,
        description="镜像源请求超时时间(秒)"
    )
    
    # 缓存类型配置
    cache_type: str = Field(
        default="cacheout",
        description="缓存类型 (memory|cacheout)"
    )
    cache_default_ttl: int = Field(
        default=3600,
        description="默认缓存TTL(秒)"
    )
    cache_max_entries: int = Field(
        default=1000,
        description="最大缓存条目数"
    )
    
    class Config:
        env_prefix = "LIBRARYMASTER_"
        case_sensitive = False
        env_file = ".env"