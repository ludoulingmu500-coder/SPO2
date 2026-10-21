from datetime import datetime
from pathlib import Path

LOG_DIR = Path(__file__).resolve().parents[1] / "logs"


def write_log(filename, text, guild_id="unknown"):
    folder = LOG_DIR / f"guild_{guild_id}"
    folder.mkdir(parents=True, exist_ok=True)
    with (folder / filename).open("a", encoding="utf-8") as log:
        log.write(f"[{datetime.now().astimezone().isoformat()}] {text}\n")
