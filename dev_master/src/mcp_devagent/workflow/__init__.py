"""LangGraph工作流模块

实现MCP-DevAgent的核心四阶段AI代理工作流：
1. 规划阶段（Planning）：分析PRD并生成项目蓝图
2. 测试阶段（Testing）：为每个模块生成测试用例
3. 开发阶段（Development）：生成通过测试的功能代码
4. 验证阶段（Validation）：执行测试并提供反馈

基于LangGraph 0.6.6构建，支持复杂的状态管理、条件路由和认知路由。
"""

from .workflow_engine import DevAgentWorkflow
from .state_manager import (
    WorkflowState,
    ModuleState,
    WorkflowPhase,
    ModuleStatus,
    create_initial_state,
    update_state_phase
)
from .nodes import (
    PlanningAgent,
    TestingAgent,
    DevelopmentAgent,
    ValidationAgent,
    CognitiveRouter
)
from .routing import WorkflowRouter
from .config import (
    WorkflowConfig,
    ModelConfig,
    ModelProvider,
    ModelTier,
    DefaultModelConfigs,
    CognitiveRoutingConfig,
    WorkflowPhaseConfig,
    get_default_workflow_config,
    get_model_config,
    get_optimal_model_for_task
)
from .integrations import (
    ServiceManager,
    LLMAdapter,
    SearchAdapter,
    DatabaseAdapter,
    WorkflowIntegrationManager
)

__all__ = [
    "DevAgentWorkflow",
    "WorkflowState",
    "ModuleState",
    "WorkflowPhase",
    "ModuleStatus",
    "create_initial_state",
    "update_state_phase",
    "PlanningAgent",
    "TestingAgent",
    "DevelopmentAgent",
    "ValidationAgent",
    "CognitiveRouter",
    "WorkflowRouter",
    "WorkflowConfig",
    "ModelConfig",
    "ModelProvider",
    "ModelTier",
    "DefaultModelConfigs",
    "CognitiveRoutingConfig",
    "WorkflowPhaseConfig",
    "get_default_workflow_config",
    "get_model_config",
    "get_optimal_model_for_task",
    "ServiceManager",
    "LLMAdapter",
    "SearchAdapter",
    "DatabaseAdapter",
    "WorkflowIntegrationManager"
]