import os
import json
import requests
import traceback
from flask import Flask, request

# ========= ENV =========
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
PROJECT_ID = int(os.getenv("PROJECT_ID"))
GITLAB_TOKEN = os.getenv("GITLAB_TOKEN")

# ========= TELEGRAM PROXY =========
TELEGRAM_API = "https://telegram-proxy-api.bulkabread2.workers.dev"

app = Flask(__name__)


# =========================
# TELEGRAM SENDER (ONLY ONE)
# =========================
def send_raw(chat_id, text):
    try:
        url = f"{TELEGRAM_API}/bot{TELEGRAM_TOKEN}/sendMessage"

        payload = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": True
        }

        print("\n========== TELEGRAM SEND ==========")
        print("URL:", url)
        print("PAYLOAD:", json.dumps(payload, ensure_ascii=False))

        r = requests.post(url, json=payload, timeout=10)

        print("STATUS:", r.status_code)
        print("RESPONSE:", r.text)
        print("===================================\n")

    except Exception:
        print("🔥 TELEGRAM SEND ERROR:")
        print(traceback.format_exc())


# =========================
# GITLAB RUNNERS
# =========================
def get_all_runners():
    try:
        url = f"https://gitlab.com/api/v4/projects/{PROJECT_ID}/runners"

        headers = {
            "PRIVATE-TOKEN": GITLAB_TOKEN
        }

        r = requests.get(url, headers=headers, timeout=10)

        print("\n========== GITLAB RESPONSE ==========")
        print("STATUS:", r.status_code)
        print("BODY:", r.text)
        print("====================================\n")

        if r.status_code != 200:
            return None

        return r.json()

    except Exception:
        print("🔥 GITLAB ERROR:")
        print(traceback.format_exc())
        return None


# =========================
# FORMAT RUNNERS
# =========================
def format_runners(runners):
    text = "📊 <b>GitLab Runners Status</b>\n\n"

    emoji_map = {
        "online": "🟢",
        "offline": "🔴",
        "stale": "🟡",
        "never_contacted": "⚪"
    }

    for r in runners:
        name = r.get("description", "Unknown")
        rid = r.get("id", "N/A")
        status = r.get("status", "unknown")
        busy = r.get("busy", False)

        emoji = emoji_map.get(status, "⚠️")

        text += (
            f"{emoji} <b>{name}</b>\n"
            f" ├ ID: <code>{rid}</code>\n"
            f" ├ Status: <code>{status}</code>\n"
            f" └ Busy: <code>{busy}</code>\n\n"
        )

    return text


# =========================
# WEBHOOK
# =========================
@app.route("/webhook", methods=["POST"])
def webhook():
    try:
        update = request.get_json(force=True)

        print("\n========== RAW UPDATE ==========")
        print(json.dumps(update, indent=2, ensure_ascii=False))
        print("================================\n")

        message = update.get("message")

        if not message:
            print("NO MESSAGE IN UPDATE")
            return "OK", 200

        chat_id = message["chat"]["id"]
        text = message.get("text", "")

        print("CHAT ID:", chat_id)
        print("TEXT:", text)

        # =========================
        # COMMAND HANDLER
        # =========================
        if text.startswith("/status"):
            print("🔥 STATUS COMMAND TRIGGERED")

            runners = get_all_runners()

            if not runners:
                send_raw(chat_id, "⚠️ Не удалось получить список runner'ов")
                return "OK", 200

            msg = format_runners(runners)
            send_raw(chat_id, msg)


        return "OK", 200

    except Exception:
        print("🔥 WEBHOOK ERROR:")
        print(traceback.format_exc())
        return "ERROR", 500


# =========================
# HEALTHCHECK
# =========================
@app.route("/", methods=["GET"])
def home():
    return "Bot is running", 200


@app.route("/health", methods=["GET"])
def health():
    return "healthy", 200


# =========================
# MAIN
# =========================
if __name__ == "__main__":
    port = int(os.getenv("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
