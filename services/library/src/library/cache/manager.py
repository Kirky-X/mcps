import threading
import json
import uuid
import logging
import time
from typing import Any, Optional, Dict, Union
from datetime import timedelta

from .base import BaseCache
from .l1_moka import MokaCache
from .l2_redis import RedisCache
from .config import CacheConfig

logger = logging.getLogger(__name__)

class MultiLevelCache(BaseCache):
    def __init__(self, config: Optional[CacheConfig] = None):
        self.config = config or CacheConfig()
        self.instance_id = str(uuid.uuid4())
        
        self.l1: Optional[BaseCache] = None
        self.l2: Optional[RedisCache] = None
        
        if self.config.L1_ENABLED:
            self.l1 = MokaCache(
                max_size=self.config.L1_MAX_SIZE,
                default_ttl=self.config.L1_TTL
            )
            
        l2_init_failed = False
        if self.config.L2_ENABLED:
            try:
                self.l2 = RedisCache(
                    host=self.config.REDIS_HOST,
                    port=self.config.REDIS_PORT,
                    db=self.config.REDIS_DB,
                    password=self.config.REDIS_PASSWORD,
                    default_ttl=self.config.L2_TTL,
                    key_prefix=self.config.CACHE_PREFIX
                )
                if self.config.AUTO_DETECT_REDIS:
                    try:
                        self.l2._redis.ping()
                    except Exception as ping_err:
                        logger.warning(f"Redis unavailable, degrading to L1 only: {ping_err}")
                        l2_init_failed = True
                        self.l2 = None
            except Exception as e:
                logger.warning(f"Redis initialization failed: {e}")
                l2_init_failed = True
                self.l2 = None

        self.sync_enabled = self.config.CACHE_SYNC_ENABLED and self.l1 and self.l2
        self._stop_event = threading.Event()
        self._sync_thread: Optional[threading.Thread] = None
        
        if self.sync_enabled:
            self._start_sync_listener()
        elif l2_init_failed and self.config.DEGRADE_ON_REDIS_UNAVAILABLE:
            logger.warning("Cache running in degraded mode: L1-only")

    def _start_sync_listener(self):
        if not self.l2:
            return
            
        def listener_loop():
            pubsub = self.l2._redis.pubsub()
            pubsub.subscribe(self.config.CACHE_SYNC_CHANNEL)
            
            while not self._stop_event.is_set():
                try:
                    message = pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
                    if message:
                        self._handle_sync_message(message)
                except Exception as e:
                    logger.error(f"Error in cache sync listener: {e}")
                    time.sleep(1)
            
            pubsub.close()

        self._sync_thread = threading.Thread(target=listener_loop, daemon=True, name="CacheSyncListener")
        self._sync_thread.start()

    def _handle_sync_message(self, message: Dict[str, Any]):
        try:
            data = message['data']
            if isinstance(data, bytes):
                data = data.decode('utf-8')
            
            payload = json.loads(data)
            if payload.get('source_id') == self.instance_id:
                return
                
            action = payload.get('action')
            key = payload.get('key')
            
            if action in ('set', 'delete') and key and self.l1:
                self.l1.delete(key)
            elif action == 'clear' and self.l1:
                self.l1.clear()
                
        except Exception as e:
            logger.error(f"Failed to process sync message: {e}")

    def _publish_invalidation(self, action: str, key: Optional[str] = None):
        if not self.sync_enabled or not self.l2:
            return
            
        try:
            payload = {
                'source_id': self.instance_id,
                'action': action,
                'key': key,
                'timestamp': time.time()
            }
            self.l2._redis.publish(self.config.CACHE_SYNC_CHANNEL, json.dumps(payload))
        except Exception as e:
            logger.warning(f"Failed to publish cache invalidation: {e}")

    def generate_key(self, language: str, library: str, operation: str, version: Optional[str]) -> str:
        return f"{language}:{library}:{operation}:{version or ''}"

    def get(self, key: str) -> Any:
        if self.l1:
            value = self.l1.get(key)
            if value is not None:
                return value
        
        if self.l2:
            try:
                value = self.l2.get(key)
            except Exception as e:
                logger.warning(f"L2 get failed, falling back to L1: {e}")
                value = None
            if value is not None:
                if self.l1:
                    self.l1.set(key, value)
                return value
                
        return None

    def set(self, key: str, value: Any, ttl: Optional[Union[int, timedelta]] = None) -> None:
        if self.l2:
            try:
                self.l2.set(key, value, ttl=ttl)
                self._publish_invalidation('set', key)
            except Exception as e:
                logger.warning(f"L2 set failed, writing to L1 only: {e}")
            
        if self.l1:
            self.l1.set(key, value, ttl=ttl)

    def delete(self, key: str) -> None:
        if self.l2:
            try:
                self.l2.delete(key)
                self._publish_invalidation('delete', key)
            except Exception as e:
                logger.warning(f"L2 delete failed: {e}")
            
        if self.l1:
            self.l1.delete(key)

    def exists(self, key: str) -> bool:
        if self.l1 and self.l1.exists(key):
            return True
        if self.l2:
            try:
                if self.l2.exists(key):
                    return True
            except Exception as e:
                logger.warning(f"L2 exists failed: {e}")
        return False

    def clear(self) -> None:
        if self.l2:
            try:
                self.l2.clear()
                self._publish_invalidation('clear')
            except Exception as e:
                logger.warning(f"L2 clear failed: {e}")
            
        if self.l1:
            self.l1.clear()

    def close(self) -> None:
        self._stop_event.set()
        if self._sync_thread:
            self._sync_thread.join(timeout=2.0)
            
        if self.l1:
            self.l1.close()
        if self.l2:
            self.l2.close()

    def get_stats(self) -> Dict[str, Any]:
        stats = {}
        if self.l1:
            stats['l1'] = self.l1.get_stats()
        if self.l2:
            stats['l2'] = self.l2.get_stats()
        return stats

def create_cache_manager(settings: Any = None) -> MultiLevelCache:
    config = CacheConfig()
    if settings:
        if hasattr(settings, 'cache_ttl'):
            config.L1_TTL = settings.cache_ttl
            config.L2_TTL = settings.cache_ttl
        if hasattr(settings, 'cache_max_size'):
            config.L1_MAX_SIZE = settings.cache_max_size
        if hasattr(settings, 'redis_host'):
            config.REDIS_HOST = settings.redis_host
        if hasattr(settings, 'redis_port'):
            config.REDIS_PORT = settings.redis_port
    return MultiLevelCache(config)
