from chat.chat_application import ChatApplication

def run_app(url: str):
    import os
    import sys

    if os.name == "nt":
        try:
            import ctypes
            import msvcrt

            kernel32 = ctypes.windll.kernel32
            con_in = open("CONIN$", "rb+", buffering=0)
            os.dup2(con_in.fileno(), 0)
            sys.stdin = open(0, "r", encoding="utf-8", closefd=False)

            in_handle = msvcrt.get_osfhandle(0)
            kernel32.SetStdHandle(-10, in_handle)  

            mode = ctypes.c_ulong()
            if kernel32.GetConsoleMode(in_handle, ctypes.byref(mode)):
                new_mode = (mode.value & ~0x0040) | 0x0080 | 0x0010 | 0x0008 | 0x0200
                kernel32.SetConsoleMode(in_handle, new_mode)

            out_handle = kernel32.GetStdHandle(-11)  
            out_mode = ctypes.c_ulong()
            if kernel32.GetConsoleMode(out_handle, ctypes.byref(out_mode)):
                kernel32.SetConsoleMode(out_handle, out_mode.value | 0x0004)
        except Exception:
            pass
    else:
        con = open("/dev/tty", "r")
        os.dup2(con.fileno(), 0)
        sys.stdin = con

    chat = ChatApplication(url)
    chat.run()
