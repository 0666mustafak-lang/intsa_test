import os
import json
import time
import random
import threading
import telebot
import smtplib
import socket  # إضافة للتحقق من الشبكة
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# --- الإعدادات ---
TOKEN = os.getenv("BOT_TOKEN")
SECRET_PASSWORD = "20002000"
bot = telebot.TeleBot(TOKEN)

active_tasks = {} 
dashboard_msg_id = None
lock = threading.Lock()

# --- البيانات ---
SUBJECTS = ["Appeal for @user", "Support Case: @user", "Urgent: @user Deactivated"]
MIDDLES = ["My account @user (Email: {email}) was disabled incorrectly.", "I request a review for @user linked to {email}."]

def get_senders():
    try: return json.loads(os.getenv("GMAIL_ACCOUNTS"))
    except: return []

def update_dashboard(chat_id):
    global dashboard_msg_id
    with lock:
        text = "🚀 *حالة الإرسال الحالية*\n"
        text += "━━━━━━━━━━━━━━━\n"
        if not active_tasks:
            text += "📭 لا توجد مهام نشطة.\n"
        else:
            for user, data in active_tasks.items():
                text += f"🔥 *@{user}*\n📩 تم بنجاح: {data['count']}\n"
        text += f"\n🔄 {time.strftime('%H:%M:%S')}"
        try:
            if dashboard_msg_id is None:
                msg = bot.send_message(chat_id, text, parse_mode="Markdown")
                dashboard_msg_id = msg.message_id
            else:
                bot.edit_message_text(text, chat_id, dashboard_msg_id, parse_mode="Markdown")
        except: pass

def spam_engine(chat_id, user, email):
    active_tasks[user] = {'count': 0}
    update_dashboard(chat_id)
    targets = ["support@instagram.com", "disabled@instagram.com"]

    while active_tasks.get(user):
        senders = get_senders()
        for acc in senders:
            for target in targets:
                if not active_tasks.get(user): return
                try:
                    # محاولة الاتصال بالمنفذ 465 مع مهلة زمنية أطول
                    server = smtplib.SMTP_SSL('smtp.gmail.com', 465, timeout=20)
                    server.login(acc['email'], acc['pass'])
                    
                    sub = random.choice(SUBJECTS).replace("@user", user)
                    body = f"Hello,\n{random.choice(MIDDLES).format(email=email).replace('@user', user)}\nRegards."
                    
                    msg = MIMEMultipart()
                    msg['From'], msg['To'], msg['Subject'] = acc['email'], target, sub
                    msg.attach(MIMEText(body, 'plain'))
                    
                    server.send_message(msg)
                    server.quit()
                    
                    active_tasks[user]['count'] += 1
                    update_dashboard(chat_id)
                    time.sleep(15) 
                except socket.error as e:
                    print(f"Network error (101): {e} - Retrying in 30s...")
                    time.sleep(30) # الانتظار عند حدوث خطأ شبكة
                except Exception as e:
                    print(f"General Error: {e}")
        time.sleep(120)

@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message, "🔐 أدخل الرمز السري:")

@bot.message_handler(func=lambda m: m.text == SECRET_PASSWORD)
def auth(message):
    bot.send_message(message.chat.id, "✅ أرسل يوزر الحساب:")
    bot.register_next_step_handler(message, get_user)

def get_user(message):
    user = message.text.strip().replace("@", "")
    bot.send_message(message.chat.id, "✅ أرسل الإيميل المربوط:")
    bot.register_next_step_handler(message, lambda m: start_t(m, user))

def start_t(message, user):
    email = message.text.strip()
    threading.Thread(target=spam_engine, args=(message.chat.id, user, email), daemon=True).start()
    bot.send_message(message.chat.id, "🚀 بدأ الإرسال. تأكد من خانة الـ Sent في بريدك.")

@bot.message_handler(commands=['stop'])
def stop(message):
    active_tasks.clear()
    bot.reply_to(message, "🛑 توقف الإرسال.")

bot.infinity_polling()
