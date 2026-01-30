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
from instagrapi import Client

# --- الإعدادات الأساسية من ريلواي/رندر ---
TOKEN = os.getenv("BOT_TOKEN")
SECRET_PASSWORD = "20002000"
bot = telebot.TeleBot(TOKEN)

# --- البيانات الحية ---
active_tasks = {}  # { 'username': {'email': '...', 'count': 0, 'status': 'Running'} }
dashboard_msg_id = None
lock = threading.Lock()

# --- قوائم الصيغ (تم تحسينها لتجنب السبام) ---
SUBJECTS = [
    "Urgent: Account @user Deactivated by Mistake", 
    "Appeal for @user Suspension - Review Needed", 
    "My Instagram Profile @user is Disabled",
    "Reactivate my account @user - Case ID #{id}"
]
STARTS = ["Hello Support,", "Dear Meta Team,", "Greetings Review Board,"]
MIDDLES = [
    "my account @user (Email: {email}) was disabled. I believe this is a mistake as I follow all community guidelines.",
    "the profile @user linked to {email} was suspended without prior notice. Please review it manually."
]
ENDS = ["I need my account for my business. Please help.", "Best regards.", "Thank you for your assistance."]

# --- الدوال المساعدة ---
def get_senders():
    """جلب حسابات الجيميل من المتغيرات البيئية"""
    data = os.getenv("GMAIL_ACCOUNTS")
    try: return json.loads(data)
    except: return []

def check_insta_status(username):
    """فحص دقيق للحساب: هل عاد للعمل فعلياً؟"""
    cl = Client()
    # نضع وقت انتظار قصير للفحص
    cl.request_timeout = 5
    try:
        # إذا نجح في جلب الـ ID، يعني الحساب شغال
        user_id = cl.user_id_from_username(username)
        return True if user_id else False
    except:
        return False

def update_dashboard(chat_id):
    """تحديث لوحة التحكم المثبتة"""
    global dashboard_msg_id
    with lock:
        text = "🚀 *لوحة تحكم فك الحظر الذكية*\n"
        text += "━━━━━━━━━━━━━━━\n"
        if not active_tasks:
            text += "📭 لا توجد عمليات إرسال حالياً.\n"
        else:
            for user, data in active_tasks.items():
                icon = "🟢" if data['status'] == 'Running' else "✅"
                text += f"{icon} *@{user}*\n"
                text += f"   - طلبات الإرسال: {data['count']}\n"
                text += f"   - الحالة: {'جاري الطعن..' if data['status'] == 'Running' else 'تم الفك بنجاح!'}\n"
                text += "━━━━━━━━━━━━━━━\n"
        text += f"\n🔄 آخر تحديث: {time.strftime('%H:%M:%S')}"

        try:
            if dashboard_msg_id is None:
                msg = bot.send_message(chat_id, text, parse_mode="Markdown")
                dashboard_msg_id = msg.message_id
                bot.pin_chat_message(chat_id, dashboard_msg_id)
            else:
                bot.edit_message_text(text, chat_id, dashboard_msg_id, parse_mode="Markdown")
        except: pass

# --- محرك الإرسال (Spam Engine) ---
def spam_engine(chat_id, user, email):
    active_tasks[user] = {'email': email, 'count': 0, 'status': 'Running'}
    update_dashboard(chat_id)
    
    meta_emails = ["support@instagram.com", "disabled@instagram.com", "appeals@instagram.com"]

    while active_tasks.get(user) and active_tasks[user]['status'] == 'Running':
        # 1. الفحص الحقيقي قبل الإرسال
        if check_insta_status(user):
            active_tasks[user]['status'] = 'Done'
            update_dashboard(chat_id)
            bot.send_message(chat_id, f"🎉 مبروك! الحساب @{user} عاد للعمل وتم إيقاف الإرسال.")
            break

        # 2. جلب الحسابات
        senders = get_senders()
        if not senders:
            bot.send_message(chat_id, "⚠️ خطأ: لم يتم إضافة حسابات جيميل في ريلواي!")
            break

        # 3. دورة الإرسال المكثف
        for acc in senders:
            for target in meta_emails:
                if not active_tasks.get(user) or active_tasks[user]['status'] != 'Running': return
                
                try:
                    # توليد طعن فريد لكل رسالة لتجنب الفلترة
                    sub = random.choice(SUBJECTS).replace("@user", user).replace("{id}", str(random.randint(1000, 9999)))
                    body = f"{random.choice(STARTS)}\n\n{random.choice(MIDDLES).format(email=email).replace('@user', user)}\n\n{random.choice(ENDS)}"
                    
                    server = smtplib.SMTP('smtp.gmail.com', 587)
                    server.starttls()
                    server.login(acc['email'], acc['pass']) # كلمة سر التطبيقات
                    
                    msg = MIMEMultipart()
                    msg['From'], msg['To'], msg['Subject'] = acc['email'], target, sub
                    msg.attach(MIMEText(body, 'plain'))
                    
                    server.send_message(msg)
                    server.quit()
                    
                    active_tasks[user]['count'] += 1
                    update_dashboard(chat_id)
                    time.sleep(15) # فاصل أمان لتجنب حظر الجيميل
                except Exception as e:
                    print(f"Error sending from {acc['email']}: {e}")

        time.sleep(600) # انتظار 10 دقائق بين كل جولة إرسال كاملة

# --- أوامر البوت ---
@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message, "🔐 البوت محمي. أدخل الرمز السري للبدء:")

@bot.message_handler(func=lambda m: m.text == SECRET_PASSWORD)
def auth(message):
    bot.send_message(message.chat.id, "✅ تم التحقق. أرسل *يوزر* الحساب المتبند (بدون @):")
    bot.register_next_step_handler(message, get_user_data)

def get_user_data(message):
    user = message.text.strip()
    bot.send_message(message.chat.id, f"تم حفظ @{user}. الآن أرسل *الإيميل المربوط بالحساب* لإرسال الطعون باسمه:")
    bot.register_next_step_handler(message, lambda m: start_process(m, user))

def start_process(message, user):
    email = message.text.strip()
    threading.Thread(target=spam_engine, args=(message.chat.id, user, email), daemon=True).start()
    bot.send_message(message.chat.id, "🚀 بدأ الإرسال. تابع التحديثات في الرسالة المثبتة.")

@bot.message_handler(commands=['stop'])
def stop_all(message):
    global active_tasks, dashboard_msg_id
    active_tasks.clear()
    dashboard_msg_id = None
    bot.reply_to(message, "🛑 تم إيقاف جميع العمليات.")

bot.infinity_polling()
