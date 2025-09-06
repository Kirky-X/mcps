"""LangGraph工作流配置

定义工作流引擎的配置参数、模型选择策略和执行参数。
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from enum import Enum


class ModelProvider(Enum):
    """LLM模型提供商"""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    OLLAMA = "ollama"
    GEMINI = "gemini"


class ModelTier(Enum):
    """模型性能等级"""
    BASIC = "basic"          # 基础模型，适用于简单任务
    STANDARD = "standard"    # 标准模型，适用于常规任务
    ADVANCED = "advanced"    # 高级模型，适用于复杂任务
    PREMIUM = "premium"      # 顶级模型，适用于最复杂任务


@dataclass
class ModelConfig:
    """模型配置"""
    provider: ModelProvider
    model_name: str
    tier: ModelTier
    max_tokens: int
    temperature: float
    cost_per_1k_tokens: float
    context_window: int
    supports_function_calling: bool = True
    supports_streaming: bool = True


@dataclass
class WorkflowConfig:
    """工作流配置"""
    # 基本配置
    max_retries: int = 3
    retry_delay: int = 5  # 重试延迟（秒）
    timeout_seconds: int = 300
    enable_checkpointing: bool = True
    enable_streaming: bool = True
    planning_phase: bool = True  # 启用规划阶段
    
    # 认知路由配置
    enable_cognitive_routing: bool = True
    cost_weight: float = 0.3
    performance_weight: float = 0.4
    complexity_weight: float = 0.3
    
    # 三振出局配置
    max_module_failures: int = 3
    enable_escalation: bool = True
    escalation_threshold: int = 3
    
    # 并发配置
    max_concurrent_modules: int = 1  # 当前版本串行处理
    enable_parallel_testing: bool = False
    
    # 缓存配置
    enable_response_caching: bool = True
    cache_ttl_seconds: int = 3600
    
    # 日志配置
    log_level: str = "INFO"
    enable_cot_logging: bool = True
    enable_performance_metrics: bool = True


class DefaultModelConfigs:
    """默认模型配置"""
    
    # OpenAI模型配置
    OPENAI_MODELS = {
        "gpt-4o": ModelConfig(
            provider=ModelProvider.OPENAI,
            model_name="gpt-4o",
            tier=ModelTier.PREMIUM,
            max_tokens=4096,
            temperature=0.1,
            cost_per_1k_tokens=0.03,
            context_window=128000
        ),
        "gpt-4o-mini": ModelConfig(
            provider=ModelProvider.OPENAI,
            model_name="gpt-4o-mini",
            tier=ModelTier.ADVANCED,
            max_tokens=4096,
            temperature=0.1,
            cost_per_1k_tokens=0.0015,
            context_window=128000
        ),
        "gpt-3.5-turbo": ModelConfig(
            provider=ModelProvider.OPENAI,
            model_name="gpt-3.5-turbo",
            tier=ModelTier.STANDARD,
            max_tokens=4096,
            temperature=0.1,
            cost_per_1k_tokens=0.001,
            context_window=16385
        )
    }
    
    # Anthropic模型配置
    ANTHROPIC_MODELS = {
        "claude-3-5-sonnet-20241022": ModelConfig(
            provider=ModelProvider.ANTHROPIC,
            model_name="claude-3-5-sonnet-20241022",
            tier=ModelTier.PREMIUM,
            max_tokens=4096,
            temperature=0.1,
            cost_per_1k_tokens=0.015,
            context_window=200000
        ),
        "claude-3-haiku-20240307": ModelConfig(
            provider=ModelProvider.ANTHROPIC,
            model_name="claude-3-haiku-20240307",
            tier=ModelTier.STANDARD,
            max_tokens=4096,
            temperature=0.1,
            cost_per_1k_tokens=0.00025,
            context_window=200000
        )
    }
    
    # Ollama本地模型配置
    OLLAMA_MODELS = {
        "llama3.1:8b": ModelConfig(
            provider=ModelProvider.OLLAMA,
            model_name="llama3.1:8b",
            tier=ModelTier.STANDARD,
            max_tokens=4096,
            temperature=0.1,
            cost_per_1k_tokens=0.0,  # 本地模型无成本
            context_window=32768
        ),
        "codellama:13b": ModelConfig(
            provider=ModelProvider.OLLAMA,
            model_name="codellama:13b",
            tier=ModelTier.ADVANCED,
            max_tokens=4096,
            temperature=0.1,
            cost_per_1k_tokens=0.0,
            context_window=16384
        )
    }
    
    @classmethod
    def get_all_models(cls) -> Dict[str, ModelConfig]:
        """获取所有可用模型配置"""
        all_models = {}
        all_models.update(cls.OPENAI_MODELS)
        all_models.update(cls.ANTHROPIC_MODELS)
        all_models.update(cls.OLLAMA_MODELS)
        return all_models
    
    @classmethod
    def get_models_by_tier(cls, tier: ModelTier) -> Dict[str, ModelConfig]:
        """根据性能等级获取模型"""
        all_models = cls.get_all_models()
        return {name: config for name, config in all_models.items() if config.tier == tier}
    
    @classmethod
    def get_models_by_provider(cls, provider: ModelProvider) -> Dict[str, ModelConfig]:
        """根据提供商获取模型"""
        all_models = cls.get_all_models()
        return {name: config for name, config in all_models.items() if config.provider == provider}


class CognitiveRoutingConfig:
    """认知路由配置"""
    
    # 任务复杂度阈值
    COMPLEXITY_THRESHOLDS = {
        "simple": 0.3,      # 简单任务：基础CRUD、简单逻辑
        "moderate": 0.6,    # 中等任务：业务逻辑、数据处理
        "complex": 0.8,     # 复杂任务：算法实现、架构设计
        "expert": 1.0       # 专家任务：复杂算法、性能优化
    }
    
    # 模型选择策略
    MODEL_SELECTION_STRATEGY = {
        "cost_optimized": {
            "cost_weight": 0.6,
            "performance_weight": 0.3,
            "complexity_weight": 0.1
        },
        "performance_optimized": {
            "cost_weight": 0.1,
            "performance_weight": 0.6,
            "complexity_weight": 0.3
        },
        "balanced": {
            "cost_weight": 0.3,
            "performance_weight": 0.4,
            "complexity_weight": 0.3
        }
    }
    
    # 任务类型到模型等级的映射
    TASK_TYPE_MODEL_MAPPING = {
        "planning": {
            "simple": ModelTier.STANDARD,
            "moderate": ModelTier.ADVANCED,
            "complex": ModelTier.PREMIUM,
            "expert": ModelTier.PREMIUM
        },
        "testing": {
            "simple": ModelTier.BASIC,
            "moderate": ModelTier.STANDARD,
            "complex": ModelTier.ADVANCED,
            "expert": ModelTier.PREMIUM
        },
        "development": {
            "simple": ModelTier.STANDARD,
            "moderate": ModelTier.ADVANCED,
            "complex": ModelTier.PREMIUM,
            "expert": ModelTier.PREMIUM
        },
        "validation": {
            "simple": ModelTier.BASIC,
            "moderate": ModelTier.STANDARD,
            "complex": ModelTier.ADVANCED,
            "expert": ModelTier.ADVANCED
        }
    }


class WorkflowPhaseConfig:
    """工作流阶段配置"""
    
    # 各阶段的超时配置（秒）
    PHASE_TIMEOUTS = {
        "planning": 180,      # 规划阶段：3分钟
        "testing": 120,       # 测试阶段：2分钟
        "development": 300,   # 开发阶段：5分钟
        "validation": 180     # 验证阶段：3分钟
    }
    
    # 各阶段的重试配置
    PHASE_RETRIES = {
        "planning": 2,        # 规划阶段最多重试2次
        "testing": 3,         # 测试阶段最多重试3次
        "development": 3,     # 开发阶段最多重试3次
        "validation": 2       # 验证阶段最多重试2次
    }
    
    # 各阶段的输出要求
    PHASE_OUTPUT_REQUIREMENTS = {
        "planning": {
            "min_modules": 1,
            "max_modules": 20,
            "required_fields": ["module_id", "description", "dependencies", "test_requirements"]
        },
        "testing": {
            "min_test_cases": 1,
            "max_test_cases": 10,
            "required_test_types": ["unit", "integration"]
        },
        "development": {
            "min_code_lines": 10,
            "max_code_lines": 1000,
            "required_elements": ["imports", "main_function", "error_handling"]
        },
        "validation": {
            "required_checks": ["syntax", "logic", "test_coverage"],
            "min_test_pass_rate": 0.8
        }
    }


def get_default_workflow_config() -> WorkflowConfig:
    """获取默认工作流配置"""
    return WorkflowConfig()


def get_model_config(model_name: str) -> Optional[ModelConfig]:
    """获取指定模型的配置"""
    all_models = DefaultModelConfigs.get_all_models()
    return all_models.get(model_name)


def get_optimal_model_for_task(
    task_type: str,
    complexity_score: float,
    strategy: str = "balanced",
    available_providers: Optional[List[ModelProvider]] = None
) -> Optional[str]:
    """为任务选择最优模型
    
    Args:
        task_type: 任务类型 (planning, testing, development, validation)
        complexity_score: 复杂度评分 (0.0-1.0)
        strategy: 选择策略 (cost_optimized, performance_optimized, balanced)
        available_providers: 可用的模型提供商列表
        
    Returns:
        最优模型名称
    """
    # 确定复杂度级别
    complexity_level = "simple"
    for level, threshold in CognitiveRoutingConfig.COMPLEXITY_THRESHOLDS.items():
        if complexity_score <= threshold:
            complexity_level = level
            break
    
    # 获取推荐的模型等级
    if task_type not in CognitiveRoutingConfig.TASK_TYPE_MODEL_MAPPING:
        return None
    
    recommended_tier = CognitiveRoutingConfig.TASK_TYPE_MODEL_MAPPING[task_type][complexity_level]
    
    # 获取该等级的所有模型
    tier_models = DefaultModelConfigs.get_models_by_tier(recommended_tier)
    
    # 根据可用提供商过滤
    if available_providers:
        tier_models = {
            name: config for name, config in tier_models.items()
            if config.provider in available_providers
        }
    
    if not tier_models:
        return None
    
    # 根据策略选择最优模型
    strategy_weights = CognitiveRoutingConfig.MODEL_SELECTION_STRATEGY.get(
        strategy, CognitiveRoutingConfig.MODEL_SELECTION_STRATEGY["balanced"]
    )
    
    best_model = None
    best_score = float('-inf')
    
    for model_name, config in tier_models.items():
        # 计算综合评分（成本越低越好，性能和复杂度处理能力越高越好）
        cost_score = 1.0 / (config.cost_per_1k_tokens + 0.001)  # 避免除零
        performance_score = config.context_window / 200000  # 归一化到0-1
        complexity_score = 1.0 if config.tier.value == recommended_tier.value else 0.5
        
        total_score = (
            cost_score * strategy_weights["cost_weight"] +
            performance_score * strategy_weights["performance_weight"] +
            complexity_score * strategy_weights["complexity_weight"]
        )
        
        if total_score > best_score:
            best_score = total_score
            best_model = model_name
    
    return best_model