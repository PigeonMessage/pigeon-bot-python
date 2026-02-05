# Pigeon Bot Python

[![Python](https://img.shields.io/badge/python-%3E%3D3.8-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)

A Python library for building chat bots on the Pigeon Messenger.

## Installation

```bash
pip install pigeon-bot
```

## Quick Start

```python

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
```

## Configuration

```python
class ClientConfig:
    token: str
    base_url: Optional[str] = "http://localhost:8000"
    ws_url: Optional[str] = None
    auto_reconnect: bool = True
    reconnect_interval_ms: int = 5000
```

## Base Events

- `ready`: Fires when the bot connects successfully
- `authenticated`: Fires after successful authentication
- `new_message`: Triggered on new messages
- `error`: Emitted on connection/authentication errors

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
