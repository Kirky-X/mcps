"""智能语言识别模块

处理常见的语言误识别情况，特别是language和ecosystem的混淆
"""

import re
from typing import Dict, List, Optional, Tuple, Set
from enum import Enum

from ..models import Language
from .language_mapper import get_language_mapper, LanguageMapper


class DetectionContext(Enum):
    """检测上下文类型"""
    LIBRARY_NAME = "library_name"
    USER_INPUT = "user_input"
    FILE_EXTENSION = "file_extension"
    PACKAGE_MANAGER = "package_manager"
    DOCUMENTATION = "documentation"
    API_REQUEST = "api_request"


class SmartLanguageDetector:
    """智能语言检测器
    
    处理常见的语言识别错误和混淆情况
    """
    
    def __init__(self):
        self.language_mapper: LanguageMapper = get_language_mapper()
        
        # 生态系统关键词映射到语言
        self.ecosystem_to_language = {
            # JavaScript生态系统
            "npm": "node",
            "yarn": "node", 
            "pnpm": "node",
            "webpack": "node",
            "babel": "node",
            "eslint": "node",
            "prettier": "node",
            "jest": "node",
            "mocha": "node",
            "express": "node",
            "react": "node",
            "vue": "node",
            "angular": "node",
            "next": "node",
            "nuxt": "node",
            "svelte": "node",
            "nodejs": "node",
            "node.js": "node",
            
            # Python生态系统
            "pip": "python",
            "conda": "python",
            "poetry": "python",
            "pipenv": "python",
            "django": "python",
            "flask": "python",
            "fastapi": "python",
            "pandas": "python",
            "numpy": "python",
            "scipy": "python",
            "matplotlib": "python",
            "tensorflow": "python",
            "pytorch": "python",
            "scikit-learn": "python",
            
            # Java生态系统
            "maven": "java",
            "gradle": "java",
            "spring": "java",
            "hibernate": "java",
            "junit": "java",
            "tomcat": "java",
            "jetty": "java",
            
            # Rust生态系统
            "cargo": "rust",
            "crates": "rust",
            "tokio": "rust",
            "serde": "rust",
            "actix": "rust",
            
            # Go生态系统
            "go mod": "go",
            "golang": "go",
            "gin": "go",
            "echo": "go",
            "gorm": "go",
            
            # C++生态系统
            "cmake": "cpp",
            "conan": "cpp",
            "vcpkg": "cpp",
            "boost": "cpp",
            "qt": "cpp",
        }
        
        # 文件扩展名映射
        self.extension_to_language = {
            ".js": "node",
            ".jsx": "node",
            ".ts": "node",
            ".tsx": "node",
            ".mjs": "node",
            ".cjs": "node",
            ".py": "python",
            ".pyx": "python",
            ".pyi": "python",
            ".java": "java",
            ".kt": "java",  # Kotlin也归类为Java生态
            ".scala": "java",  # Scala也归类为Java生态
            ".rs": "rust",
            ".go": "go",
            ".cpp": "cpp",
            ".cc": "cpp",
            ".cxx": "cpp",
            ".c++": "cpp",
            ".hpp": "cpp",
            ".hh": "cpp",
            ".hxx": "cpp",
            ".h++": "cpp",
            ".c": "cpp",  # C归类为C++
            ".h": "cpp",
        }
        
        # 常见误识别模式
        self.misidentification_patterns = {
            # JavaScript相关的常见错误
            r"\b(javascript|js|typescript|ts)\b": "node",
            r"\b(react|vue|angular|next|nuxt|svelte)\b": "node",
            r"\b(npm|yarn|pnpm|webpack|babel)\b": "node",
            
            # 包管理器被误识别为语言
            r"\b(pip|conda|poetry)\b": "python",
            r"\b(maven|gradle)\b": "java",
            r"\b(cargo|crates)\b": "rust",
            
            # 框架被误识别为语言
            r"\b(django|flask|fastapi)\b": "python",
            r"\b(spring|hibernate)\b": "java",
            r"\b(express|koa|fastify)\b": "node",
        }
    
    def detect_language_from_context(
        self, 
        text: str, 
        context: DetectionContext = DetectionContext.USER_INPUT,
        library_name: Optional[str] = None
    ) -> Optional[str]:
        """从上下文中智能检测语言
        
        Args:
            text: 输入文本
            context: 检测上下文
            library_name: 库名称（可选）
            
        Returns:
            检测到的语言，如果无法确定则返回None
        """
        text_lower = text.lower().strip()
        
        # 1. 首先尝试直接语言映射
        try:
            return self.language_mapper.normalize_language(text)
        except ValueError:
            pass
        
        # 2. 检查生态系统关键词
        for ecosystem, language in self.ecosystem_to_language.items():
            if ecosystem.lower() in text_lower:
                return language
        
        # 3. 使用正则模式匹配
        for pattern, language in self.misidentification_patterns.items():
            if re.search(pattern, text_lower, re.IGNORECASE):
                return language
        
        # 4. 根据上下文类型进行特殊处理
        if context == DetectionContext.FILE_EXTENSION:
            return self._detect_from_extension(text)
        elif context == DetectionContext.LIBRARY_NAME and library_name:
            return self._detect_from_library_name(library_name)
        elif context == DetectionContext.PACKAGE_MANAGER:
            return self._detect_from_package_manager(text)
        
        # 5. 模糊匹配
        return self._fuzzy_match_language(text)
    
    def _detect_from_extension(self, filename: str) -> Optional[str]:
        """从文件扩展名检测语言"""
        for ext, language in self.extension_to_language.items():
            if filename.lower().endswith(ext):
                return language
        return None
    
    def _detect_from_library_name(self, library_name: str) -> Optional[str]:
        """从库名称推断语言
        
        基于常见的库名称模式
        """
        library_lower = library_name.lower()
        
        # JavaScript/Node.js库的常见模式
        js_patterns = [
            r"^@[\w-]+/",  # scoped packages
            r"\.(js|ts|jsx|tsx)$",
            r"^(react|vue|angular|next|nuxt)-",
            r"-(js|ts|react|vue|angular)$",
            r"^(babel|webpack|eslint|prettier)-",
        ]
        
        for pattern in js_patterns:
            if re.search(pattern, library_lower):
                return "node"
        
        # Python库的常见模式
        python_patterns = [
            r"^py[\w-]*",
            r"[\w-]*py$",
            r"^django-",
            r"^flask-",
        ]
        
        for pattern in python_patterns:
            if re.search(pattern, library_lower):
                return "python"
        
        return None
    
    def _detect_from_package_manager(self, text: str) -> Optional[str]:
        """从包管理器命令检测语言"""
        text_lower = text.lower()
        
        if any(pm in text_lower for pm in ["npm", "yarn", "pnpm"]):
            return "node"
        elif any(pm in text_lower for pm in ["pip", "conda", "poetry", "pipenv"]):
            return "python"
        elif any(pm in text_lower for pm in ["maven", "gradle"]):
            return "java"
        elif "cargo" in text_lower:
            return "rust"
        elif "go get" in text_lower or "go mod" in text_lower:
            return "go"
        
        return None
    
    def _fuzzy_match_language(self, text: str) -> Optional[str]:
        """模糊匹配语言
    
        使用编辑距离等算法进行模糊匹配
        """
        suggestions = self.language_mapper.suggest_corrections(text)
        if suggestions:
            return suggestions[0]
        return None
    
    def resolve_language_ecosystem_confusion(
        self, 
        language_input: str, 
        ecosystem_input: Optional[str] = None
    ) -> Tuple[str, Optional[str]]:
        """解决language和ecosystem参数的混淆
        
        Args:
            language_input: 语言输入（可能被误用为生态系统）
            ecosystem_input: 生态系统输入（可能被误用为语言）
            
        Returns:
            (正确的语言, 正确的生态系统)
        """
        # 检测language_input是否实际上是生态系统
        detected_from_language = self.detect_language_from_context(
            language_input, 
            DetectionContext.USER_INPUT
        )
        
        # 检测ecosystem_input是否实际上是语言
        detected_from_ecosystem = None
        if ecosystem_input:
            detected_from_ecosystem = self.detect_language_from_context(
                ecosystem_input,
                DetectionContext.USER_INPUT
            )
        
        # 决策逻辑
        if detected_from_language:
            # language_input能够被识别为有效语言
            return detected_from_language, ecosystem_input
        elif detected_from_ecosystem:
            # ecosystem_input能够被识别为有效语言，说明参数位置颠倒了
            return detected_from_ecosystem, language_input
        else:
            # 都无法识别，尝试从生态系统映射中查找
            ecosystem_lang = self.ecosystem_to_language.get(language_input.lower())
            if ecosystem_lang:
                return ecosystem_lang, language_input
            
            # 最后尝试建议修正
            suggestions = self.language_mapper.suggest_language_corrections(language_input)
            if suggestions:
                return suggestions[0], ecosystem_input
            
            # 无法解决，抛出详细错误
            raise ValueError(
                f"Cannot resolve language/ecosystem confusion. "
                f"Language input: '{language_input}', Ecosystem input: '{ecosystem_input}'. "
                f"Please provide a valid language from: {', '.join([lang.value for lang in Language])}"
            )
    
    def validate_and_normalize_language(
        self, 
        language_input: str,
        context: DetectionContext = DetectionContext.API_REQUEST,
        additional_context: Optional[Dict[str, str]] = None
    ) -> str:
        """验证并标准化语言输入
        
        Args:
            language_input: 语言输入
            context: 检测上下文
            additional_context: 额外上下文信息
            
        Returns:
            标准化的语言字符串
            
        Raises:
            ValueError: 如果无法识别或验证语言
        """
        # 尝试智能检测
        detected_language = self.detect_language_from_context(
            language_input, 
            context,
            additional_context.get('library_name') if additional_context else None
        )
        
        if detected_language:
            return detected_language

        # 如果检测失败，提供详细的错误信息和建议
        suggestions = self.language_mapper.suggest_corrections(language_input)
        suggestion_msg = f". Did you mean: {', '.join(suggestions)}?" if suggestions else ""
        
        raise ValueError(
            f"Unsupported or unrecognized language: '{language_input}'{suggestion_msg}"
        )


# 全局实例
_smart_detector = None


def get_smart_language_detector() -> SmartLanguageDetector:
    """获取智能语言检测器的全局实例"""
    global _smart_detector
    if _smart_detector is None:
        _smart_detector = SmartLanguageDetector()
    return _smart_detector


# 便捷函数
def smart_detect_language(
    text: str, 
    context: DetectionContext = DetectionContext.USER_INPUT,
    **kwargs
) -> Optional[str]:
    """智能检测语言的便捷函数"""
    return get_smart_language_detector().detect_language_from_context(text, context, **kwargs)


def resolve_confusion(language_input: str, ecosystem_input: Optional[str] = None) -> Tuple[str, Optional[str]]:
    """解决language/ecosystem混淆的便捷函数"""
    return get_smart_language_detector().resolve_language_ecosystem_confusion(language_input, ecosystem_input)


def validate_language(
    language_input: str,
    context: DetectionContext = DetectionContext.API_REQUEST,
    **kwargs
) -> str:
    """验证语言的便捷函数"""
    return get_smart_language_detector().validate_and_normalize_language(language_input, context, kwargs)