"""
ClosedPaw - Multi-Channel Gateway
Supports Telegram, Discord, Slack, Matrix, Web UI
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Callable
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger(__name__)


class ChannelType(str, Enum):
    """Supported channel types"""
    WEBUI = "webui"
    TELEGRAM = "telegram"
    DISCORD = "discord"
    SLACK = "slack"
    MATRIX = "matrix"
    CLI = "cli"


@dataclass
class ChannelMessage:
    """Message from a channel"""
    channel_type: ChannelType
    channel_id: str
    user_id: str
    content: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # For replies
    reply_to: Optional[str] = None


@dataclass 
class ChannelConfig:
    """Configuration for a channel"""
    channel_type: ChannelType
    name: str
    enabled: bool = True
    
    # Channel-specific settings
    bot_token: Optional[str] = None
    app_id: Optional[str] = None
    webhook_url: Optional[str] = None
    allowed_users: List[str] = field(default_factory=list)
    allowed_channels: List[str] = field(default_factory=list)
    
    # Rate limiting
    rate_limit_per_user: int = 30  # messages per minute
    rate_limit_global: int = 100
    
    # Security
    require_pairing: bool = True
    allowed_commands: List[str] = field(default_factory=lambda: ["chat", "status", "help"])
    
    extra: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ChannelUser:
    """User identity in a channel"""
    channel_type: ChannelType
    user_id: str
    username: Optional[str] = None
    display_name: Optional[str] = None
    is_admin: bool = False
    is_allowed: bool = False
    paired_at: Optional[datetime] = None


class BaseChannel(ABC):
    """Abstract base class for channels"""
    
    def __init__(self, config: ChannelConfig):
        self.config = config
        self.users: Dict[str, ChannelUser] = {}
        self._message_handler: Optional[Callable] = None
        self._running = False
    
    @abstractmethod
    async def start(self):
        """Start the channel"""
        pass
    
    @abstractmethod
    async def stop(self):
        """Stop the channel"""
        pass
    
    @abstractmethod
    async def send_message(self, channel_id: str, content: str, **kwargs):
        """Send message to channel"""
        pass
    
    @abstractmethod
    async def get_me(self) -> Dict[str, Any]:
        """Get bot/user info"""
        pass
    
    def set_message_handler(self, handler: Callable):
        """Set callback for incoming messages"""
        self._message_handler = handler
    
    async def _handle_message(self, message: ChannelMessage):
        """Process incoming message"""
        if self._message_handler:
            await self._message_handler(message)
    
    def is_user_allowed(self, user_id: str) -> bool:
        """Check if user is allowed"""
        if not self.config.allowed_users:
            return True  # Allow all if not configured
        return user_id in self.config.allowed_users
    
    def add_allowed_user(self, user_id: str, username: Optional[str] = None):
        """Add user to allowlist"""
        if user_id not in self.config.allowed_users:
            self.config.allowed_users.append(user_id)
        
        self.users[user_id] = ChannelUser(
            channel_type=self.config.channel_type,
            user_id=user_id,
            username=username,
            is_allowed=True,
            paired_at=datetime.utcnow()
        )


class WebUIChannel(BaseChannel):
    """Web UI channel (internal)"""
    
    def __init__(self, config: ChannelConfig):
        super().__init__(config)
        self._pending_messages: Dict[str, List[Dict]] = {}
    
    async def start(self):
        self._running = True
        logger.info("WebUI channel started")
    
    async def stop(self):
        self._running = False
        logger.info("WebUI channel stopped")
    
    async def send_message(self, channel_id: str, content: str, **kwargs):
        """Queue message for WebUI polling"""
        if channel_id not in self._pending_messages:
            self._pending_messages[channel_id] = []
        
        self._pending_messages[channel_id].append({
            "content": content,
            "timestamp": datetime.utcnow().isoformat(),
            **kwargs
        })
    
    async def get_pending_messages(self, channel_id: str) -> List[Dict]:
        """Get pending messages for WebUI"""
        messages = self._pending_messages.get(channel_id, [])
        self._pending_messages[channel_id] = []
        return messages
    
    async def get_me(self) -> Dict[str, Any]:
        return {
            "id": "webui",
            "name": "ClosedPaw WebUI",
            "type": "webui"
        }


class TelegramChannel(BaseChannel):
    """Telegram bot channel"""
    
    def __init__(self, config: ChannelConfig):
        super().__init__(config)
        self.base_url = f"https://api.telegram.org/bot{config.bot_token}"
        self._offset = 0
    
    async def start(self):
        if not self.config.bot_token:
            logger.warning("Telegram bot token not configured")
            return
        
        self._running = True
        
        # Start polling
        asyncio.create_task(self._poll_updates())
        
        me = await self.get_me()
        logger.info(f"Telegram channel started: @{me.get('username', 'unknown')}")
    
    async def stop(self):
        self._running = False
        logger.info("Telegram channel stopped")
    
    async def _poll_updates(self):
        """Poll for updates from Telegram"""
        import httpx
        
        async with httpx.AsyncClient() as client:
            while self._running:
                try:
                    response = await client.get(
                        f"{self.base_url}/getUpdates",
                        params={"offset": self._offset, "timeout": 30},
                        timeout=35
                    )
                    
                    if response.status_code == 200:
                        data = response.json()
                        for update in data.get("result", []):
                            self._offset = update["update_id"] + 1
                            await self._process_update(update)
                
                except Exception as e:
                    logger.error(f"Telegram poll error: {e}")
                    await asyncio.sleep(5)
    
    async def _process_update(self, update: Dict):
        """Process Telegram update"""
        message = update.get("message", {})
        if not message:
            return
        
        chat_id = str(message.get("chat", {}).get("id", ""))
        user = message.get("from", {})
        user_id = str(user.get("id", ""))
        text = message.get("text", "")
        
        if not text:
            return
        
        # Check if user is allowed
        if not self.is_user_allowed(user_id):
            await self.send_message(chat_id, "⛔ You are not authorized to use this bot.")
            return
        
        # Create channel message
        channel_message = ChannelMessage(
            channel_type=ChannelType.TELEGRAM,
            channel_id=chat_id,
            user_id=user_id,
            content=text,
            metadata={
                "username": user.get("username"),
                "first_name": user.get("first_name"),
                "message_id": message.get("message_id")
            }
        )
        
        await self._handle_message(channel_message)
    
    async def send_message(self, channel_id: str, content: str, **kwargs):
        """Send message via Telegram API"""
        import httpx
        
        async with httpx.AsyncClient() as client:
            # Escape HTML and send as Markdown
            response = await client.post(
                f"{self.base_url}/sendMessage",
                json={
                    "chat_id": channel_id,
                    "text": content,
                    "parse_mode": kwargs.get("parse_mode", "Markdown")
                }
            )
            
            if response.status_code != 200:
                logger.error(f"Telegram send error: {response.text}")
    
    async def get_me(self) -> Dict[str, Any]:
        """Get bot info"""
        import httpx
        
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{self.base_url}/getMe")
            if response.status_code == 200:
                return response.json().get("result", {})
        return {}


class DiscordChannel(BaseChannel):
    """Discord bot channel"""
    
    def __init__(self, config: ChannelConfig):
        super().__init__(config)
        self.base_url = "https://discord.com/api/v10"
    
    async def start(self):
        if not self.config.bot_token:
            logger.warning("Discord bot token not configured")
            return
        
        self._running = True
        me = await self.get_me()
        logger.info(f"Discord channel started: {me.get('username', 'unknown')}")
    
    async def stop(self):
        self._running = False
        logger.info("Discord channel stopped")
    
    async def send_message(self, channel_id: str, content: str, **kwargs):
        """Send message via Discord API"""
        import httpx
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/channels/{channel_id}/messages",
                headers={"Authorization": f"Bot {self.config.bot_token}"},
                json={"content": content}
            )
            
            if response.status_code not in [200, 201]:
                logger.error(f"Discord send error: {response.text}")
    
    async def get_me(self) -> Dict[str, Any]:
        """Get bot info"""
        import httpx
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/users/@me",
                headers={"Authorization": f"Bot {self.config.bot_token}"}
            )
            if response.status_code == 200:
                return response.json()
        return {}


class SlackChannel(BaseChannel):
    """Slack bot channel"""
    
    def __init__(self, config: ChannelConfig):
        super().__init__(config)
        self.base_url = "https://slack.com/api"
    
    async def start(self):
        if not self.config.bot_token:
            logger.warning("Slack bot token not configured")
            return
        
        self._running = True
        me = await self.get_me()
        logger.info(f"Slack channel started: {me.get('user', {}).get('name', 'unknown')}")
    
    async def stop(self):
        self._running = False
        logger.info("Slack channel stopped")
    
    async def send_message(self, channel_id: str, content: str, **kwargs):
        """Send message via Slack API"""
        import httpx
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/chat.postMessage",
                headers={"Authorization": f"Bearer {self.config.bot_token}"},
                json={"channel": channel_id, "text": content}
            )
            
            if not response.json().get("ok"):
                logger.error(f"Slack send error: {response.text}")
    
    async def get_me(self) -> Dict[str, Any]:
        """Get bot info"""
        import httpx
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/auth.test",
                headers={"Authorization": f"Bearer {self.config.bot_token}"}
            )
            if response.json().get("ok"):
                return response.json()
        return {}


class CLIChannel(BaseChannel):
    """CLI channel for terminal interaction"""
    
    def __init__(self, config: ChannelConfig):
        super().__init__(config)
    
    async def start(self):
        self._running = True
        logger.info("CLI channel started")
    
    async def stop(self):
        self._running = False
    
    async def send_message(self, channel_id: str, content: str, **kwargs):
        """Print to stdout"""
        print(content)
    
    async def get_me(self) -> Dict[str, Any]:
        return {"id": "cli", "name": "ClosedPaw CLI"}


class ChannelManager:
    """
    Central manager for all channels
    Handles channel registration, message routing, and security
    """
    
    def __init__(self):
        self.channels: Dict[str, BaseChannel] = {}
        self.configs: Dict[str, ChannelConfig] = {}
        self._message_handler: Optional[Callable] = None
    
    def register_channel(self, config: ChannelConfig) -> bool:
        """Register a new channel"""
        try:
            channel_classes = {
                ChannelType.WEBUI: WebUIChannel,
                ChannelType.TELEGRAM: TelegramChannel,
                ChannelType.DISCORD: DiscordChannel,
                ChannelType.SLACK: SlackChannel,
                ChannelType.CLI: CLIChannel,
            }
            
            channel_class = channel_classes.get(config.channel_type)
            if not channel_class:
                logger.error(f"Unknown channel type: {config.channel_type}")
                return False
            
            self.channels[config.name] = channel_class(config)
            self.configs[config.name] = config
            
            if self._message_handler:
                self.channels[config.name].set_message_handler(self._message_handler)
            
            logger.info(f"Registered channel: {config.name} ({config.channel_type.value})")
            return True
            
        except Exception as e:
            logger.error(f"Failed to register channel {config.name}: {e}")
            return False
    
    async def start_all(self):
        """Start all channels"""
        for channel in self.channels.values():
            if channel.config.enabled:
                await channel.start()
    
    async def stop_all(self):
        """Stop all channels"""
        for channel in self.channels.values():
            await channel.stop()
    
    def set_message_handler(self, handler: Callable):
        """Set global message handler"""
        self._message_handler = handler
        for channel in self.channels.values():
            channel.set_message_handler(handler)
    
    async def send_message(self, channel_name: str, channel_id: str, content: str, **kwargs):
        """Send message through specific channel"""
        channel = self.channels.get(channel_name)
        if channel:
            await channel.send_message(channel_id, content, **kwargs)
        else:
            logger.error(f"Channel not found: {channel_name}")
    
    async def broadcast(self, content: str, channels: Optional[List[str]] = None):
        """Broadcast message to multiple channels"""
        target_channels = channels or list(self.channels.keys())
        
        for name in target_channels:
            channel = self.channels.get(name)
            if channel and channel.config.enabled:
                # For broadcast, use the first allowed channel ID
                if channel.config.allowed_channels:
                    await channel.send_message(
                        channel.config.allowed_channels[0], 
                        content
                    )
    
    def bind_user(self, channel_name: str, user_id: str, username: Optional[str] = None):
        """Bind user to channel allowlist"""
        channel = self.channels.get(channel_name)
        if channel:
            channel.add_allowed_user(user_id, username)
            logger.info(f"User {user_id} bound to channel {channel_name}")
    
    def get_status(self) -> Dict[str, Any]:
        """Get status of all channels"""
        return {
            "channels": {
                name: {
                    "type": config.channel_type.value,
                    "enabled": config.enabled,
                    "allowed_users": len(config.allowed_users)
                }
                for name, config in self.configs.items()
            }
        }


# Singleton instance
_channel_manager: Optional[ChannelManager] = None


def get_channel_manager() -> ChannelManager:
    """Get or create singleton channel manager"""
    global _channel_manager
    if _channel_manager is None:
        _channel_manager = ChannelManager()
        
        # Register default WebUI channel
        _channel_manager.register_channel(ChannelConfig(
            channel_type=ChannelType.WEBUI,
            name="webui",
            enabled=True,
            require_pairing=False
        ))
    
    return _channel_manager
