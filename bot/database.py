import sqlite3

DB_PATH = "queue.db"


def add_missing_column():
    with sqlite3.connect(DB_PATH) as conn:
        columns = conn.execute("PRAGMA table_info(config)").fetchall()
        col_names = [col[1] for col in columns]
        if "auto_fill_enabled" not in col_names:
            conn.execute("ALTER TABLE config ADD COLUMN auto_fill_enabled INTEGER DEFAULT 1;")


def setup_database():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # Create queue table
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS queue (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """
    )

    # Create config table
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS config (
            guild_id INTEGER PRIMARY KEY,
            waiting_channel_id INTEGER,
            live_channel_id INTEGER,
            queue_log_channel INTEGER,
            queue_text_channel_id INTEGER,
            max_guests INTEGER DEFAULT 3,
            queue_embed_message_id INTEGER,
            auto_fill_enabled INTEGER DEFAULT 1
        )
    """
    )

    conn.commit()
    conn.close()

    add_missing_column()


def add_to_queue(user_id: int, username: str):
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            "INSERT OR IGNORE INTO queue (user_id, username) VALUES (?, ?)",
            (user_id, username),
        )


def remove_from_queue(user_id: int):
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("DELETE FROM queue WHERE user_id = ?", (user_id,))


def get_queue():
    with sqlite3.connect(DB_PATH) as conn:
        return conn.execute(
            "SELECT user_id, username FROM queue ORDER BY joined_at"
        ).fetchall()


def clear_queue():
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("DELETE FROM queue")


def update_config_value(guild_id, column, value):
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            f"""
                INSERT INTO config(guild_id, {column})
                VALUES(?,?)
                ON CONFLICT(guild_id) DO UPDATE SET {column} = excluded.{column}
            """,
            (guild_id, value),
        )


def update_queue_embed_message(guild_id, message_id):
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            "UPDATE config SET queue_embed_message_id = ? WHERE guild_id = ?",
            (message_id, guild_id),
        )


def get_queue_embed_message_id(guild_id):
    with sqlite3.connect(DB_PATH) as conn:
        row = conn.execute(
            "SELECT queue_embed_message_id FROM config WHERE guild_id = ?", (guild_id,)
        ).fetchone()
        return row[0] if row else None


def get_config(guild_id):
    with sqlite3.connect(DB_PATH) as conn:
        row = conn.execute(
            "SELECT * FROM config WHERE guild_id = ?", (guild_id,)
        ).fetchone()

        if row:
            return {
                "guild_id": row[0],
                "waiting_channel_id": row[1],
                "live_channel_id": row[2],
                "queue_log_channel": row[3],
                "queue_text_channel_id": row[4],
                "max_guests": row[5],
                "queue_embed_message_id": row[6] if len(row) > 6 else None,
                "auto_fill_enabled": row[7] if len(row) > 7 else 1,
            }
