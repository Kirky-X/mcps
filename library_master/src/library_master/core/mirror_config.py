"""镜像源配置管理器

提供多镜像源配置、故障转移和健康检查功能。
"""

import os
import asyncio
import logging
from datetime import datetime, timedelta
from dataclasses import dataclass
from typing import Dict, List, Optional, Any
from enum import Enum

logger = logging.getLogger(__name__)


class Language(Enum):
    """支持的编程语言"""
    RUST = "rust"
    PYTHON = "python"
    NODE = "node"
    JAVA = "java"
    GO = "go"
    CPP = "cpp"


@dataclass
class FailureRecord:
    """故障记录"""
    url: str
    failure_count: int
    last_failure: datetime
    consecutive_failures: int


class MCPMirrorConfig:
    """MCP服务镜像源配置管理器"""
    
    def __init__(self):
        self.config = self._load_config()
        self._validate_config()
    
    def _load_config(self) -> Dict[str, Any]:
        """从环境变量加载配置"""
        config = {}
        
        # 支持的语言列表
        languages = ['RUST', 'PYTHON', 'NODE', 'JAVA', 'GO', 'CPP']
        
        for lang in languages:
            lang_config = {
                'primary_url': os.getenv(f'{lang}_MIRROR_PRIMARY_URL'),
                'mirror_urls': self._parse_urls(os.getenv(f'{lang}_MIRROR_URLS', '')),
                'timeout': int(os.getenv(f'{lang}_MIRROR_TIMEOUT', '30')),
                'retry_count': int(os.getenv(f'{lang}_MIRROR_RETRY_COUNT', '3'))
            }
            config[lang.lower()] = lang_config
        
        return config
    
    def _parse_urls(self, urls_str: str) -> List[str]:
        """解析URL列表"""
        if not urls_str:
            return []
        return [url.strip() for url in urls_str.split(',') if url.strip()]
    
    def _validate_config(self) -> None:
        """验证配置有效性"""
        for lang, config in self.config.items():
            # 不再为缺少primary_url输出警告，因为会使用默认URL
            # 只在调试模式下记录信息
            if not config['primary_url']:
                logger.debug(f"No primary URL configured for {lang}, will use default URLs")
            
            if config['timeout'] <= 0:
                raise ValueError(f"Invalid timeout for {lang}: {config['timeout']}")
    
    def get_urls_for_language(self, language: Language) -> List[str]:
        """获取指定语言的所有URL（主源+镜像源）"""
        lang_key = language.value.lower()
        config = self.config.get(lang_key, {})
        
        urls = []
        if config.get('primary_url'):
            urls.append(config['primary_url'])
        
        urls.extend(config.get('mirror_urls', []))
        
        return urls
    
    def get_config_for_language(self, language: Language) -> Dict[str, Any]:
        """获取指定语言的完整配置"""
        lang_key = language.value.lower()
        return self.config.get(lang_key, {})
    
    def get_default_urls(self, language: Language) -> List[str]:
        """获取默认的官方源URL"""
        default_urls = {
            Language.RUST: ["https://crates.io/api/v1"],
            Language.PYTHON: ["https://pypi.org/pypi"],
            Language.NODE: ["https://registry.npmjs.org"],
            Language.JAVA: ["https://search.maven.org/solrsearch/select"],
            Language.GO: ["https://proxy.golang.org"],
            Language.CPP: ["https://center.conan.io"]
        }
        return default_urls.get(language, [])
    
    def get_effective_urls(self, language: Language) -> List[str]:
        """获取有效的URL列表（配置的URL + 默认URL）"""
        configured_urls = self.get_urls_for_language(language)
        if configured_urls:
            return configured_urls
        
        # 如果没有配置，返回默认URL
        return self.get_default_urls(language)


class MCPFailoverManager:
    """MCP服务故障转移管理器"""
    
    def __init__(self, circuit_breaker_threshold: int = 5, 
                 recovery_timeout: int = 300):
        self.circuit_breaker_threshold = circuit_breaker_threshold
        self.failure_threshold = circuit_breaker_threshold  # 添加failure_threshold别名
        self.recovery_timeout = recovery_timeout
        self.failure_records: Dict[str, FailureRecord] = {}
        self._lock = asyncio.Lock()
    
    async def is_url_available(self, url: str) -> bool:
        """检查URL是否可用（熔断器模式）"""
        async with self._lock:
            record = self.failure_records.get(url)
            
            if not record:
                return True
            
            # 检查是否超过熔断阈值
            if record.consecutive_failures >= self.circuit_breaker_threshold:
                # 检查是否到了恢复时间
                recovery_time = record.last_failure + timedelta(seconds=self.recovery_timeout)
                if datetime.now() < recovery_time:
                    return False
                else:
                    # 重置连续失败计数，给一次恢复机会
                    record.consecutive_failures = 0
            
            return True
    
    async def record_success(self, url: str) -> None:
        """记录成功请求"""
        async with self._lock:
            if url in self.failure_records:
                # 重置失败记录
                self.failure_records[url].consecutive_failures = 0
    
    async def record_failure(self, url: str) -> None:
        """记录失败请求"""
        async with self._lock:
            now = datetime.now()
            
            if url not in self.failure_records:
                self.failure_records[url] = FailureRecord(
                    url=url,
                    failure_count=1,
                    last_failure=now,
                    consecutive_failures=1
                )
            else:
                record = self.failure_records[url]
                record.failure_count += 1
                record.last_failure = now
                record.consecutive_failures += 1
    
    async def get_available_urls(self, urls: List[str]) -> List[str]:
        """获取可用的URL列表"""
        available_urls = []
        for url in urls:
            if await self.is_url_available(url):
                available_urls.append(url)
        return available_urls
    
    def get_failure_stats(self) -> Dict[str, Dict[str, Any]]:
        """获取故障统计信息"""
        stats = {}
        for url, record in self.failure_records.items():
            stats[url] = {
                'total_failures': record.failure_count,
                'consecutive_failures': record.consecutive_failures,
                'last_failure': record.last_failure.isoformat(),
                'is_circuit_open': record.consecutive_failures >= self.circuit_breaker_threshold
            }
        return stats
    
    async def health_check(self, url: str, timeout: int = 10) -> bool:
        """对指定URL进行健康检查"""
        import httpx
        
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.head(url)
                return response.status_code < 500
        except Exception as e:
            logger.debug(f"Health check failed for {url}: {e}")
            return False
    
    async def periodic_health_check(self, urls: List[str], interval: int = 60) -> None:
        """定期健康检查"""
        while True:
            for url in urls:
                is_healthy = await self.health_check(url)
                if not is_healthy:
                    await self.record_failure(url)
                else:
                    await self.record_success(url)
            
            await asyncio.sleep(interval)