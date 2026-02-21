# Telegram MCP Server

A Model Context Protocol (MCP) server for Telegram that enables Claude Code to access your personal Telegram messages.

**Fork Note:** This is a modified version with additional features:
- Attachment/media support (photos, documents, videos)
- Full history sync capability
- Uses `uv` for package management

## Features

- Search personal Telegram messages
- Search contacts
- Send messages to individuals or groups
- **List and download attachments** (photos, documents, videos, audio)
- **Sync full chat history** (not just recent messages)

## Prerequisites

- Python 3.10+
- `uv` package manager
- Telegram account
- Telegram API credentials

## Installation

### 1. Clone and Install

```bash
cd ~/Documents/Dev
git clone https://github.com/Muhammad18557/telegram-mcp.git
cd telegram-mcp
uv sync
```

### 2. Get Telegram API Credentials

1. Go to https://my.telegram.org/apps
2. Log in with your phone number
3. Create a new application
4. Save your **API ID** and **API Hash**

### 3. Configure Environment

Create `.env` file in `telegram-bridge/`:

```bash
# telegram-mcp/telegram-bridge/.env
TELEGRAM_API_ID=your_api_id
TELEGRAM_API_HASH=your_api_hash
```

### 4. Run Database Migration (if upgrading)

```bash
uv run python telegram-bridge/migrations/run_migrations.py
```

### 5. Update run_telegram_server.sh

```bash
#!/bin/bash
BASE_DIR="/path/to/telegram-mcp"
uv run --directory "$BASE_DIR" python "$BASE_DIR/telegram-mcp-server/main.py"
```

### 6. Configure Claude Code

Add to `~/.claude.json`:

```json
{
  "mcpServers": {
    "telegram": {
      "type": "stdio",
      "command": "/bin/bash",
      "args": ["/path/to/telegram-mcp/run_telegram_server.sh"]
    }
  }
}
```

### 7. Authenticate with Telegram

```bash
cd ~/Documents/Dev/telegram-mcp
uv run python telegram-bridge/main.py
```

Enter your phone number and verification code. Keep this running.

### 8. Restart Claude Code

## MCP Tools

| Tool | Description |
|------|-------------|
| `search_contacts` | Search contacts by name or username |
| `list_messages` | Retrieve messages with filters and context |
| `list_chats` | List available chats with metadata |
| `get_chat` | Get information about a specific chat |
| `get_direct_chat_by_contact` | Find direct chat with a contact |
| `get_contact_chats` | List all chats involving a contact |
| `get_last_interaction` | Get most recent message with a contact |
| `get_message_context` | Retrieve context around a message |
| `send_message` | Send message to username or chat ID |
| `list_attachments` | List messages with media attachments |
| `download_attachment` | Download attachment to local storage |
| `sync_chat_history` | Fetch ALL messages from a chat |

## Architecture

```
telegram-mcp/
├── telegram-bridge/          # Telegram API client & database
│   ├── api/                  # Telethon client wrapper
│   ├── database/             # SQLAlchemy models & repositories
│   ├── server/               # FastAPI HTTP server
│   ├── store/                # SQLite database & media downloads
│   └── migrations/           # Database migrations
├── telegram-mcp-server/      # MCP server for Claude
│   └── telegram/             # MCP tools implementation
├── pyproject.toml            # uv dependencies
└── run_telegram_server.sh    # MCP server launcher
```

## Data Storage

- **Messages:** `telegram-bridge/store/messages.db` (SQLite)
- **Session:** `telegram-bridge/store/telegram_session.session`
- **Media:** `telegram-bridge/store/media/`

All data is local. Only accessed by LLM when you use the tools.

## Usage Examples

```python
# List recent chats
list_chats(limit=20)

# Search messages in a chat
list_messages(chat_id=123456, query="meeting", limit=50)

# Sync full history (for chats with limited messages)
sync_chat_history(chat_id=123456)

# List photos in a chat
list_attachments(chat_id=123456, media_type="photo")

# Download an attachment
download_attachment(message_id=789, chat_id=123456)
```

## Troubleshooting

### Session Expired
```bash
rm telegram-bridge/store/telegram_session.session
uv run python telegram-bridge/main.py
```

### Only Recent Messages Available
Use `sync_chat_history(chat_id=...)` to fetch full history.

### MCP Server Not Connecting
1. Ensure Telegram Bridge is running
2. Restart Claude Code
3. Check paths in `run_telegram_server.sh`

## Credits

Based on [Muhammad18557/telegram-mcp](https://github.com/Muhammad18557/telegram-mcp)

Modified by Orlando Bruno with:
- Media/attachment support
- Full history sync
- `uv` package management
- Bug fixes (Pydantic serialization)
