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

CHECK_SECRET = os.getenv("CHECK_SECRET")

# =======================

bot = telebot.TeleBot(TELEGRAM_TOKEN)

app = Flask(__name__)

previous_statuses = {}


# ========= GITLAB =========
# def get_runner_status():

#     url = f"https://gitlab.com/api/v4/projects/{PROJECT_ID}/runners"

#     headers = {
#         "PRIVATE-TOKEN": GITLAB_TOKEN
#     }

#     try:

#         r = requests.get(url, headers=headers, timeout=10)

#         if r.status_code != 200:
#             print(f"GitLab API error: {r.status_code}")
#             print(r.text)
#             return None

#         runners = r.json()

#         for runner in runners:

#             if runner["id"] == RUNNER_ID:
#                 return runner.get("status")

#         print("Runner not found")
#         return None

#     except Exception as e:
#         print(f"GitLab request failed: {e}")
#         return None


def get_all_runners():

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

        return r.json()

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

def send_message(chat_id, text, thread_id=None):

    payload = {
        "chat_id": chat_id,
        "text": text
    }

    if thread_id:
        payload["message_thread_id"] = thread_id

    try:

        url = (
            "https://telegram-proxy-api.bulkabread2.workers.dev"
            f"/bot{TELEGRAM_TOKEN}/sendMessage"
        )

        r = requests.post(
            url,
            json=payload,
            timeout=10
        )

        print(f"Telegram response: {r.text}")

    except Exception as e:

        print(f"Telegram send error: {e}")

@bot.message_handler(commands=['status'])
def status(message):

    runners = get_all_runners()

    if not runners:

        send_message(
            message.chat.id,
            "⚠️ Не удалось получить список раннеров",
            message.message_thread_id
        )

        return

    text = "📊 Статус раннеров\n\n"

    for runner in runners:

        runner_name = runner.get("description", "Unknown")
        runner_id = runner.get("id")
        runner_status = runner.get("status")

        emoji = {
            "online": "🟢",
            "offline": "🔴",
            "stale": "🟡",
            "never_contacted": "⚪"
        }.get(runner_status, "⚠️")

        text += (
            f"{emoji} {runner_name} "
            f"(ID: {runner_id})\n"
        )

    send_message(
        message.chat.id,
        text,
        message.message_thread_id
    )


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
        json_str = request.get_data().decode("UTF-8")
        print("RAW UPDATE:", json_str)

        update = telebot.types.Update.de_json(json_str)

        print("PROCESSING UPDATE")
        bot.process_new_updates([update])

        print("DONE PROCESSING")

        return "OK", 200

    except Exception as e:
        import traceback
        print("WEBHOOK ERROR:", traceback.format_exc())
        return "ERROR", 500


# ========= MAIN =========
if __name__ == "__main__":

    port = int(os.getenv("PORT", 10000))

    app.run(host="0.0.0.0", port=port)
