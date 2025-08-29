"""Rust语言Worker"""

from typing import Dict, Any
from .base import BaseWorker
from ..exceptions import LibraryNotFoundError


class RustWorker(BaseWorker):
    """Rust语言Worker - 处理Crates.io查询"""
    
    def _get_base_url(self) -> str:
        return "https://crates.io/api/v1"
    
    def get_latest_version(self, library: str) -> Dict[str, Any]:
        """获取Rust库的最新版本"""
        url = f"{self.base_url}/crates/{library}"
        response = self._make_request(url)
        data = response.json()
        return {
            "version": data["crate"]["max_version"],
            "url": f"https://crates.io/crates/{library}"
        }
    
    def get_documentation_url(self, library: str, version: str) -> Dict[str, Any]:
        """获取Rust库的文档URL"""
        return {
            "doc_url": f"https://docs.rs/{library}/{version}"
        }
    
    def check_version_exists(self, library: str, version: str) -> Dict[str, Any]:
        """检查Rust库版本是否存在"""
        url = f"{self.base_url}/crates/{library}/{version}"
        try:
            self._make_request(url)
            return {"exists": True}
        except LibraryNotFoundError:
            return {"exists": False}
    
    def get_dependencies(self, library: str, version: str) -> Dict[str, Any]:
        """获取Rust库的依赖关系"""
        url = f"{self.base_url}/crates/{library}/{version}/dependencies"
        response = self._make_request(url)
        data = response.json()
        dependencies = [
            {"name": dep["crate_id"], "version": dep["req"]}
            for dep in data["dependencies"]
        ]
        return {"dependencies": dependencies}