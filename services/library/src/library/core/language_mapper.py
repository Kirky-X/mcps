"""语言映射和别名处理模块

此模块提供统一的语言识别、映射和容错机制，解决以下问题：
1. JavaScript/TypeScript/Node.js统一识别为node
2. language和ecosystem的混淆问题
3. 提供智能的语言别名处理
"""

import re
from typing import Dict, List, Optional, Set, Tuple
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class LanguageCategory(Enum):
    """语言类别枚举"""
    PROGRAMMING_LANGUAGE = "programming_language"
    ECOSYSTEM = "ecosystem"
    PACKAGE_MANAGER = "package_manager"
    FRAMEWORK = "framework"


class LanguageMapper:
    """语言映射器 - 提供智能的语言识别和转换功能"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # 标准语言映射表
        self._standard_languages = {
            "rust": "rust",
            "python": "python", 
            "java": "java",
            "node": "node",
            "go": "go",
            "cpp": "cpp"
        }
        
        # 语言别名映射表 - 将各种别名统一映射到标准语言
        self._language_aliases = {
            # Rust别名
            "rust": "rust",
            "rs": "rust",
            "cargo": "rust",
            
            # Python别名
            "python": "python",
            "py": "python",
            "python3": "python",
            "pip": "python",
            "pypi": "python",
            
            # Java别名
            "java": "java",
            "jvm": "java",
            "maven": "java",
            "gradle": "java",
            "kotlin": "java",  # Kotlin运行在JVM上，使用Maven仓库
            "scala": "java",   # Scala也使用Maven仓库
            
            # Node.js/JavaScript/TypeScript别名 - 统一映射到node
            "node": "node",
            "nodejs": "node",
            "javascript": "node",
            "js": "node",
            "typescript": "node",
            "ts": "node",
            "npm": "node",
            "yarn": "node",
            "pnpm": "node",
            "bun": "node",
            "deno": "node",  # Deno也可以使用npm包
            
            # Go别名
            "go": "go",
            "golang": "go",
            "goproxy": "go",
            
            # C++别名
            "cpp": "cpp",
            "c++": "cpp",
            "cxx": "cpp",
            "cc": "cpp",
            "cmake": "cpp",
            "conan": "cpp",
            "vcpkg": "cpp",
        }
        
        # 关键词映射 - 用于从文本中识别语言
        self._keyword_mapping = {
            "rust": ["rust", "cargo", "crate", "rustc", "rustup"],
            "python": ["python", "pip", "pypi", "conda", "virtualenv", "django", "flask"],
            "java": ["java", "maven", "gradle", "spring", "junit", "kotlin", "scala"],
            "node": ["node", "nodejs", "javascript", "typescript", "npm", "yarn", "react", "vue", "angular", "express"],
            "go": ["go", "golang", "goproxy", "mod"],
            "cpp": ["c++", "cpp", "cmake", "conan", "vcpkg", "boost"]
        }
        
        # 生态系统关键词 - 帮助区分language和ecosystem
        self._ecosystem_keywords = {
            "maven", "gradle", "npm", "yarn", "pip", "cargo", "conan", "vcpkg", 
            "goproxy", "pypi", "crates.io", "npmjs", "maven-central"
        }
        
        # 框架关键词
        self._framework_keywords = {
            "react", "vue", "angular", "express", "django", "flask", "spring", 
            "spring-boot", "junit", "boost", "tokio", "actix"
        }
    
    def normalize_language(self, language_input: str) -> str:
        """标准化语言输入
        
        Args:
            language_input: 用户输入的语言字符串
            
        Returns:
            标准化后的语言名称
            
        Raises:
            ValueError: 如果无法识别语言
        """
        if not language_input:
            raise ValueError("Language input cannot be empty")
        
        # 清理输入
        cleaned_input = self._clean_input(language_input)
        
        # 直接别名匹配
        if cleaned_input in self._language_aliases:
            result = self._language_aliases[cleaned_input]
            self.logger.debug(f"Direct alias match: '{language_input}' -> '{result}'")
            return result
        
        # 智能匹配
        result = self._smart_match(cleaned_input)
        if result:
            self.logger.debug(f"Smart match: '{language_input}' -> '{result}'")
            return result
        
        # 如果都无法匹配，抛出异常
        self.logger.warning(f"Unable to normalize language: '{language_input}'")
        raise ValueError(
            f"Unsupported language: '{language_input}'. "
            f"Supported languages: {list(self._standard_languages.keys())}"
        )
    
    def _clean_input(self, input_str: str) -> str:
        """清理输入字符串"""
        # 转换为小写
        cleaned = input_str.lower().strip()
        
        # 移除常见的分隔符和特殊字符
        cleaned = re.sub(r'[\-_\s\.]+', '', cleaned)
        
        return cleaned
    
    def _smart_match(self, cleaned_input: str) -> Optional[str]:
        """智能匹配语言"""
        # 1. 部分匹配
        for alias, language in self._language_aliases.items():
            if cleaned_input in alias or alias in cleaned_input:
                return language
        
        # 2. 关键词匹配
        for language, keywords in self._keyword_mapping.items():
            for keyword in keywords:
                if keyword.lower().replace('-', '').replace('_', '') in cleaned_input:
                    return language
        
        return None
    
    def detect_language_from_text(self, text: str) -> Optional[str]:
        """从文本中检测语言
        
        Args:
            text: 包含语言信息的文本
            
        Returns:
            检测到的标准语言名称，如果无法检测则返回None
        """
        if not text:
            return None
        
        text_lower = text.lower()
        language_scores = {}
        
        # 计算每种语言的匹配分数
        for language, keywords in self._keyword_mapping.items():
            score = 0
            for keyword in keywords:
                if keyword in text_lower:
                    # 根据关键词重要性给不同权重
                    if keyword == language:  # 语言名本身权重最高
                        score += 10
                    elif keyword in self._ecosystem_keywords:
                        score += 5
                    elif keyword in self._framework_keywords:
                        score += 3
                    else:
                        score += 1
            
            if score > 0:
                language_scores[language] = score
        
        # 返回得分最高的语言
        if language_scores:
            best_language = max(language_scores.items(), key=lambda x: x[1])[0]
            self.logger.debug(f"Detected language from text: '{best_language}' (scores: {language_scores})")
            return best_language
        
        return None
    
    def categorize_input(self, input_str: str) -> LanguageCategory:
        """分类输入字符串的类型
        
        Args:
            input_str: 输入字符串
            
        Returns:
            输入的类别
        """
        cleaned = input_str.lower().strip()
        
        if cleaned in self._ecosystem_keywords:
            return LanguageCategory.ECOSYSTEM
        elif cleaned in self._framework_keywords:
            return LanguageCategory.FRAMEWORK
        elif cleaned in self._language_aliases:
            return LanguageCategory.PROGRAMMING_LANGUAGE
        else:
            # 默认认为是编程语言
            return LanguageCategory.PROGRAMMING_LANGUAGE
    
    def get_supported_languages(self) -> List[str]:
        """获取支持的标准语言列表"""
        return list(self._standard_languages.keys())
    
    def get_language_aliases(self, language: str) -> List[str]:
        """获取指定语言的所有别名
        
        Args:
            language: 标准语言名称
            
        Returns:
            该语言的所有别名列表
        """
        if language not in self._standard_languages:
            return []
        
        aliases = []
        for alias, mapped_lang in self._language_aliases.items():
            if mapped_lang == language:
                aliases.append(alias)
        
        return aliases
    
    def is_valid_language(self, language: str) -> bool:
        """检查是否为有效的语言输入
        
        Args:
            language: 语言字符串
            
        Returns:
            是否为有效语言
        """
        try:
            self.normalize_language(language)
            return True
        except ValueError:
            return False
    
    def suggest_corrections(self, invalid_language: str) -> List[str]:
        """为无效的语言输入提供建议
        
        Args:
            invalid_language: 无效的语言输入
            
        Returns:
            建议的语言列表
        """
        suggestions = []
        cleaned_input = self._clean_input(invalid_language)
        
        # 基于编辑距离的建议
        for alias in self._language_aliases.keys():
            if self._levenshtein_distance(cleaned_input, alias) <= 2:
                mapped_lang = self._language_aliases[alias]
                if mapped_lang not in suggestions:
                    suggestions.append(mapped_lang)
        
        # 基于部分匹配的建议
        for language, keywords in self._keyword_mapping.items():
            for keyword in keywords:
                if (cleaned_input in keyword or keyword in cleaned_input) and language not in suggestions:
                    suggestions.append(language)
        
        return suggestions[:5]  # 最多返回5个建议
    
    def _levenshtein_distance(self, s1: str, s2: str) -> int:
        """计算两个字符串的编辑距离"""
        if len(s1) < len(s2):
            return self._levenshtein_distance(s2, s1)
        
        if len(s2) == 0:
            return len(s1)
        
        previous_row = list(range(len(s2) + 1))
        for i, c1 in enumerate(s1):
            current_row = [i + 1]
            for j, c2 in enumerate(s2):
                insertions = previous_row[j + 1] + 1
                deletions = current_row[j] + 1
                substitutions = previous_row[j] + (c1 != c2)
                current_row.append(min(insertions, deletions, substitutions))
            previous_row = current_row
        
        return previous_row[-1]


# 全局语言映射器实例
_language_mapper = None


def get_language_mapper() -> LanguageMapper:
    """获取全局语言映射器实例"""
    global _language_mapper
    if _language_mapper is None:
        _language_mapper = LanguageMapper()
    return _language_mapper


def normalize_language(language_input: str) -> str:
    """便捷函数：标准化语言输入"""
    return get_language_mapper().normalize_language(language_input)


def detect_language_from_text(text: str) -> Optional[str]:
    """便捷函数：从文本中检测语言"""
    return get_language_mapper().detect_language_from_text(text)


def is_valid_language(language: str) -> bool:
    """便捷函数：检查是否为有效语言"""
    return get_language_mapper().is_valid_language(language)


def suggest_language_corrections(invalid_language: str) -> List[str]:
    """便捷函数：为无效语言提供建议"""
    return get_language_mapper().suggest_corrections(invalid_language)