import asyncio
import os
from telethon import TelegramClient, events, Button
from moviepy.editor import VideoFileClip, vfx, TextClip, CompositeVideoClip

# ========== CONFIG ==========
API_ID = int(os.environ["API_ID"])
API_HASH = os.environ["API_HASH"]
BOT_TOKEN = os.environ["BOT_TOKEN"]
ACCESS_CODE = "20002000"
AUTH_FILE = "authorized.txt"

# ====== تحميل المستخدمين المخولين ======
def load_authorized():
    if os.path.exists(AUTH_FILE):
        with open(AUTH_FILE, "r") as f:
            return set(map(int, f.read().splitlines()))
    return set()

def save_authorized(uid):
    if uid not in AUTHORIZED_USERS:
        with open(AUTH_FILE, "a") as f:
            f.write(f"{uid}\n")
        AUTHORIZED_USERS.add(uid)

AUTHORIZED_USERS = load_authorized()
bot = TelegramClient("bot", API_ID, API_HASH).start(bot_token=BOT_TOKEN)
state = {}

# ====== الحقوق ↔ القنوات ======
rights_channels = [
    {"user": "mxhasd",   "channel": "https://t.me/+DaXIWRnl-PAzMWE5"},
    {"user": "m3_wt4_",  "channel": "https://t.me/+WV_zEH1or1plYmUy"},
    {"user": "271f_",    "channel": "https://t.me/+Hs6PyBFPc7kzNzI5"},
    {"user": "m3_wt33",  "channel": "https://t.me/+IOdlFnTe275lZWNi"},
    {"user": "m3_wt2",   "channel": "https://t.me/+qqC1xo6x44ZmMWZi"},
    {"user": "m3_wt55",  "channel": "https://t.me/+cUDaK0ag8lI3OTYy"},
    {"user": "m3_wt6",   "channel": "https://t.me/+tZN6h2m2cUs2MjIx"},
]

# ====== HELPERS ======
def size_map(val):
    return {1:20, 2:30, 3:40, 4:50, 5:60}.get(val, 30)

def get_color(idx):
    colors = [
        "#ff0000", "#00ff00", "#0000ff", "#ffff00", "#ff00ff",
        "#00ffff", "#ff8000", "#8000ff", "#0080ff", "#808080"
    ]
    return colors[idx % len(colors)]

def process_video(file_path, rights_list, bio_text, rights_size, bio_size, output_folder):
    clip = VideoFileClip(file_path)
    width, height = clip.size

    for i, r_text in enumerate(rights_list):
        r_color = get_color(i)

        txt_clip = TextClip(
            r_text, fontsize=rights_size, color=r_color,
            method="caption", size=(width, None)
        ).set_pos(lambda t: ((t*100) % (width+200) - 200, 50)).set_duration(clip.duration)

        bio_clip = TextClip(
            bio_text, fontsize=bio_size, color=r_color,
            method="caption", size=(width, None)
        ).set_pos(("center", height - 100)).set_duration(clip.duration)

        final = CompositeVideoClip([clip, txt_clip, bio_clip])
        final = final.fx(vfx.colorx, 1 + i*0.02)

        os.makedirs(output_folder, exist_ok=True)
        out_path = os.path.join(output_folder, f"copy_{i+1}.mp4")
        final.write_videofile(out_path, codec="libx264", audio_codec="aac", threads=2)

    return output_folder

# ========== START ==========
@bot.on(events.NewMessage(pattern="/start"))
async def start(event):
    uid = event.sender_id

    if uid not in AUTHORIZED_USERS:
        state[uid] = {"step":"auth"}
        await event.respond("🔐 أرسل رمز الدخول:")
        return

    if uid not in state:
        state[uid] = {"step":"await_video"}
    await event.respond("📹 أرسل الفيديو:")

# ========== FLOW ==========
@bot.on(events.NewMessage)
async def flow(event):
    uid = event.sender_id
    txt = (event.text or "").strip()
    if uid not in state:
        return
    s = state[uid]

    if s.get("step") == "auth":
        if txt != ACCESS_CODE:
            await event.respond("❌ رمز خاطئ")
            return
        save_authorized(uid)
        state[uid]["step"] = "await_video"
        await event.respond("✅ تم التحقق\n📹 أرسل الفيديو:")
        return

    if s.get("step") == "await_video" and event.media:
        s["file_path"] = await event.download_media()
        s.setdefault("rights_list", [rc["user"] for rc in rights_channels])
        s["step"] = "choose_rights_size"
        await event.respond(
            "📏 اختر حجم الحقوق:",
            buttons=[
                [Button.inline("1️⃣", b"rights_1"), Button.inline("2️⃣", b"rights_2"), Button.inline("3️⃣", b"rights_3")],
                [Button.inline("4️⃣", b"rights_4"), Button.inline("5️⃣", b"rights_5")]
            ]
        )
        return

    if s.get("step") == "enter_bio_text":
        s["bio_text"] = txt
        await start_processing(event, s)

# ========== CALLBACKS ==========
@bot.on(events.CallbackQuery)
async def cb(event):
    await event.answer()
    uid = event.sender_id
    s = state.get(uid)
    if not s:
        return
    data = event.data.decode()

    if data.startswith("rights_"):
        s["rights_size"] = int(data.split("_")[1])
        s["step"] = "choose_bio_size"
        await event.edit(
            "📏 اختر حجم البايو:",
            buttons=[
                [Button.inline("1️⃣", b"bio_1"), Button.inline("2️⃣", b"bio_2"), Button.inline("3️⃣", b"bio_3")],
                [Button.inline("4️⃣", b"bio_4"), Button.inline("5️⃣", b"bio_5")]
            ]
        )
        return

    if data.startswith("bio_"):
        s["bio_size"] = int(data.split("_")[1])
        s["step"] = "enter_bio_text"
        await event.edit("✏️ أرسل نص البايو (يمكن استخدام إيموجي):")
        return

    if data == "new_video":
        s["step"] = "await_video"
        await event.edit("📹 أرسل فيديو جديد:")

# ========== PROCESS ==========
async def start_processing(event, s):
    await event.edit("🚀 جاري المعالجة...")
    output_folder = f"output_{event.sender_id}"

    await asyncio.get_event_loop().run_in_executor(
        None,
        process_video,
        s["file_path"],
        s["rights_list"],
        s["bio_text"],
        size_map(s["rights_size"]),
        30,  # حجم البايو ثابت لو تريد تغييره اجعل ديناميكي
        output_folder
    )

    for i, rc in enumerate(rights_channels):
        file_path = os.path.join(output_folder, f"copy_{i+1}.mp4")
        await bot.send_file(rc["channel"], file_path, caption=f"{rc['user']}")

    await event.edit(
        "✅ تم الإرسال لكل القنوات\nهل تريد فيديو جديد؟",
        buttons=[[Button.inline("➕ جديد", b"new_video")]]
    )

bot.run_until_disconnected()
