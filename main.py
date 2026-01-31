import os
import json
import time
import random
import threading
import telebot
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# --- الإعدادات الأساسية ---
# تأكد من إضافة BOT_TOKEN في متغيرات Railway
TOKEN = os.getenv("BOT_TOKEN")
SECRET_PASSWORD = "20002000"
bot = telebot.TeleBot(TOKEN)

# --- البيانات الحية ---
active_tasks = {}  # تخزين المهام النشطة
dashboard_msg_id = None
lock = threading.Lock()

# --- قوائم البيانات (صيغ احترافية) ---
SUBJECTS = [
    "Urgent Appeal: Account @user Deactivated", 
    "Request for Review: @user Suspension", 
    "Instagram Support: Account @user Case",
    "Mistake in @user Deactivation - Review Needed"
]
STARTS = ["Hello Support Team,", "To the Meta Review Board,", "Dear Instagram Support,"]
MIDDLES = [
    "My account @user linked to {email} was disabled by mistake. I follow all guidelines.",
    "I believe my profile @user (Email: {email}) was suspended in error. Please help me restore it."
]
ENDS = ["Please reactivate my access. Thank you.", "Best regards.", "I look forward to your help."]

# --- الدوال المساعدة ---
def get_senders():
    """جلب حسابات Gmail من المتغيرات"""
    data = os.getenv("GMAIL_ACCOUNTS")
    try:
        return json.loads(data)
    except:
        return []

def update_dashboard(chat_id):
    """تحديث لوحة التحكم في تليجرام"""
    global dashboard_msg_id
    with lock:
        text = "🚀 *بدأ الإرسال المستمر للطعون*\n"
        text += "━━━━━━━━━━━━━━━\n"
        if not active_tasks:
            text += "📭 لا توجد مهام شغالة حالياً.\n"
        else:
            for user, data in active_tasks.items():
                text += f"🔥 *الحساب: @{user}*\n"
                text += f"📩 تم إرسال: {data['count']} طعن بنجاح\n"
                text += "━━━━━━━━━━━━━━━\n"
        text += f"\n⚠️ سيستمر الإرسال حتى تفتح الحساب وترسل /stop\n"
        text += f"🔄 آخر تحديث: {time.strftime('%H:%M:%S')}"

        try:
            if dashboard_msg_id is None:
                msg = bot.send_message(chat_id, text, parse_mode="Markdown")
                dashboard_msg_id = msg.message_id
                bot.pin_chat_message(chat_id, dashboard_msg_id)
            else:
                bot.edit_message_text(text, chat_id, dashboard_msg_id, parse_mode="Markdown")
        except:
            pass

# --- محرك الإرسال (حل مشكلة الشبكة) ---
def spam_engine(chat_id, user, email):
    active_tasks[user] = {'count': 0}
    update_dashboard(chat_id)
    
    meta_emails = ["support@instagram.com", "disabled@instagram.com", "appeals@instagram.com"]

    while active_tasks.get(user):
        senders = get_senders()
        if not senders:
            break

        for acc in senders:
            for target in meta_emails:
                if not active_tasks.get(user):
                    return
                
                try:
                    # تعديل جوهري: استخدام المنفذ 465 و SSL لتخطي حظر Railway
                    server = smtplib.SMTP_SSL('smtp.gmail.com', 465, timeout=15)
                    server.login(acc['email'], acc['pass'])
                    
                    sub = random.choice(SUBJECTS).replace("@user", user)
                    body = f"{random.choice(STARTS)}\n\n{random.choice(MIDDLES).format(email=email).replace('@user', user)}\n\n{random.choice(ENDS)}"
                    
                    msg = MIMEMultipart()
                    msg['From'], msg['To'], msg['Subject'] = acc['email'], target, sub
                    msg.attach(MIMEText(body, 'plain'))
                    
                    server.send_message(msg)
                    server.quit()
                    
                    active_tasks[user]['count'] += 1
                    update_dashboard(chat_id)
                    time.sleep(12)  # فاصل زمني لتجنب حظر الإيميل
                except Exception as e:
                    print(f"SMTP Error for {acc['email']}: {e}")

        time.sleep(300)  # انتظار 5 دقائق بين كل دورة إرسال كاملة

# --- أوامر البوت ---
@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message, "🔐 البوت محمي، أرسل الرمز السري:")

@bot.message_handler(func=lambda m: m.text == SECRET_PASSWORD)
def auth(message):
    bot.send_message(message.chat.id, "✅ تم الدخول. أرسل *يوزر* الحساب المتبند:")
    bot.register_next_step_handler(message, get_user)

def get_user(message):
    user = message.text.strip().replace("@", "")
    bot.send_message(message.chat.id, f"حسناً @{user}. الآن أرسل *الإيميل المربوط* بالحساب:")
    bot.register_next_step_handler(message, lambda m: start_task(m, user))

def start_task(message, user):
    email = message.text.strip()
    threading.Thread(target=spam_engine, args=(message.chat.id, user, email), daemon=True).start()
    bot.send_message(message.chat.id, "🚀 بدأ الإرسال المكثف. راقب بريدك المرسل وحسابك يدوياً.")

@bot.message_handler(commands=['stop'])
def stop_all(message):
    global active_tasks, dashboard_msg_id
    active_tasks.clear()
    dashboard_msg_id = None
    bot.reply_to(message, "🛑 تم إيقاف الإرسال تماماً.")

bot.infinity_polling()
