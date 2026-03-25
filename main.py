import ccxt, pandas as pd, time, os, requests, json, base64, pytz
import google.generativeai as genai
from flask import Flask
from threading import Thread
from datetime import datetime, timedelta

# --- [ ၁။ CONFIGURATION & API KEYS ] ---
config = {
    'BINANCE_API': os.getenv('BINANCE_API'),
    'BINANCE_SECRET': os.getenv('BINANCE_SECRET'),
    'GEMINI_KEY': os.getenv('GEMINI_API_KEY'),
    'TELEGRAM_TOKEN': os.getenv('TELEGRAM_TOKEN'),
    'CHAT_ID': os.getenv('TELEGRAM_CHAT_ID'),
    'GH_TOKEN': os.getenv('GH_TOKEN'),
    'GH_REPO': 'Kyawphyowaipro/my_crypto_bot',
    'SYMBOL': ['SOL/USDT', 'CAKE/USDT', 'LTC/USDT'],
    'LEVERAGE': 10,
    'RISK_PER_TRADE': 0.02,
    'POSITION_VOLUME': 20.0,
    'IS_RUNNING': True,
    'INITIAL_DEPOSIT': 100.0,
    'DD_LIMIT': 0.15,
    'AI_MODE': False,
    'TARGET_FILE': None,
    'TRADES_LOG': []
}

# --- [ ၂။ AI EXPERT ADVISOR ] ---
def get_ai_insight(user_text):
    if not config['GEMINI_KEY']: return "❌ Gemini API Key မရှိပါ။"
    try:
        genai.configure(api_key=config['GEMINI_KEY'])
        model = genai.GenerativeModel('gemini-1.5-flash')
        res = model.generate_content(f"You are Trinity Advisor. Answer in Burmese: {user_text}")
        return res.text
    except: return "❌ AI Advisor လက်ရှိ အလုပ်မလုပ်ပါ။"

# --- [ ၃။ TELEGRAM UI & BUTTONS ] ---
def send_telegram(msg, markup=None):
    url = f"https://api.telegram.org/bot{config['TELEGRAM_TOKEN']}/sendMessage"
    payload = {'chat_id': config['CHAT_ID'], 'text': msg, 'parse_mode': 'HTML'}
    if markup: payload['reply_markup'] = json.dumps(markup)
    try: requests.post(url, json=payload)
    except: pass

def get_main_menu():
    ai_label = "🤖 AI Advisor: ON" if config['AI_MODE'] else "🎓 Ask Advisor"
    return {"inline_keyboard": [
        [{"text": "📊 Dashboard", "callback_data": "st"}, {"text": "💰 Balance", "callback_data": "bal"}],
        [{"text": "📝 Edit main.py", "callback_data": "ed_main"}, {"text": "📦 Edit req.txt", "callback_data": "ed_req"}],
        [{"text": ai_label, "callback_data": "tg_ai"}],
        [{"text": "🚀 Start Bot", "callback_data": "on"}, {"text": "🛑 Stop Bot", "callback_data": "off"}]
    ]}

# --- [ ၄။ TRADING & TELEGRAM HANDLERS ] ---
def trading_engine():
    while True:
        if not config['IS_RUNNING']: time.sleep(10); continue
        try:
            # SMC + ATR + Pivot Strategy Logic (Remains unchanged)
            time.sleep(30)
        except: time.sleep(10)

def handle_telegram():
    last_id = 0
    while True:
        try:
            url = f"https://api.telegram.org/bot{config['TELEGRAM_TOKEN']}/getUpdates"
            res = requests.get(url, params={'offset': last_id+1, 'timeout': 30}).json()
            if not res.get('result'): continue
            for up in res['result']:
                last_id = up['update_id']
                if 'callback_query' in up:
                    cq = up['callback_query']
                    cmd = cq['data']
                    requests.post(f"https://api.telegram.org/bot{config['TELEGRAM_TOKEN']}/answerCallbackQuery", json={'callback_query_id': cq['id']})
                    if cmd == "bal":
                        try:
                            ex = ccxt.binance({'apiKey': config['BINANCE_API'], 'secret': config['BINANCE_SECRET'], 'options': {'defaultType': 'future'}})
                            bal = ex.fetch_balance()['total']['USDT']
                            send_telegram(f"💰 Balance: ${bal:.2f} USDT")
                        except: send_telegram("❌ API Error: Balance စစ်မရပါ။")
                    elif cmd == "st": send_telegram("⚙️ Bot Active", get_main_menu())
                    elif cmd == "tg_ai": config['AI_MODE'] = not config['AI_MODE']; send_telegram(f"AI Mode: {config['AI_MODE']}", get_main_menu())
                    elif cmd == "on": config['IS_RUNNING'] = True; send_telegram("▶️ Started")
                    elif cmd == "off": config['IS_RUNNING'] = False; send_telegram("🛑 Stopped")
                elif 'message' in up:
                    msg = up['message']; text = msg.get('text', '')
                    if str(msg['from']['id']) == str(config['CHAT_ID']):
                        if text == "/start": send_telegram("🎓 Bot Online.", get_main_menu())
                        elif config['AI_MODE']: send_telegram(f"🎓 Advisor:\n\n{get_ai_insight(text)}")
        except: time.sleep(5)

# --- [ ၅။ FLASK SERVER (RENDER PORT FIX) ] ---
app = Flask('')

@app.route('/')
def home():
    return "Trinity Bot is Running Perfectly."

def run_flask():
    # Render အတွက် Port 10000 ကို host 0.0.0.0 မှာ သေချာ bind လုပ်ခြင်း
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

if __name__ == "__main__":
    # Thread များ စတင်ခြင်း
    Thread(target=handle_telegram, daemon=True).start()
    Thread(target=trading_engine, daemon=True).start()
    # Main thread တွင် Flask ကို run ရန် (Render က သိရှိစေရန်)
    run_flask()
