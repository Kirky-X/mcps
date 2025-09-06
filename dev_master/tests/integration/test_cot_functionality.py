#!/usr/bin/env python3
"""
测试MCP DevAgent的思维链(CoT)功能

这个脚本测试：
1. 思维链记录是否正确生成
2. 数据库存储是否正常
3. 工作流程中的思维过程是否被记录
4. 不同节点的思维链是否能正确区分
"""

import asyncio
import json
import sqlite3
from datetime import datetime
from pathlib import Path

# 添加项目路径
import sys
sys.path.append('/home/project/mcps/dev_master/src')

from mcp_devagent.workflow.state_manager import (
    WorkflowState, 
    WorkflowPhase,
    ModuleTask,
    ModuleStatus,
    create_initial_state,
    add_cot_record
)
from mcp_devagent.services.llm_service import LLMService
from mcp_devagent.services.embedding_service import EmbeddingService
from mcp_devagent.workflow.nodes import CognitiveRouter, PlanningAgent
from mcp_devagent.database.connection import get_db_connection


class CoTTester:
    """思维链功能测试器"""
    
    def __init__(self):
        self.db_path = "/home/project/mcps/dev_master/data/mcp_devagent.db"
        self.test_results = []
        
    def log_test(self, test_name: str, success: bool, details: str = ""):
        """记录测试结果"""
        result = {
            "test_name": test_name,
            "success": success,
            "details": details,
            "timestamp": datetime.now().isoformat()
        }
        self.test_results.append(result)
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name}: {details}")
    
    def test_state_manager_cot_recording(self):
        """测试状态管理器的思维链记录功能"""
        try:
            # 创建初始状态
            prd = "创建一个简单的计算器应用"
            tech_stack = {"language": "Python", "framework": "Flask"}
            state = create_initial_state(
                run_id=1,
                initial_prd=prd, 
                tech_stack=tech_stack
            )
            
            # 添加思维链记录
            state = add_cot_record(
                state=state,
                node_name="TestNode",
                thought_process="我需要分析这个PRD，理解用户需要一个计算器应用。首先我要确定功能需求：基本的加减乘除运算。",
                input_context=f"PRD: {prd}, Tech Stack: {tech_stack}",
                output_result="确定了计算器的基本功能需求：支持加减乘除四则运算，需要用户界面输入数字和操作符。",
                selected_model="gpt-4"
            )
            
            # 验证记录是否正确添加
            cot_records = state.get("cot_records", [])
            if len(cot_records) == 1:
                record = cot_records[0]
                if (record["node_name"] == "TestNode" and 
                    "计算器" in record["thought_process"] and
                    record["selected_model"] == "gpt-4"):
                    self.log_test("状态管理器CoT记录", True, "思维链记录正确添加到状态中")
                else:
                    self.log_test("状态管理器CoT记录", False, f"记录内容不正确: {record}")
            else:
                self.log_test("状态管理器CoT记录", False, f"期望1条记录，实际{len(cot_records)}条")
                
        except Exception as e:
            self.log_test("状态管理器CoT记录", False, f"异常: {str(e)}")
    
    def test_database_cot_storage(self):
        """测试数据库中的思维链存储"""
        try:
            # 检查数据库连接
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 检查cot_records表是否存在
            cursor.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name='cot_records'
            """)
            
            if cursor.fetchone():
                # 检查表结构
                cursor.execute("PRAGMA table_info(cot_records)")
                columns = [row[1] for row in cursor.fetchall()]
                
                required_columns = [
                    'cot_id', 'run_id', 'node_name', 'timestamp', 
                    'thought_process', 'input_context', 'output_result', 
                    'selected_model'
                ]
                
                missing_columns = [col for col in required_columns if col not in columns]
                
                if not missing_columns:
                    self.log_test("数据库CoT表结构", True, "cot_records表结构完整")
                    
                    # 测试插入一条记录
                    test_record = {
                        'run_id': 1,
                        'node_name': 'TestNode',
                        'timestamp': datetime.now(),
                        'thought_process': '这是一个测试思维过程',
                        'input_context': '测试输入上下文',
                        'output_result': '测试输出结果',
                        'selected_model': 'test-model'
                    }
                    
                    cursor.execute("""
                        INSERT INTO cot_records 
                        (run_id, node_name, timestamp, thought_process, input_context, output_result, selected_model)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (
                        test_record['run_id'],
                        test_record['node_name'],
                        test_record['timestamp'],
                        test_record['thought_process'],
                        test_record['input_context'],
                        test_record['output_result'],
                        test_record['selected_model']
                    ))
                    
                    conn.commit()
                    
                    # 验证插入是否成功
                    cursor.execute("""
                        SELECT * FROM cot_records 
                        WHERE node_name = 'TestNode' AND thought_process = '这是一个测试思维过程'
                    """)
                    
                    result = cursor.fetchone()
                    if result:
                        self.log_test("数据库CoT存储", True, "成功插入和查询思维链记录")
                        
                        # 清理测试数据
                        cursor.execute("DELETE FROM cot_records WHERE node_name = 'TestNode'")
                        conn.commit()
                    else:
                        self.log_test("数据库CoT存储", False, "插入记录后无法查询到")
                else:
                    self.log_test("数据库CoT表结构", False, f"缺少列: {missing_columns}")
            else:
                self.log_test("数据库CoT表结构", False, "cot_records表不存在")
                
            conn.close()
            
        except Exception as e:
            self.log_test("数据库CoT存储", False, f"异常: {str(e)}")
    
    async def test_workflow_node_cot_generation(self):
        """测试工作流节点的思维链生成"""
        try:
            # 创建模拟的LLM服务
            class MockLLMService:
                async def get_chat_model(self, model_name="gpt-4"):
                    return MockChatModel()
                    
                def get_available_models(self):
                    return ["gpt-4", "gpt-3.5-turbo"]
            
            class MockChatModel:
                async def ainvoke(self, messages):
                    class MockResponse:
                        content = "这是一个模拟的LLM响应，用于测试思维链功能。我分析了输入的PRD，确定需要创建一个计算器应用。"
                    return MockResponse()
            
            class MockEmbeddingService:
                pass
            
            # 创建认知路由器
            llm_service = MockLLMService()
            embedding_service = MockEmbeddingService()
            cognitive_router = CognitiveRouter(llm_service, embedding_service)
            
            # 创建测试状态
            state = create_initial_state(
                run_id=1,
                initial_prd="创建计算器应用", 
                tech_stack={"language": "Python"}
            )
            
            # 执行认知路由
            updated_state = await cognitive_router.execute(state)
            
            # 检查是否生成了思维链记录
            cot_records = updated_state.get("cot_records", [])
            
            if len(cot_records) > 0:
                latest_record = cot_records[-1]
                if (latest_record["node_name"] == "CognitiveRouter" and
                    latest_record["thought_process"] and
                    latest_record["selected_model"]):
                    self.log_test("工作流节点CoT生成", True, "CognitiveRouter成功生成思维链记录")
                else:
                    self.log_test("工作流节点CoT生成", False, f"思维链记录格式不正确: {latest_record}")
            else:
                self.log_test("工作流节点CoT生成", False, "未生成思维链记录")
                
        except Exception as e:
            self.log_test("工作流节点CoT生成", False, f"异常: {str(e)}")
    
    def test_cot_record_structure(self):
        """测试思维链记录的数据结构"""
        try:
            state = create_initial_state(
                run_id=1,
                initial_prd="测试PRD", 
                tech_stack={"language": "Python", "framework": "测试框架"}
            )
            
            # 添加多条不同类型的思维链记录
            test_records = [
                {
                    "node_name": "PlanningAgent",
                    "thought_process": "规划阶段：分析需求，制定开发计划",
                    "input_context": "PRD分析",
                    "output_result": "生成了项目蓝图",
                    "selected_model": "gpt-4",
                    "step_type": "LINEAR"
                },
                {
                    "node_name": "TestingAgent", 
                    "thought_process": "测试阶段：为每个模块生成测试用例",
                    "input_context": "模块规划",
                    "output_result": "生成了测试代码",
                    "selected_model": "gpt-3.5-turbo",
                    "step_type": "BRANCH"
                }
            ]
            
            for record in test_records:
                state = add_cot_record(
                    state=state,
                    node_name=record["node_name"],
                    thought_process=record["thought_process"],
                    input_context=record["input_context"],
                    output_result=record["output_result"],
                    selected_model=record["selected_model"],
                    step_type=record["step_type"]
                )
            
            cot_records = state.get("cot_records", [])
            
            if len(cot_records) == 2:
                # 验证记录结构
                all_valid = True
                for i, record in enumerate(cot_records):
                    required_fields = ["node_name", "timestamp", "thought_process", 
                                     "input_context", "output_result", "selected_model", "step_type"]
                    
                    for field in required_fields:
                        if field not in record:
                            all_valid = False
                            break
                    
                    if not all_valid:
                        break
                
                if all_valid:
                    self.log_test("CoT记录结构", True, "所有思维链记录结构完整")
                else:
                    self.log_test("CoT记录结构", False, "思维链记录缺少必要字段")
            else:
                self.log_test("CoT记录结构", False, f"期望2条记录，实际{len(cot_records)}条")
                
        except Exception as e:
            self.log_test("CoT记录结构", False, f"异常: {str(e)}")
    
    async def run_all_tests(self):
        """运行所有测试"""
        print("🚀 开始测试MCP DevAgent思维链功能...\n")
        
        # 运行测试
        self.test_state_manager_cot_recording()
        self.test_database_cot_storage()
        await self.test_workflow_node_cot_generation()
        self.test_cot_record_structure()
        
        # 统计结果
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results if result["success"])
        failed_tests = total_tests - passed_tests
        
        print(f"\n📊 测试结果统计:")
        print(f"总测试数: {total_tests}")
        print(f"通过: {passed_tests} ✅")
        print(f"失败: {failed_tests} ❌")
        print(f"成功率: {(passed_tests/total_tests)*100:.1f}%")
        
        if failed_tests > 0:
            print("\n❌ 失败的测试:")
            for result in self.test_results:
                if not result["success"]:
                    print(f"  - {result['test_name']}: {result['details']}")
        
        return passed_tests == total_tests


if __name__ == "__main__":
    async def main():
        tester = CoTTester()
        success = await tester.run_all_tests()
        
        if success:
            print("\n🎉 所有思维链功能测试通过！")
        else:
            print("\n⚠️  部分测试失败，需要检查思维链功能实现。")
        
        return success
    
    asyncio.run(main())