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
    import json
    import traceback

    print("\n========== /STATUS COMMAND ==========")
    print("CHAT ID:", message.chat.id)
    print("THREAD ID:", getattr(message, "message_thread_id", None))
    print("FROM USER:", message.from_user.username if message.from_user else None)

    try:
        runners = get_all_runners()

        print("RAW RUNNERS RESPONSE:")
        print(json.dumps(runners, indent=2, ensure_ascii=False))

        if not runners:
            print("ERROR: runners is empty or None")

            send_message(
                message.chat.id,
                "⚠️ Не удалось получить список раннеров"
            )
            return

        # ========= FORMAT MESSAGE =========
        lines = []
        lines.append("📊 <b>GitLab Runners Status</b>\n")

        for r in runners:
            name = r.get("description", "Unknown")
            rid = r.get("id", "N/A")
            status_val = r.get("status", "unknown")
            busy = r.get("busy", False)
            version = r.get("version", "n/a")

            emoji_map = {
                "online": "🟢",
                "offline": "🔴",
                "stale": "🟡",
                "never_contacted": "⚪"
            }

            emoji = emoji_map.get(status_val, "⚠️")

            line = (
                f"{emoji} <b>{name}</b>\n"
                f"   ├ ID: <code>{rid}</code>\n"
                f"   ├ Status: <code>{status_val}</code>\n"
                f"   ├ Busy: <code>{busy}</code>\n"
                f"   └ Version: <code>{version}</code>\n"
            )

            lines.append(line)

        text = "\n".join(lines)

        print("\nFORMATTED MESSAGE:\n", text)

        # ========= SAFE SEND =========
        chat_id = message.chat.id

        try:
            thread_id = getattr(message, "message_thread_id", None)
        except Exception:
            thread_id = None

        print("\nSENDING TO TELEGRAM...")
        print("CHAT:", chat_id)
        print("THREAD:", thread_id)

        payload = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": True
        }

        # forum threads ONLY if exists
        if thread_id:
            payload["message_thread_id"] = thread_id

        url = f"https://telegram-proxy-api.bulkabread2.workers.dev/bot{TELEGRAM_TOKEN}/sendMessage"

        print("REQUEST URL:", url)
        print("PAYLOAD:", json.dumps(payload, ensure_ascii=False))

        r = requests.post(url, json=payload, timeout=10)

        print("\nTELEGRAM RESPONSE STATUS:", r.status_code)
        print("TELEGRAM RESPONSE TEXT:", r.text)

        if r.status_code != 200:
            print("❌ TELEGRAM API ERROR")
        else:
            print("✅ MESSAGE SENT SUCCESSFULLY")

    except Exception:
        print("🔥 EXCEPTION IN /STATUS:")
        print(traceback.format_exc())

        try:
            send_message(
                message.chat.id,
                "❌ Ошибка при получении статуса runner'ов"
            )
        except Exception as e:
            print("FAILED TO SEND ERROR MESSAGE:", e)

    print("========== END /STATUS ==========\n")


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
