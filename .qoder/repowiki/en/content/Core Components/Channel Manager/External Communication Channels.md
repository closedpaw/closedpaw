# External Communication Channels

<cite>
**Referenced Files in This Document**
- [channels.py](file://backend/app/core/channels.py)
- [main.py](file://backend/app/main.py)
- [closedpaw.js](file://bin/closedpaw.js)
- [README.md](file://README.md)
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
This document explains the external communication channels supported by the system, focusing on Telegram, Discord, and Slack integrations. It covers authentication, message routing, rate limiting, error handling, and practical setup steps. The implementation centers around a unified channel abstraction with a shared configuration model and a channel manager that registers and controls channel instances.

## Project Structure
The channel implementations reside in the backend core module and are exposed via the FastAPI application. A command-line tool assists with initial configuration.

```mermaid
graph TB
subgraph "Backend"
A["channels.py<br/>Channel abstractions and implementations"]
B["main.py<br/>FastAPI endpoints for channel management"]
end
subgraph "CLI"
C["closedpaw.js<br/>Interactive configuration tool"]
end
D["External Services<br/>Telegram, Discord, Slack APIs"]
C --> B
B --> A
A --> D
```

**Diagram sources**
- [channels.py](file://backend/app/core/channels.py#L177-L382)
- [main.py](file://backend/app/main.py#L464-L529)
- [closedpaw.js](file://bin/closedpaw.js#L604-L677)

**Section sources**
- [channels.py](file://backend/app/core/channels.py#L1-L524)
- [main.py](file://backend/app/main.py#L1-L567)
- [closedpaw.js](file://bin/closedpaw.js#L600-L850)

## Core Components
- ChannelType: Enumerates supported channel types including telegram, discord, slack, webui, cli, and matrix.
- ChannelConfig: Holds channel-wide settings such as bot tokens, allowed users/channels, rate limits, and security flags.
- ChannelMessage: Standardized message envelope passed to the application’s message handler.
- BaseChannel: Abstract interface defining lifecycle and messaging operations.
- ChannelManager: Central registry and orchestrator for channel instances, including registration, startup, shutdown, and broadcasting.

Key configuration defaults:
- Rate limiting: per-user and global thresholds are defined in ChannelConfig.
- Allowed commands: default set includes chat, status, help.
- Pairing requirement: enabled by default for stricter access control.

**Section sources**
- [channels.py](file://backend/app/core/channels.py#L18-L77)
- [channels.py](file://backend/app/core/channels.py#L405-L503)

## Architecture Overview
The system integrates external chat platforms through asynchronous HTTP clients. Incoming messages are polled or fetched and routed into the application via a shared message handler. Outgoing messages are sent using platform-specific APIs with appropriate authorization headers.

```mermaid
sequenceDiagram
participant User as "User"
participant API as "FastAPI /api/channels"
participant Manager as "ChannelManager"
participant Channel as "BaseChannel subclass"
participant Ext as "External Platform API"
User->>API : "POST /api/channels/register"
API->>Manager : "register_channel(config)"
Manager->>Channel : "instantiate"
Channel->>Ext : "get_me() for auth test"
Ext-->>Channel : "identity info"
Channel-->>Manager : "ready"
Manager-->>API : "success"
User->>API : "POST /api/channels/start"
API->>Manager : "start_all()"
loop "Per-channel loop"
Manager->>Channel : "start()"
Channel->>Ext : "poll or connect"
end
```

**Diagram sources**
- [main.py](file://backend/app/main.py#L473-L520)
- [channels.py](file://backend/app/core/channels.py#L416-L450)

## Detailed Component Analysis

### TelegramChannel
- Polling mechanism: Uses long-polling via getUpdates with an offset to avoid duplicates and minimize missed messages.
- Update processing: Extracts chat_id, user_id, and text; validates presence; checks user allowlist; constructs ChannelMessage; invokes the global handler.
- Message routing: Sends Markdown-formatted messages using sendMessage with parse_mode.
- Authentication: Requires a bot token; fetches bot identity via getMe.
- Rate limiting: Implemented at the configuration level via ChannelConfig; enforcement occurs in the application’s orchestration layer.
- Error handling: Logs errors during polling and sending; continues polling on exceptions.

```mermaid
sequenceDiagram
participant TC as "TelegramChannel"
participant TG as "Telegram API"
participant APP as "Application Handler"
loop "Polling loop"
TC->>TG : "GET /getUpdates?offset=N&timeout=30"
TG-->>TC : "updates[]"
alt "Has message"
TC->>TC : "_process_update(update)"
TC->>APP : "_handle_message(ChannelMessage)"
else "No message"
TC->>TC : "continue"
end
end
participant CLI as "Client"
CLI->>TC : "send_message(channel_id, content)"
TC->>TG : "POST /sendMessage {chat_id, text, parse_mode}"
TG-->>TC : "result"
```

**Diagram sources**
- [channels.py](file://backend/app/core/channels.py#L202-L258)
- [channels.py](file://backend/app/core/channels.py#L259-L285)

**Section sources**
- [channels.py](file://backend/app/core/channels.py#L177-L285)

### DiscordChannel
- Integration: Uses the Discord API v10 with Authorization: Bot <token>.
- Message sending: Posts to channels/{channel_id}/messages with plain text content.
- Authentication: Validates identity via users/@me endpoint.
- Rate limiting: Configured via ChannelConfig; enforcement handled by the application layer.
- Error handling: Logs non-200/201 responses.

```mermaid
sequenceDiagram
participant DC as "DiscordChannel"
participant DISC as "Discord API v10"
participant APP as "Application Handler"
DC->>DISC : "GET /users/@me (Authorization : Bot)"
DISC-->>DC : "bot identity"
DC->>APP : "ready"
APP-->>DC : "messages to route"
DC->>DISC : "POST /channels/{id}/messages"
DISC-->>DC : "result"
```

**Diagram sources**
- [channels.py](file://backend/app/core/channels.py#L288-L334)

**Section sources**
- [channels.py](file://backend/app/core/channels.py#L288-L334)

### SlackChannel
- Integration: Uses Slack’s chat.postMessage endpoint with Authorization: Bearer <token>.
- Message sending: Sends plain text content to the specified channel.
- Authentication: Validates via auth.test endpoint.
- Rate limiting: Configured via ChannelConfig; enforcement handled by the application layer.
- Error handling: Logs failures when ok is false.

```mermaid
sequenceDiagram
participant SC as "SlackChannel"
participant SLK as "Slack API"
participant APP as "Application Handler"
SC->>SLK : "GET /auth.test (Authorization : Bearer)"
SLK-->>SC : "identity"
SC->>APP : "ready"
APP-->>SC : "messages to route"
SC->>SLK : "POST /chat.postMessage {channel, text}"
SLK-->>SC : "{ok : true/false}"
```

**Diagram sources**
- [channels.py](file://backend/app/core/channels.py#L336-L382)

**Section sources**
- [channels.py](file://backend/app/core/channels.py#L336-L382)

### ChannelManager and Registration
- Registration: Maps ChannelType to concrete channel classes and instantiates them with provided ChannelConfig.
- Lifecycle: Supports start_all and stop_all operations.
- Routing: Provides send_message and broadcast helpers; forwards messages to enabled channels.
- Status: Exposes channel counts and configuration summaries.

```mermaid
classDiagram
class ChannelManager {
+channels : Dict[str, BaseChannel]
+configs : Dict[str, ChannelConfig]
+register_channel(config) bool
+start_all() void
+stop_all() void
+send_message(name, id, content) void
+broadcast(content, channels) void
+bind_user(name, user_id, username) void
+get_status() Dict
}
class BaseChannel {
<<abstract>>
+start() void
+stop() void
+send_message(id, content) void
+get_me() Dict
+set_message_handler(handler) void
}
class TelegramChannel
class DiscordChannel
class SlackChannel
ChannelManager --> BaseChannel : "manages"
TelegramChannel --|> BaseChannel
DiscordChannel --|> BaseChannel
SlackChannel --|> BaseChannel
```

**Diagram sources**
- [channels.py](file://backend/app/core/channels.py#L405-L503)
- [channels.py](file://backend/app/core/channels.py#L177-L382)

**Section sources**
- [channels.py](file://backend/app/core/channels.py#L405-L503)

## Dependency Analysis
- HTTP client: httpx.AsyncClient is used across Telegram, Discord, and Slack implementations for outbound requests.
- Application integration: FastAPI endpoints expose channel registration, binding, and lifecycle control.
- CLI configuration: The interactive tool writes a channels.json file consumed by the configuration system.

```mermaid
graph LR
A["FastAPI endpoints<br/>/api/channels/*"] --> B["ChannelManager"]
B --> C["TelegramChannel"]
B --> D["DiscordChannel"]
B --> E["SlackChannel"]
C --> F["Telegram API"]
D --> G["Discord API v10"]
E --> H["Slack API"]
```

**Diagram sources**
- [main.py](file://backend/app/main.py#L466-L529)
- [channels.py](file://backend/app/core/channels.py#L177-L382)

**Section sources**
- [main.py](file://backend/app/main.py#L464-L529)
- [channels.py](file://backend/app/core/channels.py#L177-L382)

## Performance Considerations
- Polling overhead: TelegramChannel uses long-polling; tune timeout and offset handling to balance latency and missed updates.
- Concurrency: httpx.AsyncClient enables concurrent operations; ensure upstream platform rate limits are respected.
- Rate limiting: Configure per-user and global limits in ChannelConfig; enforce at the application level to prevent downstream throttling.
- Backoff: On exceptions during polling, the implementation retries after a short delay; consider jitter for resilience.

[No sources needed since this section provides general guidance]

## Troubleshooting Guide
Common issues and resolutions:
- Missing bot token:
  - Symptom: Warning logged and channel does not start.
  - Resolution: Provide a valid token in ChannelConfig and restart the channel.
- Unauthorized access:
  - Symptom: Messages rejected for non-allowlisted users.
  - Resolution: Bind the user to the channel allowlist via the API or CLI tool.
- Sending failures:
  - Telegram: Check parse_mode and content length; verify token permissions.
  - Discord: Confirm Authorization header format and channel accessibility.
  - Slack: Verify Bearer token and channel existence.
- Health and status:
  - Use the status endpoint to confirm connectivity and model availability.

Practical steps:
- Register a channel via the API with bot_token and allowed_users.
- Start all channels to initialize connections.
- Use the CLI tool to interactively configure tokens and allowlists.

**Section sources**
- [channels.py](file://backend/app/core/channels.py#L185-L200)
- [channels.py](file://backend/app/core/channels.py#L295-L302)
- [channels.py](file://backend/app/core/channels.py#L343-L350)
- [main.py](file://backend/app/main.py#L473-L520)
- [closedpaw.js](file://bin/closedpaw.js#L634-L670)

## Conclusion
The channel subsystem provides a consistent, extensible foundation for integrating Telegram, Discord, and Slack. By centralizing configuration, enforcing security and rate limits, and offering robust error handling, the system supports secure, scalable multi-platform communication. Use the provided APIs and CLI tooling to configure tokens, manage users, and monitor channel health.

[No sources needed since this section summarizes without analyzing specific files]

## Appendices

### Setup and Configuration Examples
- Interactive configuration:
  - Run the CLI configuration wizard and select channels to configure.
  - Provide tokens and allowed users as prompted.
- Programmatic registration:
  - Use the FastAPI endpoint to register channels with ChannelConfig.
  - Start channels to activate polling/connectivity.
- Binding users:
  - Use the bind endpoint or CLI command to add users to allowlists.

**Section sources**
- [closedpaw.js](file://bin/closedpaw.js#L604-L677)
- [main.py](file://backend/app/main.py#L473-L520)
- [main.py](file://backend/app/main.py#L507-L513)