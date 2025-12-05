"""数据模型定义"""

from enum import Enum
from typing import Optional, List, Dict, Any

from pydantic import BaseModel, Field, field_validator, ConfigDict


class Language(str, Enum):
    """支持的编程语言
    
    增强版Language枚举，支持语言别名和智能识别
    """
    RUST = "rust"
    PYTHON = "python"
    JAVA = "java"
    NODE = "node"
    GO = "go"
    CPP = "cpp"
    
    @classmethod
    def from_string(cls, language_input: str) -> 'Language':
        """从字符串创建Language实例，支持别名和容错
        
        Args:
            language_input: 语言字符串（支持别名）
            
        Returns:
            Language枚举实例
            
        Raises:
            ValueError: 如果无法识别语言
        """
        # 延迟导入避免循环依赖
        from .core.language_mapper import normalize_language
        
        try:
            normalized = normalize_language(language_input)
            return cls(normalized)
        except ValueError as e:
            # 提供更友好的错误信息
            from .core.language_mapper import suggest_language_corrections
            suggestions = suggest_language_corrections(language_input)
            
            error_msg = f"Unsupported language: '{language_input}'"
            if suggestions:
                error_msg += f". Did you mean: {', '.join(suggestions)}?"
            else:
                error_msg += f". Supported languages: {', '.join([lang.value for lang in cls])}"
            
            raise ValueError(error_msg) from e
    
    @classmethod
    def is_valid(cls, language_input: str) -> bool:
        """检查语言输入是否有效
        
        Args:
            language_input: 语言字符串
            
        Returns:
            是否为有效语言
        """
        try:
            cls.from_string(language_input)
            return True
        except ValueError:
            return False
    
    @classmethod
    def get_aliases(cls, language: 'Language') -> List[str]:
        """获取指定语言的所有别名
        
        Args:
            language: Language枚举实例
            
        Returns:
            该语言的所有别名列表
        """
        from .core.language_mapper import get_language_mapper
        return get_language_mapper().get_language_aliases(language.value)
    
    def get_display_name(self) -> str:
        """获取语言的显示名称"""
        display_names = {
            "rust": "Rust",
            "python": "Python", 
            "java": "Java",
            "node": "Node.js",
            "go": "Go",
            "cpp": "C++"
        }
        return display_names.get(self.value, self.value.title())


class LibraryQuery(BaseModel):
    """库查询请求
    
    支持智能语言识别和转换
    """
    name: str = Field(..., description="库名称")
    language: Language = Field(..., description="编程语言")
    version: Optional[str] = Field(None, description="版本号")
    depth: int = Field(1, ge=1, le=10, description="依赖查询深度，默认1")

    @field_validator('language', mode='before')
    @classmethod
    def validate_language(cls, v):
        """验证并转换语言输入
        
        支持字符串输入并自动转换为Language枚举
        """
        if isinstance(v, str):
            return Language.from_string(v)
        elif isinstance(v, Language):
            return v
        else:
            raise ValueError(f"Language must be a string or Language enum, got {type(v)}")
    
    model_config = ConfigDict(
        use_enum_values=True,
        json_schema_extra={
            "example": {
                "name": "express",
                "language": "node",  # 支持别名
                "version": "4.18.0"
            }
        }
    )


class Task(BaseModel):
    """任务模型
    
    支持智能语言识别和转换
    """
    language: Language = Field(..., description="编程语言")
    library: str = Field(..., description="库名称")
    version: Optional[str] = Field(None, description="版本号")
    operation: str = Field(..., description="操作类型")
    depth: int = Field(1, description="依赖查询深度")

    @field_validator('language', mode='before')
    @classmethod
    def validate_language(cls, v):
        """验证并转换语言输入"""
        if isinstance(v, str):
            return Language.from_string(v)
        elif isinstance(v, Language):
            return v
        else:
            raise ValueError(f"Language must be a string or Language enum, got {type(v)}")
    
    model_config = ConfigDict(use_enum_values=True)


class TaskResult(BaseModel):
    """任务结果 - 符合PRD规范"""
    language: str = Field(..., description="编程语言")
    library: str = Field(..., description="库名称")
    version: Optional[str] = Field(None, description="版本号")
    status: str = Field(..., description="执行状态: success/error")
    # 具体数据字段 - 根据操作类型动态包含
    # find_latest_versions: version, url
    # find_library_docs: doc_url
    # check_versions_exist: exists
    # find_library_dependencies: dependencies
    data: Optional[Dict[str, Any]] = Field(None, description="结果数据")
    error: Optional[str] = Field(None, description="错误信息")
    execution_time: Optional[float] = Field(None, description="执行时间(秒)")
    # 为check_versions_exist操作添加的字段
    exists: Optional[bool] = Field(None, description="版本是否存在(仅用于check_versions_exist)")
    # 为依赖分析添加的字段
    conflicts: Optional[List[Dict[str, Any]]] = Field(None, description="版本冲突列表")
    suggested_versions: Optional[Dict[str, str]] = Field(None, description="建议解决版本")


class BatchRequest(BaseModel):
    """批量请求"""
    libraries: List[LibraryQuery] = Field(..., description="库查询列表")


class BatchSummary(BaseModel):
    """批量处理摘要"""
    total: int = Field(..., description="总数量")
    success: int = Field(..., description="成功数量")
    failed: int = Field(..., description="失败数量")


class BatchResponse(BaseModel):
    """批量响应"""
    results: List[TaskResult] = Field(..., description="结果列表")
    summary: BatchSummary = Field(..., description="处理摘要")


class VersionInfo(BaseModel):
    """版本信息"""
    version: str = Field(..., description="版本号")
    url: Optional[str] = Field(None, description="库链接")


class DocumentationInfo(BaseModel):
    """文档信息"""
    doc_url: Optional[str] = Field(None, description="文档链接")


class ExistenceInfo(BaseModel):
    """存在性信息"""
    exists: bool = Field(..., description="是否存在")


class DependencyInfo(BaseModel):
    """依赖信息"""
    name: str = Field(..., description="依赖名称")
    version: str = Field(..., description="依赖版本约束")
    dependencies: Optional[List['DependencyInfo']] = Field(None, description="子依赖")
    resolved_version: Optional[str] = Field(None, description="解析后的具体版本")


class DependenciesInfo(BaseModel):
    """依赖列表信息"""
    dependencies: List[DependencyInfo] = Field(..., description="依赖列表")
