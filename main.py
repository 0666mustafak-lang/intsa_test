import os
import json
import time
import random
import threading
import telebot
import smtplib
import requests
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# --- الإعدادات الأساسية ---
TOKEN = os.getenv("BOT_TOKEN")
SECRET_PASSWORD = "20002000"
bot = telebot.TeleBot(TOKEN)

# --- البيانات الحية ---
active_tasks = {}  # { 'username': {'email': '...', 'count': 0, 'status': 'Running'} }
authenticated_users = set()
dashboard_msg_id = None
lock = threading.Lock()

# --- قوائم البيانات (50 عنوان و 50 صيغة مدمجة) ---
SUBJECTS_50 = [
    "Urgent: Account @user Deactivated", "Appeal for @user Suspension", "Review Request: @user",
    "Mistake in @user Deactivation", "Access Issue - @user", "My Profile @user is Disabled",
    "Instagram Support: @user Help", "Official Appeal for @user", "Login Problem @user",
    "Reactivate my account @user", "Case ID: @user Appeal", "Profile @user Review Needed"
    # الكود سيختار عشوائياً ويضيف أرقام تذكرة لزيادة التنوع
]

STARTS = ["Hello Support Team,", "Dear Meta Team,", "Greetings,", "To the Review Board,"]
MIDDLES = ["my account @user (Email: {email}) was disabled by mistake.", "I believe my profile @user linked to {email} was suspended in error."]
ENDS = ["I follow all rules. Please help.", "Please restore my access.", "Best regards."]

# --- الدوال المساعدة ---
def get_senders():
    data = os.getenv("GMAIL_ACCOUNTS")
    try: return json.loads(data)
    except: return []

def check_insta_status(username):
    url = f"https://www.instagram.com/{username}/"
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        r = requests.get(url, headers=headers, timeout=5)
        return True if r.status_code == 200 else False
    except: return False

def update_dashboard(chat_id):
    global dashboard_msg_id
    with lock:
        text = "🚀 *لوحة تحكم البوت الاحترافية*\n"
        text += "━━━━━━━━━━━━━━━\n"
        if not active_tasks:
            text += "📭 لا توجد مهام شغالة حالياً.\n"
        else:
            for user, data in active_tasks.items():
                icon = "🟢" if data['status'] == 'Running' else "🎉"
                text += f"{icon} *@{user}*\n"
                text += f"   - الإرسال: {data['count']} طلب\n"
                text += f"   - الحالة: {'جاري العمل..' if data['status'] == 'Running' else 'تم الفك!'}\n"
                text += "━━━━━━━━━━━━━━━\n"
        text += f"\nآخر تحديث: {time.strftime('%H:%M:%S')}"

        try:
            if dashboard_msg_id is None:
                msg = bot.send_message(chat_id, text, parse_mode="Markdown")
                dashboard_msg_id = msg.message_id
                bot.pin_chat_message(chat_id, dashboard_msg_id)
            else:
                bot.edit_message_text(text, chat_id, dashboard_msg_id, parse_mode="Markdown")
        except: pass

# --- محرك الإرسال ---
def spam_engine(chat_id, user, email):
    active_tasks[user] = {'email': email, 'count': 0, 'status': 'Running'}
    update_dashboard(chat_id)
    
    meta_emails = ["support@instagram.com", "disabled@instagram.com", "appeals@instagram.com", "case@support.facebook.com"]

    while active_tasks.get(user) and active_tasks[user]['status'] == 'Running':
        # 1. فحص هل تم الفك؟
        if check_insta_status(user):
            active_tasks[user]['status'] = 'Done'
            update_dashboard(chat_id)
            bot.send_message(chat_id, f"🎊 مبروك! الحساب @{user} اشتغل.")
            break

        # 2. جلب حسابات الجيميل من ريلواي
        senders = get_senders()
        if not senders: break

        # 3. دورة الإرسال
        for acc in senders:
            for target in meta_emails:
                if not active_tasks.get(user) or active_tasks[user]['status'] != 'Running': return
                
                try:
                    # توليد المحتوى
                    sub = random.choice(SUBJECTS_50).replace("@user", user) + f" #{random.randint(100,999)}"
                    body = f"{random.choice(STARTS)}\n\n{random.choice(MIDDLES).format(email=email).replace('@user', user)}\n\n{random.choice(ENDS)}"
                    
                    server = smtplib.SMTP('smtp.gmail.com', 587)
                    server.starttls()
                    server.login(acc['email'], acc['pass'])
                    
                    msg = MIMEMultipart()
                    msg['From'], msg['To'], msg['Subject'] = acc['email'], target, sub
                    msg.attach(MIMEText(body, 'plain'))
                    
                    server.send_message(msg)
                    server.quit()
                    
                    active_tasks[user]['count'] += 1
                    update_dashboard(chat_id)
                except: pass
                time.sleep(12) # فاصل بين الرسائل

        time.sleep(1800) # انتظار 30 دقيقة للدورة التالية

# --- أوامر البوت ---
@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message, "🔐 البوت محمي، أرسل الرمز السري:")

@bot.message_handler(func=lambda m: m.text == SECRET_PASSWORD)
def auth(message):
    authenticated_users.add(message.chat.id)
    bot.send_message(message.chat.id, "✅ تم الدخول. أرسل *اليوزر* فقط:")
    bot.register_next_step_handler(message, get_user)

def get_user(message):
    user = message.text.strip().replace("@", "")
    bot.send_message(message.chat.id, f"تم حفظ @{user}. الآن أرسل *الإيميل الأساسي*:")
    bot.register_next_step_handler(message, lambda m: start_task(m, user))

def start_task(message, user):
    email = message.text.strip()
    threading.Thread(target=spam_engine, args=(message.chat.id, user, email), daemon=True).start()
    bot.send_message(message.chat.id, "🚀 تمت الإضافة للوحة التحكم المثبتة.")

@bot.message_handler(commands=['stop'])
def stop_all(message):
    global active_tasks, dashboard_msg_id
    active_tasks.clear()
    dashboard_msg_id = None
    bot.reply_to(message, "🛑 تم إيقاف جميع العمليات وتصفير اللوحة.")

bot.infinity_polling()
