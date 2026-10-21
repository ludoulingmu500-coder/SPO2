import re
from urllib.parse import urlparse

import discord
from discord.ext import commands

from services.blacklist_service import add_blacklist, get_blacklist, is_blacklisted
from services.whitelist_service import add_whitelist, is_whitelisted
from services.spam_detector import detect_spam
from services.score_service import add_and_decay_score
from services.guild_config_service import get_guild_channels, set_guild_channel
from services.log_service import write_log

URL_PATTERN = re.compile(r"https?://\S+", re.IGNORECASE)
CHANNEL_NAMES = {
    "blacklist_channel_id": {"blacklist", "black-list", "black_list", "blacklist-channel", "ブラックリスト", "ブラックリスト登録"},
    "whitelist_channel_id": {"whitelist", "white-list", "white_list", "whitelist-channel", "ホワイトリスト", "ホワイトリスト登録"},
    "log_channel_id": {"log", "logs", "bot-log", "bot-logs", "mod-log", "mod-logs", "log-channel", "ログ", "監査ログ", "検知ログ"},
}


def setup_events(bot):
    def discover_guild_channels(guild):
        guild_id = str(guild.id)
        config = bot.guild_configs.get(guild_id)
        if config is None:
            config = get_guild_channels(guild_id)
            bot.guild_configs[guild_id] = config
        for channel in guild.text_channels:
            name = channel.name.casefold().replace("_", "-").replace(" ", "-")
            for key, aliases in CHANNEL_NAMES.items():
                if name in {item.casefold().replace("_", "-").replace(" ", "-") for item in aliases} and not config.get(key):
                    config[key] = channel.id
                    set_guild_channel(guild_id, key, channel.id)
        return config

    @bot.group(name="spo", invoke_without_command=True)
    async def spo(ctx):
        if ctx.guild:
            await ctx.send("管理者設定: `!spo blacklist #チャンネル` / `!spo whitelist #チャンネル` / `!spo logs #チャンネル`")

    async def set_channel(ctx, key, channel):
        if ctx.guild is None:
            return
        if channel.guild.id != ctx.guild.id:
            await ctx.send("同じサーバー内のチャンネルを指定してください。")
            return
        config = bot.guild_configs.setdefault(str(ctx.guild.id), get_guild_channels(ctx.guild.id))
        config[key] = channel.id
        set_guild_channel(ctx.guild.id, key, channel.id)
        await ctx.send(f"{key.removesuffix('_channel_id')} チャンネルを {channel.mention} に設定しました。")

    @spo.command(name="blacklist")
    @commands.has_permissions(administrator=True)
    async def spo_blacklist(ctx, channel: discord.TextChannel):
        await set_channel(ctx, "blacklist_channel_id", channel)

    @spo.command(name="whitelist")
    @commands.has_permissions(administrator=True)
    async def spo_whitelist(ctx, channel: discord.TextChannel):
        await set_channel(ctx, "whitelist_channel_id", channel)

    @spo.command(name="logs", aliases=["log"])
    @commands.has_permissions(administrator=True)
    async def spo_logs(ctx, channel: discord.TextChannel):
        await set_channel(ctx, "log_channel_id", channel)

    async def command_error(ctx, error):
        if isinstance(error, commands.MissingPermissions):
            await ctx.send("この設定コマンドはサーバー管理者のみ利用できます。")
        elif isinstance(error, (commands.BadArgument, commands.MissingRequiredArgument)):
            await ctx.send("チャンネルを `#チャンネル名` の形で指定してください。")

    spo.error(command_error)
    spo_blacklist.error(command_error)
    spo_whitelist.error(command_error)
    spo_logs.error(command_error)

    def log_channel_for(guild_id):
        channel_id = bot.guild_configs.get(str(guild_id), {}).get("log_channel_id")
        return bot.get_channel(channel_id) if channel_id else None

    @bot.event
    async def on_ready():
        for guild in bot.guilds:
            config = discover_guild_channels(guild)
            missing = [key.removesuffix("_channel_id") for key in CHANNEL_NAMES if not config.get(key)]
            if missing:
                print(f"{guild.name}: チャンネル未設定 ({', '.join(missing)})")
            else:
                print(f"{guild.name}: チャンネル検出完了")
        print(f"{bot.user} 起動完了 / 接続サーバー数: {len(bot.guilds)}")

    @bot.event
    async def on_guild_join(guild):
        discover_guild_channels(guild)

    @bot.event
    async def on_message(message):
        if message.author.bot or message.guild is None:
            return

        context = await bot.get_context(message)
        if context.valid:
            await bot.invoke(context)
            return

        guild_id = str(message.guild.id)
        config = discover_guild_channels(message.guild)
        if any(not config.get(key) for key in CHANNEL_NAMES):
            await bot.process_commands(message)
            return

        user_id = str(message.author.id)
        if message.channel.id == config["blacklist_channel_id"]:
            if message.content.strip():
                add_blacklist(message.content.strip(), guild_id)
                await message.channel.send(f"登録完了: {message.content.strip()}")
            return
        if message.channel.id == config["whitelist_channel_id"]:
            if message.content.strip():
                add_whitelist(message.content.strip(), guild_id)
                await message.channel.send(f"登録完了: {message.content.strip()}")
            return

        if is_blacklisted(user_id, guild_id):
            write_log("evidence.log", f"BLACKLIST USER: {user_id}", guild_id)
            log_channel = log_channel_for(guild_id)
            if log_channel:
                await log_channel.send(f"🚨 ブラックリストユーザー検知\nUser: {message.author}")
            await message.delete()
            await message.author.ban(reason="Blacklisted User")
            return

        for item in get_blacklist(guild_id):
            if item.lower() in message.content.lower():
                write_log("evidence.log", f"BLACKLIST DETECTED: {item}", guild_id)
                write_log("history.log", message.content, guild_id)
                log_channel = log_channel_for(guild_id)
                if log_channel:
                    await log_channel.send(f"🚨 ブラックリスト検知\nUser: {message.author}\nMatched: {item}\nMessage: {message.content}")
                await message.delete()
                await message.author.kick(reason="Blacklist Match")
                return

        points = detect_spam(user_id, message.content, guild_id)
        for url in URL_PATTERN.findall(message.content):
            domain = urlparse(url).netloc.lower()
            if domain and not is_whitelisted(domain, guild_id):
                points += 20

        # Persist per-user risk points, apply one 10-point reduction for each
        # complete seven-day period, then add the points from this message.
        score_change = add_and_decay_score(guild_id, user_id, points, return_details=True)
        total_score = score_change["score_after"]
        if score_change["decay_applied"] or score_change["points_added"]:
            log_channel = log_channel_for(guild_id)
            if log_channel:
                await log_channel.send(
                    f"📊 スコア変動\n"
                    f"ユーザー: {message.author.mention}\n"
                    f"変動前: {score_change['score_before']}\n"
                    f"週次減算: -{score_change['decay_applied']}（{score_change['weeks_elapsed']}週分）\n"
                    f"今回加算: +{score_change['points_added']}\n"
                    f"現在スコア: {total_score}"
                )
        if total_score >= 100:
            write_log("detection.log", f"{user_id} SCORE={total_score} (+{points})", guild_id)
            write_log("history.log", message.content, guild_id)
            write_log("evidence.log", f"{message.author}: {message.content}", guild_id)
            log_channel = log_channel_for(guild_id)
            if log_channel:
                await log_channel.send(f"🚨 スパム検知\nUser: {message.author}\nScore: {total_score} (+{points})\nMessage: {message.content}")
            await message.delete()
            await message.author.ban(reason=f"Spam Score={total_score}")
            return

        await bot.process_commands(message)
