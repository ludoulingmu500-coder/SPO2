import sqlite3
from database.database import DB_NAME

CHANNEL_KEYS = ("blacklist_channel_id", "whitelist_channel_id", "log_channel_id")


def get_guild_channels(guild_id):
    with sqlite3.connect(DB_NAME) as conn:
        row = conn.execute("SELECT blacklist_channel_id, whitelist_channel_id, log_channel_id FROM guild_channels WHERE guild_id=?", (str(guild_id),)).fetchone()
    return {key: value for key, value in zip(CHANNEL_KEYS, row or ()) if value is not None}


def set_guild_channel(guild_id, key, channel_id):
    if key not in CHANNEL_KEYS:
        raise ValueError(f"Unknown channel setting: {key}")
    with sqlite3.connect(DB_NAME) as conn:
        conn.execute(
            f"INSERT INTO guild_channels(guild_id, {key}) VALUES(?, ?) "
            f"ON CONFLICT(guild_id) DO UPDATE SET {key}=excluded.{key}",
            (str(guild_id), int(channel_id)),
        )
