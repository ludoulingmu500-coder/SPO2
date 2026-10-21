import sqlite3
from pathlib import Path

DB_NAME = Path(__file__).resolve().parent / "blacklist.db"


def _columns(cur, table):
    return {row[1] for row in cur.execute(f"PRAGMA table_info({table})")}


def _has_single_column_unique(cur, table, column):
    for index in cur.execute(f"PRAGMA index_list({table})").fetchall():
        if index[2]:
            indexed = [row[2] for row in cur.execute(f"PRAGMA index_info({index[1]})")]
            if indexed == [column]:
                return True
    return False


def _ensure_scoped_table(cur, table, column):
    cols = _columns(cur, table)
    if column not in cols or "guild_id" not in cols or _has_single_column_unique(cur, table, column):
        old_table = f"{table}_migration_old"
        cur.execute(f"DROP TABLE IF EXISTS {old_table}")
        cur.execute(f"ALTER TABLE {table} RENAME TO {old_table}")
        cur.execute(f"""CREATE TABLE {table} (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            guild_id TEXT NOT NULL DEFAULT 'legacy',
            {column} TEXT NOT NULL,
            UNIQUE(guild_id, {column})
        )""")
        old_cols = _columns(cur, old_table)
        old_guild = "guild_id" if "guild_id" in old_cols else "'legacy'"
        cur.execute(
            f"INSERT OR IGNORE INTO {table}(id, guild_id, {column}) "
            f"SELECT id, {old_guild}, {column} FROM {old_table}"
        )
        cur.execute(f"DROP TABLE {old_table}")


def init_db():
    DB_NAME.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB_NAME) as conn:
        cur = conn.cursor()
        cur.execute("CREATE TABLE IF NOT EXISTS blacklist (id INTEGER PRIMARY KEY AUTOINCREMENT, value TEXT UNIQUE)")
        cur.execute("CREATE TABLE IF NOT EXISTS whitelist (id INTEGER PRIMARY KEY AUTOINCREMENT, domain TEXT UNIQUE)")
        _ensure_scoped_table(cur, "blacklist", "value")
        _ensure_scoped_table(cur, "whitelist", "domain")
        cur.execute("""CREATE TABLE IF NOT EXISTS guild_channels (
            guild_id TEXT PRIMARY KEY,
            blacklist_channel_id INTEGER,
            whitelist_channel_id INTEGER,
            log_channel_id INTEGER
        )""")
        cur.execute("""CREATE TABLE IF NOT EXISTS user_scores (
            guild_id TEXT NOT NULL,
            user_id TEXT NOT NULL,
            score INTEGER NOT NULL DEFAULT 0,
            last_decay_at REAL NOT NULL,
            PRIMARY KEY(guild_id, user_id)
        )""")
