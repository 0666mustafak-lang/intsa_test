import asyncio
import os
from telethon import TelegramClient, events, Button
from telethon.sessions import StringSession
from moviepy.editor import VideoFileClip, vfx, TextClip, CompositeVideoClip

# ========== CONFIG ==========
API_ID = int(os.environ["API_ID"])
API_HASH = os.environ["API_HASH"]
BOT_TOKEN = os.environ["BOT_TOKEN"]
ACCESS_CODE = "20002000"

bot = TelegramClient("bot", API_ID, API_HASH).start(bot_token=BOT_TOKEN)
state = {}

# ====== الحقوق + القنوات لكل نسخة ======
# كل نسخة لها يوزر + قناة محددة
rights_channels = [
    {"user":"m3wr", "channel":"nsenejwkdidokskej"},
    {"user":"user2", "channel":"@channel2"},
    {"user":"user3", "channel":"@channel3"},
    {"user":"user4", "channel":"@channel4"},
    {"user":"user5", "channel":"@channel5"},
    {"user":"user6", "channel":"@channel6"},
    {"user":"user7", "channel":"@channel7"},
    {"user":"user8", "channel":"@channel8"},
    {"user":"user9", "channel":"@channel9"},
    {"user":"user10", "channel":"@channel10"},
]

# ====== HELPERS ======
def size_map(val):
    mapping = {1:20, 2:30, 3:40, 4:50, 5:60}
    return mapping.get(val, 30)

def get_color(idx):
    colors = [(255,0,0),(0,255,0),(0,0,255),(255,255,0),(255,0,255),
              (0,255,255),(255,128,0),(128,0,255),(0,128,255),(128,128,128)]
    return colors[idx % len(colors)]

def process_video(file_path, rights_list, bio_text, rights_size, bio_size, output_folder):
    clip = VideoFileClip(file_path)
    width, height = clip.size

    for i in range(len(rights_list)):
        r_text = rights_list[i % len(rights_list)]
        r_color = get_color(i)
        r_size = rights_size
        b_size = bio_size

        # الحقوق المتحركة أعلى الفيديو
        txt_clip = TextClip(r_text, fontsize=r_size, color=r_color)
        txt_clip = txt_clip.set_pos(lambda t: ((t*100) % (width+txt_clip.w) - txt_clip.w, 50)).set_duration(clip.duration)

        # نص أسفل الفيديو
        bio_clip = TextClip(bio_text, fontsize=b_size, color=r_color, bg_color='black')
        bio_clip = bio_clip.set_pos(("center", height - bio_clip.h - 50)).set_duration(clip.duration)

        final = CompositeVideoClip([clip, txt_clip, bio_clip])
        final = final.fx(vfx.colorx, 1 + i*0.02)  # فلتر مختلف لكل نسخة

        os.makedirs(output_folder, exist_ok=True)
        out_path = os.path.join(output_folder, f"copy_{i+1}.mp4")
        final.write_videofile(out_path, codec='libx264', audio_codec='aac', threads=2)

    return output_folder

# ========== START ==========
@bot.on(events.NewMessage(pattern="/start"))
async def start(event):
    uid = event.sender_id
    state[uid] = {"step":"auth"}
    await event.respond("🔐 اهلا وسهلا في بوتي المتواضع 🥺\nأرسل رمز الدخول للوصول للبوت:")

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
            await event.respond("❌ رمز الدخول خاطئ!")
            return
        s["step"] = "await_video"
        await event.respond("✅ تم التحقق! أرسل الفيديو الآن:")

    elif s.get("step") == "await_video" and event.media:
        file_path = await event.download_media()
        s["file_path"] = file_path
        s["step"] = "enter_rights"
        s["rights_list"] = []
        await event.respond("✏️ أرسل اليوزرات واحدة تلو الأخرى. ارسل ✅ عند الانتهاء (حتى 10):")

    elif s.get("step") == "enter_bio_text":
        s["bio_text"] = txt
        s["step"] = "processing"
        await start_processing(event, s)

# ===== إدخال الحقوق =====
@bot.on(events.NewMessage)
async def enter_rights(event):
    uid = event.sender_id
    if uid not in state:
        return
    s = state[uid]
    if s.get("step") != "enter_rights":
        return
    txt = (event.text or "").strip()
    if txt == "✅":
        if not s["rights_list"]:
            await event.respond("⚠️ يجب إضافة حق واحد على الأقل!")
            return
        s["step"] = "choose_rights_size"
        await event.respond(
            "📏 اختر حجم الحقوق (اليوزر) أعلى الفيديو:",
            buttons=[
                [Button.inline("1️⃣", b"rights_1"), Button.inline("2️⃣", b"rights_2"), Button.inline("3️⃣", b"rights_3")],
                [Button.inline("4️⃣", b"rights_4"), Button.inline("5️⃣", b"rights_5")]
            ]
        )
        return
    if len(s["rights_list"]) >= 10:
        await event.respond("⚠️ تم الوصول لحد 10 يوزرات فقط")
        return
    s["rights_list"].append(txt)
    await event.respond(f"✅ تمت الإضافة: {txt}\nأرسل حق آخر أو ✅ عند الانتهاء")

# ===== CALLBACKS =====
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
            "📏 اختر حجم النص أسفل الفيديو (البايو):",
            buttons=[
                [Button.inline("1️⃣", b"bio_1"), Button.inline("2️⃣", b"bio_2"), Button.inline("3️⃣", b"bio_3")],
                [Button.inline("4️⃣", b"bio_4"), Button.inline("5️⃣", b"bio_5")]
            ]
        )
        return

    if data.startswith("bio_"):
        s["bio_size"] = int(data.split("_")[1])
        s["step"] = "choose_bio_text"
        await event.edit(
            "✏️ اختر النص أسفل الفيديو:",
            buttons=[
                [Button.inline("✅ افتراضي", b"bio_default"), Button.inline("✍️ يدوي", b"bio_manual")]
            ]
        )
        return

    if data == "bio_default":
        s["bio_text"] = "البايو حصريات 😼🇸🇦"
        await start_processing(event, s)
        return

    if data == "bio_manual":
        s["step"] = "enter_bio_text"
        await event.edit("🖊️ أرسل النص الذي تريد إضافته أسفل الفيديو:")
        return

    if data == "new_video":
        s["step"] = "await_video"
        await event.edit("📹 أرسل الفيديو الجديد:")

# ===== معالجة الفيديو + إرسال النسخ للقنوات =====
async def start_processing(event, s):
    await event.edit("🚀 جاري معالجة الفيديو وإنشاء النسخ...")
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

    # إرسال كل نسخة للقناة المحددة لها
    for i, rc in enumerate(rights_channels):
        file_path = os.path.join(output_folder, f"copy_{i+1}.mp4")
        await bot.send_file(rc["channel"], file_path, caption=f"نسخة {i+1} | {rc['user']}")

    await event.edit("✅ تم إنشاء وإرسال النسخ العشر للفيديو!\nهل تريد إضافة مقطع جديد؟",
                     buttons=[[Button.inline("➕ جديد", b"new_video")]])

bot.run_until_disconnected()