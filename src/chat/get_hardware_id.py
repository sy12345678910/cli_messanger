import platform
import uuid
import hashlib

def get_hardware_id() -> str:
    raw_hd = f"{uuid.getnode()}-{platform.machine()}-{platform.processor()}"
    return hashlib.sha256(raw_hd.encode()).hexdigest()[:32]