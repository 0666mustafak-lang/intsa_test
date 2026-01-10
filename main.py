import asyncio
import os
from telethon import TelegramClient, events, Button
from telethon.sessions import StringSession
from moviepy.editor import VideoFileClip, vfx, TextClip, CompositeVideoClip

# ===== CONFIG =====
API_ID = int(os.environ["API_ID"])
API_HASH = os.environ["API_HASH"]
BOT_TOKEN = os.environ["BOT_TOKEN"]
ACCESS_CODE = "20002000"

bot = TelegramClient("bot", API_ID, API_HASH).start(bot_token=BOT_TOKEN)
state = {}

# ===== القنوات واليوزرات =====
rights_channels = [
    {"user":"mxhasd", "channel":"https://t.me/+DaXIWRnl-PAzMWE5"},
    {"user":"m3_wt4_", "channel":"https://t.me/+WV_zEH1or1plYmUy"},
    {"user":"271f_", "channel":"https://t.me/+Hs6PyBFPc7kzNzI5"},
    {"user":"m3_wt33", "channel":"https://t.me/+IOdlFnTe275lZWNi"},
    {"user":"m3_wt2", "channel":"https://t.me/+qqC1xo6x44ZmMWZi"},
    {"user":"m3_wt55", "channel":"https://t.me/+cUDaK0ag8lI3OTYy"},
    {"user":"m3_wt6", "channel":"https://t.me/+tZN6h2m2cUs2MjIx"},
]

# ===== HELPERS =====
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
        final = final.fx(vfx.colorx, 1 + i*0.02)

        os.makedirs(output_folder, exist_ok=True)
        out_path = os.path.join(output_folder, f"copy_{i+1}.mp4")
        final.write_videofile(out_path, codec='libx264', audio_codec='aac', threads=2)

    return output_folder

# ===== START =====
@bot.on(events.NewMessage(pattern="/start"))
async def start(event):
    uid = event.sender_id
    state[uid] = {"step":"auth"}
    await event.respond("🔐 اهلا! أرسل رمز الدخول للوصول للبوت:")

# ===== FLOW =====
@bot.on(events.NewMessage)
async def flow(event):
    uid = event.sender_id
    txt = (event.text or "").strip()
    if uid not in state:
        return
    s = state[uid]

    # التحقق من رمز الدخول
    if s.get("step") == "auth":
        if txt != ACCESS_CODE:
            await event.respond("❌ رمز خاطئ")
            return
        s["step"] = "await_video"
        await event.respond("✅ تم التحقق\n📹 أرسل الفيديو:")

    # استلام الفيديو
    elif s.get("step") == "await_video" and event.media:
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

    # إدخال نص البايو
    elif s.get("step") == "enter_bio_text":
        if txt:
            s["bio_text"] = txt  # حفظ النص فوراً لكل النسخ
            await start_processing(event, s)
        else:
            await event.respond("⚠️ يرجى كتابة نص صحيح للبـايو")

# ===== CALLBACK =====
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
        s["step"] = "enter_bio_text"
        await event.edit("✏️ أرسل نص البايو الذي تريد إضافته أسفل كل النسخ (يمكن استخدام إيموجي):")

# ===== معالجة الفيديو =====
async def start_processing(event, s):
    # استخدم رسالة جديدة للتقدم لتجنب MessageIdInvalidError
    status_msg = await event.respond("🚀 جاري المعالجة...")
    s["status"] = status_msg
    output_folder = f"output_{event.sender_id}"
    await asyncio.get_event_loop().run_in_executor(
        None,
        process_video,
        s["file_path"],
        s["rights_list"],
        s["bio_text"],
        size_map(s["rights_size"]),
        30,  # حجم البايو ثابت افتراضياً يمكن تغييره
        output_folder
    )

    # إرسال النسخ للقنوات
    for i, rc in enumerate(rights_channels):
        file_path = os.path.join(output_folder, f"copy_{i+1}.mp4")
        await bot.send_file(rc["channel"], file_path, caption=f"نسخة {i+1} | {rc['user']}")

    await status_msg.edit("✅ تم إنشاء وإرسال النسخ بنجاح!\n📹 أرسل فيديو جديد إذا أردت:")
    s["step"] = "await_video"  # إعادة الخطوة للفيديو جديد

bot.run_until_disconnected()
