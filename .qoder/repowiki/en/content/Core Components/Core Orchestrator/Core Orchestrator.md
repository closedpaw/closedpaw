# Core Orchestrator

<cite>
**Referenced Files in This Document**
- [orchestrator.py](file://backend/app/core/orchestrator.py)
- [security.py](file://backend/app/core/security.py)
- [main.py](file://backend/app/main.py)
- [agent_manager.py](file://backend/app/core/agent_manager.py)
- [providers.py](file://backend/app/core/providers.py)
- [channels.py](file://backend/app/core/channels.py)
- [__init__.py](file://backend/app/core/__init__.py)
- [README.md](file://README.md)
- [test_security.py](file://backend/tests/test_security.py)
- [skill.py](file://skills/filesystem/skill.py)
</cite>

## Update Summary
**Changes Made**
- Enhanced action type mappings in validate_action method with new action types: file_write, file_delete, command_exec, and network_request
- Updated security level assessment logic to handle new action categories
- Improved action validation workflow with comprehensive type mapping support
- Enhanced documentation to reflect expanded action tracking capabilities

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
This document describes the Core Orchestrator component that serves as the central coordination hub for the ClosedPaw system. It manages all system operations with a Zero-Trust security model, including action lifecycle management from PENDING to COMPLETED, security level classification (LOW, MEDIUM, HIGH, CRITICAL), and comprehensive audit logging. The orchestrator implements a singleton pattern via a factory function, initializes the LLM gateway, Human-in-the-Loop (HITL) interface, and skill loaders, and coordinates execution across supported action types (CHAT, SKILL_EXECUTION, MODEL_SWITCH). It also documents error handling strategies, graceful shutdown procedures, security configuration options, rate limiting, and timeout settings.

**Updated** Enhanced with expanded action type mappings including file_write, file_delete, command_exec, and network_request for improved action tracking and security level assessment.

## Project Structure
The Core Orchestrator resides in the backend application's core module alongside security, agent management, provider gateways, and channel integrations. The orchestrator integrates tightly with the FastAPI application lifecycle and exposes REST endpoints for action submission, approval, status monitoring, and audit logging.

```mermaid
graph TB
subgraph "Backend Core"
ORCH["Core Orchestrator<br/>orchestrator.py"]
SEC["Security Module<br/>security.py"]
AGM["Agent Manager<br/>agent_manager.py"]
PROV["Provider Manager<br/>providers.py"]
CHAN["Channel Manager<br/>channels.py"]
end
subgraph "Application"
MAIN["FastAPI App<br/>main.py"]
INIT["Core Init Export<br/>__init__.py"]
end
MAIN --> ORCH
ORCH --> AGM
ORCH --> PROV
ORCH --> CHAN
ORCH --> SEC
INIT --> ORCH
```

**Diagram sources**
- [main.py](file://backend/app/main.py#L59-L70)
- [__init__.py](file://backend/app/core/__init__.py#L5-L18)
- [orchestrator.py](file://backend/app/core/orchestrator.py#L87-L130)

**Section sources**
- [README.md](file://README.md#L75-L96)
- [__init__.py](file://backend/app/core/__init__.py#L1-L18)

## Core Components
- CoreOrchestrator: Central controller managing actions, security levels, audit logging, and execution pipeline.
- ActionType: Enumerates supported action categories (CHAT, SKILL_EXECUTION, MODEL_SWITCH, API_CALL, FILE_OPERATION, CONFIG_CHANGE).
- ActionStatus: Enumerates lifecycle states (PENDING, APPROVED, REJECTED, EXECUTING, COMPLETED, FAILED).
- SecurityLevel: Classifies risk (LOW, MEDIUM, HIGH, CRITICAL) with corresponding approval and logging requirements.
- AuditLogEntry: Structured audit trail entries capturing action metadata and outcomes.
- SystemAction: Runtime representation of an action with lifecycle tracking and result/error fields.
- ActionValidationResult: New validation result class for structured action validation responses.
- Singleton pattern: get_orchestrator() ensures a single orchestrator instance across the application.

Key orchestration responsibilities:
- Action submission with automatic security classification.
- Human-in-the-Loop approval for HIGH and CRITICAL actions.
- Execution pipeline for different action types with timeouts and error handling.
- Audit logging for all actions and outcomes.
- Graceful shutdown with pending action completion checks.
- **Enhanced**: Expanded action validation with comprehensive type mapping support including file_write, file_delete, command_exec, and network_request.

**Section sources**
- [orchestrator.py](file://backend/app/core/orchestrator.py#L31-L85)
- [orchestrator.py](file://backend/app/core/orchestrator.py#L87-L130)
- [orchestrator.py](file://backend/app/core/orchestrator.py#L169-L224)
- [orchestrator.py](file://backend/app/core/orchestrator.py#L477-L486)
- [orchestrator.py](file://backend/app/core/orchestrator.py#L86-L92)
- [orchestrator.py](file://backend/app/core/orchestrator.py#L259-L297)

## Architecture Overview
The Core Orchestrator sits at the center of the system, coordinating:
- LLM gateway initialization and model switching.
- Human-in-the-Loop approval workflows for risky actions.
- Skill execution delegation to the Agent Manager with sandboxed containers.
- Audit logging and security validation.

```mermaid
sequenceDiagram
participant Client as "Client"
participant API as "FastAPI App"
participant ORCH as "Core Orchestrator"
participant AGM as "Agent Manager"
participant PROV as "Provider Manager"
participant SEC as "Security Module"
Client->>API : "POST /api/chat"
API->>ORCH : "submit_action(ActionType.CHAT, parameters)"
ORCH->>ORCH : "_determine_security_level()"
ORCH->>ORCH : "store action, log audit"
alt LOW/MEDIUM
ORCH->>ORCH : "auto-approve"
ORCH->>ORCH : "_execute_chat()"
ORCH-->>API : "SystemAction"
else HIGH/CRITICAL
ORCH-->>API : "SystemAction (PENDING)"
end
API-->>Client : "ChatResponse"
Client->>API : "GET /api/actions/pending"
API->>ORCH : "get_pending_actions()"
ORCH-->>API : "List of pending actions"
API-->>Client : "Pending actions"
Client->>API : "POST /api/actions/{id}/approve"
API->>ORCH : "approve_action(id, approved)"
ORCH->>ORCH : "status=APPROVED, schedule execution"
ORCH->>ORCH : "_execute_action(id)"
ORCH->>AGM : "delegate skill execution (if applicable)"
ORCH->>PROV : "multi-provider chat (if applicable)"
ORCH->>SEC : "validate inputs (defense)"
ORCH-->>API : "updated SystemAction"
API-->>Client : "Approval result"
```

**Diagram sources**
- [main.py](file://backend/app/main.py#L131-L182)
- [main.py](file://backend/app/main.py#L265-L299)
- [orchestrator.py](file://backend/app/core/orchestrator.py#L169-L224)
- [orchestrator.py](file://backend/app/core/orchestrator.py#L251-L302)
- [agent_manager.py](file://backend/app/core/agent_manager.py#L65-L98)
- [providers.py](file://backend/app/core/providers.py#L418-L483)
- [security.py](file://backend/app/core/security.py#L35-L181)

## Detailed Component Analysis

### CoreOrchestrator Class
The CoreOrchestrator is the central controller responsible for:
- Initialization of LLM gateway, HITL interface, data vault, and skills.
- Action lifecycle management with automatic security classification.
- Execution pipeline for CHAT, SKILL_EXECUTION, and MODEL_SWITCH actions.
- Audit logging and status tracking.
- Graceful shutdown with pending action completion checks.
- **Enhanced**: Expanded action validation with comprehensive type mapping support including file_write, file_delete, command_exec, and network_request.

```mermaid
classDiagram
class CoreOrchestrator {
+dict actions
+list audit_logs
+dict skills
+object llm_gateway
+object hitl_interface
+object data_vault
+bool running
+dict security_config
+initialize() async
+submit_action(action_type, parameters, skill_id, security_level) async
+approve_action(action_id, approved, user_id) bool
+get_pending_actions() list
+get_action_status(action_id) SystemAction
+get_audit_logs(limit) list
+shutdown() async
+validate_action(action) ActionValidationResult
-_init_llm_gateway() async
-_init_hitl_interface() async
-_init_data_vault() async
-_load_skills() async
-_determine_security_level(action_type, parameters) SecurityLevel
-_execute_action(action_id) async
-_execute_chat(action) async
-_execute_skill(action) async
-_execute_model_switch(action) async
-_log_audit_event(action_id, action_type, skill_id, status, outcome, details) void
}
class SystemAction {
+string id
+ActionType action_type
+string skill_id
+dict parameters
+SecurityLevel security_level
+ActionStatus status
+datetime created_at
+datetime approved_at
+datetime completed_at
+any result
+string error
}
class AuditLogEntry {
+datetime timestamp
+string action_id
+ActionType action_type
+string skill_id
+string user_id
+ActionStatus status
+dict details
+string outcome
+string ip_address
}
class ActionValidationResult {
+bool is_valid
+bool requires_approval
+string security_level
+string action_type
+string reason
}
class ActionType {
<<enum>>
CHAT
SKILL_EXECUTION
MODEL_SWITCH
API_CALL
FILE_OPERATION
CONFIG_CHANGE
}
class ActionStatus {
<<enum>>
PENDING
APPROVED
REJECTED
EXECUTING
COMPLETED
FAILED
}
class SecurityLevel {
<<enum>>
LOW
MEDIUM
HIGH
CRITICAL
}
CoreOrchestrator --> SystemAction : "manages"
CoreOrchestrator --> AuditLogEntry : "logs"
CoreOrchestrator --> ActionValidationResult : "creates"
SystemAction --> ActionType : "has"
SystemAction --> ActionStatus : "has"
SystemAction --> SecurityLevel : "has"
```

**Diagram sources**
- [orchestrator.py](file://backend/app/core/orchestrator.py#L87-L486)

**Section sources**
- [orchestrator.py](file://backend/app/core/orchestrator.py#L87-L130)
- [orchestrator.py](file://backend/app/core/orchestrator.py#L131-L167)
- [orchestrator.py](file://backend/app/core/orchestrator.py#L169-L224)
- [orchestrator.py](file://backend/app/core/orchestrator.py#L225-L250)
- [orchestrator.py](file://backend/app/core/orchestrator.py#L251-L302)
- [orchestrator.py](file://backend/app/core/orchestrator.py#L303-L375)
- [orchestrator.py](file://backend/app/core/orchestrator.py#L376-L428)
- [orchestrator.py](file://backend/app/core/orchestrator.py#L429-L450)
- [orchestrator.py](file://backend/app/core/orchestrator.py#L451-L475)
- [orchestrator.py](file://backend/app/core/orchestrator.py#L477-L486)
- [orchestrator.py](file://backend/app/core/orchestrator.py#L86-L92)
- [orchestrator.py](file://backend/app/core/orchestrator.py#L259-L297)

### Enhanced Action Validation System
**Enhanced** The ActionValidationResult class and validate_action method provide structured validation responses for Human-in-the-Loop workflows with expanded action type support:

- ActionValidationResult: Provides structured validation outcomes with approval requirements and security levels.
- validate_action: Maps action types to ActionType enums, determines security levels, and decides approval requirements.
- **Expanded Type Mapping**: Supports comprehensive action formats including file_write, file_delete, command_exec, and network_request.
- Automated approval decisions based on security level thresholds.

```mermaid
flowchart TD
Start(["validate_action"]) --> GetType["Extract action type"]
GetType --> MapType["Map to ActionType enum<br/>with expanded support"]
MapType --> DetermineSec["Determine security level"]
DetermineSec --> CheckReq{"Requires approval?"}
CheckReq --> |HIGH/CRITICAL| ReturnHigh["requires_approval = True"]
CheckReq --> |LOW/MEDIUM| ReturnLow["requires_approval = False"]
ReturnHigh --> CreateResult["Create ActionValidationResult"]
ReturnLow --> CreateResult
CreateResult --> Done["Return validation result"]
```

**Diagram sources**
- [orchestrator.py](file://backend/app/core/orchestrator.py#L259-L297)

**Section sources**
- [orchestrator.py](file://backend/app/core/orchestrator.py#L86-L92)
- [orchestrator.py](file://backend/app/core/orchestrator.py#L259-L297)
- [test_security.py](file://backend/tests/test_security.py#L159-L189)

### Enhanced Action Type Mapping
**New** The validate_action method now includes comprehensive action type mappings for improved action tracking and security assessment:

- **File Operations**: "file_write" → FILE_OPERATION, "file_delete" → FILE_OPERATION
- **Command Execution**: "command_exec" → SKILL_EXECUTION  
- **Network Requests**: "network_request" → API_CALL
- **Legacy Support**: Maintains backward compatibility with "read", "write", "delete" mappings
- **Security Classification**: Each mapped type inherits appropriate security levels based on action characteristics

```mermaid
flowchart TD
A["Action Type String"] --> B{"Check Type Mapping"}
B --> |"file_write"| C["FILE_OPERATION<br/>HIGH Risk"]
B --> |"file_delete"| D["FILE_OPERATION<br/>HIGH Risk"]
B --> |"command_exec"| E["SKILL_EXECUTION<br/>HIGH Risk"]
B --> |"network_request"| F["API_CALL<br/>HIGH Risk"]
B --> |"read/write/delete"| G["FILE_OPERATION<br/>MEDIUM Risk"]
B --> |"chat/calculate/search"| H["CHAT<br/>LOW Risk"]
B --> |"skill/config/api"| I["SKILL/API<br/>MEDIUM Risk"]
B --> |"config_change"| J["CONFIG_CHANGE<br/>CRITICAL Risk"]
```

**Diagram sources**
- [orchestrator.py](file://backend/app/core/orchestrator.py#L271-L286)

**Section sources**
- [orchestrator.py](file://backend/app/core/orchestrator.py#L271-L286)
- [test_security.py](file://backend/tests/test_security.py#L164-L168)

### Action Submission Workflow
The submit_action method:
- Determines security level automatically if not provided.
- Creates a SystemAction and stores it.
- Logs an initial audit entry with action metadata.
- For HIGH/CRITICAL actions, returns PENDING for HITL approval.
- For LOW/MEDIUM actions, auto-approves and schedules execution.

```mermaid
flowchart TD
Start(["submit_action"]) --> CheckLevel["security_level provided?"]
CheckLevel --> |No| CalcLevel["_determine_security_level()"]
CheckLevel --> |Yes| UseProvided["Use provided level"]
CalcLevel --> CreateAction["Create SystemAction"]
UseProvided --> CreateAction
CreateAction --> Store["Store in actions dict"]
Store --> Audit["Log audit event (PENDING)"]
Audit --> LevelCheck{"HIGH/CRITICAL?"}
LevelCheck --> |Yes| ReturnPending["Return PENDING action"]
LevelCheck --> |No| AutoApprove["status=APPROVED, approved_at=now"]
AutoApprove --> ScheduleExec["asyncio.create_task(_execute_action)"]
ScheduleExec --> ReturnApproved["Return APPROVED action"]
```

**Diagram sources**
- [orchestrator.py](file://backend/app/core/orchestrator.py#L169-L224)
- [orchestrator.py](file://backend/app/core/orchestrator.py#L225-L250)

**Section sources**
- [orchestrator.py](file://backend/app/core/orchestrator.py#L169-L224)

### Automatic Security Level Determination
Security classification is based on action type and parameters:
- CONFIG_CHANGE: CRITICAL.
- FILE_OPERATION: HIGH for destructive operations (delete, write, modify), otherwise MEDIUM.
- SKILL_EXECUTION: HIGH for system-related skills, otherwise MEDIUM.
- CHAT: LOW.
- Other actions default to MEDIUM.

```mermaid
flowchart TD
A["Action Type"] --> B{"CONFIG_CHANGE?"}
B --> |Yes| C["CRITICAL"]
B --> |No| D{"FILE_OPERATION?"}
D --> |Yes| E{"operation in ['delete','write','modify']?"}
E --> |Yes| F["HIGH"]
E --> |No| G["MEDIUM"]
D --> |No| H{"SKILL_EXECUTION?"}
H --> |Yes| I{"skill_id in ['filesystem','system']?"}
I --> |Yes| J["HIGH"]
I --> |No| K["MEDIUM"]
H --> |No| L{"CHAT?"}
L --> |Yes| M["LOW"]
L --> |No| N["MEDIUM"]
```

**Diagram sources**
- [orchestrator.py](file://backend/app/core/orchestrator.py#L225-L250)

**Section sources**
- [orchestrator.py](file://backend/app/core/orchestrator.py#L225-L250)

### Human-in-the-Loop Approval Process
High-risk actions are placed in PENDING until approved. The approve_action method:
- Validates the action exists and is PENDING.
- Updates status to APPROVED or REJECTED.
- Logs audit entries with approver identity.
- Schedules execution for approved actions.

```mermaid
sequenceDiagram
participant Client as "Client"
participant API as "FastAPI App"
participant ORCH as "Core Orchestrator"
Client->>API : "GET /api/actions/pending"
API->>ORCH : "get_pending_actions()"
ORCH-->>API : "List of PENDING actions"
API-->>Client : "Pending actions"
Client->>API : "POST /api/actions/{id}/approve {approved : true}"
API->>ORCH : "approve_action(id, approved=true, user_id)"
ORCH->>ORCH : "status=APPROVED, approved_at=now"
ORCH->>ORCH : "schedule _execute_action(id)"
ORCH-->>API : "Success"
API-->>Client : "Approved"
```

**Diagram sources**
- [main.py](file://backend/app/main.py#L265-L299)
- [orchestrator.py](file://backend/app/core/orchestrator.py#L376-L428)

**Section sources**
- [orchestrator.py](file://backend/app/core/orchestrator.py#L376-L428)
- [main.py](file://backend/app/main.py#L265-L299)

### Execution Pipeline for Different Action Types
- CHAT: Sends prompt to local Ollama gateway with timeouts and error handling.
- SKILL_EXECUTION: Delegates to Agent Manager with sandboxed execution (returns delegation notice).
- MODEL_SWITCH: Verifies model availability via Ollama and returns success or error.

```mermaid
flowchart TD
ExecStart(["_execute_action"]) --> Type{"action_type"}
Type --> |CHAT| Chat["_execute_chat"]
Type --> |SKILL_EXECUTION| Skill["_execute_skill"]
Type --> |MODEL_SWITCH| Model["_execute_model_switch"]
Type --> |Other| NotImplemented["Return not_implemented"]
Chat --> ChatOK{"HTTP 200?"}
ChatOK --> |Yes| ChatRes["Parse response"]
ChatOK --> |No| ChatErr["Return error status"]
ChatRes --> Done["Mark COMPLETED"]
ChatErr --> Done
Skill --> SkillCheck{"skill_id exists and enabled?"}
SkillCheck --> |Yes| Delegate["Return delegation notice"]
SkillCheck --> |No| SkillErr["Return error"]
Delegate --> Done
SkillErr --> Done
Model --> ModelAvail{"Ollama tags OK?"}
ModelAvail --> |Yes| ModelCheck{"model in available?"}
ModelCheck --> |Yes| ModelOK["Return success"]
ModelCheck --> |No| ModelErr["Return error + available"]
ModelAvail --> |No| ModelErr
ModelOK --> Done
ModelErr --> Done
```

**Diagram sources**
- [orchestrator.py](file://backend/app/core/orchestrator.py#L251-L302)
- [orchestrator.py](file://backend/app/core/orchestrator.py#L303-L332)
- [orchestrator.py](file://backend/app/core/orchestrator.py#L333-L350)
- [orchestrator.py](file://backend/app/core/orchestrator.py#L352-L375)

**Section sources**
- [orchestrator.py](file://backend/app/core/orchestrator.py#L251-L302)
- [orchestrator.py](file://backend/app/core/orchestrator.py#L303-L375)

### Audit Logging Implementation
All actions are logged with structured entries containing timestamps, action identifiers, types, statuses, outcomes, and details. Audit logs are retained in-memory and can be queried via API endpoints.

```mermaid
sequenceDiagram
participant ORCH as "Core Orchestrator"
participant AUDIT as "AuditLogEntry"
participant LOG as "Logger"
ORCH->>AUDIT : "Create AuditLogEntry"
ORCH->>ORCH : "Append to audit_logs"
ORCH->>LOG : "Log audit event"
LOG-->>ORCH : "Event recorded"
```

**Diagram sources**
- [orchestrator.py](file://backend/app/core/orchestrator.py#L429-L450)

**Section sources**
- [orchestrator.py](file://backend/app/core/orchestrator.py#L429-L450)
- [main.py](file://backend/app/main.py#L322-L340)

### Singleton Pattern and Initialization
The orchestrator uses a singleton pattern via get_orchestrator(), ensuring a single instance across the application. Initialization includes:
- LLM gateway setup (local Ollama).
- HITL interface initialization placeholder.
- Data vault initialization placeholder.
- Dynamic skill loading.

```mermaid
sequenceDiagram
participant APP as "FastAPI App"
participant ORCH as "Core Orchestrator"
participant GET as "get_orchestrator()"
APP->>GET : "get_orchestrator()"
GET-->>APP : "Singleton instance"
APP->>ORCH : "await initialize()"
ORCH->>ORCH : "_init_llm_gateway()"
ORCH->>ORCH : "_init_hitl_interface()"
ORCH->>ORCH : "_init_data_vault()"
ORCH->>ORCH : "_load_skills()"
ORCH-->>APP : "running=True"
```

**Diagram sources**
- [main.py](file://backend/app/main.py#L59-L70)
- [orchestrator.py](file://backend/app/core/orchestrator.py#L112-L129)
- [orchestrator.py](file://backend/app/core/orchestrator.py#L131-L167)
- [orchestrator.py](file://backend/app/core/orchestrator.py#L481-L486)

**Section sources**
- [orchestrator.py](file://backend/app/core/orchestrator.py#L477-L486)
- [main.py](file://backend/app/main.py#L59-L70)

### Security Configuration Options, Rate Limiting, and Timeouts
Security configuration includes:
- require_hitl_for_critical: Enforces HITL for CRITICAL actions.
- log_all_actions: Controls audit logging.
- max_action_timeout: Default timeout for actions.
- rate_limit_per_minute: Requests per minute threshold.

Rate limiting is integrated into the security module's input validation and can escalate threats to CRITICAL level when exceeded.

**Section sources**
- [orchestrator.py](file://backend/app/core/orchestrator.py#L102-L108)
- [security.py](file://backend/app/core/security.py#L290-L318)
- [security.py](file://backend/app/core/security.py#L163-L180)

### Practical Examples

- Creating a CHAT action:
  - Submit a CHAT action with parameters including message and model.
  - For LOW security, it auto-executes and returns a response.
  - For HIGH/CRITICAL, it returns PENDING and requires approval.

- **Enhanced** Validating actions for Human-in-the-Loop with expanded type support:
  - Use validate_action() to determine approval requirements for new action types.
  - Example dangerous actions: {"type": "file_write", "path": "/etc/passwd", "content": "hacked"} requires approval.
  - Command execution: {"type": "command_exec", "command": "rm -rf /"} requires approval.
  - Network requests: {"type": "network_request", "url": "http://evil.com/exfil"} requires approval.
  - Safe actions: {"type": "read", "path": "/tmp/data.txt"} auto-approved.

- Approving a PENDING action:
  - Retrieve pending actions via API.
  - Approve or reject using the approval endpoint.
  - Approved actions are scheduled for execution.

- Audit log analysis:
  - Query audit logs via API endpoint.
  - Inspect timestamps, action types, statuses, outcomes, and details.

**Section sources**
- [main.py](file://backend/app/main.py#L131-L182)
- [main.py](file://backend/app/main.py#L265-L299)
- [main.py](file://backend/app/main.py#L322-L340)
- [test_security.py](file://backend/tests/test_security.py#L159-L189)

## Dependency Analysis
The Core Orchestrator depends on:
- Agent Manager for sandboxed skill execution.
- Provider Manager for multi-provider LLM operations.
- Security Module for input validation and rate limiting.
- Channels Manager for multi-channel integration (external to orchestrator).
- FastAPI application lifecycle for startup/shutdown.

```mermaid
graph LR
ORCH["Core Orchestrator"] --> AGM["Agent Manager"]
ORCH --> PROV["Provider Manager"]
ORCH --> SEC["Security Module"]
ORCH --> CHAN["Channel Manager"]
MAIN["FastAPI App"] --> ORCH
```

**Diagram sources**
- [main.py](file://backend/app/main.py#L14-L16)
- [agent_manager.py](file://backend/app/core/agent_manager.py#L65-L98)
- [providers.py](file://backend/app/core/providers.py#L418-L483)
- [security.py](file://backend/app/core/security.py#L35-L107)

**Section sources**
- [main.py](file://backend/app/main.py#L14-L16)
- [agent_manager.py](file://backend/app/core/agent_manager.py#L65-L98)
- [providers.py](file://backend/app/core/providers.py#L418-L483)
- [security.py](file://backend/app/core/security.py#L35-L107)

## Performance Considerations
- Asynchronous execution: Actions are executed asynchronously to avoid blocking the main thread.
- Timeouts: Ollama calls and model switches include explicit timeouts to prevent hangs.
- Pending action wait: Shutdown waits briefly for executing actions to complete.
- Rate limiting: Integrated rate limiting prevents abuse and protects downstream services.
- **Enhanced**: Expanded action validation maintains performance with efficient type mapping and security assessment algorithms.

## Troubleshooting Guide
Common issues and resolutions:
- Ollama connectivity failures:
  - Verify local Ollama service is reachable on loopback interface.
  - Check model availability via tags endpoint.
- Action stuck in PENDING:
  - Confirm HITL approval via approval endpoint.
  - Check audit logs for rejection reasons.
- Execution errors:
  - Review action result and error fields.
  - Inspect audit logs for failure details.
- Graceful shutdown delays:
  - Pending actions are awaited; ensure actions complete or cancel appropriately.
- **Enhanced**: Action validation failures:
  - Verify action type mappings are correct for new types (file_write, file_delete, command_exec, network_request).
  - Check security level calculations for edge cases in expanded type support.

**Section sources**
- [orchestrator.py](file://backend/app/core/orchestrator.py#L131-L144)
- [orchestrator.py](file://backend/app/core/orchestrator.py#L463-L475)
- [main.py](file://backend/app/main.py#L101-L129)

## Conclusion
The Core Orchestrator is the central nervous system of the ClosedPaw system, enforcing Zero-Trust security through automatic security classification, human-in-the-loop approvals, robust audit logging, and sandboxed execution. Its singleton pattern, asynchronous execution model, and integration with security and provider modules make it a resilient and secure foundation for AI-assisted operations.

**Enhanced** Expanded with comprehensive action type mappings including file_write, file_delete, command_exec, and network_request, providing improved action tracking capabilities and more accurate security level assessment for diverse operational scenarios.

## Appendices

### API Endpoints Related to Orchestrator
- POST /api/chat: Submits a CHAT action and returns immediate or pending status.
- POST /api/models/switch: Switches to a specified model with validation.
- POST /api/actions: Submits a generic action with automatic security classification.
- GET /api/actions/pending: Lists pending actions requiring approval.
- POST /api/actions/{action_id}/approve: Approves or rejects a pending action.
- GET /api/actions/{action_id}: Retrieves status and results of a specific action.
- GET /api/audit-logs: Retrieves recent audit logs.

**Section sources**
- [main.py](file://backend/app/main.py#L131-L182)
- [main.py](file://backend/app/main.py#L213-L239)
- [main.py](file://backend/app/main.py#L241-L262)
- [main.py](file://backend/app/main.py#L265-L299)
- [main.py](file://backend/app/main.py#L301-L319)
- [main.py](file://backend/app/main.py#L322-L340)

### Enhanced Action Validation API
**Enhanced** The validate_action method provides structured validation responses for Human-in-the-Loop workflows with expanded type support:

- Input format: `{"type": "action_type", "parameters": {...}}`
- Output format: ActionValidationResult with approval requirements and security levels
- **Expanded Type Mapping Support**:
  - File Operations: read, write, file_write, delete, file_delete
  - Command Execution: calculate, search, chat, skill, command_exec
  - Configuration: config
  - API Calls: api, network_request
- Approval decisions: HIGH/CRITICAL actions require approval, LOW/MEDIUM auto-approved

**Section sources**
- [orchestrator.py](file://backend/app/core/orchestrator.py#L259-L297)
- [test_security.py](file://backend/tests/test_security.py#L159-L189)

### Security Level Assessment Matrix
**New** Comprehensive security classification for all supported action types:

| Action Type | Security Level | Approval Required | Risk Factors |
|-------------|----------------|-------------------|--------------|
| CHAT | LOW | No | Informational queries |
| FILE_OPERATION (read) | MEDIUM | No | File access within sandbox |
| FILE_OPERATION (write) | HIGH | Yes | File modification, potential data loss |
| FILE_OPERATION (delete) | HIGH | Yes | File deletion, data destruction |
| SKILL_EXECUTION (skill) | MEDIUM | No | Standard skill execution |
| SKILL_EXECUTION (command_exec) | HIGH | Yes | System command execution |
| API_CALL (api) | MEDIUM | No | Standard API communication |
| API_CALL (network_request) | HIGH | Yes | External network requests |
| CONFIG_CHANGE | CRITICAL | Yes | System configuration changes |

**Section sources**
- [orchestrator.py](file://backend/app/core/orchestrator.py#L233-L257)
- [test_security.py](file://backend/tests/test_security.py#L164-L168)