import json
import sys
import subprocess
import asyncio
from unittest import case

try:
    import websockets
    from rich.markdown import Markdown
    from rich.text import Text
    from textual.app import App, ComposeResult
    from textual.containers import Horizontal, Vertical
    from textual.widgets import Footer, Header, Input, Label, ListItem, ListView, RichLog
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", "textual", "websockets"])
    import websockets
    from rich.markdown import Markdown
    from rich.text import Text
    from textual.app import App, ComposeResult
    from textual.containers import Horizontal, Vertical
    from textual.widgets import Footer, Header, Input, Label, ListItem, ListView, RichLog

from chat.get_hardware_id import get_hardware_id
from chat.login_screen import NameScreen


class ChatApplication(App):
    BINDINGS = [("d", "toggle_dark", "Toggle dark mode"), ("q", "quit", "Quit")]
    CSS = """
    #layout {
        height: 1fr;
    }
    #sidebar-list {
        width: 20%;
        height: 100%;
        border: solid cyan;
    }
    #main-column {
        width: 80%;
        height: 100%;
    }
    #chat-log {
        height: 1fr;
        border: solid green;
        padding: 1 2;
    }
    #chat-input {
        dock: bottom;
    }
    """

    USER_COLORS = [
        "bold cyan",
        "bold magenta",
        "bold yellow",
        "bold green",
        "bold bright_blue",
        "bold bright_red",
        "bold orange1",
    ]

    def __init__(self, url: str):
        super().__init__()
        self.url = url
        self.hw_id = get_hardware_id()
        self.ws = None

    def get_user_color(self, username: str) -> str:
        index = sum(ord(ch) for ch in username) % len(self.USER_COLORS)
        return self.USER_COLORS[index]

    def format_and_write(self, username: str, text: str) -> None:
        log = self.query_one("#chat-log", RichLog)
        color = self.get_user_color(username)
        log.write(Text(f"{username}:", style=color))
        log.write(Markdown(text))

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal(id="layout"):
            yield ListView(id="sidebar-list")
            with Vertical(id="main-column"):
                yield RichLog(id="chat-log", markup=True, wrap=True)
                yield Input(placeholder="Input here your message and push Enter...", id="chat-input")
        yield Footer()

    def action_toggle_dark(self) -> None:
        self.theme = "textual-dark" if self.theme == "textual-light" else "textual-light"

    def action_quit(self) -> None:
        self.exit()

    async def on_mount(self) -> None:
        self.run_worker(self.listen_ws())

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        text = event.value.strip()
        if text and self.ws:
            event.input.value = ""
            try:
                await self.ws.send(json.dumps({"type": "msg", "text": text}))
            except (websockets.ConnectionClosed, websockets.exceptions.ConnectionClosed):
                return

    async def listen_ws(self) -> None:
        try:
            async with websockets.connect(self.url) as ws:
                self.ws = ws

                try:
                    await self.ws.send(json.dumps({"hardware_id": self.hw_id}))
                except (websockets.ConnectionClosed, websockets.exceptions.ConnectionClosed):
                    return

                async for raw_msg in ws:
                    try:
                        msg = json.loads(raw_msg)
                    except json.JSONDecodeError:
                        continue

                    msg_type = msg.get("type")
                    await self.select_type_of_message(msg, msg_type)
        except (websockets.ConnectionClosed, websockets.exceptions.ConnectionClosed):
            return
        except (TimeoutError, OSError):
            return

    async def select_type_of_message(self, message: dict, msg_type: str) -> None:
        match msg_type:
            case  "need_name":
                def on_name_entered(chosen_name: str | None):
                    if chosen_name and self.ws:
                        try:
                            asyncio.create_task(self.ws.send(json.dumps({"name": chosen_name})))
                        except (websockets.ConnectionClosed, websockets.exceptions.ConnectionClosed):
                            pass
                self.push_screen(NameScreen(), callback=on_name_entered)
        
            case "history":
                for item in message.get("messages", []):
                    if not isinstance(item, dict):
                        continue
                    user = item.get("user")
                    text = item.get("text")
                    if isinstance(user, str) and isinstance(text, str):
                        self.format_and_write(user, text)
        
            case "msg" | "message":
                user = message.get("user")
                text = message.get("text")
                if isinstance(user, str) and isinstance(text, str):
                    self.format_and_write(user, text)
        
            case "users":
                sidebar = self.query_one("#sidebar-list", ListView)
                await sidebar.clear()
                for user in message.get("users", []):
                    name = user["name"] if isinstance(user, dict) else str(user)
                    color = self.get_user_color(name)
                    await sidebar.append(ListItem(Label(f"[{color}]• {name}[/]")))
