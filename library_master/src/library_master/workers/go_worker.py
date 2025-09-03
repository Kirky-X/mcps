"""Go语言Worker"""

import os
import re
from typing import Dict, Any, Optional, List
from urllib.parse import quote

from .base import BaseWorker
from ..exceptions import LibraryNotFoundError
from ..core.mirror_config import Language


class GoWorker(BaseWorker):
    """Go语言库查询工作器
    
    使用proxy.golang.org API获取Go模块的版本、依赖和文档信息
    """
    
    def __init__(self, timeout: float = 30.0):
        super().__init__(Language.GO, timeout)
    
    def _get_base_url(self) -> str:
        """获取Go模块的API基础URL
        
        支持通过环境变量GOPROXY配置镜像站：
        - GOPROXY=https://goproxy.cn,direct (七牛云镜像)
        - GOPROXY=https://goproxy.io,direct (goproxy.io镜像)
        - GOPROXY=https://mirrors.aliyun.com/goproxy,direct (阿里云镜像)
        
        Returns:
            str: Go代理服务器的基础URL
        """
        # 从环境变量获取GOPROXY配置
        goproxy = os.getenv('GOPROXY', 'https://proxy.golang.org')
        
        # 如果GOPROXY包含多个代理（用逗号分隔），使用第一个
        if ',' in goproxy:
            goproxy = goproxy.split(',')[0].strip()
        
        # 处理特殊值
        if goproxy.lower() in ['direct', 'off']:
            goproxy = 'https://proxy.golang.org'
        
        # 确保URL格式正确
        if not goproxy.startswith(('http://', 'https://')):
            goproxy = f'https://{goproxy}'
        
        return goproxy
    
    def _get_library_url(self, library: str) -> str:
        """获取特定Go模块的API URL
        
        Args:
            library: Go模块路径，如 'github.com/gin-gonic/gin'
            
        Returns:
            str: 特定模块的API URL
        """
        # 对模块路径进行URL编码
        encoded_library = quote(library, safe='')
        return f"{self.base_url}/{encoded_library}"
    
    def get_latest_version(self, library: str) -> Dict[str, Any]:
        """获取Go模块的最新版本
        
        Args:
            library: Go模块路径
            
        Returns:
            包含版本信息的字典
        """
        url = f"{self._get_library_url(library)}/@v/list"
        
        try:
            response = self._make_request(url)
            versions = response.text.strip().split('\n')
            
            # 过滤掉空行
            versions = [v for v in versions if v.strip()]
            
            if not versions:
                raise LibraryNotFoundError(f"No versions found for {library}")
            
            # 找到最新的稳定版本
            latest_version = self._find_latest_stable_version(versions)
            
            if not latest_version:
                raise LibraryNotFoundError(f"No stable versions found for {library}")
            
            return {
                "version": latest_version
            }
            
        except Exception as e:
            if "404" in str(e):
                raise LibraryNotFoundError(f"Library not found: {library}")
            raise
    
    def check_version_exists(self, library: str, version: str) -> Dict[str, Any]:
        """检查Go模块的特定版本是否存在
        
        Args:
            library: Go模块路径
            version: 版本号
            
        Returns:
            包含存在性信息的字典
        """
        url = f"{self._get_library_url(library)}/@v/list"
        
        try:
            response = self._make_request(url)
            versions = response.text.strip().split('\n')
            
            # 标准化版本号进行比较
            normalized_version = self._normalize_version(version)
            normalized_versions = [self._normalize_version(v) for v in versions if v.strip()]
            
            exists = normalized_version in normalized_versions
            
            return {"exists": exists}
            
        except Exception as e:
            if "404" in str(e):
                return {"exists": False}
            raise
    
    def get_dependencies(self, library: str, version: str) -> Dict[str, Any]:
        """获取Go模块的依赖关系
        
        Args:
            library: Go模块路径
            version: 版本号
            
        Returns:
            包含依赖信息的字典
        """
        normalized_version = self._normalize_version(version)
        url = f"{self._get_library_url(library)}/@v/{normalized_version}.mod"
        
        try:
            response = self._make_request(url)
            mod_content = response.text
            
            dependencies = self._parse_go_mod_dependencies(mod_content)
            
            return {
                "dependencies": [
                    {"name": dep[0], "version": dep[1]}
                    for dep in dependencies
                ]
            }
            
        except Exception as e:
            if "404" in str(e):
                raise LibraryNotFoundError(f"Version {version} not found for {library}")
            raise
    
    def get_documentation_url(self, library: str, version: Optional[str] = None) -> Dict[str, Any]:
        """获取Go模块的文档URL
        
        Args:
            library: Go模块路径
            version: 可选的版本号
            
        Returns:
            包含文档URL的字典
        """
        if version:
            normalized_version = self._normalize_version(version)
            doc_url = f"https://pkg.go.dev/{library}@{normalized_version}"
        else:
            doc_url = f"https://pkg.go.dev/{library}"
            
        return {"doc_url": doc_url}
    
    def _normalize_version(self, version: str) -> str:
        """标准化版本号，确保有v前缀
        
        Args:
            version: 原始版本号
            
        Returns:
            标准化后的版本号（带v前缀）
        """
        if not version.startswith('v'):
            return f'v{version}'
        return version
    
    def _find_latest_stable_version(self, versions: List[str]) -> Optional[str]:
        """从版本列表中找到最新的稳定版本
        
        Args:
            versions: 版本号列表
            
        Returns:
            最新的稳定版本号，如果没有找到则返回None
        """
        # 语义化版本正则表达式
        semver_pattern = re.compile(r'^v?(\d+)\.(\d+)\.(\d+)(?:-([\w\.\-]+))?(?:\+([\w\.\-]+))?$')
        
        stable_versions = []
        
        for version in versions:
            if not version.strip():
                continue
                
            match = semver_pattern.match(version.strip())
            if match:
                major, minor, patch, prerelease, build = match.groups()
                
                # 跳过预发布版本（包含-的版本）
                if prerelease:
                    continue
                
                stable_versions.append({
                    'version': version.strip(),
                    'major': int(major),
                    'minor': int(minor),
                    'patch': int(patch)
                })
        
        if not stable_versions:
            return None
        
        # 按语义化版本排序，找到最新版本
        stable_versions.sort(
            key=lambda x: (x['major'], x['minor'], x['patch']),
            reverse=True
        )
        
        return stable_versions[0]['version']
    
    def _parse_go_mod_dependencies(self, go_mod_content: str) -> List[tuple]:
        """解析go.mod文件内容，提取直接依赖
        
        Args:
            go_mod_content: go.mod文件的内容
            
        Returns:
            依赖列表，每个元素是(模块名, 版本)的元组
        """
        dependencies = []
        lines = go_mod_content.split('\n')
        
        in_require_block = False
        
        for line in lines:
            line = line.strip()
            
            # 检查是否进入require块
            if line.startswith('require ('):
                in_require_block = True
                continue
            
            # 检查是否退出require块
            if in_require_block and line == ')':
                in_require_block = False
                continue
            
            # 处理require块内的依赖
            if in_require_block:
                # 跳过注释行和空行
                if line.startswith('//') or not line:
                    continue
                
                # 跳过间接依赖（包含// indirect注释的行）
                if '// indirect' in line:
                    continue
                
                # 解析依赖行：模块名 版本号
                parts = line.split()
                if len(parts) >= 2:
                    module_name = parts[0]
                    version = parts[1]
                    dependencies.append((module_name, version))
            
            # 处理单行require语句
            elif line.startswith('require '):
                # 移除require前缀
                require_part = line[8:].strip()
                
                # 跳过间接依赖
                if '// indirect' in require_part:
                    continue
                
                parts = require_part.split()
                if len(parts) >= 2:
                    module_name = parts[0]
                    version = parts[1]
                    dependencies.append((module_name, version))
        
        return dependencies