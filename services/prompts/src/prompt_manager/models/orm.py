# Copyright (c) Kirky.X. 2025. All rights reserved.
import uuid
import datetime

from typing import Optional, List

from sqlmodel import SQLModel, Field, Relationship
from sqlalchemy import Index, UniqueConstraint, JSON, LargeBinary, Column, DateTime
from ..infrastructure.time_network import get_precise_time


def generate_uuid():
    return str(uuid.uuid4())


class Prompt(SQLModel, table=True):
    __tablename__ = "prompts"
    __table_args__ = {"extend_existing": True}

    id: str = Field(default_factory=generate_uuid, primary_key=True)
    name: str = Field(max_length=200, index=False, sa_column_kwargs={"unique": True})
    content: Optional[str] = None
    created_at: datetime.datetime = Field(
        default_factory=get_precise_time,
        sa_column=Column(DateTime(timezone=True), default=get_precise_time)
    )
    updated_at: datetime.datetime = Field(
        default_factory=get_precise_time,
        sa_column=Column(
            DateTime(timezone=True),
            default=get_precise_time,
            onupdate=get_precise_time
        )
    )
    is_deleted: bool = Field(default=False)
    sync_hash: Optional[str] = None

    versions: List["PromptVersion"] = Relationship(back_populates="prompt", sa_relationship_kwargs={"cascade": "all, delete-orphan"})


class PromptTag(SQLModel, table=True):
    __tablename__ = "prompt_tags"
    __table_args__ = {"extend_existing": True}

    version_id: str = Field(primary_key=True, foreign_key="prompt_versions.id")
    tag_id: str = Field(primary_key=True, foreign_key="tags.id")


class PromptVersion(SQLModel, table=True):
    __tablename__ = "prompt_versions"

    id: str = Field(default_factory=generate_uuid, primary_key=True)
    prompt_id: str = Field(foreign_key="prompts.id")
    version: str = Field(max_length=10)
    version_number: int = Field(default=1)
    description: str
    description_vector: bytes | None = Field(default=None, sa_column=Column(LargeBinary, nullable=True))
    is_active: bool = Field(default=True)
    is_latest: bool = Field(default=False)
    change_log: str | None = None
    created_at: datetime.datetime = Field(
        default_factory=get_precise_time,
        sa_column=Column(DateTime(timezone=True), default=get_precise_time)
    )

    prompt: Optional["Prompt"] = Relationship(back_populates="versions")
    roles: List["PromptRole"] = Relationship(back_populates="version", sa_relationship_kwargs={"order_by": "PromptRole.order", "cascade": "all, delete-orphan"})
    llm_config: Optional["LLMConfig"] = Relationship(back_populates="version", sa_relationship_kwargs={"uselist": False, "cascade": "all, delete-orphan"})
    tags: List["Tag"] = Relationship(back_populates="versions", link_model=PromptTag)
    principle_refs: List["PrincipleRef"] = Relationship(back_populates="version", sa_relationship_kwargs={"order_by": "PrincipleRef.order", "cascade": "all, delete-orphan"})
    client_mappings: List["ClientMapping"] = Relationship(back_populates="version", sa_relationship_kwargs={"cascade": "all, delete-orphan"})

    __table_args__ = (
        UniqueConstraint("prompt_id", "version", name="uq_prompt_version"),
        {"extend_existing": True}
    )


class PromptRole(SQLModel, table=True):
    __tablename__ = "prompt_roles"

    id: str = Field(default_factory=generate_uuid, primary_key=True)
    version_id: str = Field(foreign_key="prompt_versions.id")
    role_type: str = Field(max_length=20)
    content: str
    order: int
    template_variables: dict | None = Field(default=None, sa_column=Column(JSON, nullable=True))

    version: Optional["PromptVersion"] = Relationship(back_populates="roles")

    __table_args__ = (
        {"extend_existing": True}
    )


class LLMConfig(SQLModel, table=True):
    __tablename__ = "llm_configs"
    __table_args__ = {"extend_existing": True}

    id: str = Field(default_factory=generate_uuid, primary_key=True)
    version_id: str = Field(foreign_key="prompt_versions.id", unique=True)
    model: str = Field(default="gpt-3.5-turbo", max_length=100)
    temperature: float = 0.7
    max_tokens: int = 1000
    top_p: float = 1.0
    top_k: int | None = None
    frequency_penalty: float = 0.0
    presence_penalty: float = 0.0
    stop_sequences: list | None = Field(default=None, sa_column=Column(JSON, nullable=True))
    other_params: dict | None = Field(default=None, sa_column=Column(JSON, nullable=True))

    version: Optional["PromptVersion"] = Relationship(back_populates="llm_config")


class Tag(SQLModel, table=True):
    __tablename__ = "tags"
    __table_args__ = {"extend_existing": True}

    id: str = Field(default_factory=generate_uuid, primary_key=True)
    name: str = Field(max_length=50, index=False, sa_column_kwargs={"unique": True})
    created_at: datetime.datetime = Field(
        default_factory=get_precise_time,
        sa_column=Column(DateTime(timezone=True), default=get_precise_time)
    )

    versions: List["PromptVersion"] = Relationship(back_populates="tags", link_model=PromptTag)


 


class PrinciplePrompt(SQLModel, table=True):
    __tablename__ = "principle_prompts"
    
    id: str = Field(default_factory=generate_uuid, primary_key=True)
    name: str = Field(max_length=200, index=False)
    version: str = Field(max_length=10)
    content: str
    is_active: bool = Field(default=True)
    is_latest: bool = Field(default=False)
    created_at: datetime.datetime = Field(
        default_factory=get_precise_time,
        sa_column=Column(DateTime(timezone=True), default=get_precise_time)
    )

    __table_args__ = (
        UniqueConstraint("name", "version", name="uq_principle_version"),
        {"extend_existing": True}
    )


class PrincipleRef(SQLModel, table=True):
    __tablename__ = "version_principle_refs"

    version_id: str = Field(primary_key=True, foreign_key="prompt_versions.id")
    principle_id: str = Field(primary_key=True, foreign_key="principle_prompts.id")
    ref_version: str = Field(max_length=10)
    order: int

    version: Optional["PromptVersion"] = Relationship(back_populates="principle_refs")
    principle: Optional["PrinciplePrompt"] = Relationship()

    __table_args__ = (
        {"extend_existing": True}
    )


class LLMClient(SQLModel, table=True):
    __tablename__ = "llm_clients"
    __table_args__ = {"extend_existing": True}

    id: str = Field(default_factory=generate_uuid, primary_key=True)
    name: str = Field(max_length=50, index=False, sa_column_kwargs={"unique": True})
    default_principles: list | None = Field(default=None, sa_column=Column(JSON, nullable=True))

    mappings: List["ClientMapping"] = Relationship(back_populates="client", sa_relationship_kwargs={"cascade": "all, delete-orphan"})


class ClientMapping(SQLModel, table=True):
    __tablename__ = "version_client_mapping"
    __table_args__ = {"extend_existing": True}

    version_id: str = Field(primary_key=True, foreign_key="prompt_versions.id")
    client_id: str = Field(primary_key=True, foreign_key="llm_clients.id")

    version: Optional["PromptVersion"] = Relationship(back_populates="client_mappings")
    client: Optional["LLMClient"] = Relationship(back_populates="mappings")


class AppConfig(SQLModel, table=True):
    __tablename__ = "app_config"
    __table_args__ = {"extend_existing": True}

    key: str = Field(primary_key=True, max_length=100)
    value: Optional[str] = None
