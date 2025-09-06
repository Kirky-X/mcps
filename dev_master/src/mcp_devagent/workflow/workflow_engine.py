"""LangGraph工作流引擎

实现MCP-DevAgent的核心四阶段AI代理工作流引擎。
基于LangGraph 0.6.6构建，支持复杂的状态管理和条件路由。
"""

import asyncio
from typing import Dict, Any, Optional, List
from datetime import datetime

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from .state_manager import (
    WorkflowState, 
    WorkflowPhase, 
    ModuleStatus,
    create_initial_state,
    update_state_phase
)
from .nodes import (
    CognitiveRouter,
    PlanningAgent,
    TestingAgent,
    DevelopmentAgent,
    ValidationAgent
)
from .routing import (
    WorkflowRouter,
    should_continue_workflow,
    determine_next_agent
)
from ..services.llm_service import LLMService
from ..services.embedding_service import EmbeddingService
from ..database.models import DevelopmentRun, CotRecord
from ..database.connection import get_db_session, get_db_connection
from .integrations import WorkflowIntegrationManager, LLMAdapter, SearchAdapter, DatabaseAdapter


class DevAgentWorkflow:
    """MCP-DevAgent工作流引擎
    
    实现四阶段AI代理工作流：
    1. 规划阶段：分析PRD并生成项目蓝图
    2. 测试阶段：为每个模块生成测试用例
    3. 开发阶段：生成通过测试的功能代码
    4. 验证阶段：执行测试并提供反馈
    
    支持认知路由、错误处理、三振出局升级机制。
    """
    
    def __init__(self, llm_service: LLMService, embedding_service: EmbeddingService,
                 db_path: str = "./dev_agent.db",
                 service_config: Optional[Dict[str, Any]] = None,
                 llm_adapter=None, search_adapter=None, db_adapter=None):
        self.llm_service = llm_service
        self.embedding_service = embedding_service
        self.db_path = db_path
        self.service_config = service_config or {}
        
        # Integration manager
        self.integration_manager = WorkflowIntegrationManager(db_path, service_config)
        
        self.workflow_router = WorkflowRouter()
        
        # 初始化节点
        self.cognitive_router = CognitiveRouter(llm_service, embedding_service, llm_adapter, search_adapter, db_adapter)
        self.planning_agent = PlanningAgent(llm_service, embedding_service, llm_adapter, search_adapter, db_adapter)
        self.testing_agent = TestingAgent(llm_service, embedding_service, llm_adapter, search_adapter, db_adapter)
        self.development_agent = DevelopmentAgent(llm_service, embedding_service, llm_adapter, search_adapter, db_adapter)
        self.validation_agent = ValidationAgent(llm_service, embedding_service, llm_adapter, search_adapter, db_adapter)
        
        # 构建工作流图
        self.workflow = self._build_workflow_graph()
        
        # Initialization status
        self.initialized = False
    
    def _build_workflow_graph(self) -> StateGraph:
        """构建LangGraph工作流图"""
        # 创建状态图
        workflow = StateGraph(WorkflowState)
        
        # 添加节点
        workflow.add_node("cognitive_router", self._cognitive_router_node)
        workflow.add_node("planning_agent", self._planning_agent_node)
        workflow.add_node("testing_agent", self._testing_agent_node)
        workflow.add_node("development_agent", self._development_agent_node)
        workflow.add_node("validation_agent", self._validation_agent_node)
        workflow.add_node("escalate_problem", self._escalate_problem_node)
        workflow.add_node("error_handler", self._error_handler_node)
        
        # 设置入口点
        workflow.set_entry_point("cognitive_router")
        
        # 添加条件边
        workflow.add_conditional_edges(
            "cognitive_router",
            self._route_from_cognitive_router,
            {
                "cognitive_router": "cognitive_router",
                "planning_agent": "planning_agent",
                "testing_agent": "testing_agent",
                "development_agent": "development_agent",
                "validation_agent": "validation_agent",
                "escalate_problem": "escalate_problem",
                "error_handler": "error_handler",
                "__end__": END
            }
        )
        
        # 从各个代理节点的条件边
        for agent_name in ["planning_agent", "testing_agent", "development_agent", "validation_agent"]:
            workflow.add_conditional_edges(
                agent_name,
                self._route_next_step,
                {
                    "cognitive_router": "cognitive_router",
                    "planning_agent": "planning_agent",
                    "testing_agent": "testing_agent",
                    "development_agent": "development_agent",
                    "validation_agent": "validation_agent",
                    "escalate_problem": "escalate_problem",
                    "error_handler": "error_handler",
                    "__end__": END
                }
            )
        
        # 错误处理和升级节点的边
        workflow.add_conditional_edges(
            "error_handler",
            self._route_next_step,
            {
                "cognitive_router": "cognitive_router",
                "escalate_problem": "escalate_problem",
                "__end__": END
            }
        )
        
        workflow.add_edge("escalate_problem", END)
        
        return workflow
    
    async def initialize(self) -> bool:
        """Initialize the workflow engine and all dependencies."""
        try:
            # Initialize integration manager
            if not await self.integration_manager.initialize():
                return False
            
            self.initialized = True
            return True
            
        except Exception as e:
            return False
    
    async def shutdown(self):
        """Shutdown the workflow engine."""
        await self.integration_manager.shutdown()
        self.initialized = False
    
    async def _cognitive_router_node(self, state: WorkflowState) -> WorkflowState:
        """认知路由器节点"""
        return await self.cognitive_router.execute(state)
    
    async def _planning_agent_node(self, state: WorkflowState) -> WorkflowState:
        """规划代理节点"""
        return await self.planning_agent.execute(state)
    
    async def _testing_agent_node(self, state: WorkflowState) -> WorkflowState:
        """测试代理节点"""
        return await self.testing_agent.execute(state)
    
    async def _development_agent_node(self, state: WorkflowState) -> WorkflowState:
        """开发代理节点"""
        return await self.development_agent.execute(state)
    
    async def _validation_agent_node(self, state: WorkflowState) -> WorkflowState:
        """验证代理节点"""
        return await self.validation_agent.execute(state)
    
    async def _escalate_problem_node(self, state: WorkflowState) -> WorkflowState:
        """问题升级节点"""
        # 标记需要升级
        state["escalation_required"] = True
        state["should_continue"] = False
        state["completion_status"] = "ESCALATED"
        
        # 记录升级信息
        current_module = state["current_module"]
        escalation_record = {
            "timestamp": datetime.now().isoformat(),
            "module_id": getattr(current_module, 'module_id', None) if current_module else None,
            "failure_count": getattr(current_module, 'failure_count', 0) if current_module else 0,
            "error_context": state["error_context"],
            "failure_attempts": state["failure_attempts"]
        }
        
        # 保存升级记录到数据库
        await self._save_escalation_record(state, escalation_record)
        
        return state
    
    async def _error_handler_node(self, state: WorkflowState) -> WorkflowState:
        """错误处理节点"""
        error_context = state["error_context"]
        
        if error_context:
            # 增加重试计数
            retry_count = error_context.get("retry_count", 0) + 1
            error_context["retry_count"] = retry_count
            
            # 检查是否超过最大重试次数
            if retry_count >= 3:
                state["escalation_required"] = True
                state["should_continue"] = False
                state["completion_status"] = "ERROR_MAX_RETRIES"
            else:
                # 清理错误上下文，准备重试
                state["error_context"] = None
        
        return state
    

    
    def _route_next_step(self, state: WorkflowState) -> str:
        """路由下一步"""
        return determine_next_agent(state)
    
    def _route_from_cognitive_router(self, state: WorkflowState) -> str:
        """从认知路由器路由到具体代理"""
        current_phase = state["current_phase"]
        print(f"[DEBUG] Routing from cognitive router, current_phase: {current_phase}")
        print(f"[DEBUG] Current modules: {state.get('modules', [])}")
        
        # 根据当前阶段直接路由到对应的代理
        if current_phase == WorkflowPhase.INITIALIZATION:
            # 初始化阶段，进入规划
            state["current_phase"] = WorkflowPhase.PLANNING
            print(f"[DEBUG] Routing to planning_agent")
            return "planning_agent"
        elif current_phase == WorkflowPhase.PLANNING:
            # 规划阶段完成，进入测试阶段
            if state["modules"] and len(state["modules"]) > 0:
                state["current_phase"] = WorkflowPhase.TESTING
                state["current_module_index"] = 0
                # modules现在是字典格式，直接使用
                state["current_module"] = state["modules"][0]
                print(f"[DEBUG] Routing to testing_agent")
                return "testing_agent"
            else:
                # 规划失败，重新规划
                print(f"[DEBUG] No modules found, routing back to planning_agent")
                return "planning_agent"
        elif current_phase == WorkflowPhase.TESTING:
            return "testing_agent"
        elif current_phase == WorkflowPhase.DEVELOPMENT:
            return "development_agent"
        elif current_phase == WorkflowPhase.VALIDATION:
            return "validation_agent"
        elif current_phase == WorkflowPhase.COMPLETION:
            return "__end__"
        else:
            return "error_handler"
    

    
    async def run_workflow(
        self,
        initial_prd: str,
        tech_stack: Dict[str, Any],
        code_standards: Optional[Dict[str, Any]] = None,
        run_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """运行完整的开发工作流
        
        Args:
            initial_prd: 产品需求文档
            tech_stack: 技术栈配置
            code_standards: 代码规范
            run_id: 开发运行ID（可选）
            
        Returns:
            工作流执行结果
        """
        # 创建或获取运行ID
        if run_id is None:
            run_id = await self._create_development_run(initial_prd, tech_stack)
        
        # 创建初始状态
        initial_state = create_initial_state(
            run_id=run_id,
            initial_prd=initial_prd,
            tech_stack=tech_stack,
            code_standards=code_standards
        )
        
        # 编译工作流
        print(f"[DEBUG] Compiling workflow...")
        app = self.workflow.compile(checkpointer=MemorySaver())
        print(f"[DEBUG] Workflow compiled successfully")
        
        # 运行工作流
        config = {"configurable": {"thread_id": f"dev_run_{run_id}"}}
        print(f"[DEBUG] Starting workflow with initial_state: {initial_state}")
        
        try:
            final_state = None
            step_count = 0
            async for state in app.astream(initial_state, config):
                step_count += 1
                print(f"[DEBUG] Workflow step {step_count}, state: {state}")
                final_state = state
                
                # 记录中间状态
                await self._save_workflow_state(run_id, state)
                
                # Save to integration manager if available
                db_adapter = self.integration_manager.get_db_adapter()
                if db_adapter:
                    await db_adapter.save_workflow_state(f"dev_run_{run_id}", state)
                
                # 检查是否需要停止
                # 确保state包含必要的键
                if isinstance(state, dict) and "current_phase" in state:
                    if not should_continue_workflow(state):
                        print(f"[DEBUG] Workflow should stop, breaking")
                        break
                        
                # 防止无限循环
                if step_count > 30:
                    print(f"[DEBUG] Too many steps, breaking to prevent infinite loop")
                    break
            
            # 保存最终结果
            print(f"[DEBUG] Final state: {final_state}")
            if final_state is None:
                print(f"[DEBUG] Final state is None, creating empty result")
                final_state = {
                    "modules": [],
                    "current_phase": "ERROR",
                    "completion_status": "FAILED"
                }
            result = await self._finalize_workflow_result(run_id, final_state)
            print(f"[DEBUG] Finalized result: {result}")
            return result
            
        except Exception as e:
            # 处理工作流执行错误
            import traceback
            error_traceback = traceback.format_exc()
            print(f"[DEBUG] Workflow execution failed with error: {str(e)}")
            print(f"[DEBUG] Error traceback: {error_traceback}")
            
            error_result = {
                "run_id": run_id,
                "status": "ERROR",
                "error": str(e),
                "error_traceback": error_traceback,  # 添加完整的堆栈跟踪
                "modules": [],  # 确保包含modules键
                "current_phase": "ERROR",
                "generated_artifacts": [],
                "modules_completed": 0,
                "total_modules": 0,
                "cot_records_count": 0,
                "escalation_required": False,
                "timestamp": datetime.now().isoformat()
            }
            await self._save_error_result(run_id, error_result)
            return error_result
    
    async def _create_development_run(self, initial_prd: str, tech_stack: Dict[str, Any]) -> int:
        """创建开发运行记录"""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO development_runs (initial_prd, tech_stack, final_status, start_time)
            VALUES (?, ?, ?, ?)
        """, (
            initial_prd,
            str(tech_stack),
            "RUNNING",
            datetime.now().isoformat()
        ))
        
        run_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return run_id
    
    async def _save_workflow_state(self, run_id: int, state: Dict[str, Any]):
        """保存工作流状态"""
        # 保存思维链记录
        if "cot_records" in state:
            for record in state["cot_records"]:
                await self._save_cot_record(run_id, record)
        
        # Save to integration manager if available
        db_adapter = self.integration_manager.get_db_adapter()
        if db_adapter:
            await db_adapter.save_workflow_state(f"run_{run_id}", state)
    
    async def _save_cot_record(self, run_id: int, record: Dict[str, Any]):
        """保存思维链记录"""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO cot_records (
                run_id, node_name, timestamp, thought_process, 
                input_context, output_result, selected_model, step_type, module_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            run_id,
            record["node_name"],
            record["timestamp"],
            record["thought_process"],
            record["input_context"],
            record["output_result"],
            record["selected_model"],
            record.get("step_type", "LINEAR"),
            record.get("module_id")
        ))
        
        conn.commit()
        conn.close()
    
    async def _save_escalation_record(self, state: WorkflowState, escalation_record: Dict[str, Any]):
        """保存问题升级记录"""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 获取run_id
        run_id = state.get("run_id", 0)
        
        # 确保所有参数都是适当的类型
        module_id = escalation_record.get("module_id", 0)
        problem_type = str(escalation_record.get("problem_type", "UNKNOWN"))
        error_context = escalation_record.get("error_context", "")
        failure_attempts = escalation_record.get("failure_attempts", 1)
        resolution_status = str(escalation_record.get("resolution_status", "PENDING"))
        escalation_report = escalation_record.get("escalation_report", "")
        
        # 转换复杂类型为字符串
        if isinstance(error_context, (dict, list)):
            error_context = str(error_context)
        if isinstance(failure_attempts, (dict, list)):
            failure_attempts = str(failure_attempts)
        if isinstance(escalation_report, (dict, list)):
            escalation_report = str(escalation_report)
        
        cursor.execute("""
            INSERT INTO problem_escalations (
                run_id, module_id, problem_type, problem_description, 
                escalation_level, status, resolution, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, datetime('now'))
        """, (
            run_id,
            module_id,
            problem_type,
            str(error_context),
            str(failure_attempts),
            resolution_status,
            str(escalation_report)
        ))
        
        conn.commit()
        conn.close()
    
    async def _finalize_workflow_result(self, run_id: int, final_state: Dict[str, Any]) -> Dict[str, Any]:
        """完成工作流并返回结果"""
        # 更新开发运行状态
        conn = get_db_connection()
        cursor = conn.cursor()
        
        status = final_state.get("completion_status", "UNKNOWN")
        end_time = datetime.now().isoformat()
        
        cursor.execute("""
            UPDATE development_runs 
            SET final_status = ?, end_time = ?
            WHERE run_id = ?
        """, (
            status,
            end_time,
            run_id
        ))
        
        conn.commit()
        conn.close()
        
        # 构建返回结果
        modules = final_state.get("modules", [])
        
        # 模块已经是字典格式，直接使用
        modules_dict = modules
        
        result = {
            "run_id": run_id,
            "status": status,
            "modules": modules_dict,
            "current_phase": final_state.get("current_phase", WorkflowPhase.COMPLETION),
            "generated_artifacts": final_state.get("generated_artifacts", []),
            "modules_completed": len([m for m in modules if isinstance(m, dict) and m.get('status') == 'COMPLETED']),
            "total_modules": len(modules),
            "cot_records_count": len(final_state.get("cot_records", [])),
            "escalation_required": final_state.get("escalation_required", False),
            "end_time": end_time
        }
        
        return result
    
    async def _save_error_result(self, run_id: int, error_result: Dict[str, Any]):
        """保存错误结果"""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE development_runs 
            SET final_status = ?, end_time = ?
            WHERE run_id = ?
        """, (
            "ERROR",
            error_result["timestamp"],
            run_id
        ))
        
        conn.commit()
        conn.close()
    
    async def get_workflow_status(self, run_id: int) -> Dict[str, Any]:
        """获取工作流状态"""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 获取基本信息
        cursor.execute("""
            SELECT run_id, final_status, start_time, end_time, initial_prd, tech_stack
            FROM development_runs WHERE run_id = ?
        """, (run_id,))
        
        run_data = cursor.fetchone()
        if not run_data:
            return {"error": "Run not found"}
        
        # 获取思维链记录
        cursor.execute("""
            SELECT node_name, timestamp, thought_process, selected_model, module_id
            FROM cot_records WHERE run_id = ? ORDER BY timestamp
        """, (run_id,))
        
        cot_records = cursor.fetchall()
        
        # 获取升级记录
        cursor.execute("""
            SELECT module_id, problem_type, escalation_level, created_at, status
            FROM problem_escalations WHERE run_id = ?
        """, (run_id,))
        
        escalations = cursor.fetchall()
        
        conn.close()
        
        result = {
            "run_id": run_data[0],
            "status": run_data[1],
            "start_time": run_data[2],
            "end_time": run_data[3],
            "initial_prd": run_data[4],
            "tech_stack": run_data[5],
            "cot_records": [{
                "node_name": record[0],
                "timestamp": record[1],
                "thought_process": record[2],
                "selected_model": record[3],
                "module_id": record[4]
            } for record in cot_records],
            "escalations": [{
                "module_id": esc[0],
                "problem_type": esc[1],
                "escalation_level": esc[2],
                "created_at": esc[3],
                "status": esc[4]
            } for esc in escalations]
        }
        
        return result
    
    async def get_integration_status(self) -> Dict[str, Any]:
        """Get status of all integrated services."""
        return await self.integration_manager.get_status()