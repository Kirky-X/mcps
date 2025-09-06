"""LLM Service

Manages Large Language Model interactions with multi-provider support,
intelligent routing, and performance monitoring.
"""

import asyncio
import json
import logging
import time
from typing import Any, Dict, List, Optional, Union

try:
    from langchain_openai import ChatOpenAI
    from langchain_anthropic import ChatAnthropic
    from langchain_google_genai import ChatGoogleGenerativeAI
    from langchain_core.language_models import BaseChatModel
    from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
    from langchain_core.prompts import ChatPromptTemplate
except ImportError:
    # Fallback for development without LangChain
    ChatOpenAI = None
    ChatAnthropic = None
    ChatGoogleGenerativeAI = None
    BaseChatModel = None
    HumanMessage = None
    SystemMessage = None
    AIMessage = None
    ChatPromptTemplate = None


class LLMProvider:
    """Base class for LLM providers."""
    
    def __init__(self, name: str, model: str, max_tokens: int = 4096,
                 cost_per_input_token: float = 0.0, cost_per_output_token: float = 0.0):
        self.name = name
        self.model = model
        self.max_tokens = max_tokens
        self.cost_per_input_token = cost_per_input_token
        self.cost_per_output_token = cost_per_output_token
        self.llm = None
        self.performance_metrics = {
            "total_requests": 0,
            "total_input_tokens": 0,
            "total_output_tokens": 0,
            "total_time": 0.0,
            "error_count": 0,
            "avg_latency": 0.0
        }
    
    async def initialize(self) -> bool:
        """Initialize the LLM provider."""
        raise NotImplementedError
    
    async def generate_response(self, messages: List[Dict[str, str]], 
                              temperature: float = 0.7,
                              max_tokens: Optional[int] = None) -> Optional[Dict[str, Any]]:
        """Generate response from messages."""
        raise NotImplementedError
    
    async def generate_structured_response(self, prompt: str, schema: Dict[str, Any],
                                         temperature: float = 0.3) -> Optional[Dict[str, Any]]:
        """Generate structured response following a schema."""
        raise NotImplementedError
    
    def update_metrics(self, input_tokens: int, output_tokens: int, 
                      latency: float, success: bool):
        """Update performance metrics."""
        self.performance_metrics["total_requests"] += 1
        self.performance_metrics["total_input_tokens"] += input_tokens
        self.performance_metrics["total_output_tokens"] += output_tokens
        self.performance_metrics["total_time"] += latency
        
        if not success:
            self.performance_metrics["error_count"] += 1
        
        # Update average latency
        if self.performance_metrics["total_requests"] > 0:
            self.performance_metrics["avg_latency"] = (
                self.performance_metrics["total_time"] / 
                self.performance_metrics["total_requests"]
            )
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get performance metrics."""
        return {
            **self.performance_metrics,
            "error_rate": (
                self.performance_metrics["error_count"] / 
                max(self.performance_metrics["total_requests"], 1)
            ),
            "cost_estimate": (
                self.performance_metrics["total_input_tokens"] * self.cost_per_input_token +
                self.performance_metrics["total_output_tokens"] * self.cost_per_output_token
            )
        }


class OpenAILLMProvider(LLMProvider):
    """OpenAI LLM provider."""
    
    def __init__(self, api_key: str, model: str = "gpt-3.5-turbo"):
        # Model configurations
        model_configs = {
            "gpt-3.5-turbo": {
                "max_tokens": 4096,
                "input_cost": 0.0015,  # $1.50 per 1M tokens
                "output_cost": 0.002   # $2.00 per 1M tokens
            },
            "gpt-4": {
                "max_tokens": 8192,
                "input_cost": 0.03,    # $30 per 1M tokens
                "output_cost": 0.06    # $60 per 1M tokens
            },
            "gpt-4-turbo": {
                "max_tokens": 128000,
                "input_cost": 0.01,    # $10 per 1M tokens
                "output_cost": 0.03    # $30 per 1M tokens
            }
        }
        
        config = model_configs.get(model, model_configs["gpt-3.5-turbo"])
        
        super().__init__(
            name="openai",
            model=model,
            max_tokens=config["max_tokens"],
            cost_per_input_token=config["input_cost"] / 1000000,
            cost_per_output_token=config["output_cost"] / 1000000
        )
        self.api_key = api_key
    
    async def initialize(self) -> bool:
        """Initialize OpenAI LLM."""
        try:
            if ChatOpenAI is None:
                raise ImportError("LangChain OpenAI not available")
            
            self.llm = ChatOpenAI(
                openai_api_key=self.api_key,
                model=self.model,
                temperature=0.7
            )
            
            # Test with a simple message
            test_messages = [HumanMessage(content="Hello")]
            response = await self.llm.ainvoke(test_messages)
            
            if response and hasattr(response, 'content'):
                return True
            
            return False
        except Exception as e:
            logging.error(f"Failed to initialize OpenAI LLM: {e}")
            return False
    
    async def generate_response(self, messages: List[Dict[str, str]], 
                              temperature: float = 0.7,
                              max_tokens: Optional[int] = None) -> Optional[Dict[str, Any]]:
        """Generate response using OpenAI."""
        if not self.llm:
            return None
        
        start_time = time.time()
        try:
            # Convert messages to LangChain format
            lc_messages = []
            for msg in messages:
                role = msg.get("role", "user")
                content = msg.get("content", "")
                
                if role == "system":
                    lc_messages.append(SystemMessage(content=content))
                elif role == "assistant":
                    lc_messages.append(AIMessage(content=content))
                else:
                    lc_messages.append(HumanMessage(content=content))
            
            # Update LLM parameters
            self.llm.temperature = temperature
            if max_tokens:
                self.llm.max_tokens = min(max_tokens, self.max_tokens)
            
            response = await self.llm.ainvoke(lc_messages)
            latency = time.time() - start_time
            
            # Estimate tokens (rough approximation)
            input_tokens = sum(len(msg.get("content", "").split()) * 1.3 for msg in messages)
            output_tokens = len(response.content.split()) * 1.3
            
            self.update_metrics(int(input_tokens), int(output_tokens), latency, True)
            
            return {
                "content": response.content,
                "model": self.model,
                "provider": self.name,
                "generation_time": latency,
                "estimated_tokens": {
                    "input": int(input_tokens),
                    "output": int(output_tokens)
                }
            }
        except Exception as e:
            latency = time.time() - start_time
            self.update_metrics(0, 0, latency, False)
            logging.error(f"OpenAI response generation failed: {e}")
            return None
    
    async def generate_structured_response(self, prompt: str, schema: Dict[str, Any],
                                         temperature: float = 0.3) -> Optional[Dict[str, Any]]:
        """Generate structured response following a schema."""
        if not self.llm:
            return None
        
        # Create structured prompt
        structured_prompt = f"""{prompt}

Please respond with a valid JSON object that follows this schema:
{json.dumps(schema, indent=2)}

Response:"""
        
        messages = [{"role": "user", "content": structured_prompt}]
        response = await self.generate_response(messages, temperature=temperature)
        
        if response:
            try:
                # Try to parse JSON from response
                content = response["content"].strip()
                if content.startswith("```json"):
                    content = content[7:-3].strip()
                elif content.startswith("```"):
                    content = content[3:-3].strip()
                
                parsed_data = json.loads(content)
                response["structured_data"] = parsed_data
                return response
            except json.JSONDecodeError:
                logging.warning("Failed to parse structured response as JSON")
                return response
        
        return None


class AnthropicLLMProvider(LLMProvider):
    """Anthropic Claude LLM provider."""
    
    def __init__(self, api_key: str, model: str = "claude-3-sonnet-20240229"):
        model_configs = {
            "claude-3-sonnet-20240229": {
                "max_tokens": 200000,
                "input_cost": 0.003,   # $3 per 1M tokens
                "output_cost": 0.015   # $15 per 1M tokens
            },
            "claude-3-haiku-20240307": {
                "max_tokens": 200000,
                "input_cost": 0.00025, # $0.25 per 1M tokens
                "output_cost": 0.00125 # $1.25 per 1M tokens
            }
        }
        
        config = model_configs.get(model, model_configs["claude-3-sonnet-20240229"])
        
        super().__init__(
            name="anthropic",
            model=model,
            max_tokens=config["max_tokens"],
            cost_per_input_token=config["input_cost"] / 1000000,
            cost_per_output_token=config["output_cost"] / 1000000
        )
        self.api_key = api_key
    
    async def initialize(self) -> bool:
        """Initialize Anthropic LLM."""
        try:
            if ChatAnthropic is None:
                raise ImportError("LangChain Anthropic not available")
            
            self.llm = ChatAnthropic(
                anthropic_api_key=self.api_key,
                model=self.model,
                temperature=0.7
            )
            
            # Test with a simple message
            test_messages = [HumanMessage(content="Hello")]
            response = await self.llm.ainvoke(test_messages)
            
            if response and hasattr(response, 'content'):
                return True
            
            return False
        except Exception as e:
            logging.error(f"Failed to initialize Anthropic LLM: {e}")
            return False
    
    async def generate_response(self, messages: List[Dict[str, str]], 
                              temperature: float = 0.7,
                              max_tokens: Optional[int] = None) -> Optional[Dict[str, Any]]:
        """Generate response using Anthropic."""
        if not self.llm:
            return None
        
        start_time = time.time()
        try:
            # Convert messages to LangChain format
            lc_messages = []
            for msg in messages:
                role = msg.get("role", "user")
                content = msg.get("content", "")
                
                if role == "system":
                    lc_messages.append(SystemMessage(content=content))
                elif role == "assistant":
                    lc_messages.append(AIMessage(content=content))
                else:
                    lc_messages.append(HumanMessage(content=content))
            
            # Update LLM parameters
            self.llm.temperature = temperature
            if max_tokens:
                self.llm.max_tokens = min(max_tokens, self.max_tokens)
            
            response = await self.llm.ainvoke(lc_messages)
            latency = time.time() - start_time
            
            # Estimate tokens
            input_tokens = sum(len(msg.get("content", "").split()) * 1.3 for msg in messages)
            output_tokens = len(response.content.split()) * 1.3
            
            self.update_metrics(int(input_tokens), int(output_tokens), latency, True)
            
            return {
                "content": response.content,
                "model": self.model,
                "provider": self.name,
                "generation_time": latency,
                "estimated_tokens": {
                    "input": int(input_tokens),
                    "output": int(output_tokens)
                }
            }
        except Exception as e:
            latency = time.time() - start_time
            self.update_metrics(0, 0, latency, False)
            logging.error(f"Anthropic response generation failed: {e}")
            return None
    
    async def generate_structured_response(self, prompt: str, schema: Dict[str, Any],
                                         temperature: float = 0.3) -> Optional[Dict[str, Any]]:
        """Generate structured response following a schema."""
        structured_prompt = f"""{prompt}

Please respond with a valid JSON object that follows this schema:
{json.dumps(schema, indent=2)}

Response:"""
        
        messages = [{"role": "user", "content": structured_prompt}]
        response = await self.generate_response(messages, temperature=temperature)
        
        if response:
            try:
                content = response["content"].strip()
                if content.startswith("```json"):
                    content = content[7:-3].strip()
                elif content.startswith("```"):
                    content = content[3:-3].strip()
                
                parsed_data = json.loads(content)
                response["structured_data"] = parsed_data
                return response
            except json.JSONDecodeError:
                logging.warning("Failed to parse structured response as JSON")
                return response
        
        return None


class LLMService:
    """Main LLM service with multi-provider support and intelligent routing."""
    
    def __init__(self):
        self.providers: Dict[str, LLMProvider] = {}
        self.default_provider = None
        self.routing_rules = {
            "code_generation": "openai",
            "code_analysis": "anthropic",
            "documentation": "anthropic",
            "reasoning": "anthropic",
            "quick_response": "openai",
            "default": "openai"
        }
        self.logger = logging.getLogger(__name__)
    
    async def initialize(self, config: Dict[str, Any]) -> bool:
        """Initialize LLM service with configuration.
        
        Args:
            config: {
                "providers": {
                    "openai": {"api_key": "...", "model": "..."},
                    "anthropic": {"api_key": "...", "model": "..."}
                },
                "default_provider": "openai",
                "routing_rules": {...}
            }
        """
        try:
            providers_config = config.get("providers", {})
            
            # Initialize OpenAI provider if configured
            if "openai" in providers_config:
                openai_config = providers_config["openai"]
                if "api_key" in openai_config:
                    provider = OpenAILLMProvider(
                        api_key=openai_config["api_key"],
                        model=openai_config.get("model", "gpt-3.5-turbo")
                    )
                    
                    if await provider.initialize():
                        self.providers["openai"] = provider
                        self.logger.info(f"OpenAI LLM provider initialized: {provider.model}")
                    else:
                        self.logger.error("Failed to initialize OpenAI LLM provider")
            
            # Initialize Anthropic provider if configured
            if "anthropic" in providers_config:
                anthropic_config = providers_config["anthropic"]
                if "api_key" in anthropic_config:
                    provider = AnthropicLLMProvider(
                        api_key=anthropic_config["api_key"],
                        model=anthropic_config.get("model", "claude-3-sonnet-20240229")
                    )
                    
                    if await provider.initialize():
                        self.providers["anthropic"] = provider
                        self.logger.info(f"Anthropic LLM provider initialized: {provider.model}")
                    else:
                        self.logger.error("Failed to initialize Anthropic LLM provider")
            
            # Set default provider
            default_name = config.get("default_provider", "openai")
            if default_name in self.providers:
                self.default_provider = self.providers[default_name]
            elif self.providers:
                self.default_provider = list(self.providers.values())[0]
            
            # Update routing rules
            if "routing_rules" in config:
                self.routing_rules.update(config["routing_rules"])
            
            if not self.providers:
                self.logger.error("No LLM providers initialized")
                return False
            
            self.logger.info(f"LLM service initialized with {len(self.providers)} providers")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize LLM service: {e}")
            return False
    
    def get_provider_for_task(self, task_type: str) -> Optional[LLMProvider]:
        """Get the best provider for given task type."""
        # Check routing rules
        provider_name = self.routing_rules.get(task_type, self.routing_rules.get("default"))
        
        if provider_name in self.providers:
            provider = self.providers[provider_name]
            
            # Check if provider is healthy (low error rate)
            metrics = provider.get_metrics()
            if metrics["error_rate"] < 0.1:  # Less than 10% error rate
                return provider
        
        # Fallback to default provider
        return self.default_provider
    
    async def generate_response(self, messages: List[Dict[str, str]], 
                              model: Optional[str] = None,
                              task_type: str = "default",
                              temperature: float = 0.7,
                              max_tokens: Optional[int] = None) -> Optional[Dict[str, Any]]:
        """Generate response from messages.
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            model: Specific model to use (optional)
            task_type: Type of task for routing
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
        
        Returns:
            {
                "content": str,
                "model": str,
                "provider": str,
                "generation_time": float,
                "estimated_tokens": {...}
            }
        """
        if not messages:
            return None
        
        # Select provider
        provider = None
        if model:
            # Find provider with specific model
            for p in self.providers.values():
                if p.model == model:
                    provider = p
                    break
        
        if not provider:
            provider = self.get_provider_for_task(task_type)
        
        if not provider:
            self.logger.error("No suitable LLM provider available")
            return None
        
        return await provider.generate_response(messages, temperature, max_tokens)
    
    async def generate_structured_response(self, prompt: str, schema: Dict[str, Any],
                                         model: Optional[str] = None,
                                         task_type: str = "default",
                                         temperature: float = 0.3) -> Optional[Dict[str, Any]]:
        """Generate structured response following a schema."""
        # Select provider
        provider = None
        if model:
            for p in self.providers.values():
                if p.model == model:
                    provider = p
                    break
        
        if not provider:
            provider = self.get_provider_for_task(task_type)
        
        if not provider:
            return None
        
        return await provider.generate_structured_response(prompt, schema, temperature)
    
    async def get_status(self) -> Dict[str, Any]:
        """Get service status and metrics."""
        status = {
            "providers": {},
            "default_provider": self.default_provider.name if self.default_provider else None,
            "routing_rules": self.routing_rules,
            "total_providers": len(self.providers)
        }
        
        for name, provider in self.providers.items():
            status["providers"][name] = {
                "model": provider.model,
                "max_tokens": provider.max_tokens,
                "metrics": provider.get_metrics()
            }
        
        return status
    
    def get_available_models(self) -> List[Dict[str, Any]]:
        """Get list of available models."""
        models = []
        for provider in self.providers.values():
            models.append({
                "provider": provider.name,
                "model": provider.model,
                "max_tokens": provider.max_tokens,
                "cost_per_input_token": provider.cost_per_input_token,
                "cost_per_output_token": provider.cost_per_output_token
            })
        return models