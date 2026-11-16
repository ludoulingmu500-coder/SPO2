# SPO2 --- Spam Prevention Office

**A Discord moderation bot that monitors messages and manages
server-specific blacklists, whitelists, cumulative scores, and logs.**\
**Discordサーバー向けのスパム対策Botです。サーバーごとにブラックリスト・ホワイトリスト・累積スコア・ログを管理し、メッセージを監視します。**

[日本語](#日本語) \| [English](#english)

------------------------------------------------------------------------

## 日本語

### Botを導入する

**[Discord
Bot招待リンク](https://discord.com/oauth2/authorize?client_id=1559773897535266957&permissions=1099511704582&integration_type=0&scope=bot)**


Botの導入と設定には、対象サーバーで必要な管理権限が必要です。

### 主な機能

-   **サーバー別設定**：ブラックリスト登録用、ホワイトリスト登録用、ログ送信用チャンネルをサーバーごとに設定・保存します。
-   **ブラックリスト**：登録済みユーザーIDと、投稿本文に含まれる登録文字列を検知します。
-   **ホワイトリスト**：登録済みドメインは、未登録ドメインに対するURL加点の対象外となります。
-   **スパム検知**：同一ユーザーの10秒以内の投稿数や同一内容の繰り返しを判定します。
-   **累積スコア**：ユーザー・サーバーごとに保存し、7日経過ごとに10ポイント減算します（下限0）。
-   **通知と記録**：スコア変動や検知を設定済みログチャンネルへ通知し、検知・履歴・証拠・スコア変動ログをサーバー別に保存します。
-   **制裁**：ブラックリスト登録ユーザーと累積スコア100以上の場合はメッセージ削除・BAN、本文中のブラックリスト文字列一致の場合はメッセージ削除・KICKを実行します。

> 現行コードのブラックリスト登録対象は投稿本文の文字列です。添付画像のハッシュ登録・画像照合機能は実装済みとして扱っていません。

### サーバー管理者向け：初期設定

Botを招待後、以下の3種類のテキストチャンネルを用意し、管理者が設定してください。

``` text
!spo blacklist #チャンネル
!spo whitelist #チャンネル
!spo logs #チャンネル
```

`!spo log #チャンネル` も利用できます。`blacklist`、`whitelist`、`logs`
や対応する日本語名などのチャンネルは自動検出される場合があります。設定はSQLiteに保存され、再起動後も維持されます。

**3種類すべてのチャンネルが設定されるまでは、そのサーバーでスパム監視・制裁を行いません。**
登録用チャンネルへの投稿権限は、信頼できる管理者に限定してください。

#### 登録方法

-   **ブラックリスト**：設定したブラックリストチャンネルへ、対象のユーザーIDや検知したい文字列を投稿します。
-   **ホワイトリスト**：設定したホワイトリストチャンネルへ、ドメイン名（例：`example.com`）を投稿します。URL全体ではなくドメイン名を登録してください。

### 検知スコア

  条件                                                      加点
  ----------------------------------------------- --------------
  同一ユーザーが10秒以内に5件以上投稿                        +50
  同一ユーザーが10秒以内に同一内容を3件以上投稿              +50
  ホワイトリストにないURLのドメイン                 URLごとに+20

検知ポイントはサーバー・ユーザーごとに累積します。7日経過するごとに10ポイント減算し、合計100ポイント以上で制裁を実行します。ブラックリスト一致時は、このスコア判定とは別に処理されます。

### 開発者向け：ローカル起動

Pythonとインターネット接続が必要です。依存ライブラリは
`requirements.txt` に記載されています。

``` bash
python -m pip install -r requirements.txt
```

`.env.example` を `.env` にコピーし、Discord Developer
Portalで発行したBotトークンを設定してください。

``` dotenv
TOKEN=ここにBotトークン
```

Developer Portalで必要なPrivileged Gateway
Intentsを有効にし、Botにチャンネル閲覧・投稿・メッセージ管理・KICK・BANなど、使用する機能に応じた権限を付与してください。制裁にはDiscordのロール階層による制限もあります。

``` bash
python run.py
```

データベースは起動時に初期化・移行されます。設定の詳細は `SETUP.md`
を参照してください。

### データとログ

-   `database/blacklist.db`：サーバー別ブラックリスト・ホワイトリスト・チャンネル設定・ユーザースコア
-   `logs/guild_<サーバーID>/detection.log`：検知ログ
-   `logs/guild_<サーバーID>/history.log`：対象メッセージの履歴
-   `logs/guild_<サーバーID>/evidence.log`：検知証拠

従来形式のSQLiteリストは移行時に `legacy`
スコープとして保持され、各サーバーへ自動適用されません。必要な項目は各サーバーで再登録してください。

### 公開時の注意

`.env`、Botトークン、実データ入りの
`database/*.db`、`logs/`、`__pycache__/`
は公開リポジトリへ含めないでください。公開用には `.env.example`
を使用してください。トークンが漏えいした場合はDiscord Developer
Portalで再発行してください。

------------------------------------------------------------------------

## English

### Invite the bot

**[Discord Bot invitation
link](https://discord.com/oauth2/authorize?client_id=1559773897535266957&permissions=1099511704582&integration_type=0&scope=bot)**


You need the appropriate permissions in the target server to invite and
configure the bot.

### Features

-   **Per-server configuration:** Configure and store separate channels
    for blacklist registration, whitelist registration, and log output
    for each server.
-   **Blacklist:** Detects registered user IDs and registered text
    strings contained in message content.
-   **Whitelist:** Registered domains are excluded from URL score
    increases for unregistered domains.
-   **Spam detection:** Evaluates the number of messages posted by the
    same user within 10 seconds and repeated messages with identical
    content.
-   **Cumulative scores:** Scores are stored per user and server. 10
    points are deducted every 7 days, with a minimum score of zero.
-   **Notifications and records:** Score changes and detections are sent
    to the configured log channel. Detection, history, evidence, and
    score-change logs are stored separately for each server.
-   **Moderation actions:** If the author is a blacklisted user or the
    cumulative score reaches 100 or more, the bot deletes the message
    and bans the user. If a blacklisted string is found in the message
    body, the bot deletes the message and kicks the user.

> The current blacklist matching described here applies to text in
> message content. Image-hash registration and image matching are not
> represented as implemented features.

### Initial setup for server administrators

After inviting the bot, create three text channels and configure them
with an administrator account:

``` text
!spo blacklist #channel
!spo whitelist #channel
!spo logs #channel
```

The alias `!spo log #channel` is also supported. Channels named
`blacklist`, `whitelist`, or `logs`, including supported Japanese
equivalents, may be detected automatically. Configuration is stored in
SQLite and persists after restarts.

**Spam monitoring and moderation will not run on a server until all
three channel types have been configured.** Restrict posting access to
the registration channels to trusted administrators.

#### Registering entries

-   **Blacklist:** Post the target user ID or text string you want
    detected in the configured blacklist channel.
-   **Whitelist:** Post a domain name (for example, `example.com`) in
    the configured whitelist channel. Register the domain name, not the
    full URL.

### Detection scores

  -----------------------------------------------------------------------
  Condition                                                Score increase
  ------------------------------ ----------------------------------------
  Same user posts 5 or more                                           +50
  messages within 10 seconds     

  Same user posts identical                                           +50
  content 3 or more times within 
  10 seconds                     

  Domain in a URL is not on the                               +20 per URL
  whitelist                      
  -----------------------------------------------------------------------

Detection points accumulate per server and user. 10 points are deducted
for every 7-day period. Moderation is triggered when the total score
reaches 100 or more. Blacklist matches are handled separately from
score-based detection.

### Running locally (developers)

Python and an internet connection are required. Dependencies are listed
in `requirements.txt`.

``` bash
python -m pip install -r requirements.txt
```

Copy `.env.example` to `.env` and set the bot token generated in the
Discord Developer Portal.

``` dotenv
TOKEN=YOUR_DISCORD_BOT_TOKEN
```

Enable the required Privileged Gateway Intents in the Developer Portal.
Grant the bot the permissions needed for the features you use, such as
viewing channels, sending messages, managing messages, kicking members,
and banning members. Discord role hierarchy restrictions also apply to
moderation actions.

``` bash
python run.py
```

The database is initialized and migrated at startup. See `SETUP.md` for
configuration details.

### Data and logs

-   `database/blacklist.db`: Per-server blacklists, whitelists, channel
    configuration, and user scores
-   `logs/guild_<SERVER_ID>/detection.log`: Detection log
-   `logs/guild_<SERVER_ID>/history.log`: History of relevant messages
-   `logs/guild_<SERVER_ID>/evidence.log`: Detection evidence

Legacy-format SQLite lists are retained under the `legacy` scope during
migration and are not automatically applied to each server. Re-register
any entries that are needed on each server.

### Before publishing

Do not include `.env`, bot tokens, databases containing real operational
data (`database/*.db`), `logs/`, or `__pycache__/` in a public
repository. Use `.env.example` for public distribution. If your token is
exposed, regenerate it in the Discord Developer Portal.
