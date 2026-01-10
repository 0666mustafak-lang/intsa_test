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

def load_authorized():
    if os.path.exists(AUTH_FILE):
        with open(AUTH_FILE, "r") as f:
            return set(map(int, f.read().splitlines()))
    return set()

def save_authorized(uid):
    with open(AUTH_FILE, "a") as f:
        f.write(f"{uid}\n")

AUTHORIZED_USERS = load_authorized()

bot = TelegramClient("bot", API_ID, API_HASH).start(bot_token=BOT_TOKEN)
state = {}

# ====== يوزر ↔ قناة (ثابت) ======
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
        (255,0,0),(0,255,0),(0,0,255),(255,255,0),(255,0,255),
        (0,255,255),(255,128,0),(128,0,255),(0,128,255),(128,128,128)
    ]
    return colors[idx % len(colors)]

def process_video(file_path, rights_list, bio_text, rights_size, bio_size, output_folder):
    clip = VideoFileClip(file_path)
    width, height = clip.size

    for i in range(len(rights_list)):
        r_text = rights_list[i]
        r_color = get_color(i)

        txt_clip = TextClip(r_text, fontsize=rights_size, color=r_color)
        txt_clip = txt_clip.set_pos(
            lambda t: ((t*100) % (width+txt_clip.w) - txt_clip.w, 50)
        ).set_duration(clip.duration)

        bio_clip = TextClip(
            bio_text, fontsize=bio_size, color=r_color, bg_color="black"
        )
        bio_clip = bio_clip.set_pos(
            ("center", height - bio_clip.h - 50)
        ).set_duration(clip.duration)

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
            await event.respond("❌ رمز خطأ")
            return
        AUTHORIZED_USERS.add(uid)
        save_authorized(uid)
        state[uid] = {"step":"await_video"}
        await event.respond("✅ تم التحقق\n📹 أرسل الفيديو:")
        return

    if s.get("step") == "await_video" and event.media:
        s["file_path"] = await event.download_media()
        s["rights_list"] = [rc["user"] for rc in rights_channels]
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

    if data == "bio_default":
        s["bio_text"] = "البايو حصريات 😼🇸🇦"
        await start_processing(event, s)
        return

    if data == "bio_manual":
        s["step"] = "enter_bio_text"
        await event.edit("✏️ أرسل نص البايو:")
        return

    if data.startswith("bio_"):
        s["bio_size"] = int(data.split("_")[1])
        s["step"] = "choose_bio_text"
        await event.edit(
            "✏️ اختر نص البايو:",
            buttons=[
                [Button.inline("✅ افتراضي", b"bio_default"),
                 Button.inline("✍️ يدوي", b"bio_manual")]
            ]
        )
        return

    if data == "new_video":
        state[uid] = {"step":"await_video"}
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
        size_map(s["bio_size"]),
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
