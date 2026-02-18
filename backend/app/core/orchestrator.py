"""
SecureSphere AI - Core Orchestrator
Central component managing all system operations with Zero-Trust architecture
"""

import asyncio
import json
import logging
import os
import tempfile
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any
from enum import Enum
import httpx
from pydantic import BaseModel, Field

# Configure logging for security audit
log_path = os.path.join(tempfile.gettempdir(), 'closedpaw-audit.log')
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_path),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class ActionType(str, Enum):
    """Types of actions that can be performed by the system"""
    CHAT = "chat"
    SKILL_EXECUTION = "skill_execution"
    MODEL_SWITCH = "model_switch"
    API_CALL = "api_call"
    FILE_OPERATION = "file_operation"
    CONFIG_CHANGE = "config_change"


class ActionStatus(str, Enum):
    """Status of an action"""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"


class SecurityLevel(str, Enum):
    """Security levels for actions"""
    LOW = "low"           # No approval needed
    MEDIUM = "medium"     # Log only
    HIGH = "high"         # Requires HITL approval
    CRITICAL = "critical" # Requires HITL + additional verification


class AuditLogEntry(BaseModel):
    """Security audit log entry"""
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    action_id: str
    action_type: ActionType
    skill_id: Optional[str] = None
    user_id: str
    status: ActionStatus
    details: Dict[str, Any] = Field(default_factory=dict)
    outcome: Optional[str] = None
    ip_address: Optional[str] = None


class SystemAction(BaseModel):
    """Represents a system action"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    action_type: ActionType
    skill_id: Optional[str] = None
    parameters: Dict[str, Any] = Field(default_factory=dict)
    security_level: SecurityLevel = SecurityLevel.MEDIUM
    status: ActionStatus = ActionStatus.PENDING
    created_at: datetime = Field(default_factory=datetime.utcnow)
    approved_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    result: Optional[Any] = None
    error: Optional[str] = None


class CoreOrchestrator:
    """
    Core Orchestrator for ClosedPaw
    Manages all system operations with Zero-Trust security model
    """
    
    def __init__(self):
        self.actions: Dict[str, SystemAction] = {}
        self.audit_logs: List[AuditLogEntry] = []
        self.skills: Dict[str, Any] = {}
        self.llm_gateway = None
        self.hitl_interface = None
        self.data_vault = None
        self.running = False
        
        # Security configuration
        self.security_config = {
            "require_hitl_for_critical": True,
            "log_all_actions": True,
            "max_action_timeout": 300,  # 5 minutes
            "rate_limit_per_minute": 60
        }
        
        logger.info("CoreOrchestrator initialized")
    
    async def initialize(self):
        """Initialize the orchestrator and all components"""
        logger.info("Initializing CoreOrchestrator...")
        
        # Initialize LLM Gateway (local Ollama)
        await self._init_llm_gateway()
        
        # Initialize HITL Interface
        await self._init_hitl_interface()
        
        # Initialize Data Vault
        await self._init_data_vault()
        
        # Load available skills
        await self._load_skills()
        
        self.running = True
        logger.info("CoreOrchestrator initialized successfully")
    
    async def _init_llm_gateway(self):
        """Initialize Local LLM Gateway (Ollama)"""
        try:
            async with httpx.AsyncClient() as client:
                # Check if Ollama is running on localhost only
                response = await client.get("http://127.0.0.1:11434/api/tags", timeout=5.0)
                if response.status_code == 200:
                    models = response.json().get("models", [])
                    logger.info(f"Ollama connected. Available models: {len(models)}")
                else:
                    logger.warning("Ollama returned non-200 status")
        except Exception as e:
            logger.error(f"Failed to connect to Ollama: {e}")
            logger.warning("Ollama not available. Some features will be limited.")
    
    async def _init_hitl_interface(self):
        """Initialize Human-in-the-Loop Interface"""
        logger.info("Initializing HITL Interface...")
        # HITL interface will be initialized when web UI is ready
        pass
    
    async def _init_data_vault(self):
        """Initialize encrypted Data Vault"""
        logger.info("Initializing Data Vault...")
        # Data vault initialization
        pass
    
    async def _load_skills(self):
        """Load available skill executors"""
        logger.info("Loading skill executors...")
        # Skills will be loaded dynamically
        self.skills = {
            "filesystem": {"name": "File System", "enabled": True},
            "telegram": {"name": "Telegram", "enabled": False},
            "discord": {"name": "Discord", "enabled": False}
        }
        logger.info(f"Loaded {len(self.skills)} skills")
    
    async def submit_action(self, action_type: ActionType, parameters: Dict[str, Any], 
                          skill_id: Optional[str] = None, 
                          security_level: Optional[SecurityLevel] = None) -> SystemAction:
        """
        Submit a new action for execution
        
        Args:
            action_type: Type of action to perform
            parameters: Action parameters
            skill_id: Optional skill executor ID
            security_level: Override security level
            
        Returns:
            SystemAction: The created action
        """
        # Determine security level if not specified
        if security_level is None:
            security_level = self._determine_security_level(action_type, parameters)
        
        # Create action
        action = SystemAction(
            action_type=action_type,
            skill_id=skill_id,
            parameters=parameters,
            security_level=security_level
        )
        
        # Store action
        self.actions[action.id] = action
        
        # Log action creation
        self._log_audit_event(
            action_id=action.id,
            action_type=action_type,
            skill_id=skill_id,
            status=ActionStatus.PENDING,
            details={"parameters": parameters, "security_level": security_level.value}
        )
        
        logger.info(f"Action submitted: {action.id} ({action_type.value})")
        
        # Check if HITL approval is required
        if security_level in [SecurityLevel.HIGH, SecurityLevel.CRITICAL]:
            logger.info(f"Action {action.id} requires HITL approval")
            # HITL approval will be requested through web UI
            return action
        
        # Auto-approve low/medium security actions
        action.status = ActionStatus.APPROVED
        action.approved_at = datetime.utcnow()
        
        # Execute action
        asyncio.create_task(self._execute_action(action.id))
        
        return action
    
    def _determine_security_level(self, action_type: ActionType, parameters: Dict[str, Any]) -> SecurityLevel:
        """Determine security level based on action type and parameters"""
        
        # Critical actions
        if action_type == ActionType.CONFIG_CHANGE:
            return SecurityLevel.CRITICAL
        
        if action_type == ActionType.FILE_OPERATION:
            # Check if file operation is destructive
            operation = parameters.get("operation", "").lower()
            if operation in ["delete", "write", "modify"]:
                return SecurityLevel.HIGH
            return SecurityLevel.MEDIUM
        
        if action_type == ActionType.SKILL_EXECUTION:
            skill_id = parameters.get("skill_id", "")
            if skill_id in ["filesystem", "system"]:
                return SecurityLevel.HIGH
            return SecurityLevel.MEDIUM
        
        # Default for chat and other actions
        if action_type == ActionType.CHAT:
            return SecurityLevel.LOW
        
        return SecurityLevel.MEDIUM
    
    async def _execute_action(self, action_id: str):
        """Execute an approved action"""
        action = self.actions.get(action_id)
        if not action:
            logger.error(f"Action {action_id} not found")
            return
        
        action.status = ActionStatus.EXECUTING
        logger.info(f"Executing action: {action_id}")
        
        try:
            # Execute based on action type
            if action.action_type == ActionType.CHAT:
                result = await self._execute_chat(action)
            elif action.action_type == ActionType.SKILL_EXECUTION:
                result = await self._execute_skill(action)
            elif action.action_type == ActionType.MODEL_SWITCH:
                result = await self._execute_model_switch(action)
            else:
                result = {"status": "not_implemented", "action_type": action.action_type.value}
            
            action.result = result
            action.status = ActionStatus.COMPLETED
            action.completed_at = datetime.utcnow()
            
            self._log_audit_event(
                action_id=action.id,
                action_type=action.action_type,
                skill_id=action.skill_id,
                status=ActionStatus.COMPLETED,
                outcome="success",
                details={"result": result}
            )
            
            logger.info(f"Action completed: {action_id}")
            
        except Exception as e:
            action.status = ActionStatus.FAILED
            action.error = str(e)
            action.completed_at = datetime.utcnow()
            
            self._log_audit_event(
                action_id=action.id,
                action_type=action.action_type,
                skill_id=action.skill_id,
                status=ActionStatus.FAILED,
                outcome="error",
                details={"error": str(e)}
            )
            
            logger.error(f"Action failed: {action_id} - {e}")
    
    async def _execute_chat(self, action: SystemAction) -> Dict[str, Any]:
        """Execute a chat action"""
        message = action.parameters.get("message", "")
        model = action.parameters.get("model", "llama3.2:3b")
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "http://127.0.0.1:11434/api/generate",
                    json={
                        "model": model,
                        "prompt": message,
                        "stream": False
                    },
                    timeout=60.0
                )
                
                if response.status_code == 200:
                    result = response.json()
                    return {
                        "response": result.get("response", ""),
                        "model": model,
                        "done": result.get("done", False)
                    }
                else:
                    return {"error": f"Ollama returned status {response.status_code}"}
                    
        except Exception as e:
            return {"error": f"Failed to communicate with Ollama: {str(e)}"}
    
    async def _execute_skill(self, action: SystemAction) -> Dict[str, Any]:
        """Execute a skill action"""
        skill_id = action.skill_id
        
        if skill_id not in self.skills:
            return {"error": f"Skill {skill_id} not found"}
        
        skill = self.skills[skill_id]
        
        if not skill.get("enabled", False):
            return {"error": f"Skill {skill_id} is not enabled"}
        
        # Skill execution would be delegated to Agent Manager with sandbox
        return {
            "skill": skill_id,
            "status": "delegated_to_agent_manager",
            "parameters": action.parameters
        }
    
    async def _execute_model_switch(self, action: SystemAction) -> Dict[str, Any]:
        """Execute a model switch action"""
        new_model = action.parameters.get("model", "")
        
        if not new_model:
            return {"error": "No model specified"}
        
        # Verify model is available
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get("http://127.0.0.1:11434/api/tags", timeout=5.0)
                if response.status_code == 200:
                    models = response.json().get("models", [])
                    available_models = [m.get("name") for m in models]
                    
                    if new_model in available_models:
                        return {"status": "success", "model": new_model}
                    else:
                        return {"error": f"Model {new_model} not available", "available": available_models}
                else:
                    return {"error": "Failed to query available models"}
        except Exception as e:
            return {"error": f"Failed to switch model: {str(e)}"}
    
    def approve_action(self, action_id: str, approved: bool, user_id: str = "admin") -> bool:
        """
        Approve or reject an action (HITL)
        
        Args:
            action_id: ID of the action
            approved: True to approve, False to reject
            user_id: ID of the approving user
            
        Returns:
            bool: True if action was processed
        """
        action = self.actions.get(action_id)
        if not action:
            logger.error(f"Action {action_id} not found for approval")
            return False
        
        if action.status != ActionStatus.PENDING:
            logger.warning(f"Action {action_id} is not pending (status: {action.status.value})")
            return False
        
        if approved:
            action.status = ActionStatus.APPROVED
            action.approved_at = datetime.utcnow()
            
            self._log_audit_event(
                action_id=action.id,
                action_type=action.action_type,
                skill_id=action.skill_id,
                status=ActionStatus.APPROVED,
                details={"approved_by": user_id}
            )
            
            logger.info(f"Action {action_id} approved by {user_id}")
            
            # Execute the action
            asyncio.create_task(self._execute_action(action_id))
        else:
            action.status = ActionStatus.REJECTED
            action.completed_at = datetime.utcnow()
            
            self._log_audit_event(
                action_id=action.id,
                action_type=action.action_type,
                skill_id=action.skill_id,
                status=ActionStatus.REJECTED,
                details={"rejected_by": user_id}
            )
            
            logger.info(f"Action {action_id} rejected by {user_id}")
        
        return True
    
    def _log_audit_event(self, action_id: str, action_type: ActionType, 
                        skill_id: Optional[str], status: ActionStatus, 
                        outcome: Optional[str] = None, details: Optional[Dict] = None):
        """Log an audit event"""
        if not self.security_config["log_all_actions"]:
            return
        
        entry = AuditLogEntry(
            action_id=action_id,
            action_type=action_type,
            skill_id=skill_id,
            user_id="system",  # Would be actual user ID in production
            status=status,
            outcome=outcome,
            details=details or {}
        )
        
        self.audit_logs.append(entry)
        
        # Log to file
        logger.info(f"AUDIT: {action_id} | {action_type.value} | {status.value} | {outcome or 'N/A'}")
    
    def get_pending_actions(self) -> List[SystemAction]:
        """Get all pending actions requiring approval"""
        return [a for a in self.actions.values() if a.status == ActionStatus.PENDING]
    
    def get_action_status(self, action_id: str) -> Optional[SystemAction]:
        """Get the status of an action"""
        return self.actions.get(action_id)
    
    def get_audit_logs(self, limit: int = 100) -> List[AuditLogEntry]:
        """Get recent audit logs"""
        return sorted(self.audit_logs, key=lambda x: x.timestamp, reverse=True)[:limit]
    
    async def shutdown(self):
        """Shutdown the orchestrator gracefully"""
        logger.info("Shutting down CoreOrchestrator...")
        self.running = False
        
        # Wait for pending actions to complete
        pending = [a for a in self.actions.values() if a.status == ActionStatus.EXECUTING]
        if pending:
            logger.info(f"Waiting for {len(pending)} executing actions to complete...")
            await asyncio.sleep(2)
        
        logger.info("CoreOrchestrator shutdown complete")


# Singleton instance
_orchestrator: Optional[CoreOrchestrator] = None


def get_orchestrator() -> CoreOrchestrator:
    """Get or create the singleton orchestrator instance"""
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = CoreOrchestrator()
    return _orchestrator