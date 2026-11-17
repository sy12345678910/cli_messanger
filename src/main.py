import inspect
import json
import textwrap

from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.responses import PlainTextResponse

from chat.get_hardware_id import get_hardware_id
from chat.login_screen import NameScreen
from chat.chat_application import ChatApplication
from chat.run_app import run_app

from server.connection import manager, ActiveClient
from server.db import Database

db = Database()

@asynccontextmanager
async def lifespan(app: FastAPI):
    await db.init_tables()
    yield

app = FastAPI(lifespan=lifespan)

@app.get("/start", response_class=PlainTextResponse)
def get_client(request: Request):
    ws_url = f"ws://{request.url.netloc}/ws"

    setup_imports = textwrap.dedent("""
        import os, sys, json, hashlib, platform, uuid, subprocess, asyncio
        try:
            import websockets
            from rich.markdown import Markdown
            from rich.text import Text
            from textual.app import App, ComposeResult
            from textual.screen import ModalScreen
            from textual.containers import Horizontal, Vertical
            from textual.widgets import Footer, Header, Input, Label, ListItem, ListView, RichLog
        except ImportError:
            cmd = [sys.executable, "-m", "pip", "install", "-q", "websockets", "textual"]
            if os.name != "nt":
                cmd.append("--break-system-packages")
            subprocess.check_call(cmd)
            import websockets
            from rich.markdown import Markdown
            from rich.text import Text
            from textual.app import App, ComposeResult
            from textual.screen import ModalScreen
            from textual.containers import Horizontal, Vertical
            from textual.widgets import Footer, Header, Input, Label, ListItem, ListView, RichLog
    """).strip()

    parts = [
        setup_imports,
        inspect.getsource(get_hardware_id),
        inspect.getsource(NameScreen),
        inspect.getsource(ChatApplication),
        inspect.getsource(run_app),
        f'run_app("{ws_url}")'
    ]
    return "\n\n".join(parts)


async def register_new_user(websocket: WebSocket, hw_id: str):
    await websocket.send_json({"type": "need_name"})
    try:
        reg_data = await websocket.receive_json()
    except (WebSocketDisconnect, TypeError, ValueError):
        raise WebSocketDisconnect

    if not isinstance(reg_data, dict):
        raise WebSocketDisconnect

    username = str(reg_data.get("name", "")).strip()
    if not username:
        await websocket.close(code=1008)
        raise WebSocketDisconnect

    await db.register_user(username, hw_id)


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    client: ActiveClient | None = None

    try:
        try:
            auth_data = await websocket.receive_json()
        except (WebSocketDisconnect, TypeError, ValueError):
            raise WebSocketDisconnect

        if not isinstance(auth_data, dict):
            await websocket.close(code=1008)
            raise WebSocketDisconnect

        hw_id = str(auth_data.get("hardware_id", "")).strip()
        if not hw_id:
            await websocket.close(code=1008)
            raise WebSocketDisconnect

        user_row = await db.get_user_by_hardware_id(hw_id)
        if user_row is None:
            await register_new_user(websocket, hw_id)
            user_row = await db.get_user_by_hardware_id(hw_id)
            if user_row is None:
                await websocket.close(code=1008)
                raise WebSocketDisconnect

        await db.add_online_status(hw_id)

        client = ActiveClient(
            user_id=user_row[0],
            username=user_row[1],
            hard_id=hw_id,
            websocket=websocket
        )
        await manager.connect(client)

        history = await db.get_recent_messages(limit=100)
        init_payload = json.dumps({
            "type": "history",
            "messages": [{"user": r[0], "text": r[1]} for r in history]
        })
        await manager.send_message(init_payload, client)

        users_payload = json.dumps({
            "type": "users",
            "users": [c.username for c in manager.active_connections]
        })
        await manager.broadcast(users_payload)

        while True:
            data = await websocket.receive_json()
            if not isinstance(data, dict):
                continue

            if data.get("type") == "msg":
                text = data.get("text")
                if not isinstance(text, str):
                    continue

                text = text.strip()
                if not text:
                    continue

                await db.send_message(client.user_id, text)

                msg_payload = json.dumps({
                    "type": "msg",
                    "user": client.username,
                    "text": text
                })
                await manager.broadcast(msg_payload)

    except WebSocketDisconnect:
        pass
    except Exception:
        try:
            await websocket.close(code=1011)
        except Exception:
            pass
    finally:
        if client:
            try:
                await manager.disconnect(client)
                await db.remove_online_status(client.hard_id)
            except Exception:
                pass

            users_payload = json.dumps({
                "type": "users",
                "users": [c.username for c in manager.active_connections]
            })
            try:
                await manager.broadcast(users_payload)
            except Exception:
                pass
