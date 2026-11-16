from collections import defaultdict
import time

# サーバー・ユーザーごとに直近10秒の投稿時刻を保持する
message_cache = defaultdict(list)


def detect_spam(user_id, content, guild_id="0"):
    """
    短時間の連投だけをスパムとして判定する。
    - 直近10秒以内に5件以上投稿した場合に50点
    - 同じ文章かどうか、URLを含むかどうかは判定しない
    - チャンネルメンションだけの投稿は events.py 側でこの関数に渡さない
    """
    if not content or not content.strip():
        return 0

    now = time.time()
    key = (str(guild_id), str(user_id))

    message_cache[key].append(now)
    message_cache[key] = [
        posted_at for posted_at in message_cache[key]
        if now - posted_at < 10
    ]

    return 50 if len(message_cache[key]) >= 5 else 0
