from collections import defaultdict
import time

message_cache = defaultdict(list)


def detect_spam(user_id, content, guild_id="0"):
    now = time.time()
    key = (str(guild_id), str(user_id))
    message_cache[key].append((content, now))
    message_cache[key] = [message for message in message_cache[key] if now - message[1] < 10]
    score = 0
    if len(message_cache[key]) >= 5:
        score += 50
    same_count = sum(1 for message in message_cache[key] if message[0] == content)
    if same_count >= 3:
        score += 50
    return score
