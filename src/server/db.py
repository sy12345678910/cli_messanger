import aiosqlite

class Database:
    def __init__(self, db_path: str = "../database.db"):
        self.db_path = db_path

    async def init_tables(self):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("PRAGMA foreign_keys = ON")
            
            await db.execute("""
                CREATE TABLE IF NOT EXISTS user (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    online BOOLEAN DEFAULT 0,
                    hardware_id TEXT NOT NULL UNIQUE
                )
            """)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS message (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    sender_id INTEGER NOT NULL,
                    text TEXT NOT NULL,
                    sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (sender_id) REFERENCES user(id)
                )
            """)
            await db.execute("""
                UPDATE user SET online = 0;
            """)
            await db.commit()

    async def register_user(self, username: str, hardware_id: str):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "INSERT OR IGNORE INTO user (username, hardware_id) VALUES (?, ?)",
                (username, hardware_id)
            )
            await db.commit()

    async def get_user_by_hardware_id(self, hardware_id: str):
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("SELECT * FROM user WHERE hardware_id = ?", (hardware_id,)) as cursor:
                return await cursor.fetchone()

    async def get_user_by_username(self, username: str):
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("SELECT * FROM user WHERE username = ?", (username,)) as cursor:
                return await cursor.fetchone()

    async def send_message(self, sender_id: int, text: str):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("INSERT INTO message (sender_id, text) VALUES (?, ?)", (sender_id, text))
            await db.commit()

    async def get_hw(self):
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("SELECT hardware_id FROM user") as cursor:
                rows = await cursor.fetchall()
                return [row[0] for row in rows]

    async def get_recent_messages(self, limit: int = 50):
        async with aiosqlite.connect(self.db_path) as db:
            query = """
                SELECT user.username, message.text, message.sent_at
                FROM message
                JOIN user ON message.sender_id = user.id
                ORDER BY message.id DESC
                LIMIT ?
            """
            async with db.execute(query, (limit,)) as cursor:
                rows = await cursor.fetchall()
                return list(reversed(rows))

    async def add_online_status(self, hardware_id: str):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("UPDATE user SET online = 1 WHERE hardware_id = ?", (hardware_id,))
            await db.commit()

    async def remove_online_status(self, hardware_id: str):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("UPDATE user SET online = 0 WHERE hardware_id = ?", (hardware_id,))
            await db.commit()