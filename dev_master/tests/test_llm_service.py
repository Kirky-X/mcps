"""LLM Service tests for MCP DevAgent.

Tests LLM interaction, multi-provider support, and intelligent routing.
"""

import asyncio
import json
import os
import tempfile
import unittest
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, Any

from src.mcp_devagent.services.llm_service import (
    LLMService, LLMProvider, OpenAILLMProvider, AnthropicLLMProvider
)


class TestLLMProvider(unittest.TestCase):
    """Test base LLMProvider functionality."""
    
    def test_llm_provider_initialization_and_metrics(self):
        """Test LLMProvider initialization and metrics update."""
        provider = LLMProvider("test-provider", "test-model")
        
        # Test initialization
        assert provider.name == "test-provider"
        assert provider.model == "test-model"
        assert provider.performance_metrics["total_requests"] == 0
        assert provider.performance_metrics["error_count"] == 0
        assert provider.performance_metrics["total_input_tokens"] == 0
        assert provider.performance_metrics["total_output_tokens"] == 0
        
        # Test metrics update
        provider.update_metrics(input_tokens=50, output_tokens=50, latency=1.0, success=True)
        
        assert provider.performance_metrics["total_requests"] == 1
        assert provider.performance_metrics["error_count"] == 0
        assert provider.performance_metrics["total_input_tokens"] == 50
        assert provider.performance_metrics["total_output_tokens"] == 50
        
        # Update with failure
        provider.update_metrics(input_tokens=25, output_tokens=25, latency=1.2, success=False)
        
        assert provider.performance_metrics["total_requests"] == 2
        assert provider.performance_metrics["error_count"] == 1
        assert provider.performance_metrics["total_input_tokens"] == 75
        assert provider.performance_metrics["total_output_tokens"] == 75
    
    def test_provider_status(self):
        """Test provider status reporting."""
        provider = LLMProvider("test_provider", "test_model")
        
        # Test metrics
        metrics = provider.get_metrics()
        self.assertIn("total_requests", metrics)
        self.assertIn("error_rate", metrics)
        self.assertIn("cost_estimate", metrics)
        
        # Test metrics update
        provider.update_metrics(input_tokens=100, output_tokens=50, latency=1.5, success=True)
        updated_metrics = provider.get_metrics()
        self.assertEqual(updated_metrics["total_requests"], 1)
        self.assertEqual(updated_metrics["error_rate"], 0.0)


class TestOpenAILLMProvider(unittest.TestCase):
    """Test OpenAI LLM provider."""
    
    def setUp(self):
        """Set up OpenAI provider for testing."""
        self.config = {
            "api_key": "test_openai_key",
            "model": "gpt-4",
            "max_tokens": 4096,
            "temperature": 0.7
        }
        self.provider = OpenAILLMProvider(self.config)
    
    def test_openai_provider_initialization(self):
        """Test OpenAI provider initialization."""
        provider = OpenAILLMProvider(
            api_key=self.config["api_key"],
            model=self.config["model"]
        )
        
        self.assertEqual(provider.name, "openai")
        self.assertEqual(provider.model, self.config["model"])
        self.assertEqual(provider.api_key, self.config["api_key"])
        self.assertIsNone(provider.llm)  # Not initialized yet
    
    @patch('openai.AsyncOpenAI')
    async def test_openai_initialize(self, mock_openai):
        """Test OpenAI provider initialization."""
        # Mock OpenAI client
        mock_client = MagicMock()
        mock_openai.return_value = mock_client
        
        await self.provider.initialize()
        
        self.assertTrue(self.provider.is_available)
        mock_openai.assert_called_once_with(api_key="test_openai_key")
    
    @patch('openai.AsyncOpenAI')
    async def test_openai_generate_response(self, mock_openai):
        """Test OpenAI response generation."""
        # Mock OpenAI client and response
        mock_client = MagicMock()
        mock_openai.return_value = mock_client
        
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Generated response"
        mock_response.usage.total_tokens = 50
        
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
        
        await self.provider.initialize()
        
        messages = [{"role": "user", "content": "Test prompt"}]
        result = await self.provider.generate_response(messages)
        
        self.assertEqual(result["content"], "Generated response")
        self.assertEqual(result["tokens_used"], 50)
        self.assertEqual(result["provider"], "openai")
        self.assertIn("latency", result)
        
        # Verify API call
        mock_client.chat.completions.create.assert_called_once_with(
            model="gpt-4",
            messages=messages,
            max_tokens=4096,
            temperature=0.7
        )
    
    @patch('openai.AsyncOpenAI')
    async def test_openai_structured_response(self, mock_openai):
        """Test OpenAI structured response generation."""
        # Mock OpenAI client and response
        mock_client = MagicMock()
        mock_openai.return_value = mock_client
        
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = '{"key": "value"}'
        mock_response.usage.total_tokens = 30
        
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
        
        await self.provider.initialize()
        
        messages = [{"role": "user", "content": "Generate JSON"}]
        schema = {"type": "object", "properties": {"key": {"type": "string"}}}
        
        result = await self.provider.generate_structured_response(messages, schema)
        
        self.assertEqual(result["content"], {"key": "value"})
        self.assertEqual(result["tokens_used"], 30)
        self.assertEqual(result["provider"], "openai")
    
    @patch('openai.AsyncOpenAI')
    async def test_openai_error_handling(self, mock_openai):
        """Test OpenAI error handling."""
        # Mock OpenAI client that raises an exception
        mock_client = MagicMock()
        mock_openai.return_value = mock_client
        
        mock_client.chat.completions.create = AsyncMock(side_effect=Exception("API Error"))
        
        await self.provider.initialize()
        
        messages = [{"role": "user", "content": "Test prompt"}]
        result = await self.provider.generate_response(messages)
        
        self.assertIsNone(result)


class TestAnthropicLLMProvider(unittest.TestCase):
    """Test Anthropic LLM provider."""
    
    def setUp(self):
        """Set up Anthropic provider for testing."""
        self.config = {
            "api_key": "test_anthropic_key",
            "model": "claude-3-sonnet-20240229",
            "max_tokens": 4096,
            "temperature": 0.7
        }
        self.provider = AnthropicLLMProvider(self.config)
    
    def test_anthropic_provider_initialization(self):
        """Test Anthropic provider initialization."""
        provider = AnthropicLLMProvider(
            api_key=self.config["api_key"],
            model=self.config["model"]
        )
        
        self.assertEqual(provider.name, "anthropic")
        self.assertEqual(provider.model, self.config["model"])
        self.assertEqual(provider.api_key, self.config["api_key"])
        self.assertIsNone(provider.llm)  # Not initialized yet
    
    @patch('anthropic.AsyncAnthropic')
    async def test_anthropic_initialize(self, mock_anthropic):
        """Test Anthropic provider initialization."""
        # Mock Anthropic client
        mock_client = MagicMock()
        mock_anthropic.return_value = mock_client
        
        await self.provider.initialize()
        
        self.assertTrue(self.provider.is_available)
        mock_anthropic.assert_called_once_with(api_key="test_anthropic_key")
    
    @patch('anthropic.AsyncAnthropic')
    async def test_anthropic_generate_response(self, mock_anthropic):
        """Test Anthropic response generation."""
        # Mock Anthropic client and response
        mock_client = MagicMock()
        mock_anthropic.return_value = mock_client
        
        mock_response = MagicMock()
        mock_response.content = [MagicMock()]
        mock_response.content[0].text = "Generated response"
        mock_response.usage.output_tokens = 30
        mock_response.usage.input_tokens = 20
        
        mock_client.messages.create = AsyncMock(return_value=mock_response)
        
        await self.provider.initialize()
        
        messages = [{"role": "user", "content": "Test prompt"}]
        result = await self.provider.generate_response(messages)
        
        self.assertEqual(result["content"], "Generated response")
        self.assertEqual(result["tokens_used"], 50)  # input + output
        self.assertEqual(result["provider"], "anthropic")
        self.assertIn("latency", result)
    
    @patch('anthropic.AsyncAnthropic')
    async def test_anthropic_structured_response(self, mock_anthropic):
        """Test Anthropic structured response generation."""
        # Mock Anthropic client and response
        mock_client = MagicMock()
        mock_anthropic.return_value = mock_client
        
        mock_response = MagicMock()
        mock_response.content = [MagicMock()]
        mock_response.content[0].text = '{"analysis": "complete"}'
        mock_response.usage.output_tokens = 20
        mock_response.usage.input_tokens = 15
        
        mock_client.messages.create = AsyncMock(return_value=mock_response)
        
        await self.provider.initialize()
        
        messages = [{"role": "user", "content": "Analyze code"}]
        schema = {"type": "object", "properties": {"analysis": {"type": "string"}}}
        
        result = await self.provider.generate_structured_response(messages, schema)
        
        self.assertEqual(result["content"], {"analysis": "complete"})
        self.assertEqual(result["tokens_used"], 35)
        self.assertEqual(result["provider"], "anthropic")


class TestLLMService(unittest.TestCase):
    """Test LLMService functionality."""
    
    def setUp(self):
        """Set up LLM service for testing."""
        # Mock providers configuration
        self.providers_config = {
            "openai": {
                "api_key": "test_openai_key",
                "model": "gpt-4",
                "max_tokens": 4096
            },
            "anthropic": {
                "api_key": "test_anthropic_key",
                "model": "claude-3-sonnet-20240229",
                "max_tokens": 4096
            }
        }
        
        self.service = LLMService()
    
    def test_service_initialization(self):
        """Test LLM service initialization."""
        # Initially no providers
        self.assertEqual(len(self.service.providers), 0)
        self.assertIsNone(self.service.default_provider)
        
        # Test routing rules are set
        self.assertIn("code_generation", self.service.routing_rules)
        self.assertIn("default", self.service.routing_rules)
    
    @patch.object(OpenAILLMProvider, 'initialize')
    @patch.object(AnthropicLLMProvider, 'initialize')
    async def test_service_initialize(self, mock_anthropic_init, mock_openai_init):
        """Test service initialization."""
        # Mock provider initialization to return True
        mock_openai_init.return_value = True
        mock_anthropic_init.return_value = True
        
        # Initialize service with config
        config = {
            "providers": self.providers_config,
            "default_provider": "openai"
        }
        
        result = await self.service.initialize(config)
        
        self.assertTrue(result)
        self.assertEqual(len(self.service.providers), 2)
        self.assertIn("openai", self.service.providers)
        self.assertIn("anthropic", self.service.providers)
        mock_openai_init.assert_called_once()
        mock_anthropic_init.assert_called_once()
    
    async def test_provider_selection_default(self):
        """Test default provider selection."""
        # Initialize service first
        config = {
            "providers": self.providers_config,
            "default_provider": "openai"
        }
        
        with patch.object(OpenAILLMProvider, 'initialize', return_value=True), \
             patch.object(AnthropicLLMProvider, 'initialize', return_value=True):
            await self.service.initialize(config)
        
        provider = self.service.get_provider_for_task("code_generation")
        self.assertEqual(provider.name, "openai")
    
    async def test_provider_selection_fallback(self):
        """Test provider selection with fallback."""
        # Initialize service first
        config = {
            "providers": self.providers_config,
            "default_provider": "openai"
        }
        
        with patch.object(OpenAILLMProvider, 'initialize', return_value=True), \
             patch.object(AnthropicLLMProvider, 'initialize', return_value=True):
            await self.service.initialize(config)
        
        # Test fallback to default when specific provider not available
        provider = self.service.get_provider_for_task("unknown_task")
        self.assertIsNotNone(provider)  # Should fallback to default
    
    async def test_provider_selection_by_task_type(self):
        """Test provider selection based on task type."""
        # Initialize service first
        config = {
            "providers": self.providers_config,
            "default_provider": "openai"
        }
        
        with patch.object(OpenAILLMProvider, 'initialize', return_value=True), \
             patch.object(AnthropicLLMProvider, 'initialize', return_value=True):
            await self.service.initialize(config)
        
        # Test different task types
        code_provider = self.service.get_provider_for_task("code_generation")
        analysis_provider = self.service.get_provider_for_task("code_analysis")
        
        # Should return providers based on routing rules
        self.assertEqual(code_provider.name, "openai")  # routing rule: code_generation -> openai
        self.assertEqual(analysis_provider.name, "anthropic")  # routing rule: code_analysis -> anthropic
    
    @patch.object(OpenAILLMProvider, 'generate_response')
    async def test_generate_response(self, mock_generate):
        """Test response generation."""
        # Initialize service first
        config = {
            "providers": self.providers_config,
            "default_provider": "openai"
        }
        
        with patch.object(OpenAILLMProvider, 'initialize', return_value=True), \
             patch.object(AnthropicLLMProvider, 'initialize', return_value=True):
            await self.service.initialize(config)
        
        # Mock provider response
        mock_generate.return_value = {
            "content": "Generated response",
            "tokens_used": 50,
            "provider": "openai",
            "latency": 0.5
        }
        
        messages = [{"role": "user", "content": "Test prompt"}]
        result = await self.service.generate_response(messages, "code_generation")
        
        self.assertEqual(result["content"], "Generated response")
        self.assertEqual(result["provider"], "openai")
        self.assertEqual(result["tokens_used"], 50)
        
        mock_generate.assert_called_once_with(messages)
    
    @patch.object(OpenAILLMProvider, 'generate_structured_response')
    async def test_generate_structured_response(self, mock_generate_structured):
        """Test structured response generation."""
        # Initialize service first
        config = {
            "providers": self.providers_config,
            "default_provider": "openai"
        }
        
        with patch.object(OpenAILLMProvider, 'initialize', return_value=True), \
             patch.object(AnthropicLLMProvider, 'initialize', return_value=True):
            await self.service.initialize(config)
        
        # Mock provider response
        mock_generate_structured.return_value = {
            "content": {"analysis": "complete", "score": 0.95},
            "tokens_used": 75,
            "provider": "openai",
            "latency": 0.8
        }
        
        messages = [{"role": "user", "content": "Analyze this code"}]
        schema = {
            "type": "object",
            "properties": {
                "analysis": {"type": "string"},
                "score": {"type": "number"}
            }
        }
        
        result = await self.service.generate_structured_response(
            messages, schema, "code_analysis"
        )
        
        self.assertEqual(result["content"]["analysis"], "complete")
        self.assertEqual(result["content"]["score"], 0.95)
        self.assertEqual(result["provider"], "openai")
        
        mock_generate_structured.assert_called_once_with(messages, schema)
    
    async def test_no_available_providers(self):
        """Test behavior when no providers are available."""
        # Initialize service first
        config = {
            "providers": self.providers_config,
            "default_provider": "openai"
        }
        
        with patch.object(OpenAILLMProvider, 'initialize', return_value=True), \
             patch.object(AnthropicLLMProvider, 'initialize', return_value=True):
            await self.service.initialize(config)
        
        # Set all providers as unavailable
        for provider in self.service.providers.values():
            provider.is_available = False
        
        messages = [{"role": "user", "content": "Test prompt"}]
        result = await self.service.generate_response(messages, "code_generation")
        
        self.assertIsNone(result)
    
    async def test_get_status(self):
        """Test service status reporting."""
        # Initialize service first
        config = {
            "providers": self.providers_config,
            "default_provider": "openai"
        }
        
        with patch.object(OpenAILLMProvider, 'initialize', return_value=True), \
             patch.object(AnthropicLLMProvider, 'initialize', return_value=True):
            await self.service.initialize(config)
        
        # Set provider statuses
        self.service.providers["openai"].is_available = True
        self.service.providers["openai"].update_metrics(100, 0.5)
        
        self.service.providers["anthropic"].is_available = False
        
        status = self.service.get_status()
        
        self.assertEqual(status["total_providers"], 2)
        self.assertEqual(status["available_providers"], 1)
        self.assertEqual(status["default_provider"], "openai")
        self.assertTrue(status["intelligent_routing"])
        
        # Check provider details
        self.assertEqual(len(status["providers"]), 2)
        openai_status = next(p for p in status["providers"] if p["name"] == "openai")
        self.assertTrue(openai_status["available"])
        self.assertEqual(openai_status["total_requests"], 1)
    
    @patch.object(OpenAILLMProvider, 'generate_response')
    async def test_error_handling_with_fallback(self, mock_generate):
        """Test error handling with provider fallback."""
        # Initialize service first
        config = {
            "providers": self.providers_config,
            "default_provider": "openai"
        }
        
        with patch.object(OpenAILLMProvider, 'initialize', return_value=True), \
             patch.object(AnthropicLLMProvider, 'initialize', return_value=True):
            await self.service.initialize(config)
        
        # Mock OpenAI to fail, then succeed on retry
        mock_generate.side_effect = [None, {
            "content": "Fallback response",
            "provider": "anthropic",
            "tokens_used": 40,
            "latency": 0.6
        }]
        
        # Set both providers as available
        self.service.providers["openai"].is_available = True
        self.service.providers["anthropic"].is_available = True
        
        with patch.object(self.service.providers["anthropic"], 'generate_response') as mock_anthropic_generate:
            mock_anthropic_generate.return_value = {
                "content": "Fallback response",
                "provider": "anthropic",
                "tokens_used": 40,
                "latency": 0.6
            }
            
            messages = [{"role": "user", "content": "Test prompt"}]
            result = await self.service.generate_response(messages, "code_generation")
            
            # Should fallback to Anthropic
            self.assertEqual(result["provider"], "anthropic")
            self.assertEqual(result["content"], "Fallback response")
            mock_anthropic_generate.assert_called_once()
    
    async def test_task_type_routing(self):
        """Test intelligent routing based on task type."""
        # Initialize service first
        config = {
            "providers": self.providers_config,
            "default_provider": "openai"
        }
        
        with patch.object(OpenAILLMProvider, 'initialize', return_value=True), \
             patch.object(AnthropicLLMProvider, 'initialize', return_value=True):
            await self.service.initialize(config)
        
        # Set both providers as available with different performance characteristics
        self.service.providers["openai"].is_available = True
        self.service.providers["anthropic"].is_available = True
        
        # Simulate different performance for different tasks
        self.service.providers["openai"].avg_latency = 0.5
        self.service.providers["anthropic"].avg_latency = 0.8
        
        # Enable intelligent routing
        self.service.intelligent_routing = True
        
        # Test routing for different task types
        code_provider = self.service.get_provider_for_task("code_generation")
        analysis_provider = self.service.get_provider_for_task("code_analysis")
        
        # Should return providers based on routing rules
        self.assertEqual(code_provider.name, "openai")
        self.assertEqual(analysis_provider.name, "anthropic")


class TestLLMServiceIntegration(unittest.TestCase):
    """Integration tests for LLM service."""
    
    def setUp(self):
        """Set up integration test environment."""
        # Create service with mock providers
        self.providers_config = {
            "mock_provider": {
                "model": "mock_model"
            }
        }
        
        self.service = LLMService()
    
    async def test_end_to_end_workflow(self):
        """Test complete end-to-end workflow."""
        # Initialize service first
        config = {
            "providers": {
                "openai": {
                    "api_key": "test_openai_key",
                    "model": "gpt-4",
                    "max_tokens": 4096
                },
                "anthropic": {
                    "api_key": "test_anthropic_key",
                    "model": "claude-3-sonnet-20240229",
                    "max_tokens": 4096
                }
            },
            "default_provider": "openai"
        }
        
        with patch.object(OpenAILLMProvider, 'initialize', return_value=True), \
             patch.object(AnthropicLLMProvider, 'initialize', return_value=True):
            await self.service.initialize(config)
        
        # Set provider as available
        self.service.providers["openai"].is_available = True
        
        with patch.object(self.service.providers["openai"], 'generate_response') as mock_generate:
            mock_generate.return_value = {
                "content": "Generated code",
                "provider": "openai",
                "tokens_used": 50,
                "latency": 0.8
            }
            
            messages = [{"role": "user", "content": "Generate a function"}]
            result = await self.service.generate_response(messages, "code_generation")
            
            self.assertIsNotNone(result)
            self.assertEqual(result["content"], "Generated code")
            self.assertEqual(result["provider"], "openai")
            mock_generate.assert_called_once()
    
    def run_async_test(self, coro):
        """Helper to run async tests."""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(coro)
        finally:
            loop.close()


if __name__ == '__main__':
    # Configure logging for tests
    import logging
    logging.basicConfig(level=logging.INFO)
    
    # Run tests
    unittest.main(verbosity=2)