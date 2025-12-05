"""Node.js语言Worker"""

from typing import Dict, Any

from .base import BaseWorker
from ..core.mirror_config import Language
from ..exceptions import LibraryNotFoundError


class NodeWorker(BaseWorker):
    """Node.js语言Worker - 处理NPM查询"""

    def __init__(self, timeout: float = 120.0):
        super().__init__(Language.NODE, timeout)

    def _get_base_url(self) -> str:
        return "https://registry.npmmirror.com"

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
        try:
            response = self._make_request(endpoint)
            data = response.json()
            
            # 记录实际版本
            actual_version = data.get("version", version)
            
            deps = data.get("dependencies", {})
            dependencies = [
                {"name": name, "version": version}
                for name, version in deps.items()
            ]
            return {"dependencies": dependencies, "version": actual_version}
        except LibraryNotFoundError:
             # 尝试获取最新版
             try:
                 endpoint = f"/{library}"
                 response = self._make_request(endpoint)
                 data = response.json()
                 latest_ver = data["dist-tags"]["latest"]
                 # 获取最新版本的详细信息
                 version_data = data.get("versions", {}).get(latest_ver, {})
                 deps = version_data.get("dependencies", {})
                 dependencies = [
                    {"name": name, "version": version}
                    for name, version in deps.items()
                 ]
                 return {"dependencies": dependencies, "version": latest_ver}
             except Exception:
                 return {"dependencies": []}
        except Exception as e:
             self.logger.warning(f"Failed to get dependencies for {library}@{version}: {e}")
             return {"dependencies": []}
