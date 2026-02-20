# Core Components

<cite>
**Referenced Files in This Document**
- [backend/app/core/orchestrator.py](file://backend/app/core/orchestrator.py)
- [backend/app/core/providers.py](file://backend/app/core/providers.py)
- [backend/app/core/channels.py](file://backend/app/core/channels.py)
- [backend/app/core/agent_manager.py](file://backend/app/core/agent_manager.py)
- [backend/app/core/security.py](file://backend/app/core/security.py)
- [backend/app/main.py](file://backend/app/main.py)
- [skills/filesystem/skill.py](file://skills/filesystem/skill.py)
- [backend/requirements.txt](file://backend/requirements.txt)
</cite>

## Table of Contents
1. [Introduction](#introduction)
2. [Project Structure](#project-structure)
3. [Core Components](#core-components)
4. [Architecture Overview](#architecture-overview)
5. [Detailed Component Analysis](#detailed-component-analysis)
6. [Dependency Analysis](#dependency-analysis)
7. [Performance Considerations](#performance-considerations)
8. [Troubleshooting Guide](#troubleshooting-guide)
9. [Conclusion](#conclusion)
10. [Appendices](#appendices)

## Introduction
This document explains the core coordination architecture and component relationships of ClosedPaw. It focuses on:
- Core Orchestrator as the central coordination hub with Zero-Trust architecture, Action lifecycle management, and security level classification
- Provider Manager supporting multiple LLM backends (local Ollama plus cloud providers), dynamic registration, and health monitoring
- Channel Manager for multi-channel communication support, user authorization, and message routing
- Agent Manager for sandbox environment setup using gVisor/Kata Containers, resource limits, and security boundary enforcement
- Security module with prompt injection defense and encrypted data vault
- Event-driven architecture, singleton pattern implementation, and dependency injection
- Practical examples of component usage and configuration

## Project Structure
The backend is organized around a core module that exposes singletons for each major subsystem. The FastAPI application wires these singletons into endpoints and manages lifecycle via a lifespan context manager.

```mermaid
graph TB
subgraph "Backend"
A["FastAPI App<br/>backend/app/main.py"]
B["Core Orchestrator<br/>backend/app/core/orchestrator.py"]
C["Provider Manager<br/>backend/app/core/providers.py"]
D["Channel Manager<br/>backend/app/core/channels.py"]
E["Agent Manager<br/>backend/app/core/agent_manager.py"]
F["Security Module<br/>backend/app/core/security.py"]
end
A --> B
A --> C
A --> D
A --> E
A --> F
```

**Diagram sources**
- [backend/app/main.py](file://backend/app/main.py#L59-L70)
- [backend/app/core/orchestrator.py](file://backend/app/core/orchestrator.py#L87-L130)
- [backend/app/core/providers.py](file://backend/app/core/providers.py#L418-L457)
- [backend/app/core/channels.py](file://backend/app/core/channels.py#L405-L444)
- [backend/app/core/agent_manager.py](file://backend/app/core/agent_manager.py#L65-L98)
- [backend/app/core/security.py](file://backend/app/core/security.py#L325-L346)

**Section sources**
- [backend/app/main.py](file://backend/app/main.py#L59-L70)
- [backend/app/core/__init__.py](file://backend/app/core/__init__.py#L1-L18)

## Core Components
- Core Orchestrator: Central coordinator for actions, security levels, audit logging, and HITL approvals. Provides a singleton accessor and integrates with LLM gateways and skills.
- Provider Manager: Multi-provider LLM gateway supporting Ollama, OpenAI, Anthropic, Google, Mistral, and custom endpoints. Handles registration, selection, model listing, and health checks.
- Channel Manager: Multi-channel gateway supporting Web UI, Telegram, Discord, Slack, and CLI. Handles user authorization, message routing, and broadcasting.
- Agent Manager: Sandboxed skill executor manager using gVisor or Kata Containers with resource limits, process isolation, and security boundaries.
- Security Module: Prompt injection defense, rate limiting, and encrypted data vault with access control.

**Section sources**
- [backend/app/core/orchestrator.py](file://backend/app/core/orchestrator.py#L87-L130)
- [backend/app/core/providers.py](file://backend/app/core/providers.py#L418-L457)
- [backend/app/core/channels.py](file://backend/app/core/channels.py#L405-L444)
- [backend/app/core/agent_manager.py](file://backend/app/core/agent_manager.py#L65-L98)
- [backend/app/core/security.py](file://backend/app/core/security.py#L325-L346)

## Architecture Overview
The system follows a Zero-Trust model:
- All actions are classified by security level and audited
- Low-risk actions auto-execute; high-risk actions require Human-in-the-Loop (HITL) approval
- Providers and channels are dynamically registered and monitored
- Skills execute inside hardened sandboxes with strict resource limits

```mermaid
graph TB
subgraph "External Clients"
U["Users/Bots"]
end
subgraph "API Layer"
API["FastAPI App<br/>backend/app/main.py"]
end
subgraph "Core Coordination"
ORCH["Core Orchestrator<br/>backend/app/core/orchestrator.py"]
SEC["Security Module<br/>backend/app/core/security.py"]
end
subgraph "Integration"
PM["Provider Manager<br/>backend/app/core/providers.py"]
CM["Channel Manager<br/>backend/app/core/channels.py"]
AM["Agent Manager<br/>backend/app/core/agent_manager.py"]
end
U --> API
API --> ORCH
ORCH --> PM
ORCH --> CM
ORCH --> AM
ORCH --> SEC
PM --> |"Cloud/Llama"| U
CM --> |"Telegram/Discord/Slack"| U
AM --> |"Sandboxed Skills"| U
```

**Diagram sources**
- [backend/app/main.py](file://backend/app/main.py#L131-L182)
- [backend/app/core/orchestrator.py](file://backend/app/core/orchestrator.py#L169-L224)
- [backend/app/core/providers.py](file://backend/app/core/providers.py#L470-L483)
- [backend/app/core/channels.py](file://backend/app/core/channels.py#L462-L483)
- [backend/app/core/agent_manager.py](file://backend/app/core/agent_manager.py#L149-L192)

## Detailed Component Analysis

### Core Orchestrator
Responsibilities:
- Action lifecycle: submit, classify by security level, approve/reject (HITL), execute, and audit
- Integrates with LLM gateways and skills
- Maintains in-memory action registry and audit logs
- Provides singleton accessor

Key behaviors:
- Security levels: Low, Medium, High, Critical
- Auto-approval for Low/Medium; High/Critical require HITL
- Audit logging for all actions
- Graceful shutdown with pending action handling

```mermaid
classDiagram
class CoreOrchestrator {
+initialize()
+submit_action(action_type, parameters, skill_id, security_level) SystemAction
+approve_action(action_id, approved, user_id) bool
+get_pending_actions() SystemAction[]
+get_action_status(action_id) SystemAction
+get_audit_logs(limit) AuditLogEntry[]
+shutdown()
-_determine_security_level(action_type, parameters) SecurityLevel
-_execute_action(action_id)
-_execute_chat(action) Dict
-_execute_skill(action) Dict
-_execute_model_switch(action) Dict
-_init_llm_gateway()
-_init_hitl_interface()
-_init_data_vault()
-_load_skills()
-_log_audit_event(...)
}
class SystemAction {
+id : str
+action_type : ActionType
+skill_id : str?
+parameters : Dict
+security_level : SecurityLevel
+status : ActionStatus
+result : Any?
+error : str?
}
class AuditLogEntry {
+timestamp : datetime
+action_id : str
+action_type : ActionType
+skill_id : str?
+user_id : str
+status : ActionStatus
+details : Dict
+outcome : str?
+ip_address : str?
}
CoreOrchestrator --> SystemAction : "manages"
CoreOrchestrator --> AuditLogEntry : "logs"
```

**Diagram sources**
- [backend/app/core/orchestrator.py](file://backend/app/core/orchestrator.py#L87-L130)
- [backend/app/core/orchestrator.py](file://backend/app/core/orchestrator.py#L72-L85)
- [backend/app/core/orchestrator.py](file://backend/app/core/orchestrator.py#L59-L70)

**Section sources**
- [backend/app/core/orchestrator.py](file://backend/app/core/orchestrator.py#L87-L130)
- [backend/app/core/orchestrator.py](file://backend/app/core/orchestrator.py#L169-L224)
- [backend/app/core/orchestrator.py](file://backend/app/core/orchestrator.py#L251-L302)
- [backend/app/core/orchestrator.py](file://backend/app/core/orchestrator.py#L376-L428)
- [backend/app/core/orchestrator.py](file://backend/app/core/orchestrator.py#L451-L475)

### Provider Manager
Responsibilities:
- Dynamic registration of providers (Ollama, OpenAI, Anthropic, Google, Mistral, Custom)
- Provider selection and default provider management
- Model listing and health checks
- Unified chat interface across providers

```mermaid
classDiagram
class ProviderManager {
+register_provider(config) bool
+get_provider(name) BaseProvider?
+set_default(name) bool
+chat(messages, provider, model, ...) ChatResponse
+list_all_models() Dict~str, str[]~
+health_check_all() Dict~str, bool~
+get_status() Dict
+close_all()
}
class BaseProvider {
<<abstract>>
+chat(messages, model, ...) ChatResponse
+list_models() str[]
+health_check() bool
+close()
}
class OllamaProvider
class OpenAIProvider
class AnthropicProvider
class GoogleProvider
class MistralProvider
ProviderManager --> BaseProvider : "manages"
OllamaProvider --|> BaseProvider
OpenAIProvider --|> BaseProvider
AnthropicProvider --|> BaseProvider
GoogleProvider --|> BaseProvider
MistralProvider --|> BaseProvider
```

**Diagram sources**
- [backend/app/core/providers.py](file://backend/app/core/providers.py#L418-L457)
- [backend/app/core/providers.py](file://backend/app/core/providers.py#L68-L100)
- [backend/app/core/providers.py](file://backend/app/core/providers.py#L102-L161)
- [backend/app/core/providers.py](file://backend/app/core/providers.py#L163-L222)
- [backend/app/core/providers.py](file://backend/app/core/providers.py#L224-L294)
- [backend/app/core/providers.py](file://backend/app/core/providers.py#L296-L354)
- [backend/app/core/providers.py](file://backend/app/core/providers.py#L356-L416)

**Section sources**
- [backend/app/core/providers.py](file://backend/app/core/providers.py#L418-L457)
- [backend/app/core/providers.py](file://backend/app/core/providers.py#L470-L483)
- [backend/app/core/providers.py](file://backend/app/core/providers.py#L495-L504)

### Channel Manager
Responsibilities:
- Multi-channel support (Web UI, Telegram, Discord, Slack, CLI)
- User authorization and allowlists
- Message routing and broadcasting
- Channel registration and lifecycle management

```mermaid
classDiagram
class ChannelManager {
+register_channel(config) bool
+start_all()
+stop_all()
+set_message_handler(handler)
+send_message(channel_name, channel_id, content, ...)
+broadcast(content, channels)
+bind_user(channel_name, user_id, username)
+get_status() Dict
}
class BaseChannel {
<<abstract>>
+start()
+stop()
+send_message(channel_id, content, ...)
+get_me() Dict
+set_message_handler(handler)
+is_user_allowed(user_id) bool
+add_allowed_user(user_id, username)
}
class WebUIChannel
class TelegramChannel
class DiscordChannel
class SlackChannel
class CLIChannel
ChannelManager --> BaseChannel : "manages"
WebUIChannel --|> BaseChannel
TelegramChannel --|> BaseChannel
DiscordChannel --|> BaseChannel
SlackChannel --|> BaseChannel
CLIChannel --|> BaseChannel
```

**Diagram sources**
- [backend/app/core/channels.py](file://backend/app/core/channels.py#L405-L444)
- [backend/app/core/channels.py](file://backend/app/core/channels.py#L79-L117)
- [backend/app/core/channels.py](file://backend/app/core/channels.py#L137-L175)
- [backend/app/core/channels.py](file://backend/app/core/channels.py#L177-L286)
- [backend/app/core/channels.py](file://backend/app/core/channels.py#L288-L334)
- [backend/app/core/channels.py](file://backend/app/core/channels.py#L336-L382)
- [backend/app/core/channels.py](file://backend/app/core/channels.py#L384-L403)

**Section sources**
- [backend/app/core/channels.py](file://backend/app/core/channels.py#L405-L444)
- [backend/app/core/channels.py](file://backend/app/core/channels.py#L462-L483)
- [backend/app/core/channels.py](file://backend/app/core/channels.py#L484-L490)

### Agent Manager
Responsibilities:
- Create and manage sandboxed agents using gVisor or Kata Containers
- Enforce resource limits and security boundaries
- Execute commands in sandboxed environments
- Cleanup and status reporting

```mermaid
classDiagram
class AgentManager {
+create_agent(skill_id, resource_limits) AgentInstance
+execute_in_agent(agent_id, command, timeout) Dict
+stop_agent(agent_id, force) bool
+cleanup()
+get_agent_status(agent_id) AgentInstance?
+list_agents() AgentInstance[]
+get_sandbox_info() Dict
-_detect_sandbox_runtime() SandboxType
-_create_sandbox(agent)
-_create_gvisor_sandbox(agent)
-_create_kata_sandbox(agent)
-_exec_gvisor(agent, command)
-_exec_kata(agent, command)
-_stop_gvisor(agent, force)
-_stop_kata(agent, force)
}
class AgentInstance {
+id : str
+skill_id : str
+sandbox_type : SandboxType
+status : AgentStatus
+resource_limits : ResourceLimits
+container_id : str?
}
AgentManager --> AgentInstance : "manages"
```

**Diagram sources**
- [backend/app/core/agent_manager.py](file://backend/app/core/agent_manager.py#L65-L98)
- [backend/app/core/agent_manager.py](file://backend/app/core/agent_manager.py#L149-L192)
- [backend/app/core/agent_manager.py](file://backend/app/core/agent_manager.py#L194-L202)
- [backend/app/core/agent_manager.py](file://backend/app/core/agent_manager.py#L475-L538)
- [backend/app/core/agent_manager.py](file://backend/app/core/agent_manager.py#L586-L627)

**Section sources**
- [backend/app/core/agent_manager.py](file://backend/app/core/agent_manager.py#L65-L98)
- [backend/app/core/agent_manager.py](file://backend/app/core/agent_manager.py#L149-L192)
- [backend/app/core/agent_manager.py](file://backend/app/core/agent_manager.py#L475-L538)
- [backend/app/core/agent_manager.py](file://backend/app/core/agent_manager.py#L586-L627)

### Security Module
Responsibilities:
- Prompt injection defense with layered detection and sanitization
- Rate limiting for security
- Encrypted data vault with access control levels

```mermaid
classDiagram
class PromptInjectionDefender {
+validate_input(user_input, context) ValidationResult
+create_secure_prompt(system_prompt, user_input) str
}
class ValidationResult {
+is_valid : bool
+threat_level : ThreatLevel
+sanitized_input : str
+detected_patterns : str[]
+recommendations : str[]
}
class RateLimiter {
+check_limit(key) bool
}
class DataVault {
+store(key, value, access_level) bool
+retrieve(key, requester_level) str?
+access_log : List
}
PromptInjectionDefender --> ValidationResult : "produces"
PromptInjectionDefender --> RateLimiter : "uses"
DataVault --> "encrypted storage" : "uses"
```

**Diagram sources**
- [backend/app/core/security.py](file://backend/app/core/security.py#L35-L107)
- [backend/app/core/security.py](file://backend/app/core/security.py#L25-L33)
- [backend/app/core/security.py](file://backend/app/core/security.py#L290-L318)
- [backend/app/core/security.py](file://backend/app/core/security.py#L325-L435)

**Section sources**
- [backend/app/core/security.py](file://backend/app/core/security.py#L35-L107)
- [backend/app/core/security.py](file://backend/app/core/security.py#L290-L318)
- [backend/app/core/security.py](file://backend/app/core/security.py#L325-L435)

### API Workflow: Chat Through Orchestrator
```mermaid
sequenceDiagram
participant Client as "Client"
participant API as "FastAPI /api/chat"
participant ORCH as "CoreOrchestrator"
participant PM as "ProviderManager"
participant OLL as "OllamaProvider"
Client->>API : POST /api/chat {message, model}
API->>ORCH : submit_action(CHAT, parameters, security_level=LOW)
ORCH->>ORCH : auto-approve (LOW)
ORCH->>PM : get_provider(default)
PM-->>ORCH : OllamaProvider
ORCH->>OLL : chat(messages, model)
OLL-->>ORCH : ChatResponse
ORCH-->>API : SystemAction.completed
API-->>Client : ChatResponse
```

**Diagram sources**
- [backend/app/main.py](file://backend/app/main.py#L131-L182)
- [backend/app/core/orchestrator.py](file://backend/app/core/orchestrator.py#L169-L224)
- [backend/app/core/providers.py](file://backend/app/core/providers.py#L470-L483)
- [backend/app/core/providers.py](file://backend/app/core/providers.py#L109-L143)

### API Workflow: Skill Execution Delegation
```mermaid
sequenceDiagram
participant Client as "Client"
participant API as "FastAPI /api/actions"
participant ORCH as "CoreOrchestrator"
participant AM as "AgentManager"
Client->>API : POST /api/actions {action_type=skill_execution, skill_id}
API->>ORCH : submit_action(SKILL_EXECUTION, parameters, skill_id)
ORCH->>ORCH : determine security level (HIGH)
ORCH-->>API : ActionStatus.PENDING
API-->>Client : action_id, requires_approval=true
Client->>API : POST /api/actions/{action_id}/approve {approved=true}
API->>ORCH : approve_action(action_id, approved=true)
ORCH->>AM : create_agent(skill_id, resource_limits)
AM-->>ORCH : AgentInstance
ORCH-->>API : ActionStatus.COMPLETED (delegated_to_agent_manager)
API-->>Client : Status
```

**Diagram sources**
- [backend/app/main.py](file://backend/app/main.py#L241-L299)
- [backend/app/core/orchestrator.py](file://backend/app/core/orchestrator.py#L169-L224)
- [backend/app/core/orchestrator.py](file://backend/app/core/orchestrator.py#L376-L428)
- [backend/app/core/agent_manager.py](file://backend/app/core/agent_manager.py#L149-L192)

### Sandbox Flow: gVisor Container Creation
```mermaid
flowchart TD
Start(["Create Agent"]) --> Detect["Detect Sandbox Runtime"]
Detect --> CheckGvisor{"gVisor available?"}
CheckGvisor --> |Yes| PrepareRootFS["Prepare Minimal RootFS"]
CheckGvisor --> |No| PrepareRootFS
PrepareRootFS --> CreateOCI["Create OCI Config"]
CreateOCI --> CreateContainer["runsc create ..."]
CreateContainer --> StartContainer["runsc start ..."]
StartContainer --> Running["Agent Running"]
Running --> ExecCmd["Execute Command in Sandbox"]
ExecCmd --> StopAgent["Stop Agent"]
StopAgent --> DeleteContainer["runsc delete ..."]
DeleteContainer --> End(["Cleanup Complete"])
```

**Diagram sources**
- [backend/app/core/agent_manager.py](file://backend/app/core/agent_manager.py#L99-L114)
- [backend/app/core/agent_manager.py](file://backend/app/core/agent_manager.py#L194-L202)
- [backend/app/core/agent_manager.py](file://backend/app/core/agent_manager.py#L203-L261)
- [backend/app/core/agent_manager.py](file://backend/app/core/agent_manager.py#L498-L511)

## Dependency Analysis
- Singletons: Each core component exposes a singleton accessor to ensure centralized, shared state across the application.
- Dependency Injection: FastAPI endpoints depend on singletons from the core module, enabling loose coupling and testability.
- Event-driven: Orchestrator schedules actions asynchronously; channels and providers operate independently; AgentManager executes commands asynchronously.

```mermaid
graph LR
MAIN["backend/app/main.py"] --> ORCH["get_orchestrator()"]
MAIN --> PM["get_provider_manager()"]
MAIN --> CM["get_channel_manager()"]
MAIN --> AM["get_agent_manager()"]
MAIN --> DEF["get_defender()"]
MAIN --> VAULT["get_vault()"]
ORCH --> PM
ORCH --> CM
ORCH --> AM
ORCH --> DEF
```

**Diagram sources**
- [backend/app/main.py](file://backend/app/main.py#L14-L16)
- [backend/app/core/orchestrator.py](file://backend/app/core/orchestrator.py#L481-L486)
- [backend/app/core/providers.py](file://backend/app/core/providers.py#L530-L545)
- [backend/app/core/channels.py](file://backend/app/core/channels.py#L509-L524)
- [backend/app/core/agent_manager.py](file://backend/app/core/agent_manager.py#L703-L708)
- [backend/app/core/security.py](file://backend/app/core/security.py#L442-L455)

**Section sources**
- [backend/app/main.py](file://backend/app/main.py#L14-L16)
- [backend/app/core/__init__.py](file://backend/app/core/__init__.py#L5-L18)

## Performance Considerations
- Asynchronous execution: Orchestrator and managers use asyncio to avoid blocking I/O and improve throughput.
- Provider caching: ProviderManager caches provider instances and configurations to minimize overhead.
- Resource limits: AgentManager enforces CPU, memory, and process limits to prevent resource exhaustion.
- Health checks: ProviderManager and ChannelManager provide health monitoring to detect degraded services early.
- Audit logging: Security audit logs are written to both memory and file for performance and persistence.

[No sources needed since this section provides general guidance]

## Troubleshooting Guide
Common issues and resolutions:
- Ollama connectivity: The Orchestrator and API check Ollama availability; ensure the service is running locally on the default port.
- Provider registration failures: Verify provider type, name, and required credentials; use health checks to diagnose.
- Channel authorization errors: Confirm user allowlists and channel configuration; use binding APIs to authorize users.
- Agent sandbox unavailable: Install gVisor or Kata Containers; AgentManager detects runtime availability and falls back gracefully.
- Security alerts: Review prompt injection defender logs and recommendations; adjust thresholds or sanitize inputs accordingly.

**Section sources**
- [backend/app/core/orchestrator.py](file://backend/app/core/orchestrator.py#L131-L145)
- [backend/app/core/providers.py](file://backend/app/core/providers.py#L495-L504)
- [backend/app/core/channels.py](file://backend/app/core/channels.py#L484-L490)
- [backend/app/core/agent_manager.py](file://backend/app/core/agent_manager.py#L99-L114)
- [backend/app/core/security.py](file://backend/app/core/security.py#L176-L180)

## Conclusion
ClosedPaw’s core architecture centers on a Zero-Trust Orchestrator that governs action lifecycle, security classification, and auditing. Provider and Channel Managers offer flexible, dynamic integrations, while the Agent Manager ensures safe, sandboxed execution of skills. The Security Module provides robust defenses and secure secret storage. Together, these components form a cohesive, event-driven system with strong isolation and observability.

[No sources needed since this section summarizes without analyzing specific files]

## Appendices

### Practical Usage Examples

- Submit a chat action:
  - Endpoint: POST /api/chat
  - Behavior: Submits a CHAT action; LOW security auto-executes; returns action_id and status
  - Reference: [backend/app/main.py](file://backend/app/main.py#L131-L182)

- Approve a pending action (HITL):
  - Endpoint: POST /api/actions/{action_id}/approve
  - Behavior: Approve or reject a PENDING action; triggers execution if approved
  - Reference: [backend/app/main.py](file://backend/app/main.py#L284-L299), [backend/app/core/orchestrator.py](file://backend/app/core/orchestrator.py#L376-L428)

- Register a cloud provider:
  - Endpoint: POST /api/providers/register
  - Behavior: Registers OpenAI, Anthropic, Google, or Mistral with API keys and defaults
  - Reference: [backend/app/main.py](file://backend/app/main.py#L403-L435), [backend/app/core/providers.py](file://backend/app/core/providers.py#L429-L457)

- Enable a skill:
  - Endpoint: POST /api/skills/{skill_id}/enable
  - Behavior: Enables a skill for execution; Orchestrator delegates to Agent Manager
  - Reference: [backend/app/main.py](file://backend/app/main.py#L357-L379), [backend/app/core/orchestrator.py](file://backend/app/core/orchestrator.py#L333-L351)

- Create a sandboxed agent:
  - Behavior: AgentManager creates gVisor/Kata containers with resource limits
  - Reference: [backend/app/core/agent_manager.py](file://backend/app/core/agent_manager.py#L149-L192)

- File system skill sandbox:
  - Behavior: FileSystemSkill operates within a restricted sandbox with path validation and size limits
  - Reference: [skills/filesystem/skill.py](file://skills/filesystem/skill.py#L77-L109), [skills/filesystem/skill.py](file://skills/filesystem/skill.py#L133-L208)

### Configuration Notes
- CORS: Only allows localhost origins for security
- Host binding: Uvicorn runs on 127.0.0.1 by default
- Logging: Orchestrator writes audit logs to a temporary file for security monitoring

**Section sources**
- [backend/app/main.py](file://backend/app/main.py#L80-L87)
- [backend/app/main.py](file://backend/app/main.py#L557-L567)
- [backend/app/core/orchestrator.py](file://backend/app/core/orchestrator.py#L19-L28)

### Dependencies Overview
- Web framework: FastAPI, Uvicorn
- Data validation: Pydantic
- HTTP client: httpx
- Security: cryptography, pynacl, python-jose, passlib
- SQLAlchemy and Alembic for persistence (future use)
- Testing: pytest, pytest-asyncio

**Section sources**
- [backend/requirements.txt](file://backend/requirements.txt#L1-L36)