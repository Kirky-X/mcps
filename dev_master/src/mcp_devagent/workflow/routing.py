"""LangGraph工作流路由模块

实现四阶段工作流的条件路由和决策逻辑：
- 阶段间的智能流转控制
- 错误处理和重试机制
- 三振出局升级机制
- 认知路由决策
"""

from typing import Dict, Any, Optional, Literal
from .state_manager import (
    WorkflowState, 
    WorkflowPhase, 
    ModuleStatus,
    should_escalate_problem
)


class WorkflowRouter:
    """工作流路由器
    
    负责决定工作流的下一步执行路径，包括：
    - 正常阶段流转
    - 错误处理和重试
    - 问题升级决策
    - 工作流完成判断
    """
    
    def __init__(self):
        self.max_retries = 3
        self.escalation_threshold = 3
    
    def route_next_step(self, state: WorkflowState) -> str:
        """路由到下一个执行步骤
        
        Args:
            state: 当前工作流状态
            
        Returns:
            下一个节点名称
        """
        # 检查是否需要升级问题
        if should_escalate_problem(state):
            return "escalate_problem"
        
        # 检查是否有错误需要处理
        if state["error_context"]:
            return self._route_error_handling(state)
        
        # 根据当前阶段路由
        current_phase = state["current_phase"]
        
        if current_phase == WorkflowPhase.INITIALIZATION:
            return "cognitive_router"
        elif current_phase == WorkflowPhase.PLANNING:
            return self._route_from_planning(state)
        elif current_phase == WorkflowPhase.TESTING:
            return self._route_from_testing(state)
        elif current_phase == WorkflowPhase.DEVELOPMENT:
            return self._route_from_development(state)
        elif current_phase == WorkflowPhase.VALIDATION:
            return self._route_from_validation(state)
        elif current_phase == WorkflowPhase.COMPLETION:
            return "__end__"
        else:
            return "error_handler"
    
    def _route_from_planning(self, state: WorkflowState) -> str:
        """从规划阶段路由"""
        if not state["project_blueprint"]:
            # 规划失败，重试或升级
            return self._handle_failure(state, "planning_agent")
        
        if not state["modules"]:
            # 没有生成模块列表，重试规划
            return "planning_agent"
        
        # 规划成功，进入测试阶段
        return "cognitive_router"
    
    def _route_from_testing(self, state: WorkflowState) -> str:
        """从测试阶段路由"""
        if not state["current_test_code"]:
            # 测试生成失败
            return self._handle_failure(state, "testing_agent")
        
        # 测试生成成功，进入开发阶段
        return "cognitive_router"
    
    def _route_from_development(self, state: WorkflowState) -> str:
        """从开发阶段路由"""
        if not state["current_implementation"]:
            # 开发失败
            return self._handle_failure(state, "development_agent")
        
        # 开发成功，进入验证阶段
        return "cognitive_router"
    
    def _route_from_validation(self, state: WorkflowState) -> str:
        """从验证阶段路由"""
        test_result = state["current_test_result"]
        
        if not test_result:
            # 验证失败
            return self._handle_failure(state, "validation_agent")
        
        if test_result.status == "SUCCESS":
            # 当前模块完成，检查是否还有其他模块
            return self._check_next_module(state)
        elif test_result.status in ["TESTS_FAILED", "RUNTIME_ERROR"]:
            # 测试失败，需要重新开发
            return self._handle_test_failure(state)
        
        return "error_handler"
    
    def _route_error_handling(self, state: WorkflowState) -> str:
        """错误处理路由"""
        error_context = state["error_context"]
        
        if not error_context:
            return "cognitive_router"
        
        error_type = error_context.get("type", "unknown")
        retry_count = error_context.get("retry_count", 0)
        
        if retry_count >= self.max_retries:
            # 超过最大重试次数，升级问题
            return "escalate_problem"
        
        # 根据错误类型决定重试策略
        if error_type == "planning_error":
            return "planning_agent"
        elif error_type == "testing_error":
            return "testing_agent"
        elif error_type == "development_error":
            return "development_agent"
        elif error_type == "validation_error":
            return "validation_agent"
        else:
            return "error_handler"
    
    def _handle_failure(self, state: WorkflowState, failed_node: str) -> str:
        """处理节点失败"""
        current_module = state["current_module"]
        
        if current_module:
            # 安全获取failure_count（现在是字典格式）
            failure_count = current_module.get('failure_count', 0) + 1
            
            # 安全设置failure_count
            current_module['failure_count'] = failure_count
            
            if failure_count >= self.escalation_threshold:
                return "escalate_problem"
        
        # 记录失败并重试
        failure_record = {
            "node": failed_node,
            "timestamp": state["start_time"].isoformat(),
            "module_id": current_module.get('module_id') if current_module else None,
            "error_details": state["error_context"]
        }
        state["failure_attempts"].append(failure_record)
        
        # 重新路由到认知路由器选择合适的模型
        return "cognitive_router"
    
    def _handle_test_failure(self, state: WorkflowState) -> str:
        """处理测试失败"""
        test_result = state["current_test_result"]
        current_module = state["current_module"]
        
        if not current_module:
            return "error_handler"
        
        # 安全增加失败计数（现在是字典格式）
        current_failure_count = current_module.get('failure_count', 0)
        new_failure_count = current_failure_count + 1
        
        current_module['failure_count'] = new_failure_count
        
        if new_failure_count >= self.escalation_threshold:
            return "escalate_problem"
        
        # 根据测试失败类型决定重试策略
        if test_result.status == "TESTS_FAILED":
            # 测试用例失败，重新开发
            return "cognitive_router"  # 重新选择模型进行开发
        elif test_result.status == "RUNTIME_ERROR":
            # 运行时错误，可能需要重新生成测试或重新开发
            error_details = getattr(test_result, 'error_details', '')
            if "import" in error_details.lower() or "module" in error_details.lower():
                # 导入错误，重新开发
                return "cognitive_router"
            else:
                # 其他运行时错误，重新生成测试
                return "testing_agent"
        
        return "cognitive_router"
    
    def _check_next_module(self, state: WorkflowState) -> str:
        """检查是否有下一个模块需要处理"""
        current_index = state["current_module_index"]
        total_modules = len(state["modules"])
        
        if current_index + 1 < total_modules:
            # 还有模块需要处理，继续下一个模块
            state["current_module_index"] = current_index + 1
            next_module = state["modules"][current_index + 1]
            # 确保current_module是ModuleTask对象，不需要转换为字典
            state["current_module"] = next_module
            state["current_phase"] = WorkflowPhase.TESTING
            
            # 清理当前模块的临时状态
            state["current_test_code"] = None
            state["current_implementation"] = None
            state["current_test_result"] = None
            state["error_context"] = None
            
            return "cognitive_router"
        else:
            # 所有模块完成，结束工作流
            state["current_phase"] = WorkflowPhase.COMPLETION
            state["completion_status"] = "SUCCESS"
            return "__end__"


def should_continue_workflow(state: WorkflowState) -> bool:
    """判断工作流是否应该继续
    
    Args:
        state: 当前工作流状态
        
    Returns:
        是否继续工作流
    """
    # 检查完成状态
    if state["current_phase"] == WorkflowPhase.COMPLETION:
        return False
    
    # 检查是否被标记为停止
    if not state["should_continue"]:
        return False
    
    # 检查是否需要升级（三振出局）
    if state["escalation_required"]:
        return False
    
    return True


def determine_next_agent(state: WorkflowState) -> str:
    """确定下一个执行的代理
    
    基于当前阶段和状态确定下一个应该执行的代理节点。
    
    Args:
        state: 当前工作流状态
        
    Returns:
        下一个代理节点名称
    """
    router = WorkflowRouter()
    return router.route_next_step(state)


def get_cognitive_routing_context(state: WorkflowState) -> Dict[str, Any]:
    """获取认知路由的上下文信息
    
    为认知路由器提供决策所需的上下文信息。
    
    Args:
        state: 当前工作流状态
        
    Returns:
        认知路由上下文
    """
    context = {
        "current_phase": state["current_phase"],
        "current_module": state["current_module"],
        "failure_count": 0,
        "previous_errors": [],
        "complexity_indicators": {},
        "performance_requirements": {}
    }
    
    # 添加失败信息
    if state["current_module"]:
        current_module = state["current_module"]
        context["failure_count"] = current_module.get('failure_count', 0)
    
    # 添加错误历史
    context["previous_errors"] = state["failure_attempts"][-3:]  # 最近3次错误
    
    # 分析复杂度指标
    if state["current_module"]:
        module = state["current_module"]
        # 安全获取模块属性（现在是字典格式）
        dependencies = module.get('dependencies', [])
        description = module.get('description', '')
        name = module.get('name', '')
        
        context["complexity_indicators"] = {
            "dependencies_count": len(dependencies),
            "description_length": len(description),
            "is_core_module": "core" in name.lower(),
            "has_external_deps": any("external" in dep for dep in dependencies)
        }
    
    # 性能要求
    context["performance_requirements"] = {
        "estimated_cost": state["estimated_cost"],
        "time_pressure": len(state["modules"]) > 10,  # 大型项目时间压力
        "accuracy_priority": state["current_phase"] in [WorkflowPhase.TESTING, WorkflowPhase.VALIDATION]
    }
    
    return context