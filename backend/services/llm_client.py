"""
Unified LLM Client with Rate Limiting, Model Fallback, and Streaming Support
Handles Gemini primary with OpenRouter fallback for all modules
"""

import os
import json
import time
import asyncio
import logging
from typing import AsyncGenerator, Dict, Any, Optional, Union
from enum import Enum
import aiohttp
import litellm
from litellm import acompletion, get_supported_openai_params

logger = logging.getLogger(__name__)

class ModelType(Enum):
    HIGH_REASONING = "high_reasoning"  # For Mock Tests, Interviews
    FAST_CHEAP = "fast_cheap"  # For English Drills, Grammar checks

class LLMProvider(Enum):
    GEMINI = "gemini"
    OPENROUTER = "openrouter"

class LLMClient:
    """Unified LLM client with automatic fallback and rate limiting"""
    
    def __init__(self):
        # API Keys
        self.gemini_key = os.getenv("GOOGLE_API_KEY")
        self.openrouter_key = os.getenv("OPENROUTER_API_KEY")
        self.hf_token = os.getenv("HF_TOKEN")
        
        # Configurable timeout settings
        self.default_timeout = int(os.getenv("LLM_DEFAULT_TIMEOUT", "60"))
        self.max_timeout = int(os.getenv("LLM_MAX_TIMEOUT", "120"))
        
        # Configure litellm
        litellm.set_verbose = "DEBUG"
        litellm.drop_params = True
        
        # Rate limiting configuration
        self.rate_limits = {
            LLMProvider.GEMINI: {
                "requests_per_minute": 60,
                "tokens_per_minute": 32000,
                "last_request_time": 0,
                "request_count": 0,
                "tokens_used": 0,
                "window_start": time.time()
            },
            LLMProvider.OPENROUTER: {
                "requests_per_minute": 200,
                "tokens_per_minute": 40000,
                "last_request_time": 0,
                "request_count": 0,
                "tokens_used": 0,
                "window_start": time.time()
            }
        }
        
        # Model configuration
        self.model_configs = {
            ModelType.HIGH_REASONING: {
                LLMProvider.GEMINI: "gemini-1.5-pro",
                LLMProvider.OPENROUTER: "anthropic/claude-3-sonnet"
            },
            ModelType.FAST_CHEAP: {
                LLMProvider.GEMINI: "gemini-1.5-flash",
                LLMProvider.OPENROUTER: "meta-llama/llama-3.1-8b-instruct"
            }
        }
        
        # Current provider state
        self.current_provider = LLMProvider.GEMINI
        self.provider_errors = {
            LLMProvider.GEMINI: 0,
            LLMProvider.OPENROUTER: 0
        }
        
        # Circuit breaker configuration
        self.circuit_breaker_threshold = 3
        self.circuit_breaker_timeout = 300  # 5 minutes

    def _check_rate_limit(self, provider: LLMProvider) -> bool:
        """Check if we're within rate limits for a provider"""
        current_time = time.time()
        limits = self.rate_limits[provider]
        
        # Reset window if needed
        if current_time - limits["window_start"] > 60:
            limits["window_start"] = current_time
            limits["request_count"] = 0
            limits["tokens_used"] = 0
        
        # Check rate limits
        if limits["request_count"] >= limits["requests_per_minute"]:
            logger.warning(f"Rate limit exceeded for {provider.value}")
            return False
            
        if limits["tokens_used"] >= limits["tokens_per_minute"]:
            logger.warning(f"Token limit exceeded for {provider.value}")
            return False
            
        return True

    def _update_rate_limit(self, provider: LLMProvider, tokens_used: int):
        """Update rate limit counters"""
        limits = self.rate_limits[provider]
        limits["request_count"] += 1
        limits["tokens_used"] += tokens_used
        limits["last_request_time"] = time.time()

    def _should_use_fallback(self, error: Exception) -> bool:
        """Determine if we should fallback to secondary provider"""
        error_str = str(error).lower()
        
        # Rate limit errors
        if "429" in error_str or "rate limit" in error_str:
            return True
            
        # Server errors
        if "5" in error_str and "error" in error_str:
            return True
            
        # Authentication errors
        if "401" in error_str or "403" in error_str:
            return True
            
        # Timeout errors
        if "timeout" in error_str:
            return True
            
        # Circuit breaker
        if self.provider_errors[self.current_provider] >= self.circuit_breaker_threshold:
            return True
            
        return False

    def _get_model_for_type(self, model_type: ModelType, provider: LLMProvider) -> str:
        """Get the appropriate model for a given type and provider"""
        return self.model_configs[model_type][provider]

    async def _make_request(
        self,
        model_type: ModelType,
        messages: list,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        stream: bool = False,
        **kwargs
    ) -> Union[Dict[str, Any], AsyncGenerator]:
        """Make LLM request with automatic fallback"""
        
        # Try current provider first
        for attempt in range(2):  # Try up to 2 providers
            provider = self.current_provider if attempt == 0 else (
                LLMProvider.OPENROUTER if self.current_provider == LLMProvider.GEMINI else LLMProvider.GEMINI
            )
            
            # Skip if provider is in circuit breaker
            if self.provider_errors[provider] >= self.circuit_breaker_threshold:
                logger.warning(f"Provider {provider.value} is in circuit breaker, skipping")
                continue
                
            # Check rate limits
            if not self._check_rate_limit(provider):
                logger.warning(f"Rate limit exceeded for {provider.value}")
                continue
                
            try:
                model = self._get_model_for_type(model_type, provider)
                
                # Prepare request
                request_params = {
                    "model": model,
                    "messages": messages,
                    "temperature": temperature,
                    "stream": stream,
                    "timeout": min(self.default_timeout, self.max_timeout),  # Use configurable timeout
                    **kwargs
                }
                
                if max_tokens:
                    request_params["max_tokens"] = max_tokens
                
                # Add API key based on provider with validation
                if provider == LLMProvider.GEMINI:
                    if not self.gemini_key:
                        logger.error("Gemini API key not configured")
                        raise ValueError("Gemini API key not available")
                    request_params["api_key"] = self.gemini_key
                else:
                    # Validate OpenRouter API key before fallback
                    if not self.openrouter_key:
                        logger.error("OpenRouter API key not configured for fallback")
                        raise ValueError("OpenRouter API key not available for fallback")
                    
                    # Basic OpenRouter API key validation
                    if len(self.openrouter_key) < 20 or not self.openrouter_key.startswith('sk-or-v1'):
                        logger.error("Invalid OpenRouter API key format")
                        raise ValueError("Invalid OpenRouter API key format")
                    
                    request_params["api_key"] = self.openrouter_key
                
                logger.info(f"Making request to {provider.value} with model {model}")
                
                # Make request
                response = await acompletion(**request_params)
                
                # Update rate limits
                tokens_used = response.usage.total_tokens if hasattr(response, 'usage') else 1000
                self._update_rate_limit(provider, tokens_used)
                
                # Reset error count on success
                self.provider_errors[provider] = 0
                self.current_provider = provider
                
                if stream:
                    return self._stream_response(response)
                else:
                    return response
                    
            except Exception as e:
                logger.error(f"Error with {provider.value}: {str(e)}")
                self.provider_errors[provider] += 1
                
                if self._should_use_fallback(e) and attempt == 0:
                    logger.info(f"Falling back to secondary provider")
                    continue
                else:
                    raise e
                    
        raise Exception("All LLM providers failed")

    async def _stream_response(self, response) -> AsyncGenerator[str, None]:
        """Handle streaming response"""
        async for chunk in response:
            if chunk.choices and len(chunk.choices) > 0:
                delta = chunk.choices[0].delta
                if hasattr(delta, 'content') and delta.content:
                    yield delta.content

    async def generate_response(
        self,
        model_type: ModelType,
        messages: list,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Generate non-streaming response"""
        return await self._make_request(
            model_type=model_type,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=False,
            **kwargs
        )

    async def generate_streaming_response(
        self,
        model_type: ModelType,
        messages: list,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> AsyncGenerator[str, None]:
        """Generate streaming response"""
        return await self._make_request(
            model_type=model_type,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=True,
            **kwargs
        )

    async def generate_with_context(
        self,
        model_type: ModelType,
        messages: list,
        context: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Generate response with optional context (RAG)"""
        if context:
            # Add context to system message
            system_message = {
                "role": "system",
                "content": f"Use the following context to inform your response:\n\n{context}\n\nBased on this context, answer the user's query."
            }
            messages = [system_message] + messages
            
        return await self.generate_response(
            model_type=model_type,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs
        )

    def get_provider_status(self) -> Dict[str, Any]:
        """Get current provider status for monitoring"""
        return {
            "current_provider": self.current_provider.value,
            "provider_errors": {k.value: v for k, v in self.provider_errors.items()},
            "rate_limits": {
                k.value: {
                    "requests_per_minute": v["requests_per_minute"],
                    "current_requests": v["request_count"],
                    "tokens_per_minute": v["tokens_per_minute"],
                    "current_tokens": v["tokens_used"]
                } for k, v in self.rate_limits.items()
            }
        }

# Global instance
llm_client = LLMClient()

# Helper functions for different use cases
async def generate_mock_test_response(
    messages: list,
    context: Optional[str] = None,
    **kwargs
) -> Dict[str, Any]:
    """Generate response for mock tests using high-reasoning models"""
    return await llm_client.generate_with_context(
        model_type=ModelType.HIGH_REASONING,
        messages=messages,
        context=context,
        **kwargs
    )

async def generate_interview_response(
    messages: list,
    context: Optional[str] = None,
    **kwargs
) -> Dict[str, Any]:
    """Generate response for interviews using high-reasoning models"""
    return await llm_client.generate_with_context(
        model_type=ModelType.HIGH_REASONING,
        messages=messages,
        context=context,
        **kwargs
    )

async def generate_english_response(
    messages: list,
    context: Optional[str] = None,
    stream: bool = False,
    **kwargs
) -> Union[Dict[str, Any], AsyncGenerator]:
    """Generate response for English drills using fast models"""
    if stream:
        return await llm_client.generate_streaming_response(
            model_type=ModelType.FAST_CHEAP,
            messages=messages,
            **kwargs
        )
    else:
        return await llm_client.generate_with_context(
            model_type=ModelType.FAST_CHEAP,
            messages=messages,
            context=context,
            **kwargs
        )
