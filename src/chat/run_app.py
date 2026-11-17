from chat.chat_application import ChatApplication

def run_app(url: str):
    import os
    import sys
    con = open("CON" if os.name == "nt" else "/dev/tty", "r")
    os.dup2(con.fileno(), 0)
    sys.stdin = con

    chat = ChatApplication(url)
    chat.run()