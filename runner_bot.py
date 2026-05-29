from flask import Flask, request
import telebot

TOKEN = "TOKEN"

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

@bot.message_handler(commands=['status'])
def status(message):
    bot.reply_to(message, "Runner online")

@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    json_str = request.get_data().decode("UTF-8")
    update = telebot.types.Update.de_json(json_str)
    bot.process_new_updates([update])
    return "ok", 200

@app.route("/")
def index():
    return "Bot alive", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)