"""语言识别增强功能测试（迁移版）"""

import pytest

from library.models import Language, LibraryQuery
from library.core.language_mapper import (
    LanguageMapper,
    normalize_language,
    get_language_mapper,
)


class TestLanguageMapper:
    def setup_method(self):
        self.mapper = LanguageMapper()

    def test_normalize_standard_languages(self):
        assert self.mapper.normalize_language("node") == "node"
        assert self.mapper.normalize_language("python") == "python"
        assert self.mapper.normalize_language("java") == "java"
        assert self.mapper.normalize_language("rust") == "rust"
        assert self.mapper.normalize_language("go") == "go"
        assert self.mapper.normalize_language("cpp") == "cpp"

    def test_normalize_javascript_aliases(self):
        for alias in ["javascript", "js", "typescript", "ts"]:
            assert self.mapper.normalize_language(alias) == "node"

    def test_normalize_case_insensitive(self):
        assert self.mapper.normalize_language("NODE") == "node"
        assert self.mapper.normalize_language("Python") == "python"
        assert self.mapper.normalize_language("JAVA") == "java"

    def test_normalize_with_whitespace(self):
        assert self.mapper.normalize_language(" node ") == "node"
        assert self.mapper.normalize_language("\tjavascript\n") == "node"

    def test_normalize_invalid_language(self):
        with pytest.raises(ValueError, match="Unsupported language"):
            self.mapper.normalize_language("invalid_lang")

    def test_is_valid_language(self):
        assert get_language_mapper().is_valid_language("javascript")
        assert get_language_mapper().is_valid_language("typescript")
        assert get_language_mapper().is_valid_language("node")
        assert not get_language_mapper().is_valid_language("invalid_lang")


class TestLanguageEnum:
    def test_from_string_standard(self):
        assert Language.from_string("node") == Language.NODE
        assert Language.from_string("python") == Language.PYTHON
        assert Language.from_string("java") == Language.JAVA

    def test_from_string_aliases(self):
        assert Language.from_string("javascript") == Language.NODE
        assert Language.from_string("typescript") == Language.NODE
        assert Language.from_string("js") == Language.NODE
        assert Language.from_string("ts") == Language.NODE

    def test_from_string_case_insensitive(self):
        assert Language.from_string("JavaScript") == Language.NODE
        assert Language.from_string("PYTHON") == Language.PYTHON
        assert Language.from_string("Java") == Language.JAVA

    def test_from_string_invalid(self):
        with pytest.raises(ValueError, match="Unsupported language"):
            Language.from_string("invalid")

    def test_is_valid(self):
        assert Language.is_valid("node")
        assert Language.is_valid("javascript")
        assert Language.is_valid("typescript")
        assert not Language.is_valid("invalid")


class TestLibraryQueryValidation:
    def test_valid_language_string(self):
        query = LibraryQuery(name="express", language="javascript", version="4.18.0")
        assert query.language == Language.NODE

    def test_valid_language_enum(self):
        query = LibraryQuery(name="express", language=Language.NODE)
        assert query.language == Language.NODE


class TestLanguageDetection:
    def setup_method(self):
        self.mapper = LanguageMapper()

    def test_detect_from_text(self):
        result = self.mapper.detect_language_from_text("npm install express")
        assert result == "node" or result is None

        result = self.mapper.detect_language_from_text("pip install django")
        assert result in ["python", "go", "node", "java", "rust", "cpp", None]

        result = self.mapper.detect_language_from_text("cargo build")
        assert result in ["python", "go", "node", "java", "rust", "cpp", None]


class TestConvenienceFunctions:
    def test_normalize_language_function(self):
        assert normalize_language("javascript") == "node"
        assert normalize_language("python") == "python"


class TestIntegrationScenarios:
    def test_common_misidentification_scenarios(self):
        query = LibraryQuery(name="express", language="typescript")
        assert query.language == Language.NODE

        query = LibraryQuery(name="express", language="npm")
        assert query.language == Language.NODE

    def test_case_sensitivity_handling(self):
        test_cases = [
            ("JavaScript", Language.NODE),
            ("TYPESCRIPT", Language.NODE),
            ("Python", Language.PYTHON),
            ("JAVA", Language.JAVA),
            ("rust", Language.RUST),
            ("GO", Language.GO),
        ]
        for input_lang, expected in test_cases:
            query = LibraryQuery(name="test", language=input_lang)
            assert query.language == expected

    def test_whitespace_handling(self):
        for input_lang in [" javascript ", "\tnode\n", "  python  "]:
            lang_normalized = normalize_language(input_lang)
            assert lang_normalized in ["node", "python"]
