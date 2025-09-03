"""Node.js语言Worker"""

from typing import Dict, Any
from .base import BaseWorker
from ..exceptions import LibraryNotFoundError
from ..core.mirror_config import Language


class NodeWorker(BaseWorker):
    """Node.js语言Worker - 处理NPM查询"""
    
    def __init__(self, timeout: float = 30.0):
        super().__init__(Language.NODE, timeout)
    
    def _get_base_url(self) -> str:
        return "https://registry.npmjs.org"
    
    def get_latest_version(self, library: str) -> Dict[str, Any]:
        """获取Node.js包的最新版本"""
        endpoint = f"/{library}"
        response = self._make_request(endpoint)
        data = response.json()
        return {
            "version": data["dist-tags"]["latest"]
        }
    
    def get_documentation_url(self, library: str, version: str) -> Dict[str, Any]:
        """获取Node.js包的文档URL"""
        # 使用版本特定的NPM URL格式
        doc_url = f"https://www.npmjs.com/package/{library}/v/{version}"
        return {"doc_url": doc_url}
    
    def check_version_exists(self, library: str, version: str) -> Dict[str, Any]:
        """检查Node.js包版本是否存在"""
        endpoint = f"/{library}/{version}"
        try:
            self._make_request(endpoint)
            return {"exists": True}
        except LibraryNotFoundError:
            return {"exists": False}
    
    def get_dependencies(self, library: str, version: str) -> Dict[str, Any]:
        """获取Node.js包的依赖关系"""
        endpoint = f"/{library}/{version}"
        response = self._make_request(endpoint)
        data = response.json()
        deps = data.get("dependencies", {})
        dependencies = [
            {"name": name, "version": version}
            for name, version in deps.items()
        ]
        return {"dependencies": dependencies}