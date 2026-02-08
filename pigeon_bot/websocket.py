import asyncio
import json
import uuid
from typing import Dict, Callable, Any, List, Optional
import websockets
from websockets.exceptions import ConnectionClosed

from .types import (
    WsEnvelope,
    WsAuthenticatedData,
    WsErrorData,
    WsOnlineListData,
    Message,
    MessageAttachment,
    MessageReaction,
)
from .config import ClientConfig, resolve_ws_url


class EventManager:
    """Simple event manager for handling WebSocket events."""

    def __init__(self):
        self._handlers: Dict[str, List[Callable]] = {}
        self._handler_ids: Dict[Callable, str] = {}

    def on(self, event: str):
        """Decorator to register an event handler."""
        def decorator(func: Callable):
            if event not in self._handlers:
                self._handlers[event] = []
            self._handlers[event].append(func)
            self._handler_ids[func] = str(uuid.uuid4())
            return func
        return decorator

    def emit(self, event: str, *args, **kwargs):
        """Emit an event to all registered handlers."""
        if event in self._handlers:
            for handler in self._handlers[event].copy():
                try:
                    if asyncio.iscoroutinefunction(handler):
                        asyncio.create_task(handler(*args, **kwargs))
                    else:
                        handler(*args, **kwargs)
                except Exception as e:
                    print(f"Error in event handler for {event}: {e}")

    def remove_listener(self, event: str, handler: Callable):
        """Remove a specific event handler."""
        if event in self._handlers and handler in self._handlers[event]:
            self._handlers[event].remove(handler)
            if handler in self._handler_ids:
                del self._handler_ids[handler]

    def remove_all_listeners(self, event: Optional[str] = None):
        """Remove all listeners for an event or all events."""
        if event is None:
            self._handlers.clear()
            self._handler_ids.clear()
        elif event in self._handlers:
            for handler in self._handlers[event]:
                if handler in self._handler_ids:
                    del self._handler_ids[handler]
            del self._handlers[event]


class WebSocketClient:
    """WebSocket client for Pigeon Messenger."""

    def __init__(self, config: ClientConfig):
        self.config = config
        self.websocket: Optional[websockets.WebSocketServerProtocol] = None
        self._connected = False
        self._authenticated = False
        self.events = EventManager()
        self._reconnect_task: Optional[asyncio.Task] = None
        self._pending_requests: Dict[str, asyncio.Future] = {}
        self._client = None

    @property
    def connected(self) -> bool:
        """Check if the WebSocket is connected."""
        return self._connected

    @property
    def authenticated(self) -> bool:
        """Check if the client is authenticated."""
        return self._authenticated

    async def connect(self):
        """Connect to the WebSocket server."""
        if self._connected:
            raise Exception("Client is already connected")

        url = resolve_ws_url(self.config)
        await self._connect_with_retry(url)

    async def _connect_with_retry(self, url: str):
        """Connect with retry logic."""
        while True:
            try:
                self.websocket = await websockets.connect(url)
                self._connected = True
                self._authenticated = False
                self.events.emit("connect")
                
                await self._authenticate()
                
                await self._listen()
                
            except (ConnectionClosed, ConnectionRefusedError, OSError, Exception) as e:
                self._connected = False
                self._authenticated = False
                
                if isinstance(e, (ConnectionClosed, ConnectionRefusedError, OSError)):
                    self.events.emit("disconnect", e)
                else:
                    self.events.emit("error", f"Connection failed: {e}")
                
                for request_id, future in self._pending_requests.items():
                    if not future.done():
                        future.set_exception(Exception(f"Connection lost: {e}"))
                self._pending_requests.clear()
                
                if self.config.auto_reconnect:
                    await asyncio.sleep(self.config.reconnect_interval_ms / 1000)
                    continue
                else:
                    break
            except Exception as e:
                self.events.emit("error", e)
                break

    async def _authenticate(self):
        """Send authentication message."""
        auth_msg = WsEnvelope(
            type="authenticate",
            data={"token": f"Bot {self.config.token}"}
        )
        await self._send_raw(auth_msg)

    async def _listen(self):
        """Listen for incoming messages."""
        try:
            async for message in self.websocket:
                try:
                    data = json.loads(message)
                    envelope = WsEnvelope(**data)
                    await self._handle_message(envelope)
                except json.JSONDecodeError as e:
                    self.events.emit("error", f"Invalid JSON: {e}")
                except Exception as e:
                    self.events.emit("error", f"Message handling error: {e}")
        except ConnectionClosed:
            pass
        except Exception as e:
            self.events.emit("error", f"Listen error: {e}")

    def _deserialize_message_data(self, message_data: Dict[str, Any]) -> Message:
        """Deserialize message data dictionary to Message object."""
        msg_data = dict(message_data)
        
        if msg_data.get("attachments"):
            msg_data["attachments"] = [
                MessageAttachment(**attachment) for attachment in msg_data["attachments"]
            ]
        else:
            msg_data["attachments"] = None
        
        if msg_data.get("reactions"):
            msg_data["reactions"] = [
                MessageReaction(**reaction) for reaction in msg_data["reactions"]
            ]
        else:
            msg_data["reactions"] = None
        
        return Message(**msg_data)

    async def _handle_message(self, envelope: WsEnvelope):
        """Handle incoming WebSocket messages."""
        self.events.emit("raw", envelope)

        if envelope.type == "authenticated":
            self._authenticated = True
            auth_data = WsAuthenticatedData(**envelope.data)
            self.events.emit("authenticated", auth_data)
            self.events.emit("ready")
            
        elif envelope.type == "error":
            error_data = WsErrorData(**envelope.data)
            if not self._authenticated and error_data.message == "Please authenticate first":
                return
            self.events.emit("error", Exception(error_data.message))
            
        elif envelope.type == "new_message":
            message_data = envelope.data.get("message", {})
            message = self._deserialize_message_data(message_data)
            if self._client:
                from .entities import MessageEntity
                message_entity = MessageEntity(self._client, message)
                self.events.emit("new_message", message_entity)
            else:
                self.events.emit("new_message", message, envelope.data)
            
        elif envelope.type == "message_edited":
            message_data = envelope.data.get("message", {})
            message = self._deserialize_message_data(message_data)
            if self._client:
                from .entities import MessageEntity
                message_entity = MessageEntity(self._client, message)
                self.events.emit("message_edited", message_entity)
            else:
                self.events.emit("message_edited", message, envelope.data)
            
        elif envelope.type == "message_deleted":
            self.events.emit("message_deleted", envelope.data)
            
        elif envelope.type in ["reaction_added", "reaction_removed"]:
            self.events.emit(envelope.type, envelope.data)
            
        elif envelope.type in ["user_online", "user_offline"]:
            self.events.emit(envelope.type, envelope.data)
            
        elif envelope.type == "online_list":
            online_data = WsOnlineListData(**envelope.data)
            self.events.emit("online_list", online_data)
            
            request_id = envelope.data.get("request_id")
            if request_id and request_id in self._pending_requests:
                future = self._pending_requests.pop(request_id)
                if not future.done():
                    future.set_result(online_data.users)
            
        else:
            self.events.emit(envelope.type, envelope.data)

    async def _send_raw(self, envelope: WsEnvelope):
        """Send a raw WebSocket message."""
        if not self.websocket:
            raise Exception("Not connected to WebSocket")
        
        if not self._authenticated and envelope.type != "authenticate":
            raise Exception("Please authenticate first.")
        
        message = json.dumps(envelope.__dict__)
        await self.websocket.send(message)

    async def send_message(
        self,
        chat_id: int,
        content: str,
        reply_to: Optional[int] = None,
        attachment_ids: Optional[List[int]] = None,
    ):
        """Send a message."""
        envelope = WsEnvelope(
            type="send_message",
            data={
                "chat_id": chat_id,
                "content": content,
                "reply_to": reply_to,
                "attachment_ids": attachment_ids,
            },
        )
        await self._send_raw(envelope)

    async def edit_message(self, message_id: int, content: str):
        """Edit a message."""
        envelope = WsEnvelope(
            type="edit_message",
            data={"message_id": message_id, "content": content},
        )
        await self._send_raw(envelope)

    async def delete_message(self, message_id: int):
        """Delete a message."""
        envelope = WsEnvelope(
            type="delete_message",
            data={"message_id": message_id},
        )
        await self._send_raw(envelope)

    async def add_reaction(self, message_id: int, emoji: str):
        """Add a reaction to a message."""
        envelope = WsEnvelope(
            type="add_reaction",
            data={"message_id": message_id, "emoji": emoji},
        )
        await self._send_raw(envelope)

    async def remove_reaction(self, message_id: int, emoji: str):
        """Remove a reaction from a message."""
        envelope = WsEnvelope(
            type="remove_reaction",
            data={"message_id": message_id, "emoji": emoji},
        )
        await self._send_raw(envelope)

    async def set_typing(self, chat_id: int, is_typing: bool = True):
        """Set typing status."""
        envelope = WsEnvelope(
            type="typing",
            data={"chat_id": chat_id, "is_typing": is_typing},
        )
        await self._send_raw(envelope)

    async def get_online_list(self) -> List[Dict[str, int]]:
        """Get the list of online users."""
        request_id = str(uuid.uuid4())
        future = asyncio.Future()
        self._pending_requests[request_id] = future
        
        try:
            envelope = WsEnvelope(
                type="get_online_list",
                data={"request_id": request_id}
            )
            await self._send_raw(envelope)
            
            return await asyncio.wait_for(future, timeout=5.0)
        except asyncio.TimeoutError:
            if request_id in self._pending_requests:
                del self._pending_requests[request_id]
            raise Exception("Timed out waiting for online list")
        except Exception as e:
            if request_id in self._pending_requests:
                del self._pending_requests[request_id]
            raise

    async def disconnect(self):
        """Disconnect from the WebSocket."""
        for request_id, future in self._pending_requests.items():
            if not future.done():
                future.set_exception(Exception("Disconnected"))
        self._pending_requests.clear()
        
        if self.websocket:
            try:
                await self.websocket.close()
            except Exception:
                pass
        self._connected = False
        self._authenticated = False