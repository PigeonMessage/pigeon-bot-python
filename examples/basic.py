"""
Basic example bot for Pigeon Messenger using the Python library
"""

import asyncio
import os
from pigeon_bot import Client, ClientConfig

async def main():
    token = os.getenv("BOT_TOKEN")
    if not token:
        print("Please set your bot token in the BOT_TOKEN environment variable")
        return

    config = ClientConfig(
        token=token,
        base_url="http://localhost",
        ws_url="ws://localhost/api/v1/ws"
    )
    client = Client(config)

    @client.on_event("ready")
    async def on_ready():
        print("bot is ready!")

    @client.on_event("new_message")
    async def on_new_message(message):
        print(f"new message: {message.content} (ID: {message.id}, chat: {message.chat_id})")
        if "hello" in message.content.lower():
            await message.reply("hi")

    @client.on_event("message_edited")
    async def on_message_edited(message):
        print(f"message edited: {message.content} (ID: {message.id})")
    
    @client.on_event("message_deleted")
    async def on_message_deleted(data):
        print(f"message deleted: {data}")
    
    @client.on_event("reaction_added")
    async def on_reaction_added(data):
        print(f"reaction added: {data}")
    
    @client.on_event("reaction_removed")
    async def on_reaction_removed(data):
        print(f"reaction removed: {data}")
    
    @client.on_event("user_online")
    async def on_user_online(data):
        print(f"user online: {data}")
    
    @client.on_event("user_offline")
    async def on_user_offline(data):
        print(f"user offline: {data}")
    
    @client.on_event("connect")
    async def on_connect():
        print("connected to Websocket")
    
    @client.on_event("disconnect")
    async def on_disconnect(error):
        print(f"disconnected: {error}")
    
    @client.on_event("error")
    async def on_error(error):
        print(f"error: {error}")
    
    await client.connect()

if __name__ == "__main__":
    asyncio.run(main())