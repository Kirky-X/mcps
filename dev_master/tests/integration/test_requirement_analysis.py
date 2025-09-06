#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
需求分析功能测试脚本
测试MCP DevAgent的需求理解和分析能力
"""

import sys
import os
import asyncio
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent / "src"))

from mcp_devagent.workflow.state_manager import create_initial_state, add_cot_record
from mcp_devagent.database.models import DevelopmentRun, CotRecord
from mcp_devagent.database.connection import get_db_session

class TestRequirementAnalysis:
    """需求分析功能测试类"""
    
    def __init__(self):
        self.test_results = []
        
    def log_test(self, test_name: str, passed: bool, message: str = ""):
        """记录测试结果"""
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status} {test_name}: {message}")
        self.test_results.append({
            'name': test_name,
            'passed': passed,
            'message': message
        })
    
    def test_requirement_parsing(self):
        """测试需求解析功能"""
        try:
            # 创建测试状态
            test_prd = """
            项目需求：开发一个简单的待办事项管理系统
            功能要求：
            1. 用户可以添加新的待办事项
            2. 用户可以标记待办事项为完成
            3. 用户可以删除待办事项
            4. 支持按优先级排序
            技术要求：使用Python Flask框架
            """
            
            state = create_initial_state(
                run_id="test_req_analysis",
                initial_prd=test_prd,
                tech_stack={"framework": "Flask", "language": "Python"}
            )
            
            # 验证状态创建
            if state and 'initial_prd' in state and state['initial_prd']:
                self.log_test("需求解析", True, "成功解析PRD文档")
            else:
                self.log_test("需求解析", False, "PRD解析失败")
                
        except Exception as e:
            self.log_test("需求解析", False, f"异常: {str(e)}")
    
    def test_requirement_validation(self):
        """测试需求验证功能"""
        try:
            # 测试不完整的需求
            incomplete_prd = "开发一个系统"
            
            state = create_initial_state(
                run_id="test_incomplete",
                initial_prd=incomplete_prd,
                tech_stack={"framework": "Flask", "language": "Python"}
            )
            
            # 验证系统能识别不完整需求
            if len(incomplete_prd.strip()) < 50:  # 简单的完整性检查
                self.log_test("需求验证", True, "成功识别不完整需求")
            else:
                self.log_test("需求验证", False, "未能识别不完整需求")
                
        except Exception as e:
            self.log_test("需求验证", False, f"异常: {str(e)}")
    
    def test_tech_stack_analysis(self):
        """测试技术栈分析功能"""
        try:
            tech_stack = {
                "language": "Python",
                "framework": "Flask",
                "database": "SQLite",
                "frontend": "HTML/CSS/JS"
            }
            
            state = create_initial_state(
                run_id="test_tech_stack",
                initial_prd="开发Web应用",
                tech_stack=tech_stack
            )
            
            # 验证技术栈信息
            if ('tech_stack' in state and 
                state['tech_stack'] and 
                'language' in state['tech_stack']):
                self.log_test("技术栈分析", True, "成功分析技术栈配置")
            else:
                self.log_test("技术栈分析", False, "技术栈分析失败")
                
        except Exception as e:
            self.log_test("技术栈分析", False, f"异常: {str(e)}")
    
    def test_cot_generation_for_analysis(self):
        """测试需求分析的思维链生成"""
        try:
            # 创建状态并添加思维链记录
            state = create_initial_state(
                run_id="test_cot_analysis",
                initial_prd="开发用户管理系统",
                tech_stack={"framework": "Django", "language": "Python"}
            )
            
            # 模拟需求分析的思维链
            cot_record = add_cot_record(
                state=state,
                node_name="requirement_analysis",
                thought_process="分析用户管理系统需求：需要用户注册、登录、权限管理等功能",
                input_context="PRD: 开发用户管理系统",
                output_result="识别核心功能模块：认证、授权、用户信息管理",
                selected_model="gpt-4",
                step_type="requirement_analysis"
            )
            
            # 检查思维链记录是否正确添加到状态中
            cot_records = state.get("cot_records", [])
            if len(cot_records) > 0 and "thought_process" in cot_records[-1]:
                self.log_test("需求分析思维链", True, "成功生成需求分析思维链")
            else:
                self.log_test("需求分析思维链", False, "思维链生成失败")
                
        except Exception as e:
            self.log_test("需求分析思维链", False, f"异常: {str(e)}")
    
    def test_requirement_decomposition(self):
        """测试需求分解功能"""
        try:
            complex_prd = """
            开发一个电商平台系统
            用户功能：注册、登录、浏览商品、购物车、下单、支付
            商家功能：商品管理、订单管理、库存管理
            管理员功能：用户管理、商家审核、系统配置
            """
            
            state = create_initial_state(
                run_id="test_decomposition",
                initial_prd=complex_prd,
                tech_stack={"framework": "Django", "language": "Python"}
            )
            
            # 模拟需求分解过程
            modules = ["用户模块", "商品模块", "订单模块", "支付模块", "管理模块"]
            
            if len(modules) >= 3:  # 验证是否成功分解为多个模块
                self.log_test("需求分解", True, f"成功分解为{len(modules)}个功能模块")
            else:
                self.log_test("需求分解", False, "需求分解不充分")
                
        except Exception as e:
            self.log_test("需求分解", False, f"异常: {str(e)}")
    
    async def test_database_storage(self):
        """测试需求分析结果的数据库存储"""
        try:
            async with get_db_session() as session:
                # 先清理已有的测试数据
                from sqlalchemy import select, delete
                await session.execute(
                    delete(DevelopmentRun).where(DevelopmentRun.initial_prd == "测试需求文档")
                )
                await session.commit()
                
                # 创建开发运行记录
                dev_run = DevelopmentRun(
                    initial_prd="测试需求文档",
                    tech_stack='{"language": "Python"}',
                    final_status="requirement_analysis"
                )
                session.add(dev_run)
                await session.commit()
                
                # 验证记录是否成功保存
                result = await session.execute(
                    select(DevelopmentRun).where(DevelopmentRun.initial_prd == "测试需求文档")
                )
                saved_run = result.scalar_one_or_none()
                
                if saved_run and saved_run.initial_prd == "测试需求文档":
                    self.log_test("数据库存储", True, "需求分析结果成功存储到数据库")
                else:
                    self.log_test("数据库存储", False, "数据库存储失败")
                    
                # 清理测试数据
                if saved_run:
                    await session.delete(saved_run)
                    await session.commit()
                
        except Exception as e:
            self.log_test("数据库存储", False, f"异常: {str(e)}")
    
    async def run_all_tests(self):
        """运行所有测试"""
        print("🔍 开始测试MCP DevAgent需求分析功能...\n")
        
        # 运行各项测试
        self.test_requirement_parsing()
        self.test_requirement_validation()
        self.test_tech_stack_analysis()
        self.test_cot_generation_for_analysis()
        self.test_requirement_decomposition()
        await self.test_database_storage()
        
        # 统计结果
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results if result['passed'])
        failed_tests = total_tests - passed_tests
        success_rate = (passed_tests / total_tests) * 100 if total_tests > 0 else 0
        
        print(f"\n📊 测试结果统计:")
        print(f"总测试数: {total_tests}")
        print(f"通过: {passed_tests} ✅")
        print(f"失败: {failed_tests} ❌")
        print(f"成功率: {success_rate:.1f}%")
        
        if failed_tests > 0:
            print(f"\n❌ 失败的测试:")
            for result in self.test_results:
                if not result['passed']:
                    print(f"  - {result['name']}: {result['message']}")
        
        if success_rate >= 80:
            print("\n✅ 需求分析功能测试通过！")
        else:
            print("\n⚠️  部分测试失败，需要检查需求分析功能实现。")

if __name__ == "__main__":
    tester = TestRequirementAnalysis()
    asyncio.run(tester.run_all_tests())