"""Python语言Worker"""

import re
from typing import Dict, Any
from .base import BaseWorker
from ..exceptions import LibraryNotFoundError


class PythonWorker(BaseWorker):
    """Python语言Worker - 处理PyPI查询"""
    
    def _get_base_url(self) -> str:
        return "https://pypi.org/pypi"
    
    def get_latest_version(self, library: str) -> Dict[str, Any]:
        """获取Python包的最新版本"""
        url = f"{self.base_url}/{library}/json"
        response = self._make_request(url)
        data = response.json()
        return {
            "version": data["info"]["version"],
            "url": data["info"]["package_url"]
        }
    
    def get_documentation_url(self, library: str, version: str) -> Dict[str, Any]:
        """获取Python包的文档URL"""
        url = f"{self.base_url}/{library}/json"
        response = self._make_request(url)
        data = response.json()
        doc_url = data["info"].get("project_urls", {}).get("Documentation")
        if not doc_url:
            doc_url = data["info"].get("home_page")
        return {"doc_url": doc_url}
    
    def check_version_exists(self, library: str, version: str) -> Dict[str, Any]:
        """检查Python包版本是否存在"""
        url = f"{self.base_url}/{library}/{version}/json"
        try:
            self._make_request(url)
            return {"exists": True}
        except LibraryNotFoundError:
            return {"exists": False}
    
    def get_dependencies(self, library: str, version: str) -> Dict[str, Any]:
        """获取Python包的依赖关系"""
        url = f"{self.base_url}/{library}/{version}/json"
        response = self._make_request(url)
        data = response.json()
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
        return {"dependencies": dependencies}
    
    def _parse_dependency_string(self, req_string: str) -> Dict[str, str]:
        """解析Python依赖字符串，分离库名和版本约束"""
        # 移除环境标记 (如 ; python_version >= "3.8")
        req_string = req_string.split(';')[0].strip()
        
        # 正则表达式匹配库名和版本约束
        # 支持格式: package_name, package_name>=1.0, package_name==1.0.0, package_name~=1.0等
        pattern = r'^([a-zA-Z0-9][a-zA-Z0-9._-]*[a-zA-Z0-9]|[a-zA-Z0-9])\s*([><=!~]+.*)?$'
        match = re.match(pattern, req_string)
        
        if match:
            name = match.group(1)
            version_spec = match.group(2)
            
            if version_spec:
                # 清理版本约束字符串
                version_spec = version_spec.strip()
                return {"name": name, "version": version_spec}
            else:
                return {"name": name, "version": "*"}
        
        # 如果正则匹配失败，回退到简单分割
        parts = req_string.split()
        if parts:
            return {"name": parts[0], "version": "*"}
        
        return None