"""
Tatsu AI — Long-Term Memory
==============================
SQLite-backed persistent storage for conversations, memories,
user preferences, action logs, and application registry.
"""

import json
import logging
import uuid
from datetime import datetime

import aiosqlite

import config
from memory.models import get_db

logger = logging.getLogger("tatsu.memory.long_term")


class LongTermMemory:
    """
    Persistent memory backed by SQLite.
    Stores conversations, facts, preferences, and action history.
    """

    # ── Conversations ──────────────────────────────────────────────────────

    async def create_conversation(self, title: str = "New Conversation") -> str:
        """Create a new conversation and return its ID."""
        conv_id = str(uuid.uuid4())
        async with get_db() as db:
            await db.execute(
                "INSERT INTO conversations (id, title) VALUES (?, ?)",
                (conv_id, title),
            )
            await db.commit()
        logger.info(f"Created conversation: {conv_id}")
        return conv_id

    async def list_conversations(self, limit: int = 20) -> list[dict]:
        """List recent conversations."""
        async with get_db() as db:
            cursor = await db.execute(
                """SELECT c.id, c.title, c.created_at, c.updated_at,
                          COUNT(m.id) as message_count
                   FROM conversations c
                   LEFT JOIN messages m ON m.conversation_id = c.id
                   GROUP BY c.id
                   ORDER BY c.updated_at DESC
                   LIMIT ?""",
                (limit,),
            )
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

    async def update_conversation_title(self, conv_id: str, title: str) -> None:
        """Update a conversation's title."""
        async with get_db() as db:
            await db.execute(
                "UPDATE conversations SET title = ?, updated_at = ? WHERE id = ?",
                (title, datetime.now().isoformat(), conv_id),
            )
            await db.commit()

    # ── Messages ───────────────────────────────────────────────────────────

    async def save_message(
        self,
        conversation_id: str,
        role: str,
        content: str,
        tool_calls: list[dict] | None = None,
        tool_name: str | None = None,
    ) -> str:
        """Save a message to the database."""
        msg_id = str(uuid.uuid4())
        async with get_db() as db:
            await db.execute(
                """INSERT INTO messages (id, conversation_id, role, content, tool_calls, tool_name)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (
                    msg_id,
                    conversation_id,
                    role,
                    content,
                    json.dumps(tool_calls) if tool_calls else None,
                    tool_name,
                ),
            )
            # Update conversation timestamp
            await db.execute(
                "UPDATE conversations SET updated_at = ? WHERE id = ?",
                (datetime.now().isoformat(), conversation_id),
            )
            await db.commit()
        return msg_id

    async def load_conversation_messages(
        self, conversation_id: str, limit: int = 50
    ) -> list[dict]:
        """Load messages for a conversation."""
        async with get_db() as db:
            cursor = await db.execute(
                """SELECT id, role, content, tool_calls, tool_name, created_at
                   FROM messages
                   WHERE conversation_id = ?
                   ORDER BY created_at ASC
                   LIMIT ?""",
                (conversation_id, limit),
            )
            rows = await cursor.fetchall()
            messages = []
            for row in rows:
                msg = dict(row)
                if msg.get("tool_calls"):
                    msg["tool_calls"] = json.loads(msg["tool_calls"])
                messages.append(msg)
            return messages

    # ── Memories (Facts & Knowledge) ───────────────────────────────────────

    async def save_memory(
        self,
        category: str,
        key: str,
        value: str,
        importance: int = 5,
    ) -> None:
        """Save or update a memory. Uses UPSERT to handle duplicates."""
        mem_id = str(uuid.uuid4())
        async with get_db() as db:
            await db.execute(
                """INSERT INTO memories (id, category, key, value, importance)
                   VALUES (?, ?, ?, ?, ?)
                   ON CONFLICT(category, key) DO UPDATE SET
                     value = excluded.value,
                     importance = excluded.importance,
                     last_accessed = CURRENT_TIMESTAMP""",
                (mem_id, category, key, value, importance),
            )
            await db.commit()
        logger.info(f"Saved memory: [{category}] {key}")

    async def recall_memory(self, category: str, key: str) -> str | None:
        """Recall a specific memory by category and key."""
        async with get_db() as db:
            cursor = await db.execute(
                """SELECT value FROM memories WHERE category = ? AND key = ?""",
                (category, key),
            )
            row = await cursor.fetchone()
            if row:
                # Update access time
                await db.execute(
                    """UPDATE memories SET last_accessed = CURRENT_TIMESTAMP
                       WHERE category = ? AND key = ?""",
                    (category, key),
                )
                await db.commit()
                return row[0]
            return None

    async def search_memories(
        self, category: str | None = None, query: str = ""
    ) -> list[dict]:
        """Search memories by category and/or keyword."""
        async with get_db() as db:
            if category and query:
                cursor = await db.execute(
                    """SELECT * FROM memories
                       WHERE category = ? AND (key LIKE ? OR value LIKE ?)
                       ORDER BY importance DESC, last_accessed DESC""",
                    (category, f"%{query}%", f"%{query}%"),
                )
            elif category:
                cursor = await db.execute(
                    """SELECT * FROM memories
                       WHERE category = ?
                       ORDER BY importance DESC, last_accessed DESC""",
                    (category,),
                )
            elif query:
                cursor = await db.execute(
                    """SELECT * FROM memories
                       WHERE key LIKE ? OR value LIKE ?
                       ORDER BY importance DESC, last_accessed DESC""",
                    (f"%{query}%", f"%{query}%"),
                )
            else:
                cursor = await db.execute(
                    "SELECT * FROM memories ORDER BY importance DESC LIMIT 50"
                )
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

    # ── User Preferences ──────────────────────────────────────────────────

    async def get_preference(self, key: str) -> str | None:
        """Get a user preference by key."""
        async with get_db() as db:
            cursor = await db.execute(
                "SELECT value FROM user_preferences WHERE key = ?", (key,)
            )
            row = await cursor.fetchone()
            return row[0] if row else None

    async def set_preference(self, key: str, value: str) -> None:
        """Set a user preference (upsert)."""
        async with get_db() as db:
            await db.execute(
                """INSERT INTO user_preferences (key, value, updated_at)
                   VALUES (?, ?, ?)
                   ON CONFLICT(key) DO UPDATE SET
                     value = excluded.value,
                     updated_at = excluded.updated_at""",
                (key, value, datetime.now().isoformat()),
            )
            await db.commit()

    async def get_all_preferences(self) -> dict[str, str]:
        """Get all user preferences as a dict."""
        async with get_db() as db:
            cursor = await db.execute("SELECT key, value FROM user_preferences")
            rows = await cursor.fetchall()
            return {row[0]: row[1] for row in rows}

    # ── Action Logs ────────────────────────────────────────────────────────

    async def log_action(
        self,
        conversation_id: str | None,
        tool_name: str,
        action: str,
        parameters: dict,
        result: str,
        status: str,
        required_confirmation: bool = False,
        was_approved: bool = False,
    ) -> None:
        """Log a tool execution for audit trail."""
        log_id = str(uuid.uuid4())
        async with get_db() as db:
            await db.execute(
                """INSERT INTO action_logs
                   (id, conversation_id, tool_name, action, parameters, result,
                    status, required_confirmation, was_approved)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    log_id,
                    conversation_id,
                    tool_name,
                    action,
                    json.dumps(parameters),
                    result,
                    status,
                    int(required_confirmation),
                    int(was_approved),
                ),
            )
            await db.commit()

    async def get_action_logs(
        self, conversation_id: str | None = None, limit: int = 50
    ) -> list[dict]:
        """Get action logs, optionally filtered by conversation."""
        async with get_db() as db:
            if conversation_id:
                cursor = await db.execute(
                    """SELECT * FROM action_logs
                       WHERE conversation_id = ?
                       ORDER BY executed_at DESC LIMIT ?""",
                    (conversation_id, limit),
                )
            else:
                cursor = await db.execute(
                    "SELECT * FROM action_logs ORDER BY executed_at DESC LIMIT ?",
                    (limit,),
                )
            rows = await cursor.fetchall()
            results = []
            for row in rows:
                entry = dict(row)
                if entry.get("parameters"):
                    entry["parameters"] = json.loads(entry["parameters"])
                results.append(entry)
            return results

    # ── App Registry ──────────────────────────────────────────────────────

    async def register_app(self, name: str, path: str, aliases: list[str] | None = None) -> None:
        """Register or update an application in the registry."""
        async with get_db() as db:
            await db.execute(
                """INSERT INTO app_registry (name, path, aliases)
                   VALUES (?, ?, ?)
                   ON CONFLICT(name) DO UPDATE SET
                     path = excluded.path,
                     aliases = excluded.aliases""",
                (name, path, json.dumps(aliases or [])),
            )
            await db.commit()

    async def get_app(self, name: str) -> dict | None:
        """Get an app by name from the registry."""
        async with get_db() as db:
            cursor = await db.execute(
                "SELECT * FROM app_registry WHERE name = ?", (name.lower(),)
            )
            row = await cursor.fetchone()
            if row:
                entry = dict(row)
                entry["aliases"] = json.loads(entry.get("aliases", "[]"))
                return entry
            return None

    async def record_app_launch(self, name: str) -> None:
        """Record that an app was launched (increment counter)."""
        async with get_db() as db:
            await db.execute(
                """UPDATE app_registry
                   SET launch_count = launch_count + 1,
                       last_launched = CURRENT_TIMESTAMP
                   WHERE name = ?""",
                (name.lower(),),
            )
            await db.commit()
