import sqlite3
import time

from database.database import DB_NAME
from services.log_service import write_log

WEEK_SECONDS = 7 * 24 * 60 * 60
DECAY_POINTS_PER_WEEK = 10


def add_and_decay_score(guild_id, user_id, points, return_details=False):
    """Apply weekly decay, add points, persist the score, and log changes."""
    now = time.time()
    guild_id = str(guild_id)
    user_id = str(user_id)
    points_added = max(0, int(points))
    weeks_elapsed = 0
    score_before = 0
    decay_applied = 0

    with sqlite3.connect(DB_NAME) as conn:
        row = conn.execute(
            "SELECT score, last_decay_at FROM user_scores WHERE guild_id=? AND user_id=?",
            (guild_id, user_id),
        ).fetchone()

        if row is None:
            last_decay = now
        else:
            score_before, last_decay = row
            weeks_elapsed = max(0, int((now - last_decay) // WEEK_SECONDS))
            if weeks_elapsed:
                score_after_decay = max(
                    0, score_before - weeks_elapsed * DECAY_POINTS_PER_WEEK
                )
                decay_applied = score_before - score_after_decay
                score_before = score_after_decay
                last_decay += weeks_elapsed * WEEK_SECONDS

        score_after = score_before + points_added
        conn.execute(
            "INSERT INTO user_scores(guild_id, user_id, score, last_decay_at) VALUES(?, ?, ?, ?) "
            "ON CONFLICT(guild_id, user_id) DO UPDATE SET "
            "score=excluded.score, last_decay_at=excluded.last_decay_at",
            (guild_id, user_id, score_after, last_decay),
        )

    if decay_applied or points_added:
        write_log(
            "score.log",
            f"USER_ID={user_id} SCORE={score_before} -> {score_after} "
            f"(DECAY=-{decay_applied} over {weeks_elapsed} week(s), ADD=+{points_added})",
            guild_id,
        )

    if return_details:
        return {
            "score_before": score_before + decay_applied,
            "decay_applied": decay_applied,
            "weeks_elapsed": weeks_elapsed,
            "points_added": points_added,
            "score_after": score_after,
        }

    return score_after
