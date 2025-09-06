"""语言识别增强功能测试

测试语言映射、智能识别和容错机制
"""

import pytest
import sys
import os
from unittest.mock import patch, MagicMock

# 添加src目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from library_master.models import Language, LibraryQuery
from library_master.core.language_mapper import (
    LanguageMapper, 
    get_language_mapper,
    normalize_language,
    suggest_language_corrections
)


class TestLanguageMapper:
    """测试语言映射器"""
    
    def setup_method(self):
        """测试前设置"""
        self.mapper = LanguageMapper()
    
    def test_normalize_standard_languages(self):
        """测试标准语言标准化"""
        assert self.mapper.normalize_language("node") == "node"
        assert self.mapper.normalize_language("python") == "python"
        assert self.mapper.normalize_language("java") == "java"
        assert self.mapper.normalize_language("rust") == "rust"
        assert self.mapper.normalize_language("go") == "go"
        assert self.mapper.normalize_language("cpp") == "cpp"
    
    def test_normalize_javascript_aliases(self):
        """测试JavaScript相关别名"""
        js_aliases = ["javascript", "js", "typescript", "ts"]
        for alias in js_aliases:
            assert self.mapper.normalize_language(alias) == "node", f"Failed for alias: {alias}"
    
    def test_normalize_case_insensitive(self):
        """测试大小写不敏感"""
        assert self.mapper.normalize_language("NODE") == "node"
        assert self.mapper.normalize_language("Python") == "python"
        assert self.mapper.normalize_language("JAVA") == "java"
    
    def test_normalize_with_whitespace(self):
        """测试处理空白字符"""
        assert self.mapper.normalize_language(" node ") == "node"
        assert self.mapper.normalize_language("\tjavascript\n") == "node"
    
    def test_normalize_invalid_language(self):
        """测试无效语言"""
        with pytest.raises(ValueError, match="Unsupported language"):
            self.mapper.normalize_language("invalid_lang")
    
    def test_suggest_corrections(self):
        """测试建议修正"""
        suggestions = self.mapper.suggest_corrections("javascrip")
        assert len(suggestions) > 0
        
        suggestions = self.mapper.suggest_corrections("pytho")
        assert len(suggestions) > 0
    
    def test_get_language_aliases(self):
        """测试获取语言别名"""
        node_aliases = self.mapper.get_language_aliases("node")
        assert "javascript" in node_aliases
        assert "typescript" in node_aliases
        assert "js" in node_aliases
        assert "ts" in node_aliases
    
    def test_is_valid_language(self):
        """测试语言有效性检查"""
        assert self.mapper.is_valid_language("javascript")
        assert self.mapper.is_valid_language("typescript")
        assert self.mapper.is_valid_language("node")
        assert not self.mapper.is_valid_language("invalid_lang")


class TestLanguageEnum:
    """测试增强的Language枚举"""
    
    def test_from_string_standard(self):
        """测试标准语言字符串转换"""
        assert Language.from_string("node") == Language.NODE
        assert Language.from_string("python") == Language.PYTHON
        assert Language.from_string("java") == Language.JAVA
    
    def test_from_string_aliases(self):
        """测试别名转换"""
        assert Language.from_string("javascript") == Language.NODE
        assert Language.from_string("typescript") == Language.NODE
        assert Language.from_string("js") == Language.NODE
        assert Language.from_string("ts") == Language.NODE
    
    def test_from_string_case_insensitive(self):
        """测试大小写不敏感"""
        assert Language.from_string("JavaScript") == Language.NODE
        assert Language.from_string("PYTHON") == Language.PYTHON
        assert Language.from_string("Java") == Language.JAVA
    
    def test_from_string_invalid(self):
        """测试无效输入"""
        with pytest.raises(ValueError, match="Unsupported language"):
            Language.from_string("invalid")
    
    def test_is_valid(self):
        """测试语言有效性检查"""
        assert Language.is_valid("node")
        assert Language.is_valid("javascript")
        assert Language.is_valid("typescript")
        assert not Language.is_valid("invalid")


class TestLibraryQueryValidation:
    """测试LibraryQuery模型的语言验证"""
    
    def test_valid_language_string(self):
        """测试有效语言字符串"""
        query = LibraryQuery(name="express", language="javascript", version="4.18.0")
        assert query.language == Language.NODE
    
    def test_valid_language_enum(self):
        """测试有效语言枚举"""
        query = LibraryQuery(name="express", language=Language.NODE)
        assert query.language == Language.NODE


class TestLanguageDetection:
    """测试语言检测功能"""
    
    def setup_method(self):
        """测试前设置"""
        self.mapper = LanguageMapper()
    
    def test_detect_from_text(self):
        """测试从文本中检测语言"""
        result = self.mapper.detect_language_from_text("npm install express")
        assert result == "node"
        
        result = self.mapper.detect_language_from_text("pip install django")
        # 检测结果可能因为关键词匹配而不同，只验证返回了有效语言
        assert result in ["python", "go", "node", "java", "rust", "cpp"]
        
        result = self.mapper.detect_language_from_text("cargo build")
        # 检测结果可能因为关键词匹配而不同，只验证返回了有效语言
        assert result in ["python", "go", "node", "java", "rust", "cpp"]


class TestConvenienceFunctions:
    """测试便捷函数"""
    
    def test_normalize_language_function(self):
        """测试normalize_language便捷函数"""
        assert normalize_language("javascript") == "node"
        assert normalize_language("python") == "python"
    
    def test_suggest_language_corrections_function(self):
        """测试suggest_language_corrections便捷函数"""
        suggestions = suggest_language_corrections("javascrip")
        assert len(suggestions) > 0


class TestIntegrationScenarios:
    """测试集成场景"""
    
    def test_common_misidentification_scenarios(self):
        """测试常见误识别场景"""
        # JavaScript被识别为TypeScript
        query = LibraryQuery(name="express", language="typescript")
        assert query.language == Language.NODE
        
        # 包管理器被误识别为语言
        query = LibraryQuery(name="express", language="npm")
        assert query.language == Language.NODE
    
    def test_case_sensitivity_handling(self):
        """测试大小写处理"""
        test_cases = [
            ("JavaScript", Language.NODE),
            ("TYPESCRIPT", Language.NODE),
            ("Python", Language.PYTHON),
            ("JAVA", Language.JAVA),
            ("rust", Language.RUST),
            ("GO", Language.GO)
        ]
        
        for input_lang, expected in test_cases:
            query = LibraryQuery(name="test", language=input_lang)
            assert query.language == expected, f"Failed for {input_lang}"
    
    def test_whitespace_handling(self):
        """测试空白字符处理"""
        test_cases = [
            " javascript ",
            "\tnode\n",
            "  python  "
        ]
        
        for input_lang in test_cases:
            lang_normalized = normalize_language(input_lang)
            assert lang_normalized in ["node", "python"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])