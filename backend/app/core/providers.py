"""
ClosedPaw - Multi-Provider LLM Gateway
Supports Ollama, OpenAI, Anthropic, Google, Mistral, and custom endpoints
"""

import logging
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime

import httpx

logger = logging.getLogger(__name__)


class ProviderType(str, Enum):
    """Supported LLM provider types"""
    OLLAMA = "ollama"
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"
    MISTRAL = "mistral"
    CUSTOM = "custom"


@dataclass
class ProviderConfig:
    """Configuration for a provider"""
    provider_type: ProviderType
    name: str
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    models: List[str] = field(default_factory=list)
    default_model: Optional[str] = None
    enabled: bool = True
    rate_limit: int = 60  # requests per minute
    timeout: int = 60
    
    # Provider-specific settings
    settings: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ChatMessage:
    """Chat message structure"""
    role: str  # system, user, assistant
    content: str
    
    def to_dict(self) -> Dict[str, str]:
        return {"role": self.role, "content": self.content}


@dataclass
class ChatResponse:
    """Response from chat completion"""
    content: str
    model: str
    provider: str
    tokens_used: Optional[int] = None
    finish_reason: Optional[str] = None
    latency_ms: Optional[int] = None


class BaseProvider(ABC):
    """Abstract base class for LLM providers"""
    
    def __init__(self, config: ProviderConfig):
        self.config = config
        self.client = httpx.AsyncClient(timeout=config.timeout)
        self._request_count = 0
        self._last_request_time = datetime.utcnow()
    
    @abstractmethod
    async def chat(
        self, 
        messages: List[ChatMessage], 
        model: Optional[str] = None,
        **kwargs
    ) -> ChatResponse:
        """Send chat completion request"""
        pass
    
    @abstractmethod
    async def list_models(self) -> List[str]:
        """List available models"""
        pass
    
    @abstractmethod
    async def health_check(self) -> bool:
        """Check if provider is healthy"""
        pass
    
    async def close(self):
        """Close HTTP client"""
        await self.client.aclose()


class OllamaProvider(BaseProvider):
    """Ollama local LLM provider"""
    
    def __init__(self, config: ProviderConfig):
        config.base_url = config.base_url or "http://127.0.0.1:11434"
        super().__init__(config)
    
    async def chat(
        self, 
        messages: List[ChatMessage], 
        model: Optional[str] = None,
        **kwargs
    ) -> ChatResponse:
        model = model or self.config.default_model or "llama3.2:3b"
        start_time = datetime.utcnow()
        
        # Convert messages to Ollama format
        prompt = "\n".join([f"{m.role}: {m.content}" for m in messages])
        
        response = await self.client.post(
            f"{self.config.base_url}/api/generate",
            json={
                "model": model,
                "prompt": prompt,
                "stream": False,
                **kwargs
            }
        )
        
        if response.status_code != 200:
            raise Exception(f"Ollama error: {response.status_code}")
        
        data = response.json()
        latency = (datetime.utcnow() - start_time).total_seconds() * 1000
        
        return ChatResponse(
            content=data.get("response", ""),
            model=model,
            provider="ollama",
            tokens_used=data.get("eval_count"),
            latency_ms=int(latency)
        )
    
    async def list_models(self) -> List[str]:
        try:
            response = await self.client.get(f"{self.config.base_url}/api/tags")
            if response.status_code == 200:
                models = response.json().get("models", [])
                return [m.get("name") for m in models]
        except Exception as e:
            logger.error(f"Failed to list Ollama models: {e}")
        return []
    
    async def health_check(self) -> bool:
        try:
            response = await self.client.get(f"{self.config.base_url}/api/tags", timeout=5.0)
            return response.status_code == 200
        except Exception:
            return False


class OpenAIProvider(BaseProvider):
    """OpenAI API provider"""
    
    MODELS = [
        "gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "gpt-4", 
        "gpt-3.5-turbo", "o1-preview", "o1-mini"
    ]
    
    def __init__(self, config: ProviderConfig):
        config.base_url = config.base_url or "https://api.openai.com/v1"
        super().__init__(config)
    
    async def chat(
        self, 
        messages: List[ChatMessage], 
        model: Optional[str] = None,
        **kwargs
    ) -> ChatResponse:
        if not self.config.api_key:
            raise Exception("OpenAI API key not configured")
        
        model = model or self.config.default_model or "gpt-4o-mini"
        start_time = datetime.utcnow()
        
        response = await self.client.post(
            f"{self.config.base_url}/chat/completions",
            headers={
                "Authorization": f"Bearer {self.config.api_key}",
                "Content-Type": "application/json"
            },
            json={
                "model": model,
                "messages": [m.to_dict() for m in messages],
                **kwargs
            }
        )
        
        if response.status_code != 200:
            error = response.json().get("error", {}).get("message", "Unknown error")
            raise Exception(f"OpenAI error: {error}")
        
        data = response.json()
        latency = (datetime.utcnow() - start_time).total_seconds() * 1000
        choice = data.get("choices", [{}])[0]
        
        return ChatResponse(
            content=choice.get("message", {}).get("content", ""),
            model=model,
            provider="openai",
            tokens_used=data.get("usage", {}).get("total_tokens"),
            finish_reason=choice.get("finish_reason"),
            latency_ms=int(latency)
        )
    
    async def list_models(self) -> List[str]:
        return self.MODELS
    
    async def health_check(self) -> bool:
        return self.config.api_key is not None


class AnthropicProvider(BaseProvider):
    """Anthropic Claude API provider"""
    
    MODELS = [
        "claude-3-5-sonnet-20241022", "claude-3-5-haiku-20241022",
        "claude-3-opus-20240229", "claude-3-sonnet-20240229", 
        "claude-3-haiku-20240307"
    ]
    
    def __init__(self, config: ProviderConfig):
        config.base_url = config.base_url or "https://api.anthropic.com/v1"
        super().__init__(config)
    
    async def chat(
        self, 
        messages: List[ChatMessage], 
        model: Optional[str] = None,
        **kwargs
    ) -> ChatResponse:
        if not self.config.api_key:
            raise Exception("Anthropic API key not configured")
        
        model = model or self.config.default_model or "claude-3-5-sonnet-20241022"
        start_time = datetime.utcnow()
        
        # Separate system message from other messages
        system_prompt = ""
        chat_messages = []
        for m in messages:
            if m.role == "system":
                system_prompt = m.content
            else:
                chat_messages.append(m.to_dict())
        
        response = await self.client.post(
            f"{self.config.base_url}/messages",
            headers={
                "x-api-key": self.config.api_key,
                "anthropic-version": "2023-06-01",
                "Content-Type": "application/json"
            },
            json={
                "model": model,
                "max_tokens": kwargs.get("max_tokens", 4096),
                "system": system_prompt if system_prompt else None,
                "messages": chat_messages
            }
        )
        
        if response.status_code != 200:
            error = response.json().get("error", {}).get("message", "Unknown error")
            raise Exception(f"Anthropic error: {error}")
        
        data = response.json()
        latency = (datetime.utcnow() - start_time).total_seconds() * 1000
        
        return ChatResponse(
            content=data.get("content", [{}])[0].get("text", ""),
            model=model,
            provider="anthropic",
            tokens_used=data.get("usage", {}).get("input_tokens", 0) + data.get("usage", {}).get("output_tokens", 0),
            finish_reason=data.get("stop_reason"),
            latency_ms=int(latency)
        )
    
    async def list_models(self) -> List[str]:
        return self.MODELS
    
    async def health_check(self) -> bool:
        return self.config.api_key is not None


class GoogleProvider(BaseProvider):
    """Google Gemini API provider"""
    
    MODELS = ["gemini-2.0-flash-exp", "gemini-1.5-pro", "gemini-1.5-flash"]
    
    def __init__(self, config: ProviderConfig):
        config.base_url = config.base_url or "https://generativelanguage.googleapis.com/v1beta"
        super().__init__(config)
    
    async def chat(
        self, 
        messages: List[ChatMessage], 
        model: Optional[str] = None,
        **kwargs
    ) -> ChatResponse:
        if not self.config.api_key:
            raise Exception("Google API key not configured")
        
        model = model or self.config.default_model or "gemini-1.5-flash"
        start_time = datetime.utcnow()
        
        # Convert to Gemini format
        contents = []
        for m in messages:
            role = "user" if m.role in ["user", "system"] else "model"
            contents.append({
                "role": role,
                "parts": [{"text": m.content}]
            })
        
        response = await self.client.post(
            f"{self.config.base_url}/models/{model}:generateContent",
            headers={"Content-Type": "application/json"},
            params={"key": self.config.api_key},
            json={"contents": contents}
        )
        
        if response.status_code != 200:
            error = response.json().get("error", {}).get("message", "Unknown error")
            raise Exception(f"Google error: {error}")
        
        data = response.json()
        latency = (datetime.utcnow() - start_time).total_seconds() * 1000
        
        text = data.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "")
        
        return ChatResponse(
            content=text,
            model=model,
            provider="google",
            latency_ms=int(latency)
        )
    
    async def list_models(self) -> List[str]:
        return self.MODELS
    
    async def health_check(self) -> bool:
        return self.config.api_key is not None


class MistralProvider(BaseProvider):
    """Mistral API provider"""
    
    MODELS = [
        "mistral-large-latest", "mistral-medium-latest", 
        "mistral-small-latest", "codestral-latest",
        "open-mistral-7b", "open-mixtral-8x7b", "open-mixtral-8x22b"
    ]
    
    def __init__(self, config: ProviderConfig):
        config.base_url = config.base_url or "https://api.mistral.ai/v1"
        super().__init__(config)
    
    async def chat(
        self, 
        messages: List[ChatMessage], 
        model: Optional[str] = None,
        **kwargs
    ) -> ChatResponse:
        if not self.config.api_key:
            raise Exception("Mistral API key not configured")
        
        model = model or self.config.default_model or "mistral-small-latest"
        start_time = datetime.utcnow()
        
        response = await self.client.post(
            f"{self.config.base_url}/chat/completions",
            headers={
                "Authorization": f"Bearer {self.config.api_key}",
                "Content-Type": "application/json"
            },
            json={
                "model": model,
                "messages": [m.to_dict() for m in messages],
                **kwargs
            }
        )
        
        if response.status_code != 200:
            error = response.json().get("message", "Unknown error")
            raise Exception(f"Mistral error: {error}")
        
        data = response.json()
        latency = (datetime.utcnow() - start_time).total_seconds() * 1000
        choice = data.get("choices", [{}])[0]
        
        return ChatResponse(
            content=choice.get("message", {}).get("content", ""),
            model=model,
            provider="mistral",
            tokens_used=data.get("usage", {}).get("total_tokens"),
            finish_reason=choice.get("finish_reason"),
            latency_ms=int(latency)
        )
    
    async def list_models(self) -> List[str]:
        return self.MODELS
    
    async def health_check(self) -> bool:
        return self.config.api_key is not None


class ProviderManager:
    """
    Central manager for all LLM providers
    Handles provider registration, selection, and failover
    """
    
    def __init__(self):
        self.providers: Dict[str, BaseProvider] = {}
        self.configs: Dict[str, ProviderConfig] = {}
        self._default_provider: Optional[str] = None
    
    def register_provider(self, config: ProviderConfig) -> bool:
        """Register a new provider"""
        try:
            provider_classes = {
                ProviderType.OLLAMA: OllamaProvider,
                ProviderType.OPENAI: OpenAIProvider,
                ProviderType.ANTHROPIC: AnthropicProvider,
                ProviderType.GOOGLE: GoogleProvider,
                ProviderType.MISTRAL: MistralProvider,
            }
            
            provider_class = provider_classes.get(config.provider_type)
            if not provider_class:
                logger.error(f"Unknown provider type: {config.provider_type}")
                return False
            
            self.providers[config.name] = provider_class(config)
            self.configs[config.name] = config
            
            if self._default_provider is None:
                self._default_provider = config.name
            
            logger.info(f"Registered provider: {config.name} ({config.provider_type.value})")
            return True
            
        except Exception as e:
            logger.error(f"Failed to register provider {config.name}: {e}")
            return False
    
    def get_provider(self, name: Optional[str] = None) -> Optional[BaseProvider]:
        """Get provider by name or default"""
        name = name or self._default_provider
        return self.providers.get(name)
    
    def set_default(self, name: str) -> bool:
        """Set default provider"""
        if name in self.providers:
            self._default_provider = name
            return True
        return False
    
    async def chat(
        self, 
        messages: List[ChatMessage],
        provider: Optional[str] = None,
        model: Optional[str] = None,
        **kwargs
    ) -> ChatResponse:
        """Send chat request to provider"""
        prov = self.get_provider(provider)
        if not prov:
            raise Exception(f"Provider not found: {provider or self._default_provider}")
        
        return await prov.chat(messages, model, **kwargs)
    
    async def list_all_models(self) -> Dict[str, List[str]]:
        """List models from all providers"""
        result = {}
        for name, provider in self.providers.items():
            try:
                result[name] = await provider.list_models()
            except Exception as e:
                logger.warning(f"Failed to list models from {name}: {e}")
                result[name] = []
        return result
    
    async def health_check_all(self) -> Dict[str, bool]:
        """Health check all providers"""
        result = {}
        for name, provider in self.providers.items():
            try:
                result[name] = await provider.health_check()
            except Exception:
                result[name] = False
        return result
    
    def get_status(self) -> Dict[str, Any]:
        """Get status of all providers"""
        return {
            "default_provider": self._default_provider,
            "providers": {
                name: {
                    "type": config.provider_type.value,
                    "enabled": config.enabled,
                    "default_model": config.default_model,
                    "base_url": config.base_url
                }
                for name, config in self.configs.items()
            }
        }
    
    async def close_all(self):
        """Close all provider connections"""
        for provider in self.providers.values():
            await provider.close()


# Singleton instance
_provider_manager: Optional[ProviderManager] = None


def get_provider_manager() -> ProviderManager:
    """Get or create singleton provider manager"""
    global _provider_manager
    if _provider_manager is None:
        _provider_manager = ProviderManager()
        
        # Register default Ollama provider
        _provider_manager.register_provider(ProviderConfig(
            provider_type=ProviderType.OLLAMA,
            name="ollama",
            default_model="llama3.2:3b",
            enabled=True
        ))
    
    return _provider_manager


# ============================================
# LLMProvider - Simplified interface
# ============================================

@dataclass
class ModelInfo:
    """Information about a model"""
    name: str
    description: str = ""
    size: str = "Unknown"
    parameters: str = "Unknown"


class LLMProvider:
    """
    Simplified LLM provider interface
    Provides easy access to models and chat functionality
    """
    
    def __init__(self):
        self.manager = get_provider_manager()
        self._selected_model: Optional[str] = None
        self._cloud_providers: Dict[str, bool] = {
            "openai": False,
            "anthropic": False,
            "google": False,
            "mistral": False,
        }
    
    async def list_models(self) -> List[ModelInfo]:
        """List all available models"""
        models = []
        
        # Get models from all providers
        all_models = await self.manager.list_all_models()
        
        for provider_name, model_names in all_models.items():
            for model_name in model_names:
                models.append(ModelInfo(
                    name=model_name,
                    description=f"Model from {provider_name}",
                    size="Unknown",
                    parameters="Unknown"
                ))
        
        return models
    
    async def select_model(self, model_name: str) -> bool:
        """Select a model for use"""
        self._selected_model = model_name
        return True
    
    def get_cloud_status(self) -> Dict[str, bool]:
        """Get status of cloud providers"""
        return self._cloud_providers.copy()
    
    def enable_cloud_provider(self, provider: str, api_key: str) -> bool:
        """Enable a cloud provider with API key"""
        if provider not in self._cloud_providers:
            return False
        
        provider_types = {
            "openai": ProviderType.OPENAI,
            "anthropic": ProviderType.ANTHROPIC,
            "google": ProviderType.GOOGLE,
            "mistral": ProviderType.MISTRAL,
        }
        
        config = ProviderConfig(
            provider_type=provider_types[provider],
            name=provider,
            api_key=api_key,
            enabled=True
        )
        
        success = self.manager.register_provider(config)
        if success:
            self._cloud_providers[provider] = True
        
        return success
    
    async def chat(
        self, 
        message: str, 
        model: Optional[str] = None,
        provider: Optional[str] = None,
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> ChatResponse:
        """Send chat message"""
        messages = []
        
        if system_prompt:
            messages.append(ChatMessage(role="system", content=system_prompt))
        
        messages.append(ChatMessage(role="user", content=message))
        
        model = model or self._selected_model
        
        return await self.manager.chat(
            messages=messages,
            provider=provider,
            model=model,
            **kwargs
        )
    
    async def health_check(self) -> Dict[str, bool]:
        """Check health of all providers"""
        return await self.manager.health_check_all()
    
    def get_status(self) -> Dict[str, Any]:
        """Get provider status"""
        return self.manager.get_status()
