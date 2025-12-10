import uvicorn
from prompt_manager.api.http_server import app
from prompt_manager.utils.config import load_config

def main():
    config = load_config()
    uvicorn.run(
        app,
        host=config.api.get("http", {}).get("host", "0.0.0.0"),
        port=config.api.get("http", {}).get("port", 8000),
        log_level=config.logging.get("level", "INFO").lower()
    )

if __name__ == "__main__":
    main()
