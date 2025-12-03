# Multi-Level Cache Module

A production-grade, multi-level caching solution for Python applications, featuring local (L1) and remote (L2) caching with automatic synchronization.

## Features

- **Two-Level Architecture**:
  - **L1 (Local)**: High-performance in-memory cache using `moka-py` (Rust-backed) or `cacheout` fallback.
  - **L2 (Remote)**: Distributed cache using Redis.
- **Synchronization**: Pub/Sub based invalidation to keep local caches consistent across instances.
- **Flexible Configuration**: Enable/disable layers, adjust TTLs, and configure Redis connection via environment variables.
- **Performance**: Optimized for high read throughput (L1 hits ~2.8M ops/s).

## Installation

Ensure dependencies are installed:

```toml
dependencies = [
    "redis>=5.0.0",
    "moka-py>=0.2.0",  # Optional but recommended for performance
    "cacheout>=0.16.0", # Fallback
    "pydantic-settings>=2.0.0"
]
```

## Usage

### Basic Usage

```python
from cache import create_cache_manager, CacheConfig

# Auto-configured from environment variables
cache = create_cache_manager()

# Set
cache.set("user:123", {"name": "Alice"}, ttl=300)

# Get
user = cache.get("user:123")

# Delete
cache.delete("user:123")
```

### Configuration

Configuration is handled via Pydantic Settings. You can set these environment variables (prefix `LIB_` by default):

| Variable | Default | Description |
|----------|---------|-------------|
| `LIB_CACHE_ENABLED` | `True` | Master switch |
| `LIB_L1_ENABLED` | `True` | Enable local cache |
| `LIB_L1_MAX_SIZE` | `10000` | Max items in L1 |
| `LIB_L1_TTL` | `300` | Default L1 TTL (seconds) |
| `LIB_L2_ENABLED` | `True` | Enable Redis cache |
| `LIB_L2_TTL` | `3600` | Default L2 TTL (seconds) |
| `LIB_REDIS_HOST` | `localhost` | Redis Host |
| `LIB_REDIS_PORT` | `6379` | Redis Port |
| `LIB_CACHE_SYNC_ENABLED` | `True` | Enable invalidation sync |

## Architecture

1. **Get Operation**:
   - Check L1. If hit, return immediately.
   - Check L2. If hit, populate L1 and return.
   - Return `None` if miss.

2. **Set Operation**:
   - Write to L2 (Source of Truth).
   - Publish invalidation event (if sync enabled).
   - Write to L1.

3. **Synchronization**:
   - Background thread subscribes to Redis channel.
   - On `set`/`delete` from other instances, local L1 key is invalidated.

## Performance

Benchmark results (Typical):
- **L1 Hit**: ~2.8M ops/s
- **L2 Hit**: ~50k ops/s (Network dependent)
- **Multi-Level Hit**: ~2.8M ops/s (L1 speed)

## Integration

To replace an existing cache module, simply point your application to use `create_cache_manager` factory. The module is designed to be interface-compatible with common cache patterns.
