import asyncio
import json
import uuid
from typing import Dict, Callable, Any, List, Optional, Union
import websockets
from websockets.exceptions import ConnectionClosed

from .types import (
    WsEnvelope,
    WsAuthenticatedData,
    WsErrorData,
    WsOnlineListData,
    Message,
    MessageMedia,
    MessageReaction,
    UserPublic,
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
        self.websocket: Optional[websockets.WebSocketClientProtocol] = None
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
            except (ConnectionClosed, ConnectionRefusedError, OSError) as e:
                self._connected = False
                self._authenticated = False
                self.events.emit("disconnect", e)
                for req_id, fut in self._pending_requests.items():
                    if not fut.done():
                        fut.set_exception(Exception(f"Connection lost: {e}"))
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
        msg = WsEnvelope(type="authenticate", data={"token": f"Bot {self.config.token}"})
        await self._send_raw(msg)

    async def _listen(self):
        """Listen for incoming messages."""
        try:
            async for message in self.websocket:
                try:
                    data = json.loads(message)
                    env = WsEnvelope(**data)
                    await self._handle_message(env)
                except json.JSONDecodeError as e:
                    self.events.emit("error", f"Invalid JSON: {e}")
                except Exception as e:
                    self.events.emit("error", f"Message handling error: {e}")
        except ConnectionClosed:
            pass
        except Exception as e:
            self.events.emit("error", f"Listen error: {e}")

    def _deserialize_message(self, msg_dict: dict) -> Message:
        """Deserialize message data dictionary to Message object."""
        """Handle incoming WebSocket messages."""
        md = dict(msg_dict)
        if md.get("media"):
            pass
        if md.get("reactions"):
            md["reactions"] = [MessageReaction(**r) for r in md["reactions"]]
        if md.get("new_chat_members"):
            md["new_chat_members"] = [UserPublic(**u) for u in md["new_chat_members"]]
        if md.get("left_chat_member"):
            md["left_chat_member"] = UserPublic(**md["left_chat_member"])
        if md.get("pinned_message"):
            md["pinned_message"] = self._deserialize_message(md["pinned_message"])
        return Message(**md)

    async def _handle_message(self, env: WsEnvelope):
        self.events.emit("raw", env)
        if env.type == "authenticated":
            self._authenticated = True
            data = WsAuthenticatedData(**env.data)
            self.events.emit("authenticated", data)
            self.events.emit("ready")
        elif env.type == "error":
            err = WsErrorData(**env.data)
            if not self._authenticated and err.message == "Please authenticate first":
                return
            self.events.emit("error", Exception(err.message))
        elif env.type in ("new_message", "message_edited"):
            msg_data = env.data.get("message", {})
            msg = self._deserialize_message(msg_data)
            if self._client:
                from .entities import MessageEntity
                entity = MessageEntity(self._client, msg)
                self.events.emit(env.type, entity)
            else:
                self.events.emit(env.type, msg, env.data)
        elif env.type == "message_deleted":
            self.events.emit("message_deleted", env.data)
        elif env.type == "reaction_added":
            reaction = env.data.get("reaction", {})
            unified_data = {
                "message_id": reaction.get("message_id") or env.data.get("message_id"),
                "user_id": reaction.get("user_id"),
                "emoji": reaction.get("emoji"),
                "reaction_id": reaction.get("id"),
                "created_at": reaction.get("created_at"),
            }
            self.events.emit("reaction_added", unified_data)
        elif env.type == "reaction_removed":
            self.events.emit("reaction_removed", env.data)
        elif env.type in ("user_online", "user_offline", "user_typing"):
            self.events.emit(env.type, env.data)
        elif env.type == "online_list":
            online_data = WsOnlineListData(**env.data)
            self.events.emit("online_list", online_data)
            req_id = env.data.get("request_id")
            if req_id and req_id in self._pending_requests:
                fut = self._pending_requests.pop(req_id)
                if not fut.done():
                    fut.set_result(online_data.users)
        elif env.type in ("poll_voted", "poll_closed", "poll_created"):
            self.events.emit(env.type, env.data)
        else:
            self.events.emit(env.type, env.data)

    async def _send_raw(self, envelope: WsEnvelope):
        """Send a raw WebSocket message."""
        if not self.websocket:
            raise Exception("Not connected to WebSocket")
        if not self._authenticated and envelope.type != "authenticate":
            raise Exception("Please authenticate first.")
        await self.websocket.send(json.dumps({"type": envelope.type, "data": envelope.data}))

    async def send_message(
        self,
        chat_id: int,
        content: str,
        reply_to: Optional[int] = None,
        media: Optional[List[MessageMedia]] = None,
    ):
        """Send a message."""
        data = {
            "chat_id": chat_id,
            "content": content,
            "reply_to": reply_to,
            "media": media,
        }
        await self._send_raw(WsEnvelope(type="send_message", data=data))

    async def edit_message(self, message_id: int, content: str):
        """Edit a message."""
        await self._send_raw(WsEnvelope(type="edit_message", data={"message_id": message_id, "content": content}))

    async def delete_message(self, message_id: int):
        """Delete a message."""
        await self._send_raw(WsEnvelope(type="delete_message", data={"message_id": message_id}))

    async def add_reaction(self, message_id: int, emoji: str):
        """Add a reaction to a message."""
        await self._send_raw(WsEnvelope(type="add_reaction", data={"message_id": message_id, "emoji": emoji}))

    async def remove_reaction(self, message_id: int, emoji: str):
        """Remove a reaction from a message."""
        await self._send_raw(WsEnvelope(type="remove_reaction", data={"message_id": message_id, "emoji": emoji}))

    async def set_typing(self, chat_id: int, is_typing: bool = True):
        """Set typing status."""
        envelope = WsEnvelope(
            type="typing",
            data={"chat_id": chat_id, "is_typing": is_typing},
        )
        await self._send_raw(envelope)

    async def get_online_list(self) -> List[Dict[str, int]]:
        """Get the list of online users."""
        req_id = str(uuid.uuid4())
        future = asyncio.Future()
        self._pending_requests[req_id] = future
        try:
            await self._send_raw(WsEnvelope(type="get_online_list", data={"request_id": req_id}))
            return await asyncio.wait_for(future, timeout=5.0)
        except asyncio.TimeoutError:
            self._pending_requests.pop(req_id, None)
            raise Exception("Timed out waiting for online list")
        except Exception:
            self._pending_requests.pop(req_id, None)
            raise

    async def disconnect(self):
        """Disconnect from the WebSocket."""
        for req_id, fut in self._pending_requests.items():
            if not fut.done():
                fut.set_exception(Exception("Disconnected"))
        self._pending_requests.clear()
        if self.websocket:
            try:
                await self.websocket.close()
            except Exception:
                pass
        self._connected = False
        self._authenticated = False