import sqlite3
from database.database import DB_NAME


def add_blacklist(value, guild_id):
    with sqlite3.connect(DB_NAME) as conn:
        conn.execute("INSERT OR IGNORE INTO blacklist(guild_id, value) VALUES(?, ?)", (str(guild_id), value))


def is_blacklisted(value, guild_id):
    with sqlite3.connect(DB_NAME) as conn:
        return conn.execute("SELECT 1 FROM blacklist WHERE guild_id=? AND value=?", (str(guild_id), value)).fetchone() is not None


def get_blacklist(guild_id):
    with sqlite3.connect(DB_NAME) as conn:
        rows = conn.execute("SELECT value FROM blacklist WHERE guild_id=?", (str(guild_id),)).fetchall()
    return [row[0] for row in rows]
