import os
import requests
import telebot

from telebot import apihelper
from flask import Flask, request

# ========= TELEGRAM PROXY =========
apihelper.API_URL = "https://telegram-proxy-api.bulkabread2.workers.dev"

# ========= ENV =========
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = int(os.getenv("CHAT_ID"))

GITLAB_TOKEN = os.getenv("GITLAB_TOKEN")
PROJECT_ID = int(os.getenv("PROJECT_ID"))
RUNNER_ID = int(os.getenv("RUNNER_ID"))

CHECK_SECRET = os.getenv("CHECK_SECRET")

# =======================

bot = telebot.TeleBot(TELEGRAM_TOKEN)

app = Flask(__name__)

previous_status = None


# ========= GITLAB =========
def get_runner_status():

    url = f"https://gitlab.com/api/v4/projects/{PROJECT_ID}/runners"

    headers = {
        "PRIVATE-TOKEN": GITLAB_TOKEN
    }

    try:

        r = requests.get(url, headers=headers, timeout=10)

        if r.status_code != 200:
            print(f"GitLab API error: {r.status_code}")
            print(r.text)
            return None

        runners = r.json()

        for runner in runners:

            if runner["id"] == RUNNER_ID:
                return runner.get("status")

        print("Runner not found")
        return None

    except Exception as e:
        print(f"GitLab request failed: {e}")
        return None


# ========= TELEGRAM =========
def send_alert(status):

    if status == "online":
        text = "🟢 Backend runner ONLINE"

    elif status == "offline":
        text = "🔴 Backend runner OFFLINE"

    else:
        text = f"⚠️ Runner status changed: {status}"

    try:

        bot.send_message(CHAT_ID, text)

        print(f"Alert sent: {text}")

    except Exception as e:
        print(f"Telegram send error: {e}")


# ========= COMMANDS =========
@bot.message_handler(commands=['status'])
def status(message):

    print("STATUS COMMAND")

    if message.chat.id != CHAT_ID:
        print(f"Unauthorized chat: {message.chat.id}")
        return

    runner_status = get_runner_status()

    if runner_status == "online":
        reply = "🟢 Runner online"

    elif runner_status == "offline":
        reply = "🔴 Runner offline"

    else:
        reply = "⚠️ Could not get runner status"

    bot.reply_to(message, reply)


# ========= DEBUG =========
@bot.message_handler(func=lambda message: True)
def debug_all(message):

    print(f"MESSAGE RECEIVED: {message.text}")

    bot.reply_to(message, f"Echo: {message.text}")


# ========= FLASK =========
@app.route("/", methods=["GET"])
def home():
    return "Bot is running", 200


@app.route("/health", methods=["GET"])
def health():
    return "healthy", 200


@app.route("/webhook", methods=["POST"])
def webhook():
    try:
        print("Webhook received")
        json_str = request.get_data().decode("UTF-8")
        print(json_str)
        update = telebot.types.Update.de_json(json_str)

        # Ручная обработка команды /status
        if update.message and update.message.text and update.message.text.startswith('/status'):
            print("Manual handling of /status")
            runner_status = get_runner_status()
            if runner_status == "online":
                reply = "🟢 Runner online"
            elif runner_status == "offline":
                reply = "🔴 Runner offline"
            else:
                reply = "⚠️ Could not get runner status"
            # Отправляем ответ через API (через прокси)
            send_url = f"https://telegram-proxy-api.bulkabread2.workers.dev/bot{TELEGRAM_TOKEN}/sendMessage"
            payload = {
                "chat_id": update.message.chat.id,
                "text": reply,
                "reply_to_message_id": update.message.message_id
            }
            try:
                r = requests.post(send_url, json=payload, timeout=10)
                print(f"Manual send response: {r.status_code} - {r.text}")
            except Exception as e:
                print(f"Manual send error: {e}")
            return "OK", 200

        # Если не /status, передаём в обычные обработчики (на всякий случай)
        bot.process_new_updates([update])
        return "OK", 200
    except Exception as e:
        print(f"Webhook error: {e}")
        return "ERROR", 500


# ========= RUNNER CHECK =========
def check_runner():

    global previous_status

    current_status = get_runner_status()

    if current_status is None:
        return

    if previous_status is None:

        previous_status = current_status

        print(f"Initial status: {current_status}")

        return

    if current_status != previous_status:

        print(f"Status changed: {previous_status} -> {current_status}")

        send_alert(current_status)

        previous_status = current_status


@app.route("/check", methods=["GET"])
def check():

    secret = request.args.get("secret")

    if secret != CHECK_SECRET:
        return "Forbidden", 403

    check_runner()

    return "Checked", 200


# ========= MAIN =========
if __name__ == "__main__":

    port = int(os.getenv("PORT", 10000))

    app.run(host="0.0.0.0", port=port)
