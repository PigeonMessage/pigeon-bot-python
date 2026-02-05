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
        if "hello" in message.content.lower():
            await message.reply("hi")

    await client.connect()

if __name__ == "__main__":
    asyncio.run(main())