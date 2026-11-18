from textual.app import ComposeResult 
from textual.screen import ModalScreen
from textual.widgets import Input, Label
from textual.containers import Vertical

class NameScreen(ModalScreen[str]):
    CSS = """
    NameScreen {
        align: center middle;  
    }
    #dialog {
        width: 50;
        height: auto;
        border: thick $accent;
        background: $surface;
        padding: 1 2;
    }
    """

    def compose(self) -> ComposeResult:
        with Vertical(id="dialog"):
            yield Label("Enter your name")
            yield Input(placeholder="Enter here")

    def on_input_submitted(self, event: Input.Submitted):
        name = event.value.strip()
        if name:
            self.dismiss(name)
