# Copyright (c) Kirky.X. 2025. All rights reserved.
import uvicorn
import socketserver
from src.prompt_manager.utils.config import load_config
from src.prompt_manager.utils.logger import setup_logging, get_logger


def _port_available(host: str, port: int) -> bool:
    class _Handler(socketserver.BaseRequestHandler):
        def handle(self):
            pass
    try:
        srv = socketserver.TCPServer((host, port), _Handler)
    except OSError:
        return False
    else:
        srv.server_close()
        return True


def _choose_port(host: str, base_port: int, max_attempts: int = 100) -> int:
    if _port_available(host, base_port):
        return base_port
    for p in range(base_port + 1, base_port + 1 + max_attempts):
        if _port_available(host, p):
            return p
    raise RuntimeError(f"No available port found starting from {base_port} within {max_attempts} attempts")

if __name__ == "__main__":
    config = load_config()
    setup_logging(config.logging)
    logger = get_logger(__name__)
    host = config.api["http"]["host"]
    configured_port = config.api["http"]["port"]
    try:
        selected_port = _choose_port(host, configured_port, 100)
        if selected_port != configured_port:
            logger.info(f"configured port {configured_port} occupied, switched to {selected_port}")
        uvicorn.run(
            "src.prompt_manager.api.http_server:app",
            host=host,
            port=selected_port,
            reload=True
        )
    except Exception as e:
        logger.error("server start failed", error=str(e), host=host, configured_port=configured_port)
        raise
