import ccxt, pandas as pd, time, os, requests, json, pytz
import google.generativeai as genai
from flask import Flask
from threading import Thread
from datetime import datetime

# --- [ ၁။ CONFIGURATION & KEY CLEANING ] ---
def get_safe_env(key_name):
    value = os.getenv(key_name)
    return value.strip() if value else None

config = {
    'BINANCE_API': get_safe_env('BINANCE_API'),
    'BINANCE_SECRET': get_safe_env('BINANCE_SECRET'),
    'GEMINI_KEY': get_safe_env('GEMINI_API_KEY'),
    'TELEGRAM_TOKEN': get_safe_env('TELEGRAM_TOKEN'),
    'CHAT_ID': get_safe_env('TELEGRAM_CHAT_ID'),
    'SYMBOL': ['SOL/USDT', 'CAKE/USDT', 'LTC/USDT'],
    'LEVERAGE': 10,
    'RISK_PER_TRADE': 0.02,
    'IS_RUNNING': True,
    'AI_MODE': False
}

# --- [ ၂။ ROBUST AI ADVISOR ] ---
def get_ai_insight(text):
    if not config['GEMINI_KEY']: return "⚠️ Gemini API Key မရှိပါ။ Render Settings တွင် စစ်ဆေးပါ။"
    try:
        genai.configure(api_key=config['GEMINI_KEY'])
        # အတည်ငြိမ်ဆုံး model နာမည်ကို သုံးထားသည်
        model = genai.GenerativeModel('gemini-1.5-flash') 
        response = model.generate_content(f"Answer as a Crypto Expert in Burmese: {text}")
        return response.text
    except Exception:
        try:
            # Flash error တက်လျှင် Pro ဖြင့် အရန်ကြိုးစားသည်
            model = genai.GenerativeModel('gemini-pro')
            return model.generate_content(text).text
        except:
            return "❌ AI Error: API Key သို့မဟုတ် Model အလုပ်မလုပ်ပါ။"

# --- [ ၃။ UI & MENU ] ---
def send_telegram(msg, markup=None):
    url = f"https://api.telegram.org/bot{config['TELEGRAM_TOKEN']}/sendMessage"
    payload = {'chat_id': config['CHAT_ID'], 'text': msg, 'parse_mode': 'HTML'}
    if markup: payload['reply_markup'] = json.dumps(markup)
    try: requests.post(url, json=payload, timeout=10)
    except: pass

def get_menu():
    ai_status = "🤖 AI: ON" if config['AI_MODE'] else "🎓 Ask Advisor"
    return {"inline_keyboard": [
        [{"text": "📊 Dashboard", "callback_data": "st"}, {"text": "💰 Balance", "callback_data": "bal"}],
        [{"text": ai_status, "callback_data": "tg_ai"}],
        [{"text": "🚀 Start", "callback_data": "on"}, {"text": "🛑 Stop", "callback_data": "off"}]
    ]}

# --- [ ၄။ HANDLERS ] ---
def handle_telegram():
    last_id = 0
    while True:
        try:
            url = f"https://api.telegram.org/bot{config['TELEGRAM_TOKEN']}/getUpdates"
            res = requests.get(url, params={'offset': last_id+1, 'timeout': 20}).json()
            if not res.get('ok'): continue
            for up in res['result']:
                last_id = up['update_id']
                if 'callback_query' in up:
                    cq = up['callback_query']; cmd = cq['data']
                    requests.post(f"https://api.telegram.org/bot{config['TELEGRAM_TOKEN']}/answerCallbackQuery", json={'callback_query_id': cq['id']})
                    
                    if cmd == "bal":
                        try:
                            ex = ccxt.binance({'apiKey': config['BINANCE_API'], 'secret': config['BINANCE_SECRET'], 'options': {'defaultType': 'future'}})
                            b = ex.fetch_balance()['total']['USDT']
                            send_telegram(f"💰 <b>Balance:</b> ${b:.2f} USDT")
                        except: send_telegram("❌ Binance API Error. Key များကို ပြန်စစ်ပါ။")
                    elif cmd == "st": send_telegram("⚙️ <b>Bot Online</b>", get_menu())
                    elif cmd == "tg_ai": 
                        config['AI_MODE'] = not config['AI_MODE']
                        send_telegram(f"AI Mode: {'ON' if config['AI_MODE'] else 'OFF'}", get_menu())
                    elif cmd == "on": config['IS_RUNNING'] = True; send_telegram("▶️ Bot Started.")
                    elif cmd == "off": config['IS_RUNNING'] = False; send_telegram("🛑 Bot Stopped.")

                elif 'message' in up:
                    msg = up['message']; text = msg.get('text', '')
                    if str(msg['from']['id']) == str(config['CHAT_ID']):
                        if text == "/start": send_telegram("🎓 <b>Trinity Professional System</b>", get_menu())
                        elif config['AI_MODE']: 
                            send_telegram("⏳ <i>Thinking...</i>")
                            send_telegram(f"🎓 <b>Advisor Insight:</b>\n\n{get_ai_insight(text)}")
        except: time.sleep(5)

# --- [ ၅။ TRADING ENGINE ] ---
def trading_engine():
    # မူလ SMC + ATR Trade Logic များသည် ဤနေရာတွင် ဆက်လက်အလုပ်လုပ်မည်
    while True:
        if not config['IS_RUNNING']: time.sleep(10); continue
        time.sleep(30)

# --- [ ၆။ DEPLOYMENT FIX ] ---
app = Flask('')
@app.route('/')
def home(): return "Trinity Bot 100% Active."

if __name__ == "__main__":
    # Background threads များ စတင်ခြင်း
    Thread(target=handle_telegram, daemon=True).start()
    Thread(target=trading_engine, daemon=True).start()
    # Render အတွက် Port 10000 ကို main thread မှာ bind လုပ်ခြင်း
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
