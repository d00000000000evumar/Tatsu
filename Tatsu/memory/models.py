"""
Tatsu AI — Database Models
============================
SQLite schema definitions and initialization.
Uses aiosqlite for async database operations.
"""

import aiosqlite
import logging

import config

logger = logging.getLogger("tatsu.db")

# ── Schema SQL ─────────────────────────────────────────────────────────────────

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS conversations (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL DEFAULT 'New Conversation',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS messages (
    id TEXT PRIMARY KEY,
    conversation_id TEXT NOT NULL,
    role TEXT NOT NULL CHECK(role IN ('user', 'assistant', 'system', 'tool')),
    content TEXT NOT NULL DEFAULT '',
    tool_calls TEXT,
    tool_name TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS memories (
    id TEXT PRIMARY KEY,
    category TEXT NOT NULL,
    key TEXT NOT NULL,
    value TEXT NOT NULL,
    importance INTEGER DEFAULT 5 CHECK(importance BETWEEN 1 AND 10),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_accessed TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(category, key)
);

CREATE TABLE IF NOT EXISTS action_logs (
    id TEXT PRIMARY KEY,
    conversation_id TEXT,
    tool_name TEXT NOT NULL,
    action TEXT NOT NULL,
    parameters TEXT,
    result TEXT,
    status TEXT NOT NULL CHECK(status IN ('success', 'failed', 'denied', 'cancelled', 'error')),
    required_confirmation INTEGER DEFAULT 0,
    was_approved INTEGER DEFAULT 0,
    executed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (conversation_id) REFERENCES conversations(id)
);

CREATE TABLE IF NOT EXISTS user_preferences (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS app_registry (
    name TEXT PRIMARY KEY,
    path TEXT NOT NULL,
    aliases TEXT DEFAULT '[]',
    launch_count INTEGER DEFAULT 0,
    last_launched TIMESTAMP
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_messages_conversation ON messages(conversation_id, created_at);
CREATE INDEX IF NOT EXISTS idx_memories_category ON memories(category);
CREATE INDEX IF NOT EXISTS idx_action_logs_conversation ON action_logs(conversation_id);
CREATE INDEX IF NOT EXISTS idx_action_logs_tool ON action_logs(tool_name);
"""


async def init_database() -> None:
    """Initialize the database with all required tables."""
    logger.info(f"Initializing database at: {config.DATABASE_PATH}")
    async with aiosqlite.connect(config.DATABASE_PATH) as db:
        await db.executescript(SCHEMA_SQL)
        await db.commit()
    logger.info("Database initialized successfully.")


from contextlib import asynccontextmanager

@asynccontextmanager
async def get_db():
    """Get an async database connection."""
    async with aiosqlite.connect(config.DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        yield db
