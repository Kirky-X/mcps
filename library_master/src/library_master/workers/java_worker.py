"""Java语言Worker - 使用Maven Central搜索API和POM文件解析"""

import time
import os
from typing import Dict, List, Optional, Any
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import xml.etree.ElementTree as ET

from .base import BaseWorker
from ..exceptions import LibraryNotFoundError, UpstreamError
from ..core.mirror_config import Language


class JavaWorker(BaseWorker):
    """Worker for Java libraries using Maven Central Search API and POM file parsing."""
    
    def __init__(self, timeout: float = 30.0):
        # 根据文档建议：搜索API使用官方源，文件下载使用阿里云镜像解决国内网络超时问题
        self.search_api_url = os.getenv('MAVEN_SEARCH_URL', 'https://search.maven.org/solrsearch/select')
        # 默认使用阿里云镜像来解决国内网络超时问题
        self.maven_repo_url = os.getenv('MAVEN_CENTRAL_URL', 'https://maven.aliyun.com/repository/public')
        self.timeout = timeout
        super().__init__(Language.JAVA, timeout)
        
        # Setup session with retry strategy
        self.session = requests.Session()
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
    
    def _get_base_url(self) -> str:
        """获取API基础URL"""
        return self.search_api_url
    
    def _parse_library_name(self, library_name: str) -> tuple[str, str]:
        """解析库名，返回(groupId, artifactId)"""
        if ':' in library_name:
            parts = library_name.split(':')
            if len(parts) >= 2:
                return parts[0], parts[1]
        
        # 如果没有冒号，尝试从常见模式推断
        if '.' in library_name:
            # 假设最后一部分是artifactId
            parts = library_name.split('.')
            group_id = '.'.join(parts[:-1])
            artifact_id = parts[-1]
            return group_id, artifact_id
        
        # 默认情况
        return library_name, library_name
    
    def _search_maven_central(self, group_id: str, artifact_id: str, fuzzy: bool = False) -> Dict[str, Any]:
        """使用Maven Central搜索API查询库信息，支持模糊搜索"""
        try:
            # 策略1: 精确搜索 (当group_id和artifact_id都不相同时)
            if not fuzzy and group_id != artifact_id:
                params = {
                    'q': f'g:"{group_id}" AND a:"{artifact_id}"',
                    'core': 'gav',
                    'rows': 20,
                    'wt': 'json'
                }
                
                response = self.session.get(self.search_api_url, params=params, timeout=self.timeout)
                response.raise_for_status()
                
                data = response.json()
                result = data.get('response', {})
                
                if result.get('docs'):
                    self.logger.info(f"Found {group_id}:{artifact_id} using exact search")
                    return result
            
            # 策略2: artifactId模糊搜索
            self.logger.info(f"Trying fuzzy search for artifact: {artifact_id}")
            params = {
                'q': f'a:{artifact_id}*',  # 修复通配符格式
                'core': 'gav',
                'rows': 50,  # 增加结果数量以便筛选
                'wt': 'json'
            }
            
            response = self.session.get(self.search_api_url, params=params, timeout=self.timeout)
            response.raise_for_status()
            
            data = response.json()
            result = data.get('response', {})
            
            if result.get('docs'):
                self.logger.info(f"Found results using artifactId fuzzy search for: {artifact_id}")
                return result
            
            # 策略3: 全文搜索
            self.logger.info(f"Trying full-text search for: {artifact_id}")
            params = {
                'q': artifact_id,
                'core': 'gav',
                'rows': 50,
                'wt': 'json'
            }
            
            response = self.session.get(self.search_api_url, params=params, timeout=self.timeout)
            response.raise_for_status()
            
            data = response.json()
            result = data.get('response', {})
            
            if result.get('docs'):
                self.logger.info(f"Found results using full-text search for: {artifact_id}")
                return result
            
            # 如果所有策略都失败，返回空结果
            self.logger.warning(f"No results found for {group_id}:{artifact_id} using any search strategy")
            return {'docs': []}
            
        except Exception as e:
            self.logger.error(f"Error searching Maven Central for {group_id}:{artifact_id}: {e}")
            raise UpstreamError(f"Failed to search Maven Central: {str(e)}")
    
    def _get_pom_url(self, group_id: str, artifact_id: str, version: str) -> str:
        """构建POM文件的URL"""
        group_path = group_id.replace('.', '/')
        return f"{self.maven_repo_url}/{group_path}/{artifact_id}/{version}/{artifact_id}-{version}.pom"
    
    def _fetch_and_parse_pom(self, group_id: str, artifact_id: str, version: str) -> Optional[ET.Element]:
        """获取并解析POM文件"""
        try:
            pom_url = self._get_pom_url(group_id, artifact_id, version)
            response = self.session.get(pom_url, timeout=self.timeout)
            
            if response.status_code == 404:
                return None
            
            response.raise_for_status()
            
            # 解析XML
            root = ET.fromstring(response.text)
            return root
        except Exception as e:
            self.logger.error(f"Error fetching POM for {group_id}:{artifact_id}:{version}: {e}")
            return None
    
    def _extract_dependencies_from_pom(self, pom_root: ET.Element) -> List[str]:
        """从POM文件中提取依赖"""
        dependencies = []
        
        try:
            # 定义XML命名空间
            ns = {'maven': 'http://maven.apache.org/POM/4.0.0'}
            
            # 查找dependencies节点
            deps_element = pom_root.find('.//maven:dependencies', ns)
            if deps_element is None:
                # 尝试不使用命名空间
                deps_element = pom_root.find('.//dependencies')
            
            if deps_element is not None:
                for dep in deps_element.findall('.//dependency', ns) or deps_element.findall('.//dependency'):
                    group_id_elem = dep.find('groupId', ns) or dep.find('groupId')
                    artifact_id_elem = dep.find('artifactId', ns) or dep.find('artifactId')
                    scope_elem = dep.find('scope', ns) or dep.find('scope')
                    
                    if group_id_elem is not None and artifact_id_elem is not None:
                        group_id = group_id_elem.text
                        artifact_id = artifact_id_elem.text
                        scope = scope_elem.text if scope_elem is not None else 'compile'
                        
                        # 只返回compile和runtime scope的依赖
                        if scope in ['compile', 'runtime']:
                            dependencies.append(f"{group_id}:{artifact_id}")
        
        except Exception as e:
            self.logger.error(f"Error extracting dependencies from POM: {e}")
        
        return dependencies[:10]  # 限制返回10个依赖
    

    

    

    
    def get_latest_version(self, library: str) -> Dict[str, Any]:
        """Get the latest version of a Java library using Maven Central Search API with intelligent matching."""
        try:
            group_id, artifact_id = self._parse_library_name(library)
            if not group_id or not artifact_id:
                raise LibraryNotFoundError(f"Invalid library name format: {library}")
            
            # 尝试搜索，如果是简短名称则启用模糊搜索
            fuzzy_search = (group_id == artifact_id)  # 当解析出的group_id和artifact_id相同时，说明是简短名称
            search_result = self._search_maven_central(group_id, artifact_id, fuzzy=fuzzy_search)
            docs = search_result.get('docs', [])
            
            if not docs:
                raise LibraryNotFoundError(f"Library not found: {library}")
            
            # 智能匹配逻辑
            if fuzzy_search and len(docs) > 1:
                # 对于模糊搜索结果，优先选择最受欢迎的库
                # 1. 优先选择artifactId完全匹配的
                exact_matches = [doc for doc in docs if doc.get('a') == artifact_id]
                if exact_matches:
                    docs = exact_matches
                    self.logger.info(f"Found {len(exact_matches)} exact artifact matches for: {artifact_id}")
                    
                    # 优先选择知名的groupId（如com.fasterxml.jackson, org.springframework等）
                    known_groups = {
                        'com.fasterxml.jackson.core': 1000,
                        'org.springframework': 900,
                        'org.apache': 800,
                        'com.google': 700,
                        'org.eclipse': 600,
                        'junit': 500,
                        'org.slf4j': 400
                    }
                    
                    def get_priority_score(doc):
                        group_id = doc.get('g', '')
                        # 检查是否是知名groupId
                        for known_group, score in known_groups.items():
                            if group_id.startswith(known_group):
                                return score + doc.get('usageCount', 0)
                        # 默认按使用量排序
                        return doc.get('usageCount', 0)
                    
                    # 按优先级分数排序
                    docs.sort(key=get_priority_score, reverse=True)
                    selected_doc = docs[0]
                    self.logger.info(f"Selected best match: {selected_doc.get('g')}:{selected_doc.get('a')} (priority score: {get_priority_score(selected_doc)})")
                else:
                    # 2. 按受欢迎程度排序（使用usageCount或timestamp）
                    docs.sort(key=lambda x: (
                        x.get('usageCount', 0),  # 优先使用量
                        x.get('timestamp', 0)    # 然后是时间戳
                    ), reverse=True)
                    
                    selected_doc = docs[0]
                    self.logger.info(f"Selected most popular match: {selected_doc.get('g')}:{selected_doc.get('a')} (usageCount: {selected_doc.get('usageCount', 0)})")
            else:
                # 精确搜索或只有一个结果，按时间戳排序获取最新版本
                selected_doc = max(docs, key=lambda x: x.get('timestamp', 0))
            
            version = selected_doc.get('v')
            
            if not version:
                raise LibraryNotFoundError(f"No version found for library: {library}")
            
            return {"version": version}
            
        except Exception as e:
            self.logger.error(f"Error getting latest version for {library}: {e}")
            raise UpstreamError(f"Failed to get latest version: {str(e)}")
    

    
    def get_documentation_url(self, library: str, version: str) -> Dict[str, Any]:
        """Get the documentation URL for a Java library."""
        try:
            group_id, artifact_id = self._parse_library_name(library)
            if not group_id or not artifact_id:
                raise LibraryNotFoundError(f"Invalid library name format: {library}")
            
            # Return MVN Repository URL for documentation
            doc_url = f"https://mvnrepository.com/artifact/{group_id}/{artifact_id}/{version}"
            return {"doc_url": doc_url}
        except Exception as e:
            self.logger.error(f"Error getting documentation URL for {library}: {e}")
            raise UpstreamError(f"Failed to get documentation URL: {str(e)}")
    
    def check_version_exists(self, library: str, version: str) -> Dict[str, Any]:
        """Check if a specific version exists for a Java library using Maven Central Search API."""
        try:
            group_id, artifact_id = self._parse_library_name(library)
            if not group_id or not artifact_id:
                raise LibraryNotFoundError(f"Invalid library name format: {library}")
            
            # 如果是简短名称，需要先获取正确的Maven坐标
            if group_id == artifact_id:  # 简短名称
                # 使用模糊搜索获取正确的库信息
                search_result = self._search_maven_central(group_id, artifact_id, fuzzy=True)
                docs = search_result.get('docs', [])
                
                if not docs:
                    return {"exists": False}
                
                # 使用与get_latest_version相同的智能匹配逻辑
                exact_matches = [doc for doc in docs if doc.get('a') == artifact_id]
                if exact_matches:
                    docs = exact_matches
                    
                    # 优先选择知名的groupId
                    known_groups = {
                        'com.fasterxml.jackson.core': 1000,
                        'org.springframework': 900,
                        'org.springframework.boot': 950,  # 添加spring-boot支持
                        'org.apache': 800,
                        'com.google': 700,
                        'org.eclipse': 600,
                        'junit': 500,
                        'org.slf4j': 400
                    }
                    
                    def get_priority_score(doc):
                        group_id_temp = doc.get('g', '')
                        for known_group, score in known_groups.items():
                            if group_id_temp.startswith(known_group):
                                return score + doc.get('usageCount', 0)
                        return doc.get('usageCount', 0)
                    
                    docs.sort(key=get_priority_score, reverse=True)
                    selected_doc = docs[0]
                    group_id = selected_doc.get('g')
                    artifact_id = selected_doc.get('a')
                    self.logger.info(f"Resolved {library} to {group_id}:{artifact_id} for version check")
                else:
                    # 按受欢迎程度排序
                    docs.sort(key=lambda x: (
                        x.get('usageCount', 0),
                        x.get('timestamp', 0)
                    ), reverse=True)
                    
                    selected_doc = docs[0]
                    group_id = selected_doc.get('g')
                    artifact_id = selected_doc.get('a')
                    self.logger.info(f"Resolved {library} to {group_id}:{artifact_id} for version check")
            
            # 使用版本特定的搜索查询
            try:
                params = {
                    'q': f'g:"{group_id}" AND a:"{artifact_id}" AND v:"{version}"',
                    'core': 'gav',
                    'rows': 1,
                    'wt': 'json'
                }
                
                response = self.session.get(self.search_api_url, params=params, timeout=self.timeout)
                response.raise_for_status()
                
                data = response.json()
                result = data.get('response', {})
                docs = result.get('docs', [])
                
                # 如果找到了精确匹配的版本
                if docs:
                    self.logger.info(f"Found version {version} for {group_id}:{artifact_id}")
                    return {"exists": True}
                else:
                    self.logger.info(f"Version {version} not found for {group_id}:{artifact_id}")
                    return {"exists": False}
                    
            except Exception as e:
                self.logger.error(f"Error in version-specific search for {group_id}:{artifact_id}:{version}: {e}")
                return {"exists": False}
            
        except Exception as e:
            self.logger.error(f"Error checking version {version} for {library}: {e}")
            raise UpstreamError(f"Failed to check version: {str(e)}")
    
    def get_dependencies(self, library: str, version: str) -> Dict[str, Any]:
        """Get dependencies for a Java library by parsing POM file."""
        try:
            group_id, artifact_id = self._parse_library_name(library)
            if not group_id or not artifact_id:
                raise LibraryNotFoundError(f"Invalid library name format: {library}")
            
            # 如果是简短名称，需要先获取完整的Maven坐标
            if group_id == artifact_id:  # 简短名称
                # 使用模糊搜索获取正确的库信息
                search_result = self._search_maven_central(group_id, artifact_id, fuzzy=True)
                docs = search_result.get('docs', [])
                
                if not docs:
                    raise LibraryNotFoundError(f"Library not found: {library}")
                
                # 使用与get_latest_version相同的智能匹配逻辑
                exact_matches = [doc for doc in docs if doc.get('a') == artifact_id]
                if exact_matches:
                    docs = exact_matches
                    
                    # 优先选择知名的groupId
                    known_groups = {
                        'com.fasterxml.jackson.core': 1000,
                        'org.springframework': 900,
                        'org.apache': 800,
                        'com.google': 700,
                        'org.eclipse': 600,
                        'junit': 500,
                        'org.slf4j': 400
                    }
                    
                    def get_priority_score(doc):
                        group_id_temp = doc.get('g', '')
                        for known_group, score in known_groups.items():
                            if group_id_temp.startswith(known_group):
                                return score + doc.get('usageCount', 0)
                        return doc.get('usageCount', 0)
                    
                    docs.sort(key=get_priority_score, reverse=True)
                else:
                    # 按受欢迎程度排序
                    docs.sort(key=lambda x: (
                        x.get('usageCount', 0),
                        x.get('timestamp', 0)
                    ), reverse=True)
                
                selected_doc = docs[0]
                group_id = selected_doc.get('g')
                artifact_id = selected_doc.get('a')
                self.logger.info(f"Resolved {library} to {group_id}:{artifact_id}")
            
            # Get latest version if not specified
            if not version:
                latest_result = self.get_latest_version(f"{group_id}:{artifact_id}")
                version = latest_result.get("version")
                if not version:
                    raise LibraryNotFoundError(f"No version found for library: {library}")
            
            # 获取并解析POM文件
            pom_root = self._fetch_and_parse_pom(group_id, artifact_id, version)
            if pom_root is None:
                self.logger.warning(f"POM file not found for {group_id}:{artifact_id}:{version}")
                return {"dependencies": []}
            
            # 从POM文件中提取依赖
            dependencies = self._extract_dependencies_from_pom(pom_root)
            return {"dependencies": dependencies}
            
        except Exception as e:
            self.logger.error(f"Error getting dependencies for {library}: {e}")
            raise UpstreamError(f"Failed to get dependencies: {str(e)}")