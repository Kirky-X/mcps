"""Database models for MCP-DevAgent.

This module defines the SQLAlchemy models for the MCP-DevAgent database,
including core entities, search indexes, and vector storage.
"""

from datetime import datetime
from typing import Optional, Dict, Any, List
from sqlalchemy import (
    Column, Integer, String, Text, DateTime, Float, Boolean,
    JSON, ForeignKey, Index, UniqueConstraint
)
from sqlalchemy.orm import declarative_base, relationship
from pydantic import BaseModel, Field, ConfigDict

Base = declarative_base()


class DevelopmentRun(Base):
    """Development run tracking."""
    __tablename__ = "development_runs"
    
    run_id = Column(Integer, primary_key=True, autoincrement=True)
    start_time = Column(DateTime, default=datetime.utcnow)
    end_time = Column(DateTime)
    initial_prd = Column(Text, nullable=False)
    tech_stack = Column(Text, nullable=False)
    final_status = Column(String(20), default='IN_PROGRESS')
    codebase_index_id = Column(String(100), ForeignKey("codebase_indexes.index_id"))
    
    # Relationships
    modules = relationship("Module", back_populates="development_run", cascade="all, delete-orphan")
    cot_records = relationship("CotRecord", back_populates="development_run", cascade="all, delete-orphan")
    codebase_index = relationship("CodebaseIndex", back_populates="development_runs")
    problem_escalations = relationship("ProblemEscalation", back_populates="development_run", cascade="all, delete-orphan")
    code_artifacts = relationship("CodeArtifact", back_populates="development_run", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index("idx_development_runs_status", "final_status"),
        Index("idx_development_runs_start_time", "start_time"),
        Index("idx_development_runs_codebase_index", "codebase_index_id"),
    )


class CodeRepository(Base):
    """Code repository information."""
    __tablename__ = "code_repositories"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    path = Column(String(500), nullable=False, unique=True)
    description = Column(Text)
    language = Column(String(50))
    framework = Column(String(100))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_indexed_at = Column(DateTime)
    is_active = Column(Boolean, default=True)
    repo_metadata = Column(JSON)
    
    # Relationships
    files = relationship("CodeFile", back_populates="repository", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index("idx_repo_name", "name"),
        Index("idx_repo_language", "language"),
        Index("idx_repo_active", "is_active"),
    )


class Module(Base):
    """Module information for development runs."""
    __tablename__ = "modules"
    
    module_id = Column(Integer, primary_key=True, autoincrement=True)
    run_id = Column(Integer, ForeignKey("development_runs.run_id"), nullable=False)
    module_name = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    description = Column(Text)
    development_order = Column(Integer, nullable=False)
    status = Column(String(50), default='PENDING')
    failure_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    development_run = relationship("DevelopmentRun", back_populates="modules")
    cot_records = relationship("CotRecord", back_populates="module", cascade="all, delete-orphan")
    test_results = relationship("TestResult", back_populates="module", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index("idx_modules_run_id", "run_id"),
        Index("idx_modules_status", "status"),
        Index("idx_modules_development_order", "development_order"),
        Index("idx_modules_failure_count", "failure_count"),
    )


class CodeFile(Base):
    """Individual code file information."""
    __tablename__ = "code_files"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    repository_id = Column(Integer, ForeignKey("code_repositories.id"), nullable=False)
    file_path = Column(String(1000), nullable=False)
    file_name = Column(String(255), nullable=False)
    file_extension = Column(String(20))
    file_size = Column(Integer)
    content_hash = Column(String(64))  # SHA-256 hash
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_modified = Column(DateTime)
    is_active = Column(Boolean, default=True)
    file_metadata = Column(JSON)
    
    # Relationships
    repository = relationship("CodeRepository", back_populates="files")
    chunks = relationship("CodeChunk", back_populates="file", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index("idx_file_repo_path", "repository_id", "file_path"),
        Index("idx_file_extension", "file_extension"),
        Index("idx_file_hash", "content_hash"),
        Index("idx_file_active", "is_active"),
        UniqueConstraint("repository_id", "file_path", name="uq_repo_file_path"),
    )


class CotRecord(Base):
    """Chain of Thought records for development process."""
    __tablename__ = "cot_records"
    
    cot_id = Column(Integer, primary_key=True, autoincrement=True)
    run_id = Column(Integer, ForeignKey("development_runs.run_id"), nullable=False)
    module_id = Column(Integer, ForeignKey("modules.module_id"))
    node_name = Column(String(100), nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)
    thought_process = Column(Text, nullable=False)
    input_context = Column(Text)
    output_result = Column(Text)
    parent_step_id = Column(Integer, ForeignKey("cot_records.cot_id"))
    step_type = Column(String(20), default='LINEAR')
    revises_step_id = Column(Integer, ForeignKey("cot_records.cot_id"))
    selected_model = Column(String(100))
    
    # Relationships
    development_run = relationship("DevelopmentRun", back_populates="cot_records")
    module = relationship("Module", back_populates="cot_records")
    parent_step = relationship("CotRecord", remote_side=[cot_id], foreign_keys=[parent_step_id])
    revises_step = relationship("CotRecord", remote_side=[cot_id], foreign_keys=[revises_step_id])
    
    __table_args__ = (
        Index("idx_cot_records_run_id", "run_id"),
        Index("idx_cot_records_module_id", "module_id"),
        Index("idx_cot_records_timestamp", "timestamp"),
        Index("idx_cot_records_node_name", "node_name"),
        Index("idx_cot_records_parent_step", "parent_step_id"),
        Index("idx_cot_records_step_type", "step_type"),
        Index("idx_cot_records_selected_model", "selected_model"),
    )


class CodeChunk(Base):
    """Code chunks for processing and embedding."""
    __tablename__ = "code_chunks"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    file_id = Column(Integer, ForeignKey("code_files.id"), nullable=False)
    chunk_index = Column(Integer, nullable=False)
    content = Column(Text, nullable=False)
    content_type = Column(String(50))  # function, class, comment, etc.
    start_line = Column(Integer)
    end_line = Column(Integer)
    token_count = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    chunk_metadata = Column(JSON)
    
    # Relationships
    file = relationship("CodeFile", back_populates="chunks")
    embeddings = relationship("CodeEmbedding", back_populates="chunk", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index("idx_chunk_file_index", "file_id", "chunk_index"),
        Index("idx_chunk_type", "content_type"),
        Index("idx_chunk_lines", "start_line", "end_line"),
        UniqueConstraint("file_id", "chunk_index", name="uq_file_chunk_index"),
    )


class TestResult(Base):
    """Test execution results for modules."""
    __tablename__ = "test_results"
    
    result_id = Column(Integer, primary_key=True, autoincrement=True)
    module_id = Column(Integer, ForeignKey("modules.module_id"), nullable=False)
    status = Column(String(20), nullable=False)  # SUCCESS, TESTS_FAILED, RUNTIME_ERROR
    total_tests = Column(Integer, default=0)
    passed_count = Column(Integer, default=0)
    failed_count = Column(Integer, default=0)
    error_details = Column(Text)
    execution_time = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    module = relationship("Module", back_populates="test_results")
    
    __table_args__ = (
        Index("idx_test_results_module_id", "module_id"),
        Index("idx_test_results_status", "status"),
        Index("idx_test_results_execution_time", "execution_time"),
    )


class CodeEmbedding(Base):
    """Vector embeddings for code chunks."""
    __tablename__ = "code_embeddings"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    chunk_id = Column(Integer, ForeignKey("code_chunks.id"), nullable=False)
    model_name = Column(String(100), nullable=False)
    embedding_vector = Column(Text, nullable=False)  # JSON serialized vector
    vector_dimension = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    embedding_metadata = Column(JSON)
    
    # Relationships
    chunk = relationship("CodeChunk", back_populates="embeddings")
    
    __table_args__ = (
        Index("idx_embedding_chunk_model", "chunk_id", "model_name"),
        Index("idx_embedding_model", "model_name"),
        UniqueConstraint("chunk_id", "model_name", name="uq_chunk_model_embedding"),
    )


class CodebaseIndex(Base):
    """Codebase indexing information for RAG."""
    __tablename__ = "codebase_indexes"
    
    index_id = Column(String(100), primary_key=True)  # String ID as per architecture doc
    project_path = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    indexed_files_count = Column(Integer, default=0)
    file_patterns = Column(Text, default='*.js,*.ts,*.py,*.java,*.cpp,*.h')
    exclude_patterns = Column(Text, default='node_modules,dist,build,.git')
    
    # Relationships
    development_runs = relationship("DevelopmentRun", back_populates="codebase_index")
    
    __table_args__ = (
        Index("idx_codebase_indexes_project_path", "project_path"),
        Index("idx_codebase_indexes_created_at", "created_at"),
    )


class ProblemEscalation(Base):
    """Problem escalation records."""
    __tablename__ = "problem_escalations"
    
    escalation_id = Column(Integer, primary_key=True, autoincrement=True)
    run_id = Column(Integer, ForeignKey("development_runs.run_id"), nullable=False)
    problem_type = Column(String(50), nullable=False)  # COMPILATION_ERROR, TEST_FAILURE, RUNTIME_ERROR, LOGIC_ERROR
    problem_description = Column(Text, nullable=False)
    context_data = Column(JSON)
    escalation_level = Column(String(20), nullable=False)  # LOW, MEDIUM, HIGH, CRITICAL
    status = Column(String(20), nullable=False)  # OPEN, IN_PROGRESS, RESOLVED, CLOSED
    error_code = Column(String(50))  # Error classification code
    affected_modules = Column(Text)  # Comma-separated list of affected module paths
    suggested_actions = Column(Text)  # AI-generated suggestions for resolution
    human_intervention_required = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    resolved_at = Column(DateTime)
    resolution_notes = Column(Text)
    
    # Relationships
    development_run = relationship("DevelopmentRun", back_populates="problem_escalations")
    
    __table_args__ = (
        Index("idx_problem_escalations_run_id", "run_id"),
        Index("idx_problem_escalations_problem_type", "problem_type"),
        Index("idx_problem_escalations_escalation_level", "escalation_level"),
        Index("idx_problem_escalations_status", "status"),
        Index("idx_problem_escalations_error_code", "error_code"),
        Index("idx_problem_escalations_created_at", "created_at"),
    )


class AgentSession(Base):
    """Agent session tracking."""
    __tablename__ = "agent_sessions"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(100), nullable=False, unique=True)
    agent_type = Column(String(50), nullable=False)  # development, search, export, etc.
    user_id = Column(String(100))  # Optional user identification
    created_at = Column(DateTime, default=datetime.utcnow)
    last_activity = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)
    agent_metadata = Column(JSON)
    
    __table_args__ = (
        Index("idx_agent_sessions_user", "user_id"),
        Index("idx_agent_sessions_active", "is_active"),
        Index("idx_agent_sessions_activity", "last_activity"),
        Index("idx_agent_sessions_type", "agent_type"),
    )


class AgentInteraction(Base):
    """Agent interaction tracking for CoT records."""
    __tablename__ = "agent_interactions"
    
    id = Column(String(100), primary_key=True)  # UUID
    session_id = Column(String(100), ForeignKey("agent_sessions.session_id"), nullable=False)
    interaction_type = Column(String(50), nullable=False)  # cot_record, analysis, etc.
    content = Column(Text, nullable=False)
    interaction_metadata = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        Index("idx_agent_interactions_session", "session_id"),
        Index("idx_agent_interactions_type", "interaction_type"),
        Index("idx_agent_interactions_created", "created_at"),
    )


class SearchSession(Base):
    """Search session tracking."""
    __tablename__ = "search_sessions"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(100), nullable=False, unique=True)
    user_id = Column(String(100))  # Optional user identification
    created_at = Column(DateTime, default=datetime.utcnow)
    last_activity = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)
    session_metadata = Column(JSON)
    
    # Relationships
    queries = relationship("SearchQuery", back_populates="session", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index("idx_session_user", "user_id"),
        Index("idx_session_active", "is_active"),
        Index("idx_session_activity", "last_activity"),
    )


class SearchQuery(Base):
    """Search query tracking."""
    __tablename__ = "search_queries"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(Integer, ForeignKey("search_sessions.id"), nullable=False)
    query_text = Column(Text, nullable=False)
    query_type = Column(String(50), default="hybrid")  # hybrid, fulltext, semantic
    content_types = Column(JSON)  # Filter by content types
    created_at = Column(DateTime, default=datetime.utcnow)
    execution_time_ms = Column(Integer)  # Query execution time
    result_count = Column(Integer, default=0)
    query_metadata = Column(JSON)
    
    # Relationships
    session = relationship("SearchSession", back_populates="queries")
    
    __table_args__ = (
        Index("idx_query_session", "session_id"),
        Index("idx_query_type", "query_type"),
        Index("idx_query_created", "created_at"),
    )


class CodeArtifact(Base):
    """Generated code artifacts during development."""
    __tablename__ = "code_artifacts"
    
    artifact_id = Column(Integer, primary_key=True, autoincrement=True)
    run_id = Column(Integer, ForeignKey("development_runs.run_id"), nullable=False)
    module_id = Column(Integer, ForeignKey("modules.module_id"))
    artifact_type = Column(String(50), nullable=False)
    file_path = Column(String(500), nullable=False)
    content = Column(Text, nullable=False)
    version = Column(Integer, default=1)
    status = Column(String(20), default='DRAFT')
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    development_run = relationship("DevelopmentRun", back_populates="code_artifacts")
    module = relationship("Module", foreign_keys=[module_id])
    
    __table_args__ = (
        Index("idx_code_artifacts_run_id", "run_id"),
        Index("idx_code_artifacts_module_id", "module_id"),
        Index("idx_code_artifacts_artifact_type", "artifact_type"),
        Index("idx_code_artifacts_file_path", "file_path"),
        Index("idx_code_artifacts_status", "status"),
        Index("idx_code_artifacts_version", "version"),
    )


# Old models removed - replaced with new architecture models above


# Pydantic models for API serialization
class DevelopmentRunCreate(BaseModel):
    """Create development run request."""
    prd_content: str
    tech_stack: str
    target_framework: Optional[str] = None
    
class DevelopmentRunResponse(BaseModel):
    """Development run response."""
    run_id: int
    prd_content: str
    tech_stack: str
    target_framework: Optional[str]
    status: str
    start_time: datetime
    end_time: Optional[datetime]
    
    model_config = ConfigDict(from_attributes=True)

class ModuleCreate(BaseModel):
    """Create module request."""
    run_id: int
    module_name: str
    file_path: str
    description: Optional[str] = None
    development_order: int
    
class ModuleResponse(BaseModel):
    """Module response."""
    module_id: int
    run_id: int
    module_name: str
    file_path: str
    description: Optional[str]
    development_order: int
    status: str
    failure_count: int
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

class CotRecordCreate(BaseModel):
    """Create CoT record request."""
    run_id: int
    module_id: Optional[int] = None
    node_name: str
    thought_process: str
    input_context: Optional[str] = None
    output_result: Optional[str] = None
    parent_step_id: Optional[int] = None
    step_type: str = 'LINEAR'
    selected_model: Optional[str] = None
    
class CotRecordResponse(BaseModel):
    """CoT record response."""
    cot_id: int
    run_id: int
    module_id: Optional[int]
    node_name: str
    timestamp: datetime
    thought_process: str
    input_context: Optional[str]
    output_result: Optional[str]
    step_type: str
    selected_model: Optional[str]
    
    model_config = ConfigDict(from_attributes=True)