"""数据模型定义"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum


class Language(str, Enum):
    """支持的编程语言"""
    RUST = "rust"
    PYTHON = "python"
    JAVA = "java"
    NODE = "node"


class LibraryQuery(BaseModel):
    """库查询请求"""
    name: str = Field(..., description="库名称")
    language: Language = Field(..., description="编程语言")
    version: Optional[str] = Field(None, description="版本号")


class Task(BaseModel):
    """任务模型"""
    language: Language = Field(..., description="编程语言")
    library: str = Field(..., description="库名称")
    version: Optional[str] = Field(None, description="版本号")
    operation: str = Field(..., description="操作类型")


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
    version: str = Field(..., description="依赖版本")


class DependenciesInfo(BaseModel):
    """依赖列表信息"""
    dependencies: List[DependencyInfo] = Field(..., description="依赖列表")
