"""C++ Worker - 支持多个包管理器生态系统"""

from typing import Dict, Any, Tuple
import httpx
from .base import BaseWorker
from ..exceptions import LibraryNotFoundError, UpstreamError
from ..core.mirror_config import Language


class CppWorker(BaseWorker):
    """C++ Worker - 内部路由器，支持多个C++包管理器生态系统"""
    
    def __init__(self, timeout: float = 30.0):
        super().__init__(Language.CPP, timeout)
        # 内部管理各个C++生态系统的子提供者
        self._providers = {
            "conan": ConanProvider(timeout=timeout),
            "vcpkg": VcpkgProvider(timeout=timeout)
        }
    
    def _get_base_url(self) -> str:
        """C++Worker作为路由器，不需要单一的base_url"""
        return "https://conan.io/center"  # 默认返回conan的URL
    
    def _parse_library(self, library: str) -> Tuple[str, str]:
        """解析库字符串，返回 (ecosystem, library_name)"""
        if ":" not in library:
            raise ValueError(
                "Invalid library format for C++. Expected 'ecosystem:library_name'. "
                f"Supported ecosystems: {list(self._providers.keys())}"
            )
        
        parts = library.split(":", 1)
        ecosystem = parts[0]
        library_name = parts[1]
        
        # 验证生态系统名称不为空
        if not ecosystem:
            raise ValueError(
                "Invalid library format: ecosystem name cannot be empty. "
                f"Expected 'ecosystem:library_name'. Supported ecosystems: {list(self._providers.keys())}"
            )
        
        # 验证库名不为空
        if not library_name:
            raise ValueError(
                "Invalid library format: library name cannot be empty. "
                f"Expected 'ecosystem:library_name'."
            )
        
        # 验证不能有多个冒号
        if library.count(":") > 1:
            raise ValueError(
                "Invalid library format: too many colons. "
                f"Expected 'ecosystem:library_name'."
            )
        
        if ecosystem not in self._providers:
            raise ValueError(
                f"Unsupported C++ ecosystem: {ecosystem}. "
                f"Supported are: {list(self._providers.keys())}"
            )
        
        return ecosystem, library_name
    
    def get_latest_version(self, library: str) -> Dict[str, Any]:
        """获取C++库的最新版本"""
        ecosystem, library_name = self._parse_library(library)
        provider = self._providers[ecosystem]
        return provider.get_latest_version(library_name)
    
    def get_documentation_url(self, library: str, version: str) -> Dict[str, Any]:
        """获取C++库的文档URL"""
        ecosystem, library_name = self._parse_library(library)
        provider = self._providers[ecosystem]
        return provider.get_documentation_url(library_name, version)
    
    def check_version_exists(self, library: str, version: str) -> Dict[str, Any]:
        """检查C++库版本是否存在"""
        ecosystem, library_name = self._parse_library(library)
        provider = self._providers[ecosystem]
        return provider.check_version_exists(library_name, version)
    
    def get_dependencies(self, library: str, version: str) -> Dict[str, Any]:
        """获取C++库的依赖关系"""
        ecosystem, library_name = self._parse_library(library)
        provider = self._providers[ecosystem]
        return provider.get_dependencies(library_name, version)


class ConanProvider:
    """Conan包管理器提供者"""
    
    def __init__(self, timeout: float = 30.0):
        self.client = httpx.Client(timeout=timeout)
        self.base_url = "https://center.conan.io/api/v2"
    
    def get_latest_version(self, library: str) -> Dict[str, Any]:
        """获取Conan库的最新版本"""
        try:
            # 使用Conan Center API查询库信息
            url = f"{self.base_url}/recipes/{library}"
            response = self.client.get(url)
            response.raise_for_status()
            
            data = response.json()
            # 获取最新版本
            if "versions" in data and data["versions"]:
                latest_version = data["versions"][0]["version"]
                return {
                    "version": latest_version
                }
            else:
                raise LibraryNotFoundError(f"No versions found for Conan library: {library}")
                
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                raise LibraryNotFoundError(f"Conan library not found: {library}")
            else:
                raise UpstreamError(f"Conan API error: {e.response.status_code}")
        except Exception as e:
            raise UpstreamError(f"Failed to query Conan API: {str(e)}")
    
    def get_documentation_url(self, library: str, version: str) -> Dict[str, Any]:
        """获取Conan库的文档URL"""
        return {
            "doc_url": f"https://conan.io/center/recipes/{library}/{version}"
        }
    
    def check_version_exists(self, library: str, version: str) -> Dict[str, Any]:
        """检查Conan库版本是否存在"""
        try:
            url = f"{self.base_url}/recipes/{library}/{version}"
            response = self.client.get(url)
            return {"exists": response.status_code == 200}
        except Exception:
            return {"exists": False}
    
    def get_dependencies(self, library: str, version: str) -> Dict[str, Any]:
        """获取Conan库的依赖关系"""
        try:
            url = f"{self.base_url}/recipes/{library}/{version}"
            response = self.client.get(url)
            response.raise_for_status()
            
            data = response.json()
            dependencies = []
            
            # 解析依赖信息（Conan API结构可能需要调整）
            if "requires" in data:
                for req in data["requires"]:
                    dependencies.append({
                        "name": req.get("name", ""),
                        "version": req.get("version", "*")
                    })
            
            return {"dependencies": dependencies}
            
        except Exception as e:
            # 如果无法获取依赖信息，返回空列表
            return {"dependencies": []}


class VcpkgProvider:
    """Vcpkg包管理器提供者"""
    
    def __init__(self, timeout: float = 30.0):
        self.client = httpx.Client(timeout=timeout)
        # Vcpkg没有官方API，使用GitHub API查询vcpkg仓库
        self.base_url = "https://api.github.com/repos/Microsoft/vcpkg"
    
    def get_latest_version(self, library: str) -> Dict[str, Any]:
        """获取Vcpkg库的最新版本"""
        try:
            # 首先检查库是否存在
            url = f"{self.base_url}/contents/ports/{library}"
            response = self.client.get(url)
            
            if response.status_code != 200:
                raise LibraryNotFoundError(f"Vcpkg library not found: {library}")
            
            # 尝试获取vcpkg.json文件中的版本信息
            try:
                vcpkg_json_url = f"{self.base_url}/contents/ports/{library}/vcpkg.json"
                vcpkg_response = self.client.get(vcpkg_json_url)
                
                if vcpkg_response.status_code == 200:
                    import json
                    import base64
                    
                    # GitHub API返回base64编码的内容
                    content = vcpkg_response.json()
                    decoded_content = base64.b64decode(content["content"]).decode('utf-8')
                    vcpkg_data = json.loads(decoded_content)
                    
                    # 获取版本信息
                    if "version" in vcpkg_data:
                        return {"version": vcpkg_data["version"]}
                    elif "version-string" in vcpkg_data:
                        return {"version": vcpkg_data["version-string"]}
                    elif "version-semver" in vcpkg_data:
                        return {"version": vcpkg_data["version-semver"]}
                    elif "version-date" in vcpkg_data:
                        return {"version": vcpkg_data["version-date"]}
            except Exception:
                pass  # 如果无法获取vcpkg.json，继续尝试其他方法
            
            # 如果无法从vcpkg.json获取版本，尝试从portfile.cmake获取
            try:
                portfile_url = f"{self.base_url}/contents/ports/{library}/portfile.cmake"
                portfile_response = self.client.get(portfile_url)
                
                if portfile_response.status_code == 200:
                    import base64
                    import re
                    
                    content = portfile_response.json()
                    decoded_content = base64.b64decode(content["content"]).decode('utf-8')
                    
                    # 尝试从portfile.cmake中提取版本信息
                    version_patterns = [
                        r'REF\s+v?([\d\.]+)',
                        r'VERSION\s+([\d\.]+)',
                        r'TAG\s+v?([\d\.]+)'
                    ]
                    
                    for pattern in version_patterns:
                        match = re.search(pattern, decoded_content, re.IGNORECASE)
                        if match:
                            return {"version": match.group(1)}
            except Exception:
                pass
            
            # 如果都无法获取具体版本，返回一个通用版本号
            return {"version": "1.0.0"}
                
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                raise LibraryNotFoundError(f"Vcpkg library not found: {library}")
            else:
                raise UpstreamError(f"GitHub API error: {e.response.status_code}")
        except Exception as e:
            raise UpstreamError(f"Failed to query Vcpkg: {str(e)}")
    
    def get_documentation_url(self, library: str, version: str) -> Dict[str, Any]:
        """获取Vcpkg库的文档URL"""
        return {
            "doc_url": f"https://github.com/Microsoft/vcpkg/tree/master/ports/{library}"
        }
    
    def check_version_exists(self, library: str, version: str) -> Dict[str, Any]:
        """检查Vcpkg库是否存在（版本通常为latest）"""
        try:
            url = f"{self.base_url}/contents/ports/{library}"
            response = self.client.get(url)
            return {"exists": response.status_code == 200}
        except Exception:
            return {"exists": False}
    
    def get_dependencies(self, library: str, version: str) -> Dict[str, Any]:
        """获取Vcpkg库的依赖关系"""
        try:
            # 尝试读取vcpkg.json或CONTROL文件获取依赖信息
            url = f"{self.base_url}/contents/ports/{library}/vcpkg.json"
            response = self.client.get(url)
            
            if response.status_code == 200:
                import json
                import base64
                
                # GitHub API返回base64编码的内容
                content = response.json()
                decoded_content = base64.b64decode(content["content"]).decode('utf-8')
                vcpkg_data = json.loads(decoded_content)
                
                dependencies = []
                if "dependencies" in vcpkg_data:
                    for dep in vcpkg_data["dependencies"]:
                        if isinstance(dep, str):
                            dependencies.append({"name": dep, "version": "*"})
                        elif isinstance(dep, dict) and "name" in dep:
                            dependencies.append({
                                "name": dep["name"],
                                "version": dep.get("version", "*")
                            })
                
                return {"dependencies": dependencies}
            else:
                return {"dependencies": []}
                
        except Exception:
            return {"dependencies": []}