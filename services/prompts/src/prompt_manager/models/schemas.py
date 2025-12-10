# Copyright (c) Kirky.X. 2025. All rights reserved.
from datetime import datetime
from typing import List, Optional, Dict, Any, Literal

from pydantic import BaseModel, Field, PrivateAttr


class RoleConfig(BaseModel):
    role_type: Literal["system", "user", "assistant", "principle"]
    content: str
    order: int
    template_variables: Optional[Dict[str, Any]] = None


class LLMConfigModel(BaseModel):
    model: str = "gpt-3.5-turbo"
    temperature: float = 0.7
    max_tokens: int = 1000
    top_p: float = 1.0
    top_k: Optional[int] = None
    frequency_penalty: float = 0.0
    presence_penalty: float = 0.0
    stop_sequences: Optional[List[str]] = None
    other_params: Optional[Dict[str, Any]] = None


class PrincipleRefModel(BaseModel):
    principle_name: str
    version: str = "latest"


class CreatePrincipleRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=200, pattern="^[a-zA-Z0-9_]+$")
    version: str = Field(..., min_length=1, max_length=10)
    content: str
    is_active: bool = True
    is_latest: bool = True


class CreatePromptRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=200, pattern="^[a-zA-Z0-9_]+$")
    description: str
    roles: List[RoleConfig]
    version_type: Literal["major", "minor"] = "minor"
    tags: Optional[List[str]] = None
    llm_config: Optional[LLMConfigModel] = None
    client_type: Optional[str] = None
    principle_refs: Optional[List[PrincipleRefModel]] = None
    change_log: Optional[str] = None


class UpdatePromptRequest(CreatePromptRequest):
    pass


class SearchRequest(BaseModel):
    query: Optional[str] = None
    tags: Optional[List[str]] = None
    logic: Literal["AND", "OR"] = "AND"
    version_filter: Literal["latest", "all", "specific"] = "latest"
    specific_version: Optional[str] = None
    limit: int = 10
    offset: int = 0


class SearchResultItem(BaseModel):
    prompt_id: str
    name: str
    version: str
    description: str
    tags: List[str]
    similarity_score: Optional[float]
    created_at: datetime


class SearchResult(BaseModel):
    total: int
    results: List[SearchResultItem]


class GetRequest(BaseModel):
    name: str
    version: Optional[str] = None
    output_format: Literal["openai", "formatted", "both"] = "both"
    template_vars: Optional[Dict[str, Any]] = None
    runtime_params: Optional[Dict[str, Any]] = None


class OpenAIRequest(BaseModel):
    model: str
    messages: List[Dict[str, str]]
    temperature: float
    max_tokens: int
    top_p: float
    frequency_penalty: float
    presence_penalty: float
    stop: Optional[List[str]]
    stream: bool = False
    user: Optional[str] = None


class FormattedPrompt(BaseModel):
    messages: List[Dict[str, str]]


class BothFormats(BaseModel):
    openai_format: OpenAIRequest
    formatted: FormattedPrompt
    _meta_version: str = PrivateAttr(default=None)

    @property
    def version(self):
        class _V:
            def __init__(self, ver: str):
                self.version = ver
        return _V(self._meta_version or "")


class FullPrompt:
    def __init__(self, version, roles, principles, llm_config):
        """聚合完整提示所需的结构体

        封装提示版本主体、角色配置、原则集合与 LLM 配置，以便下游格式化输出。

        Args:
            version (PromptVersion): ORM 提示版本对象。
            roles (List[PromptRole]): 角色消息配置列表。
            principles (List[Any]): 原则提示集合。
            llm_config (LLMConfig): LLM 参数配置。

        Returns:
            None

        Raises:
            None
        """
        self.version = version
        self.roles = roles
        self.principles = principles
        self.llm_config = llm_config
