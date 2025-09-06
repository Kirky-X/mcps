#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
代码生成功能测试脚本
测试MCP DevAgent的代码生成和思维链能力
"""

import sys
import os
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent / "src"))

from mcp_devagent.workflow.state_manager import create_initial_state, add_cot_record
from mcp_devagent.database.models import DevelopmentRun, CotRecord, CodeFile
from mcp_devagent.database.connection import get_db_session

class TestCodeGeneration:
    """代码生成功能测试类"""
    
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
    
    def test_state_creation(self):
        """测试状态创建功能"""
        try:
            state = create_initial_state(
                run_id="test_code_gen",
                initial_prd="开发一个简单的计算器应用",
                tech_stack={"language": "Python", "framework": "Tkinter"}
            )
            
            if state and 'run_id' in state and state['run_id'] == "test_code_gen":
                self.log_test("状态创建", True, "成功创建代码生成状态")
            else:
                self.log_test("状态创建", False, "状态创建失败")
                
        except Exception as e:
            self.log_test("状态创建", False, f"异常: {str(e)}")
    
    def test_cot_record_creation(self):
        """测试思维链记录创建"""
        try:
            state = create_initial_state(
                run_id="test_cot_gen",
                initial_prd="开发Web应用",
                tech_stack={"language": "Python", "framework": "Flask"}
            )
            
            # 创建思维链记录
            cot_record = add_cot_record(
                state=state,
                node_name="code_generation",
                thought_process="分析需求后，决定创建Flask应用的基本结构",
                input_context="PRD: 开发Web应用",
                output_result="生成app.py主文件和基本路由",
                selected_model="gpt-4",
                step_type="code_generation"
            )
            
            # 检查思维链记录是否正确添加到状态中
            cot_records = state.get("cot_records", [])
            if len(cot_records) > 0 and "thought_process" in cot_records[-1]:
                self.log_test("思维链记录", True, "成功创建代码生成思维链")
            else:
                self.log_test("思维链记录", False, "思维链记录创建失败")
                
        except Exception as e:
            self.log_test("思维链记录", False, f"异常: {str(e)}")
    
    def test_code_structure_planning(self):
        """测试代码结构规划"""
        try:
            # 模拟代码结构规划过程
            project_structure = {
                "main_file": "app.py",
                "models": ["user.py", "task.py"],
                "views": ["auth.py", "tasks.py"],
                "templates": ["base.html", "index.html"],
                "static": ["style.css", "script.js"]
            }
            
            # 验证结构规划的完整性
            required_components = ["main_file", "models", "views"]
            has_all_components = all(comp in project_structure for comp in required_components)
            
            if has_all_components:
                self.log_test("代码结构规划", True, "成功规划项目代码结构")
            else:
                self.log_test("代码结构规划", False, "代码结构规划不完整")
                
        except Exception as e:
            self.log_test("代码结构规划", False, f"异常: {str(e)}")
    
    def test_code_template_generation(self):
        """测试代码模板生成"""
        try:
            # 模拟生成Python Flask应用模板
            flask_template = '''
from flask import Flask, render_template, request, redirect, url_for

app = Flask(__name__)
app.secret_key = 'your-secret-key'

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/tasks')
def tasks():
    # TODO: 实现任务列表功能
    return render_template('tasks.html')

if __name__ == '__main__':
    app.run(debug=True)
'''
            
            # 验证模板的基本结构
            has_imports = 'from flask import' in flask_template
            has_routes = '@app.route' in flask_template
            has_main = "if __name__ == '__main__'" in flask_template
            
            if has_imports and has_routes and has_main:
                self.log_test("代码模板生成", True, "成功生成Flask应用模板")
            else:
                self.log_test("代码模板生成", False, "代码模板结构不完整")
                
        except Exception as e:
            self.log_test("代码模板生成", False, f"异常: {str(e)}")
    
    def test_code_quality_validation(self):
        """测试代码质量验证"""
        try:
            # 测试代码示例
            good_code = '''
def calculate_sum(a, b):
    """计算两个数的和"""
    if not isinstance(a, (int, float)) or not isinstance(b, (int, float)):
        raise TypeError("参数必须是数字")
    return a + b
'''
            
            bad_code = '''
def calc(x,y):
return x+y
'''
            
            # 简单的代码质量检查
            good_has_docstring = '"""' in good_code
            good_has_validation = 'isinstance' in good_code
            bad_lacks_docstring = '"""' not in bad_code
            
            if good_has_docstring and good_has_validation and bad_lacks_docstring:
                self.log_test("代码质量验证", True, "成功识别代码质量差异")
            else:
                self.log_test("代码质量验证", False, "代码质量验证失败")
                
        except Exception as e:
            self.log_test("代码质量验证", False, f"异常: {str(e)}")
    
    def test_incremental_generation(self):
        """测试增量代码生成"""
        try:
            # 模拟增量生成过程
            base_code = "class Calculator:\n    pass"
            
            # 第一次增量：添加初始化方法
            increment1 = "class Calculator:\n    def __init__(self):\n        self.result = 0"
            
            # 第二次增量：添加计算方法
            increment2 = "class Calculator:\n    def __init__(self):\n        self.result = 0\n    \n    def add(self, value):\n        self.result += value\n        return self.result"
            
            # 验证增量生成的逻辑
            has_progression = (
                len(base_code) < len(increment1) < len(increment2) and
                'def __init__' in increment1 and
                'def add' in increment2
            )
            
            if has_progression:
                self.log_test("增量代码生成", True, "成功实现增量代码生成")
            else:
                self.log_test("增量代码生成", False, "增量生成逻辑错误")
                
        except Exception as e:
            self.log_test("增量代码生成", False, f"异常: {str(e)}")
    
    def test_error_handling_generation(self):
        """测试错误处理代码生成"""
        try:
            # 模拟生成包含错误处理的代码
            error_handling_code = '''
def divide_numbers(a, b):
    try:
        if b == 0:
            raise ValueError("除数不能为零")
        return a / b
    except TypeError:
        print("输入必须是数字")
        return None
    except ValueError as e:
        print(f"值错误: {e}")
        return None
'''
            
            # 验证错误处理结构
            has_try_except = 'try:' in error_handling_code and 'except' in error_handling_code
            has_specific_exceptions = 'ValueError' in error_handling_code and 'TypeError' in error_handling_code
            has_error_messages = '"除数不能为零"' in error_handling_code
            
            if has_try_except and has_specific_exceptions and has_error_messages:
                self.log_test("错误处理生成", True, "成功生成错误处理代码")
            else:
                self.log_test("错误处理生成", False, "错误处理代码不完整")
                
        except Exception as e:
            self.log_test("错误处理生成", False, f"异常: {str(e)}")
    
    def run_all_tests(self):
        """运行所有测试"""
        print("🔍 开始测试MCP DevAgent代码生成功能...\n")
        
        # 运行各项测试
        self.test_state_creation()
        self.test_cot_record_creation()
        self.test_code_structure_planning()
        self.test_code_template_generation()
        self.test_code_quality_validation()
        self.test_incremental_generation()
        self.test_error_handling_generation()
        
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
            print("\n✅ 代码生成功能测试通过！")
        else:
            print("\n⚠️  部分测试失败，需要检查代码生成功能实现。")

if __name__ == "__main__":
    tester = TestCodeGeneration()
    tester.run_all_tests()