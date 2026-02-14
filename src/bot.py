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

# state: { "<origin_message_id>": { "status": "confirmed|unconfirmed", "confirm_reply_id": "...", "unconfirm_reply_id": "..." } }
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

async def handle_confirm(channel: discord.TextChannel, origin: discord.Message):
    key = str(origin.id)
    entry = state.get(key, {})

    events = parse_events(origin.content)
    if not events:
        return
    ev = events[0]

    url = google_template_url(
        ev.title, ev.location, ev.start, ev.end,
        all_day=getattr(ev, "all_day", False)
    )

    embed = discord.Embed(title="📅 確定：Googleカレンダーに追加")
    embed.add_field(name="タイトル", value=ev.title, inline=False)

    if getattr(ev, "all_day", False):
        embed.add_field(name="日時", value=f"{ev.start:%Y/%m/%d}（終日）", inline=False)
    else:
        embed.add_field(
            name="日時",
            value=f"{ev.start:%Y/%m/%d %H:%M} - {ev.end:%H:%M}",
            inline=False
        )

    embed.add_field(name="場所", value=ev.location or "（未設定）", inline=False)
    embed.set_footer(text="各自でリンクから追加してください")

    # 既に返信メッセージがあるなら「編集」で上書き（増殖しない）
    reply_id = entry.get("confirm_reply_id")
    if reply_id:
        try:
            m = await channel.fetch_message(int(reply_id))
            await m.edit(embed=embed, view=GoogleOnlyView(url))
        except Exception:
            # 取れない/消えてる場合は新規で作り直す
            sent = await origin.reply(embed=embed, view=GoogleOnlyView(url), mention_author=False)
            state[key] = {"status": "confirmed", "confirm_reply_id": str(sent.id)}
            save_state(state)
            return

        state[key] = {"status": "confirmed", "confirm_reply_id": str(reply_id)}
        save_state(state)
        return

    # 返信が無いなら新規に1つ作る
    sent = await origin.reply(embed=embed, view=GoogleOnlyView(url), mention_author=False)
    state[key] = {"status": "confirmed", "confirm_reply_id": str(sent.id)}
    save_state(state)


async def handle_unconfirm(channel: discord.TextChannel, origin: discord.Message):
    key = str(origin.id)
    entry = state.get(key, {})
    reply_id = entry.get("confirm_reply_id")

    # 返信が無いなら何もしない（増やさない）
    if not reply_id:
        state[key] = {"status": "unconfirmed", "confirm_reply_id": None}
        save_state(state)
        return

    embed = discord.Embed(title="🗑️ 確定が解除されました")
    embed.description = (
        "この予定は削除扱いになりました（各自のGoogleカレンダーに入れた分は手動で削除してください）。"
    )

    # 返信を削除せず「編集」して解除状態にする（これで2つに分離しない）
    try:
        m = await channel.fetch_message(int(reply_id))
        await m.edit(embed=embed, view=None)
    except Exception:
        pass

    state[key] = {"status": "unconfirmed", "confirm_reply_id": str(reply_id)}
    save_state(state)

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user} (id={bot.user.id})")

@bot.event
async def on_raw_reaction_add(payload: discord.RawReactionActionEvent):
    # bot自身は無視
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