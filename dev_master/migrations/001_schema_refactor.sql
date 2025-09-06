-- MCP-DevAgent 数据库Schema重构迁移脚本
-- 版本: v1.0.0
-- 创建日期: 2025年01月20日
-- 描述: 根据技术架构文档重构数据库Schema，移除现有搜索相关表，创建新的7个核心表

-- ============================================================================
-- 第一步：备份现有数据（如果需要）
-- ============================================================================

-- 创建备份表（保留重要数据）
CREATE TABLE IF NOT EXISTS backup_code_repositories AS SELECT * FROM code_repositories;
CREATE TABLE IF NOT EXISTS backup_code_files AS SELECT * FROM code_files;
CREATE TABLE IF NOT EXISTS backup_code_chunks AS SELECT * FROM code_chunks;
CREATE TABLE IF NOT EXISTS backup_code_embeddings AS SELECT * FROM code_embeddings;

-- ============================================================================
-- 第二步：删除现有表结构（保留FTS5和VSS相关表）
-- ============================================================================

-- 删除外键约束相关表（按依赖顺序）
DROP TABLE IF EXISTS search_results;
DROP TABLE IF EXISTS search_queries;
DROP TABLE IF EXISTS search_sessions;
DROP TABLE IF EXISTS agent_interactions;
DROP TABLE IF EXISTS agent_sessions;
DROP TABLE IF EXISTS code_embeddings;
DROP TABLE IF EXISTS code_chunks;
DROP TABLE IF EXISTS code_files;
DROP TABLE IF EXISTS code_repositories;

-- 注意：保留FTS5和VSS相关的虚拟表
-- code_chunks_fts, code_files_fts, code_embeddings_vss, code_embeddings_vss_768
-- 这些表将在后续步骤中重新配置

-- ============================================================================
-- 第三步：创建新的核心表结构（严格按照技术架构文档）
-- ============================================================================

-- 1. 开发运行表 (development_runs)
CREATE TABLE development_runs (
    run_id INTEGER PRIMARY KEY AUTOINCREMENT,
    start_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    end_time DATETIME,
    initial_prd TEXT NOT NULL,
    tech_stack TEXT NOT NULL,
    final_status TEXT DEFAULT 'IN_PROGRESS' CHECK (final_status IN ('IN_PROGRESS', 'COMPLETED', 'FAILED', 'ABORTED')),
    codebase_index_id TEXT,
    FOREIGN KEY (codebase_index_id) REFERENCES codebase_indexes(index_id)
);

-- 2. 模块表 (modules)
CREATE TABLE modules (
    module_id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id INTEGER NOT NULL,
    module_name VARCHAR(255) NOT NULL,
    file_path VARCHAR(500) NOT NULL,
    description TEXT,
    development_order INTEGER NOT NULL,
    status VARCHAR(50) DEFAULT 'PENDING' CHECK (status IN ('PENDING', 'IN_PROGRESS', 'COMPLETED', 'FAILED')),
    failure_count INTEGER DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (run_id) REFERENCES development_runs(run_id)
);

-- 3. 思维链记录表 (cot_records)
CREATE TABLE cot_records (
    cot_id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id INTEGER NOT NULL,
    module_id INTEGER,
    node_name VARCHAR(100) NOT NULL,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    thought_process TEXT NOT NULL,
    input_context TEXT,
    output_result TEXT,
    parent_step_id INTEGER,
    step_type VARCHAR(20) DEFAULT 'LINEAR' CHECK (step_type IN ('LINEAR', 'REVISION', 'BRANCH')),
    revises_step_id INTEGER,
    selected_model VARCHAR(100),
    FOREIGN KEY (run_id) REFERENCES development_runs(run_id),
    FOREIGN KEY (module_id) REFERENCES modules(module_id),
    FOREIGN KEY (parent_step_id) REFERENCES cot_records(cot_id),
    FOREIGN KEY (revises_step_id) REFERENCES cot_records(cot_id)
);

-- 4. 测试结果表 (test_results)
CREATE TABLE test_results (
    result_id INTEGER PRIMARY KEY AUTOINCREMENT,
    module_id INTEGER NOT NULL,
    status VARCHAR(20) NOT NULL CHECK (status IN ('SUCCESS', 'TESTS_FAILED', 'RUNTIME_ERROR')),
    total_tests INTEGER DEFAULT 0,
    passed_count INTEGER DEFAULT 0,
    failed_count INTEGER DEFAULT 0,
    error_details TEXT,
    execution_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (module_id) REFERENCES modules(module_id)
);

-- 5. 代码库索引表 (codebase_indexes)
CREATE TABLE codebase_indexes (
    index_id TEXT PRIMARY KEY,
    project_path TEXT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    indexed_files_count INTEGER DEFAULT 0,
    file_patterns TEXT DEFAULT '*.js,*.ts,*.py,*.java,*.cpp,*.h',
    exclude_patterns TEXT DEFAULT 'node_modules,dist,build,.git'
);

-- 6. 代码构件表 (code_artifacts)
CREATE TABLE code_artifacts (
    artifact_id INTEGER PRIMARY KEY AUTOINCREMENT,
    index_id TEXT NOT NULL,
    file_path TEXT NOT NULL,
    file_type VARCHAR(50) NOT NULL,
    ast_data TEXT,
    symbols TEXT,
    dependencies TEXT,
    last_modified DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (index_id) REFERENCES codebase_indexes(index_id)
);

-- 7. 问题升级表 (problem_escalations)
CREATE TABLE problem_escalations (
    escalation_id INTEGER PRIMARY KEY AUTOINCREMENT,
    module_id INTEGER NOT NULL,
    problem_type VARCHAR(100) NOT NULL,
    failure_attempts TEXT NOT NULL,
    error_context TEXT,
    escalation_report TEXT,
    alternative_solutions TEXT,
    human_decision_required BOOLEAN DEFAULT TRUE,
    escalated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    resolution_status VARCHAR(50) DEFAULT 'PENDING' CHECK (resolution_status IN ('PENDING', 'RESOLVED', 'ABANDONED')),
    FOREIGN KEY (module_id) REFERENCES modules(module_id)
);

-- ============================================================================
-- 第四步：创建索引（按照技术架构文档）
-- ============================================================================

-- 开发运行索引
CREATE INDEX idx_development_runs_status ON development_runs(final_status);
CREATE INDEX idx_development_runs_start_time ON development_runs(start_time);
CREATE INDEX idx_development_runs_codebase_index ON development_runs(codebase_index_id);

-- 模块索引
CREATE INDEX idx_modules_run_id ON modules(run_id);
CREATE INDEX idx_modules_status ON modules(status);
CREATE INDEX idx_modules_development_order ON modules(development_order);
CREATE INDEX idx_modules_failure_count ON modules(failure_count);

-- 思维链记录索引
CREATE INDEX idx_cot_records_run_id ON cot_records(run_id);
CREATE INDEX idx_cot_records_module_id ON cot_records(module_id);
CREATE INDEX idx_cot_records_timestamp ON cot_records(timestamp);
CREATE INDEX idx_cot_records_node_name ON cot_records(node_name);
CREATE INDEX idx_cot_records_parent_step ON cot_records(parent_step_id);
CREATE INDEX idx_cot_records_step_type ON cot_records(step_type);
CREATE INDEX idx_cot_records_selected_model ON cot_records(selected_model);

-- 测试结果索引
CREATE INDEX idx_test_results_module_id ON test_results(module_id);
CREATE INDEX idx_test_results_status ON test_results(status);
CREATE INDEX idx_test_results_execution_time ON test_results(execution_time);

-- 代码库索引表索引
CREATE INDEX idx_codebase_indexes_project_path ON codebase_indexes(project_path);
CREATE INDEX idx_codebase_indexes_created_at ON codebase_indexes(created_at);

-- 代码构件表索引
CREATE INDEX idx_code_artifacts_index_id ON code_artifacts(index_id);
CREATE INDEX idx_code_artifacts_file_path ON code_artifacts(file_path);
CREATE INDEX idx_code_artifacts_file_type ON code_artifacts(file_type);
CREATE INDEX idx_code_artifacts_last_modified ON code_artifacts(last_modified);

-- 问题升级表索引
CREATE INDEX idx_problem_escalations_module_id ON problem_escalations(module_id);
CREATE INDEX idx_problem_escalations_problem_type ON problem_escalations(problem_type);
CREATE INDEX idx_problem_escalations_escalated_at ON problem_escalations(escalated_at);
CREATE INDEX idx_problem_escalations_resolution_status ON problem_escalations(resolution_status);
CREATE INDEX idx_problem_escalations_human_decision ON problem_escalations(human_decision_required);

-- ============================================================================
-- 第五步：插入初始化数据（按照技术架构文档）
-- ============================================================================

-- 插入示例代码库索引
INSERT INTO codebase_indexes (index_id, project_path, indexed_files_count, file_patterns, exclude_patterns) VALUES 
('idx_mcp_devagent_001', '/home/project/mcp/dev_master', 25, '*.py,*.sql,*.md,*.json', '__pycache__,*.pyc,.git,migrations'),
('idx_example_project_001', '/home/user/projects/example-project', 18, '*.js,*.ts,*.jsx,*.tsx', 'node_modules,dist,build,.git');

-- 插入示例开发运行
INSERT INTO development_runs (initial_prd, tech_stack, final_status, codebase_index_id) VALUES 
('MCP-DevAgent 数据库Schema重构', 'Python + SQLite + LangGraph + FastAPI', 'IN_PROGRESS', 'idx_mcp_devagent_001'),
('示例项目开发', 'React + Node.js + TypeScript', 'COMPLETED', 'idx_example_project_001');

-- 插入示例模块
INSERT INTO modules (run_id, module_name, file_path, description, development_order, status, failure_count) VALUES 
(1, 'DatabaseSchemaRefactor', 'migrations/001_schema_refactor.sql', '数据库Schema重构迁移脚本', 1, 'IN_PROGRESS', 0),
(1, 'ModelsUpdate', 'src/mcp_devagent/database/models.py', '更新SQLAlchemy模型定义', 2, 'PENDING', 0),
(2, 'UserComponent', 'src/components/User.tsx', '用户组件实现', 1, 'COMPLETED', 0);

-- 插入示例代码构件
INSERT INTO code_artifacts (index_id, file_path, file_type, symbols, dependencies) VALUES 
('idx_mcp_devagent_001', 'src/mcp_devagent/database/models.py', 'python', 'Base,CodeRepository,CodeFile,CodeChunk', 'sqlalchemy,datetime'),
('idx_mcp_devagent_001', 'src/mcp_devagent/database/init.py', 'python', 'DatabaseInitializer,create_tables', 'sqlalchemy,sqlite3'),
('idx_example_project_001', 'src/components/User.tsx', 'typescript', 'User,UserProps,useState', 'react');

-- 插入示例思维链记录
INSERT INTO cot_records (run_id, module_id, node_name, thought_process, input_context, output_result, step_type, selected_model) VALUES 
(1, 1, 'planning_agent', '分析技术架构文档，确定需要创建的7个核心表结构', '技术架构文档定义了development_runs、modules等7个表', '创建了完整的数据库迁移脚本', 'LINEAR', 'claude-3.5-sonnet'),
(1, 1, 'development_agent', '实现数据库Schema重构迁移脚本', '基于planning_agent的表结构设计', '完成了001_schema_refactor.sql文件', 'LINEAR', 'gpt-4'),
(2, 3, 'development_agent', '实现User组件的TypeScript接口', '用户组件需要支持基本的用户信息展示', '完成了User.tsx组件实现', 'LINEAR', 'claude-3.5-sonnet');

-- 插入示例测试结果
INSERT INTO test_results (module_id, status, total_tests, passed_count, failed_count) VALUES 
(3, 'SUCCESS', 5, 5, 0),
(1, 'SUCCESS', 1, 1, 0);

-- ============================================================================
-- 第六步：验证新Schema
-- ============================================================================

-- 验证表创建
SELECT name FROM sqlite_master WHERE type='table' AND name IN (
    'development_runs', 'modules', 'cot_records', 'test_results', 
    'codebase_indexes', 'code_artifacts', 'problem_escalations'
);

-- 验证索引创建
SELECT name FROM sqlite_master WHERE type='index' AND name LIKE 'idx_%';

-- 验证数据插入
SELECT COUNT(*) as total_records FROM (
    SELECT 'development_runs' as table_name, COUNT(*) as count FROM development_runs
    UNION ALL
    SELECT 'modules', COUNT(*) FROM modules
    UNION ALL
    SELECT 'cot_records', COUNT(*) FROM cot_records
    UNION ALL
    SELECT 'test_results', COUNT(*) FROM test_results
    UNION ALL
    SELECT 'codebase_indexes', COUNT(*) FROM codebase_indexes
    UNION ALL
    SELECT 'code_artifacts', COUNT(*) FROM code_artifacts
);

-- ============================================================================
-- 迁移完成
-- ============================================================================

-- 迁移脚本执行完成
-- 新的数据库Schema已按照技术架构文档要求创建
-- 保留了FTS5和VSS相关的搜索表结构
-- 插入了初始化数据用于验证