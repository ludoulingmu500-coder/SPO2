import sqlite3
from database.database import DB_NAME


def add_whitelist(domain, guild_id):
    with sqlite3.connect(DB_NAME) as conn:
        conn.execute("INSERT OR IGNORE INTO whitelist(guild_id, domain) VALUES(?, ?)", (str(guild_id), domain))


def is_whitelisted(domain, guild_id):
    with sqlite3.connect(DB_NAME) as conn:
        return conn.execute("SELECT 1 FROM whitelist WHERE guild_id=? AND domain=?", (str(guild_id), domain)).fetchone() is not None
