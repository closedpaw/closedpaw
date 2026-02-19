"""
SecureSphere AI - FastAPI Backend
Main application entry point
"""

import asyncio
from contextlib import asynccontextmanager
from typing import List, Optional

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from app.core.orchestrator import get_orchestrator, ActionType, SecurityLevel
from app.core.providers import get_provider_manager, ProviderType, ChatMessage
from app.core.channels import get_channel_manager, ChannelType


# Pydantic models for API
class ChatRequest(BaseModel):
    message: str = Field(..., description="User message")
    model: str = Field(default="llama3.2:3b", description="Model to use")
    use_cloud: bool = Field(default=False, description="Use cloud LLM instead of local")


class ChatResponse(BaseModel):
    response: str
    model: str
    action_id: str
    status: str


class ActionRequest(BaseModel):
    action_type: str
    parameters: dict = Field(default_factory=dict)
    skill_id: Optional[str] = None


class ActionApprovalRequest(BaseModel):
    approved: bool
    user_id: str = "admin"


class ModelInfo(BaseModel):
    name: str
    description: str
    size: str
    parameters: str


class SystemStatus(BaseModel):
    status: str
    ollama_connected: bool
    available_models: List[str]
    pending_actions: int


# Lifespan context manager for startup/shutdown
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan"""
    # Startup
    orchestrator = get_orchestrator()
    await orchestrator.initialize()
    
    yield
    
    # Shutdown
    await orchestrator.shutdown()


# Create FastAPI app
app = FastAPI(
    title="ClosedPaw API",
    description="Zero-Trust AI Assistant API",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware - only allow localhost for security
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "name": "ClosedPaw",
        "version": "1.0.0",
        "status": "running",
        "security_model": "zero_trust"
    }


@app.get("/api/status", response_model=SystemStatus)
async def get_status():
    """Get system status"""
    orchestrator = get_orchestrator()
    
    # Check Ollama connection
    ollama_connected = False
    available_models = []
    
    try:
        import httpx
        async with httpx.AsyncClient() as client:
            response = await client.get("http://127.0.0.1:11434/api/tags", timeout=5.0)
            if response.status_code == 200:
                ollama_connected = True
                models = response.json().get("models", [])
                available_models = [m.get("name") for m in models]
    except Exception:
        pass
    
    pending_count = len(orchestrator.get_pending_actions())
    
    return SystemStatus(
        status="running" if orchestrator.running else "initializing",
        ollama_connected=ollama_connected,
        available_models=available_models,
        pending_actions=pending_count
    )


@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest, background_tasks: BackgroundTasks):
    """
    Send a chat message to the AI
    
    This endpoint submits a chat action to the orchestrator.
    For low-security actions, it executes immediately.
    For high-security actions, it may require HITL approval.
    """
    orchestrator = get_orchestrator()
    
    # Submit chat action
    action = await orchestrator.submit_action(
        action_type=ActionType.CHAT,
        parameters={
            "message": request.message,
            "model": request.model,
            "use_cloud": request.use_cloud
        },
        security_level=SecurityLevel.LOW  # Chat is low security
    )
    
    # Wait for action to complete (with timeout)
    max_wait = 60  # seconds
    waited = 0
    while action.status.value not in ["completed", "failed", "rejected"] and waited < max_wait:
        await asyncio.sleep(0.5)
        waited += 0.5
        # Refresh action status
        action = orchestrator.get_action_status(action.id)
    
    if action.status.value == "completed":
        result = action.result or {}
        return ChatResponse(
            response=result.get("response", "No response"),
            model=result.get("model", request.model),
            action_id=action.id,
            status="completed"
        )
    elif action.status.value == "failed":
        raise HTTPException(status_code=500, detail=action.error or "Action failed")
    elif action.status.value == "rejected":
        raise HTTPException(status_code=403, detail="Action was rejected")
    else:
        # Timeout - action is still pending or executing
        return ChatResponse(
            response="Processing...",
            model=request.model,
            action_id=action.id,
            status=action.status.value
        )


@app.get("/api/models", response_model=List[ModelInfo])
async def get_models():
    """Get available LLM models"""
    models = []
    
    try:
        import httpx
        async with httpx.AsyncClient() as client:
            response = await client.get("http://127.0.0.1:11434/api/tags", timeout=5.0)
            if response.status_code == 200:
                ollama_models = response.json().get("models", [])
                for model in ollama_models:
                    models.append(ModelInfo(
                        name=model.get("name", "unknown"),
                        description=f"Size: {model.get('size', 'unknown')}",
                        size=str(model.get("size", "unknown")),
                        parameters="unknown"
                    ))
    except Exception:
        # Return default models if Ollama is not available
        models = [
            ModelInfo(name="llama3.2:3b", description="Fast, good for chat", size="2GB", parameters="3B"),
            ModelInfo(name="mistral:7b", description="Balance of speed and quality", size="4GB", parameters="7B"),
            ModelInfo(name="qwen2.5-coder:7b", description="Excellent for code", size="4GB", parameters="7B")
        ]
    
    return models


@app.post("/api/models/switch")
async def switch_model(model: str):
    """Switch to a different model"""
    orchestrator = get_orchestrator()
    
    action = await orchestrator.submit_action(
        action_type=ActionType.MODEL_SWITCH,
        parameters={"model": model},
        security_level=SecurityLevel.MEDIUM
    )
    
    # Wait for completion
    max_wait = 10
    waited = 0
    while action.status.value not in ["completed", "failed"] and waited < max_wait:
        await asyncio.sleep(0.5)
        waited += 0.5
        action = orchestrator.get_action_status(action.id)
    
    if action.status.value == "completed":
        result = action.result or {}
        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])
        return {"status": "success", "model": model}
    else:
        raise HTTPException(status_code=500, detail="Failed to switch model")


@app.post("/api/actions")
async def submit_action(request: ActionRequest):
    """Submit a generic action"""
    orchestrator = get_orchestrator()
    
    try:
        action_type = ActionType(request.action_type)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid action type: {request.action_type}")
    
    action = await orchestrator.submit_action(
        action_type=action_type,
        parameters=request.parameters,
        skill_id=request.skill_id
    )
    
    return {
        "action_id": action.id,
        "status": action.status.value,
        "security_level": action.security_level.value,
        "requires_approval": action.status.value == "pending"
    }


@app.get("/api/actions/pending")
async def get_pending_actions():
    """Get all pending actions requiring approval"""
    orchestrator = get_orchestrator()
    pending = orchestrator.get_pending_actions()
    
    return [
        {
            "id": a.id,
            "action_type": a.action_type.value,
            "skill_id": a.skill_id,
            "security_level": a.security_level.value,
            "parameters": a.parameters,
            "created_at": a.created_at.isoformat()
        }
        for a in pending
    ]


@app.post("/api/actions/{action_id}/approve")
async def approve_action(action_id: str, request: ActionApprovalRequest):
    """Approve or reject a pending action"""
    orchestrator = get_orchestrator()
    
    success = orchestrator.approve_action(action_id, request.approved, request.user_id)
    
    if not success:
        raise HTTPException(status_code=404, detail="Action not found or not pending")
    
    return {
        "action_id": action_id,
        "approved": request.approved,
        "status": "approved" if request.approved else "rejected"
    }


@app.get("/api/actions/{action_id}")
async def get_action_status(action_id: str):
    """Get status of a specific action"""
    orchestrator = get_orchestrator()
    action = orchestrator.get_action_status(action_id)
    
    if not action:
        raise HTTPException(status_code=404, detail="Action not found")
    
    return {
        "id": action.id,
        "action_type": action.action_type.value,
        "status": action.status.value,
        "security_level": action.security_level.value,
        "result": action.result,
        "error": action.error,
        "created_at": action.created_at.isoformat(),
        "completed_at": action.completed_at.isoformat() if action.completed_at else None
    }


@app.get("/api/audit-logs")
async def get_audit_logs(limit: int = 100):
    """Get security audit logs"""
    orchestrator = get_orchestrator()
    logs = orchestrator.get_audit_logs(limit)
    
    return [
        {
            "timestamp": log.timestamp.isoformat(),
            "action_id": log.action_id,
            "action_type": log.action_type.value,
            "skill_id": log.skill_id,
            "status": log.status.value,
            "outcome": log.outcome,
            "details": log.details
        }
        for log in logs
    ]


@app.get("/api/skills")
async def get_skills():
    """Get available skills"""
    orchestrator = get_orchestrator()
    
    return [
        {
            "id": skill_id,
            "name": info.get("name", skill_id),
            "enabled": info.get("enabled", False)
        }
        for skill_id, info in orchestrator.skills.items()
    ]


@app.post("/api/skills/{skill_id}/enable")
async def enable_skill(skill_id: str):
    """Enable a skill"""
    orchestrator = get_orchestrator()
    
    if skill_id not in orchestrator.skills:
        raise HTTPException(status_code=404, detail="Skill not found")
    
    orchestrator.skills[skill_id]["enabled"] = True
    return {"skill_id": skill_id, "enabled": True}


@app.post("/api/skills/{skill_id}/disable")
async def disable_skill(skill_id: str):
    """Disable a skill"""
    orchestrator = get_orchestrator()
    
    if skill_id not in orchestrator.skills:
        raise HTTPException(status_code=404, detail="Skill not found")
    
    orchestrator.skills[skill_id]["enabled"] = False
    return {"skill_id": skill_id, "enabled": False}


# === Provider Management ===

@app.get("/api/providers")
async def get_providers():
    """Get all registered providers"""
    manager = get_provider_manager()
    return manager.get_status()


@app.get("/api/providers/{provider_name}/models")
async def get_provider_models(provider_name: str):
    """Get models available from a provider"""
    manager = get_provider_manager()
    provider = manager.get_provider(provider_name)
    
    if not provider:
        raise HTTPException(status_code=404, detail="Provider not found")
    
    models = await provider.list_models()
    return {"provider": provider_name, "models": models}


@app.post("/api/providers/register")
async def register_provider(
    provider_type: str,
    name: str,
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
    default_model: Optional[str] = None
):
    """Register a new provider"""
    from app.core.providers import ProviderConfig
    
    try:
        provider_type_enum = ProviderType(provider_type)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid provider type: {provider_type}")
    
    manager = get_provider_manager()
    
    config = ProviderConfig(
        provider_type=provider_type_enum,
        name=name,
        api_key=api_key,
        base_url=base_url,
        default_model=default_model
    )
    
    success = manager.register_provider(config)
    
    if not success:
        raise HTTPException(status_code=500, detail="Failed to register provider")
    
    return {"status": "success", "provider": name}


@app.post("/api/providers/{provider_name}/default")
async def set_default_provider(provider_name: str):
    """Set default provider"""
    manager = get_provider_manager()
    
    if not manager.set_default(provider_name):
        raise HTTPException(status_code=404, detail="Provider not found")
    
    return {"status": "success", "default_provider": provider_name}


@app.get("/api/providers/health")
async def check_providers_health():
    """Health check all providers"""
    manager = get_provider_manager()
    results = await manager.health_check_all()
    return results


@app.get("/api/providers/models")
async def list_all_models():
    """List models from all providers"""
    manager = get_provider_manager()
    results = await manager.list_all_models()
    return results


# === Channel Management ===

@app.get("/api/channels")
async def get_channels():
    """Get all registered channels"""
    manager = get_channel_manager()
    return manager.get_status()


@app.post("/api/channels/register")
async def register_channel(
    channel_type: str,
    name: str,
    bot_token: Optional[str] = None,
    allowed_users: List[str] = [],
    enabled: bool = True
):
    """Register a new channel"""
    from app.core.channels import ChannelConfig
    
    try:
        channel_type_enum = ChannelType(channel_type)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid channel type: {channel_type}")
    
    manager = get_channel_manager()
    
    config = ChannelConfig(
        channel_type=channel_type_enum,
        name=name,
        bot_token=bot_token,
        allowed_users=allowed_users,
        enabled=enabled
    )
    
    success = manager.register_channel(config)
    
    if not success:
        raise HTTPException(status_code=500, detail="Failed to register channel")
    
    return {"status": "success", "channel": name}


@app.post("/api/channels/{channel_name}/bind-user")
async def bind_channel_user(channel_name: str, user_id: str, username: Optional[str] = None):
    """Bind user to channel allowlist"""
    manager = get_channel_manager()
    manager.bind_user(channel_name, user_id, username)
    return {"status": "success", "channel": channel_name, "user_id": user_id}


@app.post("/api/channels/start")
async def start_channels():
    """Start all channels"""
    manager = get_channel_manager()
    await manager.start_all()
    return {"status": "started"}


@app.post("/api/channels/stop")
async def stop_channels():
    """Stop all channels"""
    manager = get_channel_manager()
    await manager.stop_all()
    return {"status": "stopped"}


# === Multi-Provider Chat ===

@app.post("/api/chat/multi")
async def chat_multi_provider(
    message: str,
    provider: Optional[str] = None,
    model: Optional[str] = None
):
    """Chat using specific provider"""
    manager = get_provider_manager()
    
    messages = [ChatMessage(role="user", content=message)]
    
    try:
        response = await manager.chat(messages, provider=provider, model=model)
        return {
            "response": response.content,
            "model": response.model,
            "provider": response.provider,
            "tokens": response.tokens_used,
            "latency_ms": response.latency_ms
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    
    # Run with localhost only for security
    uvicorn.run(
        "app.main:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
        log_level="info"
    )