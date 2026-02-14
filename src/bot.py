import os
from dotenv import load_dotenv
import discord
from discord.ext import commands

from .parser import parse_events
from .calendar_links import google_template_url
from .storage import load_state, save_state

load_dotenv()

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
MEMO_CHANNEL_NAME = os.getenv("MEMO_CHANNEL_NAME", "memo")
TRIGGER_EMOJI = os.getenv("TRIGGER_EMOJI", "✅")
ADMIN_USER_ID = int(os.getenv("ADMIN_USER_ID", "0"))

intents = discord.Intents.default()
intents.guilds = True
intents.messages = True
intents.message_content = True
intents.reactions = True

bot = commands.Bot(command_prefix="!", intents=intents)

# state: { "<origin_message_id>": { "status": "confirmed|unconfirmed", "reply_id": "..." } }
state = load_state()


class GoogleOnlyView(discord.ui.View):
    def __init__(self, url: str):
        super().__init__(timeout=None)
        self.add_item(
            discord.ui.Button(
                label="Googleカレンダーに追加",
                style=discord.ButtonStyle.link,
                url=url,
            )
        )


def is_trigger_emoji(payload: discord.RawReactionActionEvent) -> bool:
    return str(payload.emoji) == TRIGGER_EMOJI


async def fetch_channel_and_message(payload: discord.RawReactionActionEvent):
    guild = bot.get_guild(payload.guild_id) if payload.guild_id else None
    if guild is None:
        return None, None

    channel = guild.get_channel(payload.channel_id)
    if channel is None:
        return None, None

    # memoチャンネル以外は無視
    if getattr(channel, "name", None) != MEMO_CHANNEL_NAME:
        return None, None

    try:
        message = await channel.fetch_message(payload.message_id)
    except (discord.NotFound, discord.Forbidden):
        return None, None

    return channel, message


def build_confirm_embed(ev) -> discord.Embed:
    embed = discord.Embed(title="📅 確定：Googleカレンダーに追加")
    embed.add_field(name="タイトル", value=ev.title, inline=False)

    if getattr(ev, "all_day", False):
        embed.add_field(name="日時", value=f"{ev.start:%Y/%m/%d}（終日）", inline=False)
    else:
        embed.add_field(
            name="日時",
            value=f"{ev.start:%Y/%m/%d %H:%M} - {ev.end:%H:%M}",
            inline=False,
        )

    if getattr(ev, "notes", ""):
        embed.add_field(name="メモ", value=ev.notes, inline=False)

    embed.set_footer(text="各自でリンクから追加してください")
    return embed


def build_unconfirm_embed() -> discord.Embed:
    embed = discord.Embed(title="🗑️ 確定が解除されました")
    embed.description = "この予定は削除扱いになりました（各自のGoogleカレンダーに入れた分は手動で削除してください）。"
    return embed


async def handle_confirm(channel: discord.TextChannel, origin: discord.Message):
    key = str(origin.id)
    entry = state.get(key, {})
    reply_id = entry.get("reply_id")

    events = parse_events(origin.content)
    if not events:
        return

    # 1行複数対応は将来。いまは先頭1件のみ。
    ev = events[0]

    url = google_template_url(
        ev.title,
        ev.start,
        ev.end,
        all_day=getattr(ev, "all_day", False),
        details=getattr(ev, "notes", ""),
    )
    embed = build_confirm_embed(ev)
    view = GoogleOnlyView(url)

    # 既に返信があるなら「編集」で上書き（増殖しない）
    if reply_id:
        try:
            m = await channel.fetch_message(int(reply_id))
            await m.edit(embed=embed, view=view)
            state[key] = {"status": "confirmed", "reply_id": str(reply_id)}
            save_state(state)
            return
        except Exception:
            # 取れない/消えてる場合は作り直す
            pass

    sent = await origin.reply(embed=embed, view=view, mention_author=False)
    state[key] = {"status": "confirmed", "reply_id": str(sent.id)}
    save_state(state)


async def handle_unconfirm(channel: discord.TextChannel, origin: discord.Message):
    key = str(origin.id)
    entry = state.get(key, {})
    reply_id = entry.get("reply_id")

    if not reply_id:
        state[key] = {"status": "unconfirmed", "reply_id": None}
        save_state(state)
        return

    # 返信を削除せず、編集で解除状態にする（これで2つにならない）
    try:
        m = await channel.fetch_message(int(reply_id))
        await m.edit(embed=build_unconfirm_embed(), view=None)
    except Exception:
        pass

    state[key] = {"status": "unconfirmed", "reply_id": str(reply_id)}
    save_state(state)


@bot.event
async def on_ready():
    print(f"Logged in as {bot.user} (id={bot.user.id})")


@bot.event
async def on_raw_reaction_add(payload: discord.RawReactionActionEvent):
    if payload.user_id == bot.user.id:
        return

    # 管理者（あなた）だけが確定操作できる
    if ADMIN_USER_ID and payload.user_id != ADMIN_USER_ID:
        return

    if not is_trigger_emoji(payload):
        return

    channel, origin = await fetch_channel_and_message(payload)
    if channel is None or origin is None:
        return

    await handle_confirm(channel, origin)


@bot.event
async def on_raw_reaction_remove(payload: discord.RawReactionActionEvent):
    if payload.user_id == bot.user.id:
        return

    # 管理者（あなた）だけが解除操作できる
    if ADMIN_USER_ID and payload.user_id != ADMIN_USER_ID:
        return

    if not is_trigger_emoji(payload):
        return

    channel, origin = await fetch_channel_and_message(payload)
    if channel is None or origin is None:
        return

    await handle_unconfirm(channel, origin)


def main():
    if not DISCORD_TOKEN:
        raise RuntimeError("DISCORD_TOKEN が未設定です")

    from threading import Thread
    from .web import run_web

    print("BOT: starting web thread")
    Thread(target=run_web, daemon=True).start()

    bot.run(DISCORD_TOKEN)


if __name__ == "__main__":
    main()