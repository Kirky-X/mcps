import logging
import re
from typing import Dict, Any

from .base import BaseWorker
from ..core.mirror_config import Language
from ..exceptions import LibraryNotFoundError


class PythonWorker(BaseWorker):
    """Python语言Worker - 处理PyPI查询"""

    def __init__(self, timeout: float = 30.0):
        super().__init__(Language.PYTHON, timeout)
        self.logger = logging.getLogger(__name__)
        # Python worker只使用官方PyPI API，因为镜像源通常是simple格式，不兼容JSON API
        self.effective_urls = ["https://pypi.org/pypi"]

    def _get_base_url(self) -> str:
        return "https://pypi.org/pypi"

    def get_latest_version(self, library: str) -> Dict[str, Any]:
        """获取Python包的最新版本"""
        endpoint = f"/{library}/json"
        response = self._make_request(endpoint)
        data = response.json()
        return {
            "version": data["info"]["version"]
        }

    def get_documentation_url(self, library: str, version: str) -> Dict[str, Any]:
        """获取Python包的文档URL"""
        # 使用版本特定的URL格式
        doc_url = f"https://pypi.org/project/{library}/{version}/"
        return {"doc_url": doc_url}

    def check_version_exists(self, library: str, version: str) -> Dict[str, Any]:
        """检查Python包版本是否存在"""
        endpoint = f"/{library}/{version}/json"
        try:
            self._make_request(endpoint)
            return {"exists": True}
        except LibraryNotFoundError:
            return {"exists": False}

    def get_dependencies(self, library: str, version: str) -> Dict[str, Any]:
        """获取Python包的依赖关系"""
        # PyPI API 对版本中的通配符支持不好，如果version包含*或><等符号，API会返回404
        # 因此，如果version不是具体的版本号，我们需要先解析出具体版本或直接查最新版
        # 为了支持递归查询，我们这里做一个简化的处理：
        # 如果version包含非法字符，尝试只用库名查询（即最新版），或者尝试清理version
        
        target_version = version
        if any(c in version for c in "><=!~*"):
            # 如果是版本约束，PyPI API不支持直接查询约束
            # 这种情况下，我们降级为查询最新版本（或者可以在这里做一个版本匹配逻辑，但这比较复杂）
            # 简单起见，我们查询最新版本
            # 注意：这可能导致查询到的依赖不是该约束下的实际依赖，但在没有完整版本库索引的情况下这是合理的妥协
            endpoint = f"/{library}/json"
        else:
            endpoint = f"/{library}/{version}/json"

        try:
            response = self._make_request(endpoint)
            data = response.json()
            
            # 如果我们降级查询了最新版，更新实际返回的版本
            if endpoint == f"/{library}/json":
                actual_version = data["info"]["version"]
            else:
                actual_version = version
                
            requires_dist = data["info"].get("requires_dist", [])
            dependencies = []
            if requires_dist:
                for req in requires_dist:
                    if not req:
                        continue
                    # 解析Python依赖字符串格式
                    parsed = self._parse_dependency_string(req)
                    if parsed:
                        dependencies.append(parsed)
            return {"dependencies": dependencies, "version": actual_version}
            
        except LibraryNotFoundError:
            # 如果指定版本找不到，尝试最新版本作为容错
             if endpoint != f"/{library}/json":
                 try:
                     endpoint = f"/{library}/json"
                     response = self._make_request(endpoint)
                     data = response.json()
                     requires_dist = data["info"].get("requires_dist", [])
                     dependencies = []
                     if requires_dist:
                        for req in requires_dist:
                            if not req: continue
                            parsed = self._parse_dependency_string(req)
                            if parsed: dependencies.append(parsed)
                     return {"dependencies": dependencies, "version": data["info"]["version"]}
                 except Exception:
                     pass
             # 还是失败，返回空依赖
             return {"dependencies": []}
        except Exception as e:
            self.logger.warning(f"Failed to get dependencies for {library}@{version}: {e}")
            return {"dependencies": []}

    def _parse_dependency_string(self, req_string: str) -> Dict[str, str]:
        """解析Python依赖字符串，分离库名和版本约束"""
        # 移除环境标记 (如 ; python_version >= "3.8")
        # 注意：对于递归依赖查询，忽略环境标记可能导致查到不适用于当前环境的依赖
        # 但为了通用性，我们暂时只取第一部分
        req_string = req_string.split(';')[0].strip()
        if not req_string: # 如果仅有环境标记
            return None

        # 正则表达式匹配库名和版本约束
        # 支持格式: package_name, package_name>=1.0, package_name==1.0.0, package_name~=1.0等
        # 增加对 [] extras 的支持，如 requests[security]
        pattern = r'^([a-zA-Z0-9][a-zA-Z0-9._-]*[a-zA-Z0-9]|[a-zA-Z0-9])(?:\[.*\])?\s*([><=!~]+.*)?$'
        match = re.match(pattern, req_string)

        if match:
            name = match.group(1)
            version_spec = match.group(2)

            if version_spec:
                # 清理版本约束字符串
                version_spec = version_spec.strip()
                # 移除括号（有些格式是 (>=1.0)）
                version_spec = version_spec.strip('()')
                return {"name": name, "version": version_spec}
            else:
                return {"name": name, "version": "*"}

        # 如果正则匹配失败，回退到简单分割
        parts = req_string.split()
        if parts:
            # 简单清理
            name = parts[0].split('[')[0] # 移除extras
            return {"name": name, "version": "*"}

        return None
