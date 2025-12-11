"""
WebSocket connection manager for real-time chat.
Handles connection lifecycle, broadcasting, and room-based messaging.
"""

import json
import asyncio
from datetime import datetime
from typing import Dict, Set, Optional, Any
from fastapi import WebSocket, WebSocketDisconnect
from pydantic import ValidationError

from models.message import WebSocketMessage
from models.user import UserSession


class ConnectionManager:
    """
    Manages WebSocket connections for real-time chat.
    Supports room-based messaging and user presence tracking.
    """
    
    def __init__(self):
        # room_id -> set of WebSocket connections
        self._room_connections: Dict[int, Set[WebSocket]] = {}
        
        # WebSocket -> UserSession mapping
        self._connection_sessions: Dict[WebSocket, UserSession] = {}
        
        # user_id -> WebSocket mapping for direct messaging
        self._user_connections: Dict[str, WebSocket] = {}
        
        # room_id -> set of user_ids currently typing
        self._typing_users: Dict[int, Set[str]] = {}
        
        # Lock for thread-safe operations
        self._lock = asyncio.Lock()
    
    async def connect(
        self,
        websocket: WebSocket,
        room_id: int,
        user_id: str,
        device_id: str
    ) -> UserSession:
        """
        Accept a WebSocket connection and register it to a room.
        
        Args:
            websocket: The WebSocket connection
            room_id: Room to join
            user_id: User identifier
            device_id: Device identifier for reconnection
            
        Returns:
            UserSession object for the connection
        """
        await websocket.accept()
        
        session = UserSession(
            user_id=user_id,
            room_id=room_id,
            device_id=device_id,
            connected_at=datetime.utcnow()
        )
        
        async with self._lock:
            # Add to room connections
            if room_id not in self._room_connections:
                self._room_connections[room_id] = set()
            self._room_connections[room_id].add(websocket)
            
            # Store session mapping
            self._connection_sessions[websocket] = session
            
            # Store user connection (overwrite if reconnecting)
            self._user_connections[user_id] = websocket
            
            # Initialize typing set for room if needed
            if room_id not in self._typing_users:
                self._typing_users[room_id] = set()
        
        # Broadcast user joined event
        await self.broadcast_to_room(
            room_id,
            WebSocketMessage(
                event="user_joined",
                data={"user_id": user_id},
                room_id=room_id
            ),
            exclude_user=user_id
        )
        
        return session
    
    async def disconnect(self, websocket: WebSocket) -> Optional[UserSession]:
        """
        Handle WebSocket disconnection.
        
        Args:
            websocket: The disconnecting WebSocket
            
        Returns:
            The disconnected UserSession or None
        """
        async with self._lock:
            session = self._connection_sessions.pop(websocket, None)
            
            if session:
                room_id = session.room_id
                user_id = session.user_id
                
                # Remove from room connections
                if room_id in self._room_connections:
                    self._room_connections[room_id].discard(websocket)
                    if not self._room_connections[room_id]:
                        del self._room_connections[room_id]
                
                # Remove from user connections
                if self._user_connections.get(user_id) == websocket:
                    del self._user_connections[user_id]
                
                # Remove from typing users
                if room_id in self._typing_users:
                    self._typing_users[room_id].discard(user_id)
        
        # Broadcast user left event (outside lock to avoid deadlock)
        if session:
            await self.broadcast_to_room(
                session.room_id,
                WebSocketMessage(
                    event="user_left",
                    data={"user_id": session.user_id},
                    room_id=session.room_id
                ),
                exclude_user=session.user_id
            )
        
        return session
    
    async def broadcast_to_room(
        self,
        room_id: int,
        message: WebSocketMessage,
        exclude_user: Optional[str] = None
    ) -> int:
        """
        Broadcast a message to all connections in a room.
        
        Args:
            room_id: Target room
            message: Message to broadcast
            exclude_user: Optional user_id to exclude from broadcast
            
        Returns:
            Number of connections that received the message
        """
        connections = self._room_connections.get(room_id, set()).copy()
        sent_count = 0
        
        message_json = message.model_dump_json()
        
        for websocket in connections:
            session = self._connection_sessions.get(websocket)
            if session and (exclude_user is None or session.user_id != exclude_user):
                try:
                    await websocket.send_text(message_json)
                    sent_count += 1
                except Exception:
                    # Connection might be closed, will be cleaned up
                    pass
        
        return sent_count
    
    async def send_to_user(
        self,
        user_id: str,
        message: WebSocketMessage
    ) -> bool:
        """
        Send a message to a specific user.
        
        Args:
            user_id: Target user
            message: Message to send
            
        Returns:
            True if message was sent successfully
        """
        websocket = self._user_connections.get(user_id)
        if websocket:
            try:
                await websocket.send_text(message.model_dump_json())
                return True
            except Exception:
                pass
        return False
    
    async def set_typing(self, room_id: int, user_id: str, is_typing: bool) -> None:
        """
        Update typing status for a user.
        
        Args:
            room_id: Room where user is typing
            user_id: User who is typing
            is_typing: Whether user is currently typing
        """
        async with self._lock:
            if room_id not in self._typing_users:
                self._typing_users[room_id] = set()
            
            if is_typing:
                self._typing_users[room_id].add(user_id)
            else:
                self._typing_users[room_id].discard(user_id)
        
        # Broadcast typing status
        await self.broadcast_to_room(
            room_id,
            WebSocketMessage(
                event="typing_status",
                data={
                    "user_id": user_id,
                    "is_typing": is_typing,
                    "typing_users": list(self._typing_users.get(room_id, set()))
                },
                room_id=room_id
            ),
            exclude_user=user_id
        )
    
    def get_room_users(self, room_id: int) -> Set[str]:
        """
        Get all user IDs currently connected to a room.
        
        Args:
            room_id: Target room
            
        Returns:
            Set of user IDs
        """
        connections = self._room_connections.get(room_id, set())
        users = set()
        for websocket in connections:
            session = self._connection_sessions.get(websocket)
            if session:
                users.add(session.user_id)
        return users
    
    def get_room_count(self, room_id: int) -> int:
        """
        Get number of connections in a room.
        
        Args:
            room_id: Target room
            
        Returns:
            Number of active connections
        """
        return len(self._room_connections.get(room_id, set()))
    
    def is_user_online(self, user_id: str) -> bool:
        """
        Check if a user is currently online.
        
        Args:
            user_id: User to check
            
        Returns:
            True if user has an active connection
        """
        return user_id in self._user_connections
    
    def get_session(self, websocket: WebSocket) -> Optional[UserSession]:
        """
        Get the session for a WebSocket connection.
        
        Args:
            websocket: WebSocket to look up
            
        Returns:
            UserSession or None
        """
        return self._connection_sessions.get(websocket)
    
    async def close_room_connections(self, room_id: int, reason: str = "Room closed") -> None:
        """
        Close all connections in a room.
        
        Args:
            room_id: Room to close
            reason: Closure reason to send to clients
        """
        connections = self._room_connections.get(room_id, set()).copy()
        
        # Notify all users
        close_message = WebSocketMessage(
            event="room_closed",
            data={"reason": reason},
            room_id=room_id
        )
        
        for websocket in connections:
            try:
                await websocket.send_text(close_message.model_dump_json())
                await websocket.close(code=1000, reason=reason)
            except Exception:
                pass
            
            await self.disconnect(websocket)


# Singleton instance
connection_manager = ConnectionManager()
