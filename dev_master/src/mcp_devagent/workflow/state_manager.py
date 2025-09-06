"""LangGraph工作流状态管理

定义工作流状态结构，支持四阶段代理间的数据传递和状态跟踪。
基于TypedDict实现类型安全的状态管理。
"""

from typing import Dict, List, Optional, Any, TypedDict, Literal
from datetime import datetime
from dataclasses import dataclass
from enum import Enum


class ModuleStatus(str, Enum):
    """模块开发状态枚举"""
    PENDING = "PENDING"
    PLANNING = "PLANNING"
    TESTING = "TESTING"
    DEVELOPING = "DEVELOPING"
    VALIDATING = "VALIDATING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    ESCALATED = "ESCALATED"


class WorkflowPhase(str, Enum):
    """工作流阶段枚举"""
    INITIALIZATION = "INITIALIZATION"
    PLANNING = "PLANNING"
    TESTING = "TESTING"
    DEVELOPMENT = "DEVELOPMENT"
    VALIDATION = "VALIDATION"
    COMPLETION = "COMPLETION"
    ERROR_HANDLING = "ERROR_HANDLING"


@dataclass
class ModuleTask:
    """单个模块任务定义"""
    module_id: int
    name: str
    file_path: str
    description: str
    dependencies: List[str]
    development_order: int
    status: ModuleStatus = ModuleStatus.PENDING
    failure_count: int = 0
    created_at: datetime = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        """将ModuleTask对象转换为字典格式"""
        return {
            "module_id": self.module_id,
            "name": self.name,
            "file_path": self.file_path,
            "description": self.description,
            "dependencies": self.dependencies,
            "development_order": self.development_order,
            "status": self.status.value if isinstance(self.status, ModuleStatus) else self.status,
            "failure_count": self.failure_count,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }


@dataclass
class TestResult:
    """测试结果数据结构"""
    module_id: int
    status: Literal["SUCCESS", "TESTS_FAILED", "RUNTIME_ERROR"]
    total_tests: int = 0
    passed_count: int = 0
    failed_count: int = 0
    error_details: Optional[str] = None
    execution_time: datetime = None
    
    def __post_init__(self):
        if self.execution_time is None:
            self.execution_time = datetime.now()


@dataclass
class CodeArtifact:
    """代码构件数据结构"""
    file_path: str
    content: str
    file_type: str
    symbols: List[str]
    dependencies: List[str]
    test_file_path: Optional[str] = None
    test_content: Optional[str] = None


class WorkflowState(TypedDict):
    """LangGraph工作流状态定义
    
    这是工作流在各个节点间传递的核心状态对象。
    使用TypedDict确保类型安全和IDE支持。
    """
    # 基础信息
    run_id: int
    current_phase: WorkflowPhase
    start_time: datetime
    
    # PRD和技术栈
    initial_prd: str
    tech_stack: Dict[str, Any]
    code_standards: Dict[str, Any]
    
    # 项目蓝图
    project_blueprint: Optional[Dict[str, Any]]
    modules: List[ModuleTask]
    current_module_index: int
    
    # 当前模块状态
    current_module: Optional[ModuleTask]
    current_test_code: Optional[str]
    current_implementation: Optional[str]
    current_test_result: Optional[TestResult]
    
    # 代码构件
    generated_artifacts: List[CodeArtifact]
    
    # 错误处理
    error_context: Optional[Dict[str, Any]]
    failure_attempts: List[Dict[str, Any]]
    escalation_required: bool
    
    # 认知路由
    selected_model: Optional[str]
    routing_reason: Optional[str]
    estimated_cost: float
    
    # 思维链记录
    cot_records: List[Dict[str, Any]]
    
    # 工作流控制
    should_continue: bool
    next_action: Optional[str]
    completion_status: Optional[str]


class ModuleState(TypedDict):
    """单个模块的详细状态
    
    用于跟踪单个模块在四阶段流程中的详细状态。
    """
    module_task: ModuleTask
    planning_result: Optional[Dict[str, Any]]
    test_generation_result: Optional[Dict[str, Any]]
    development_result: Optional[Dict[str, Any]]
    validation_result: Optional[TestResult]
    
    # 阶段时间戳
    planning_start: Optional[datetime]
    planning_end: Optional[datetime]
    testing_start: Optional[datetime]
    testing_end: Optional[datetime]
    development_start: Optional[datetime]
    development_end: Optional[datetime]
    validation_start: Optional[datetime]
    validation_end: Optional[datetime]
    
    # 错误和重试
    errors: List[Dict[str, Any]]
    retry_count: int
    max_retries: int


def create_initial_state(
    run_id: int,
    initial_prd: str,
    tech_stack: Dict[str, Any],
    code_standards: Optional[Dict[str, Any]] = None
) -> WorkflowState:
    """创建初始工作流状态
    
    Args:
        run_id: 开发运行ID
        initial_prd: 产品需求文档内容
        tech_stack: 技术栈配置
        code_standards: 代码规范要求
        
    Returns:
        初始化的工作流状态
    """
    return WorkflowState(
        run_id=run_id,
        current_phase=WorkflowPhase.INITIALIZATION,
        start_time=datetime.now(),
        initial_prd=initial_prd,
        tech_stack=tech_stack,
        code_standards=code_standards or {},
        project_blueprint=None,
        modules=[],
        current_module_index=0,
        current_module=None,
        current_test_code=None,
        current_implementation=None,
        current_test_result=None,
        generated_artifacts=[],
        error_context=None,
        failure_attempts=[],
        escalation_required=False,
        selected_model=None,
        routing_reason=None,
        estimated_cost=0.0,
        cot_records=[],
        should_continue=True,
        next_action=None,
        completion_status=None
    )


def create_module_state(module_task: ModuleTask) -> ModuleState:
    """创建模块状态
    
    Args:
        module_task: 模块任务定义
        
    Returns:
        初始化的模块状态
    """
    return ModuleState(
        module_task=module_task,
        planning_result=None,
        test_generation_result=None,
        development_result=None,
        validation_result=None,
        planning_start=None,
        planning_end=None,
        testing_start=None,
        testing_end=None,
        development_start=None,
        development_end=None,
        validation_start=None,
        validation_end=None,
        errors=[],
        retry_count=0,
        max_retries=3
    )


def update_state_phase(state: WorkflowState, new_phase: WorkflowPhase) -> WorkflowState:
    """更新工作流阶段
    
    Args:
        state: 当前工作流状态
        new_phase: 新的工作流阶段
        
    Returns:
        更新后的工作流状态
    """
    state["current_phase"] = new_phase
    return state


def add_cot_record(
    state: WorkflowState,
    node_name: str,
    thought_process: str,
    input_context: str,
    output_result: str,
    selected_model: str,
    step_type: str = "LINEAR"
) -> WorkflowState:
    """添加思维链记录
    
    Args:
        state: 当前工作流状态
        node_name: 节点名称
        thought_process: 思维过程
        input_context: 输入上下文
        output_result: 输出结果
        selected_model: 选择的模型
        step_type: 步骤类型
        
    Returns:
        更新后的工作流状态
    """
    cot_record = {
        "node_name": node_name,
        "timestamp": datetime.now().isoformat(),
        "thought_process": thought_process,
        "input_context": input_context,
        "output_result": output_result,
        "selected_model": selected_model,
        "step_type": step_type,
        "module_id": getattr(state["current_module"], "module_id", None) if state["current_module"] else None
    }
    
    state["cot_records"].append(cot_record)
    return state


def should_escalate_problem(state: WorkflowState) -> bool:
    """判断是否需要升级问题
    
    基于三振出局机制，连续3次失败后触发升级。
    
    Args:
        state: 当前工作流状态
        
    Returns:
        是否需要升级问题
    """
    if not state["current_module"]:
        return False
        
    return getattr(state["current_module"], "failure_count", 0) >= 3
