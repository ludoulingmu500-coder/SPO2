import re

import discord
from discord.ext import commands

from services.blacklist_service import add_blacklist, get_blacklist, is_blacklisted
from services.whitelist_service import add_whitelist, is_whitelisted
from services.spam_detector import detect_spam
from services.score_service import add_and_decay_score
from services.guild_config_service import (
    get_guild_channels, set_guild_channel,
    get_excluded_channels, add_excluded_channel, remove_excluded_channel,
)
from services.log_service import write_log

CHANNEL_MENTION_PATTERN = re.compile(r"<#\d+>")
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

    def resolve_channel_arguments(ctx, arguments):
        """#チャンネル名、Discordのチャンネルメンション、チャンネルIDを解決する。"""
        resolved = []
        for argument in arguments:
            match = re.fullmatch(r"<#(\\d+)>", argument)
            if match:
                channel_id = int(match.group(1))
                channel = ctx.guild.get_channel(channel_id)
            elif argument.isdigit():
                channel = ctx.guild.get_channel(int(argument))
            else:
                channel_name = argument.removeprefix("#").casefold()
                matches = [c for c in ctx.guild.channels if c.name.casefold() == channel_name]
                channel = matches[0] if len(matches) == 1 else None
            if channel is None:
                return None, argument
            resolved.append(channel)
        # 同じチャンネルの重複指定を除く
        unique = {channel.id: channel for channel in resolved}
        return list(unique.values()), None

    @spo.command(name="exclude")
    @commands.has_permissions(administrator=True)
    async def spo_exclude(ctx, *arguments: str):
        if not arguments:
            await ctx.send("除外するチャンネルを指定してください。例: `!spo exclude #お知らせ #ブラックリスト`（チャンネルメンションも使用できます）")
            return
        channels, invalid = resolve_channel_arguments(ctx, arguments)
        if invalid:
            await ctx.send(f"チャンネルを特定できませんでした: `{invalid}`。チャンネルをメンションするか、正確なチャンネル名を指定してください。")
            return
        for channel in channels:
            add_excluded_channel(ctx.guild.id, channel.id)
        await ctx.send("監視対象外に設定しました: " + "、".join(c.mention for c in channels))

    @spo.command(name="include")
    @commands.has_permissions(administrator=True)
    async def spo_include(ctx, *arguments: str):
        if not arguments:
            await ctx.send("監視対象に戻すチャンネルを指定してください。例: `!spo include #お知らせ`")
            return
        channels, invalid = resolve_channel_arguments(ctx, arguments)
        if invalid:
            await ctx.send(f"チャンネルを特定できませんでした: `{invalid}`。チャンネルをメンションするか、正確なチャンネル名を指定してください。")
            return
        removed = [c.mention for c in channels if remove_excluded_channel(ctx.guild.id, c.id)]
        await ctx.send("監視対象に戻しました: " + "、".join(removed) if removed else "指定されたチャンネルは監視対象外ではありません。")

    @spo.command(name="excluded")
    @commands.has_permissions(administrator=True)
    async def spo_excluded(ctx):
        ids = get_excluded_channels(ctx.guild.id)
        channels = [ctx.guild.get_channel(channel_id) for channel_id in ids]
        mentions = [c.mention for c in channels if c is not None]
        await ctx.send("監視対象外チャンネル: " + ("、".join(mentions) if mentions else "なし"))

    async def command_error(ctx, error):
        if isinstance(error, commands.MissingPermissions):
            await ctx.send("この設定コマンドはサーバー管理者のみ利用できます。")
        elif isinstance(error, (commands.BadArgument, commands.MissingRequiredArgument)):
            await ctx.send("チャンネルを `#チャンネル名` の形で指定してください。")

    spo.error(command_error)
    spo_blacklist.error(command_error)
    spo_whitelist.error(command_error)
    spo_logs.error(command_error)
    spo_exclude.error(command_error)
    spo_include.error(command_error)
    spo_excluded.error(command_error)

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
        # 管理者が指定した複数のチャンネルはスパム監視対象外
        excluded_channel_ids = get_excluded_channels(guild_id)
        # フォーラム等のチャンネル内で作成されたスレッドも、親チャンネルが
        # 除外対象なら監視しない（message.channel は Thread になるため）。
        parent_channel_id = getattr(message.channel, "parent_id", None)
        if message.channel.id in excluded_channel_ids or parent_channel_id in excluded_channel_ids:
            return
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

        # ブラックリスト・ホワイトリスト・ログとして指定したチャンネルは
        # 登録処理以外のスパム監視（スコア計算・制裁）から除外する。
        configured_channel_ids = {
            channel_id for channel_id in config.values() if channel_id
        }
        if message.channel.id in configured_channel_ids:
            return

        # Discordの「管理者」または「サーバー管理」権限を持つメンバーは
        # ブラックリスト照合・スパムスコア計算・制裁の対象外にする。
        # ※「管理者」というロール名だけでは判定せず、実際の権限で判定する。
        member_permissions = message.author.guild_permissions
        if member_permissions.administrator or member_permissions.manage_guild:
            return

        if is_blacklisted(user_id, guild_id):
            write_log("evidence.log", f"BLACKLIST USER: {user_id}", guild_id)
            log_channel = log_channel_for(guild_id)
            if log_channel:
                await log_channel.send(f"🚨 ブラックリストユーザー検知\nUser: {message.author}")
            await message.delete()
            await message.author.ban(reason="Blacklisted User")
            return

        # Discordのチャンネルメンション（例: <#123456789>）は
        # ブラックリスト照合から除外する。通常の文章やURLの判定は維持する。
        content_for_blacklist = CHANNEL_MENTION_PATTERN.sub("", message.content)
        for item in get_blacklist(guild_id):
            # ブラックリスト側にチャンネルメンションだけが登録されている場合も照合しない。
            if CHANNEL_MENTION_PATTERN.fullmatch(item.strip()):
                continue
            if item.lower() in content_for_blacklist.lower():
                write_log("evidence.log", f"BLACKLIST DETECTED: {item}", guild_id)
                write_log("history.log", message.content, guild_id)
                log_channel = log_channel_for(guild_id)
                if log_channel:
                    await log_channel.send(f"🚨 ブラックリスト検知\nUser: {message.author}\nMatched: {item}\nMessage: {message.content}")
                await message.delete()
                await message.author.kick(reason="Blacklist Match")
                return

        # チャンネルメンションはスパム判定の本文からも除外する。
        content_for_spam = CHANNEL_MENTION_PATTERN.sub("", message.content).strip()
        # スパム判定は短時間の連投のみ。URLやドメインだけではスパム扱いしない。
        points = detect_spam(user_id, content_for_spam, guild_id) if content_for_spam else 0

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
