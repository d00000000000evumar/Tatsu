"""
Tatsu AI — FastAPI Server
============================
Main server with WebSocket for real-time chat and REST endpoints
for system info, conversations, and tool management.
"""

import json
import logging
import asyncio
from datetime import datetime
from contextlib import asynccontextmanager

import psutil
import uvicorn
from pydantic import BaseModel
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

import config
from core.llm_provider import LLMProvider
from core.agent import TatsuAgent
from memory.models import init_database
from memory.short_term import ShortTermMemory
from memory.long_term import LongTermMemory
from memory.semantic import SemanticMemory
from tools.registry import ToolRegistry
from tools.calculator import CalculatorTool
from tools.browser import BrowserTool
from tools.system_info import SystemInfoTool
from tools.app_launcher import AppLauncherTool
from tools.file_manager import FileManagerTool
from tools.search import SearchTool
from tools.terminal import TerminalTool
from tools.memory_tool import MemoryTool
from tools.task_planner import TaskPlannerTool
from safety.confirmation import ConfirmationGate
from safety.action_logger import ActionLogger
from safety.permissions import PermissionManager
from api.auth import get_current_user, verify_websocket, create_token

logger = logging.getLogger("tatsu.server")

# ── Global instances ──────────────────────────────────────────────────────────
llm: LLMProvider | None = None
agent: TatsuAgent | None = None
tool_registry: ToolRegistry | None = None
long_term_memory: LongTermMemory | None = None
confirmation_gate: ConfirmationGate | None = None
semantic_memory: SemanticMemory | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize all subsystems on startup."""
    global llm, agent, tool_registry, long_term_memory, confirmation_gate, semantic_memory

    logger.info("🚀 Starting Tatsu AI...")

    # 1. Database
    await init_database()
    logger.info("✅ Database initialized")

    # 2. Memory systems
    short_term = ShortTermMemory()
    long_term_memory = LongTermMemory()
    semantic_memory = SemanticMemory()
    await semantic_memory.initialize()
    logger.info("✅ Memory systems ready")

    # 3. Safety
    confirmation_gate = ConfirmationGate()
    permission_mgr = PermissionManager()
    action_logger = ActionLogger(long_term_memory)
    logger.info("✅ Safety systems ready")

    # 4. LLM
    llm = LLMProvider()
    connected = await llm.check_connection()
    if connected:
        logger.info(f"✅ LLM connected: {config.OLLAMA_MODEL}")
    else:
        logger.warning(
            f"⚠️ LLM not available. Ensure Ollama is running with model '{config.OLLAMA_MODEL}'. "
            f"Run: ollama pull {config.OLLAMA_MODEL}"
        )

    # 5. Tool registry
    tool_registry = ToolRegistry()
    tool_registry.register_many([
        CalculatorTool(),
        BrowserTool(),
        SystemInfoTool(),
        AppLauncherTool(),
        FileManagerTool(),
        SearchTool(),
        TerminalTool(),
        MemoryTool(long_term_memory),
        TaskPlannerTool(),
    ])
    logger.info(f"✅ {tool_registry.count} tools registered")

    # 6. Agent
    agent = TatsuAgent(
        llm=llm,
        tool_registry=tool_registry,
        short_term_memory=short_term,
        long_term_memory=long_term_memory,
        confirmation_gate=confirmation_gate,
        action_logger=action_logger,
        permission_manager=permission_mgr,
    )
    logger.info("✅ Agent ready")

    logger.info(f"🌐 Tatsu AI is live at http://{config.SERVER_HOST}:{config.SERVER_PORT}")

    yield

    logger.info("Tatsu AI shutting down...")


# ── FastAPI App ───────────────────────────────────────────────────────────────

app = FastAPI(
    title="Tatsu AI",
    description="Local AI Assistant for Windows",
    version="1.0.0",
    lifespan=lifespan,
)

# Serve static UI files
app.mount("/static", StaticFiles(directory=str(config.UI_DIR)), name="static")


# ── Routes ────────────────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def serve_ui():
    """Serve the main UI page."""
    html_path = config.UI_DIR / "index.html"
    return HTMLResponse(content=html_path.read_text(encoding="utf-8"))

class LoginRequest(BaseModel):
    password: str

@app.post("/api/login")
async def login(req: LoginRequest):
    """Authenticate user and return JWT."""
    if req.password == config.AUTH_PASSWORD:
        token = create_token()
        return {"status": "success", "token": token}
    raise HTTPException(status_code=401, detail="Invalid password")

@app.get("/api/status")
async def get_status(authenticated: bool = Depends(get_current_user)):
    """Get system status."""
    llm_ok = await llm.check_connection() if llm else False
    return {
        "status": "ok",
        "version": "1.0.0",
        "model": config.OLLAMA_MODEL,
        "tools_count": tool_registry.count if tool_registry else 0,
        "llm_connected": llm_ok,
        "timestamp": datetime.now().isoformat(),
    }


@app.get("/api/system")
async def get_system_info(authenticated: bool = Depends(get_current_user)):
    """Get real-time system stats for the HUD."""
    cpu = psutil.cpu_percent(interval=0.1)
    mem = psutil.virtual_memory()
    disk = psutil.disk_usage("/")
    boot = datetime.fromtimestamp(psutil.boot_time())
    uptime = datetime.now() - boot

    return {
        "cpu": round(cpu, 1),
        "ram": round(mem.percent, 1),
        "ram_used": round(mem.used / (1024**3), 1),
        "ram_total": round(mem.total / (1024**3), 1),
        "disk": round(disk.percent, 1),
        "disk_used": round(disk.used / (1024**3), 1),
        "disk_total": round(disk.total / (1024**3), 1),
        "uptime": str(uptime).split(".")[0],
        "time": datetime.now().strftime("%H:%M:%S"),
        "date": datetime.now().strftime("%Y-%m-%d"),
    }


@app.get("/api/tools")
async def list_tools(authenticated: bool = Depends(get_current_user)):
    """List all available tools."""
    if not tool_registry:
        return []
    tools = []
    for name, tool in tool_registry.get_all_tools().items():
        tools.append({
            "name": tool.name,
            "description": tool.description,
            "risk_level": tool.risk_level.value,
            "requires_confirmation": tool.requires_confirmation,
        })
    return tools


@app.get("/api/conversations")
async def list_conversations(authenticated: bool = Depends(get_current_user)):
    """List recent conversations."""
    if not long_term_memory:
        return []
    return await long_term_memory.list_conversations()


@app.get("/api/conversations/{conv_id}/messages")
async def get_conversation_messages(conv_id: str, authenticated: bool = Depends(get_current_user)):
    """Get messages for a conversation."""
    if not long_term_memory:
        return []
    return await long_term_memory.load_conversation_messages(conv_id)

@app.put("/api/conversations/{conv_id}")
async def update_conversation_title(conv_id: str, data: dict, authenticated: bool = Depends(get_current_user)):
    """Update conversation title."""
    if not long_term_memory:
        return {"status": "error"}
    title = data.get("title", "Untitled")
    await long_term_memory.update_conversation_title(conv_id, title)
    return {"status": "success"}

@app.delete("/api/conversations/{conv_id}")
async def delete_conversation(conv_id: str, authenticated: bool = Depends(get_current_user)):
    """Delete a conversation."""
    if not long_term_memory:
        return {"status": "error"}
    # LongTermMemory doesn't have delete_conversation natively, let's implement it or execute SQL directly
    from memory.models import get_db
    async with get_db() as db:
        await db.execute("DELETE FROM conversations WHERE id = ?", (conv_id,))
        await db.execute("DELETE FROM messages WHERE conversation_id = ?", (conv_id,))
        await db.execute("DELETE FROM action_logs WHERE conversation_id = ?", (conv_id,))
        await db.commit()
    return {"status": "success"}


# ── WebSocket Chat ────────────────────────────────────────────────────────────

@app.websocket("/ws/chat")
async def websocket_chat(websocket: WebSocket):
    """Real-time bidirectional chat via WebSocket."""
    # Check Auth
    if not await verify_websocket(websocket):
        await websocket.close(code=1008, reason="Unauthorized")
        return

    await websocket.accept()
    logger.info("WebSocket client connected")

    # Set up confirmation callback for this connection
    async def send_confirmation_request(data: dict):
        await websocket.send_json(data)

    if confirmation_gate:
        confirmation_gate.set_send_callback(send_confirmation_request)

    # Start a new conversation
    if agent:
        conversation_id = await agent.start_conversation()
    else:
        conversation_id = None

    try:
        while True:
            # Receive message from client
            raw = await websocket.receive_text()
            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                data = {"type": "message", "content": raw}

            msg_type = data.get("type", "message")

            # Handle confirmation responses
            if msg_type == "confirm" and confirmation_gate:
                action_id = data.get("action_id", "")
                approved = data.get("approved", False)
                confirmation_gate.resolve(action_id, approved)
                continue

            # Handle cancel
            if msg_type == "cancel":
                await websocket.send_json({
                    "type": "status",
                    "content": "Operation cancelled.",
                })
                continue
                
            # Handle switching conversations
            if msg_type == "load_conversation":
                conv_id = data.get("id")
                if agent and conv_id:
                    await agent.start_conversation(conv_id)
                    await websocket.send_json({"type": "status", "content": "Loaded conversation context."})
                continue

            if msg_type == "new_conversation":
                if agent:
                    await agent.start_conversation()
                    await websocket.send_json({"type": "status", "content": "Started new conversation context."})
                continue

            # Handle chat messages
            if msg_type == "message":
                content = data.get("content", "").strip()
                if not content:
                    continue

                if not agent:
                    await websocket.send_json({
                        "type": "error",
                        "content": "Agent not initialized. Please check server logs.",
                    })
                    continue

                # Process through agent and stream events
                try:
                    async for event in agent.run(content):
                        event_data = {
                            "type": event.type,
                            "content": event.content,
                            "tool": event.tool,
                            "args": event.args or {},
                            "result": event.result,
                            "action_id": event.action_id,
                            "details": event.details or {},
                            "timestamp": datetime.now().isoformat(),
                        }
                        await websocket.send_json(event_data)
                except Exception as e:
                    logger.exception(f"Agent error: {e}")
                    await websocket.send_json({
                        "type": "error",
                        "content": f"An error occurred: {str(e)}",
                    })

    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected")
    except Exception as e:
        logger.exception(f"WebSocket error: {e}")


# ── Server Runner ─────────────────────────────────────────────────────────────

def run_server():
    """Start the Uvicorn server."""
    # Configure logging
    logging.basicConfig(
        level=getattr(logging, config.LOG_LEVEL),
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(config.LOG_FILE, encoding="utf-8"),
        ],
    )

    uvicorn.run(
        "api.server:app",
        host=config.SERVER_HOST,
        port=config.SERVER_PORT,
        reload=False,
        log_level="info",
    )
