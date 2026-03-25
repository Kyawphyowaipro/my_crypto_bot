import ccxt, pandas as pd, time, os, requests, json, pytz
import google.generativeai as genai
from flask import Flask
from threading import Thread

# --- [ ၁။ CONFIGURATION & AUTO-STRIP KEYS ] ---
def get_clean_env(key_name):
    # .env ထဲက Key တွေမှာ Space ပါနေရင် အလိုအလျောက် ဖယ်ထုတ်ရန်
    val = os.getenv(key_name)
    return val.strip() if val else ""

config = {
    'BINANCE_API': get_clean_env('BINANCE_API'),
    'BINANCE_SECRET': get_clean_env('BINANCE_SECRET'),
    'GEMINI_KEY': get_clean_env('GEMINI_API_KEY'),
    'TELEGRAM_TOKEN': get_clean_env('TELEGRAM_TOKEN'),
    'CHAT_ID': get_clean_env('TELEGRAM_CHAT_ID'),
    'SYMBOL': ['SOL/USDT', 'CAKE/USDT', 'LTC/USDT'],
    'IS_RUNNING': True,
    'AI_MODE': False
}

# --- [ ၂။ STABLE AI ADVISOR - FIX 404 & MODEL ISSUE ] ---
def get_ai_insight(text):
    if not config['GEMINI_KEY']: return "⚠️ Gemini API Key missing in Render."
    try:
        genai.configure(api_key=config['GEMINI_KEY'])
        # 404 model not found ဖြစ်ခြင်းကို ဖြေရှင်းရန်
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content(f"Answer as a pro crypto trader in Burmese: {text}")
        return response.text
    except Exception as e:
        return f"❌ AI System Error: {str(e)[:50]}"

# --- [ ၃။ TELEGRAM INTERFACE ] ---
def send_telegram(msg, markup=None):
    url = f"https://api.telegram.org/bot{config['TELEGRAM_TOKEN']}/sendMessage"
    payload = {'chat_id': config['CHAT_ID'], 'text': msg, 'parse_mode': 'HTML'}
    if markup: payload['reply_markup'] = json.dumps(markup)
    try: requests.post(url, json=payload, timeout=10)
    except: pass

def get_menu():
    ai_status = "🤖 AI Advisor: ON" if config['AI_MODE'] else "🎓 Ask Advisor"
    return {"inline_keyboard": [
        [{"text": "📊 Dashboard", "callback_data": "st"}, {"text": "💰 Balance", "callback_data": "bal"}],
        [{"text": ai_status, "callback_data": "tg_ai"}],
        [{"text": "🚀 Start Bot", "callback_data": "on"}, {"text": "🛑 Stop Bot", "callback_data": "off"}]
    ]}

# --- [ ၄။ HANDLERS & BOT LOGIC ] ---
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
                            # Binance API Error ကာကွယ်ရန်
                            ex = ccxt.binance({'apiKey': config['BINANCE_API'], 'secret': config['BINANCE_SECRET'], 'options': {'defaultType': 'future'}})
                            b = ex.fetch_balance()['total']['USDT']
                            send_telegram(f"💰 <b>Current Balance:</b> ${b:.2f} USDT")
                        except: send_telegram("❌ Binance API Connection Failed.")
                    elif cmd == "st": send_telegram("⚙️ <b>Trinity Bot Status: Active</b>", get_menu())
                    elif cmd == "tg_ai": 
                        config['AI_MODE'] = not config['AI_MODE']
                        send_telegram(f"AI Advisor is now: {'ON' if config['AI_MODE'] else 'OFF'}", get_menu())
                    elif cmd == "on": config['IS_RUNNING'] = True; send_telegram("▶️ Trading Engine Started.")
                    elif cmd == "off": config['IS_RUNNING'] = False; send_telegram("🛑 Trading Engine Stopped.")

                elif 'message' in up:
                    msg = up['message']; text = msg.get('text', '')
                    if str(msg['from']['id']) == str(config['CHAT_ID']):
                        if text == "/start": send_telegram("🎓 <b>Trinity Professional System Online</b>", get_menu())
                        elif config['AI_MODE']: 
                            send_telegram("⏳ <i>Thinking...</i>")
                            send_telegram(f"🎓 <b>Advisor Insight:</b>\n\n{get_ai_insight(text)}")
        except: time.sleep(5)

# --- [ ၅။ FLASK & PORT BINDING (RENDER FIX) ] ---
app = Flask('')
@app.route('/')
def home(): return "Trinity Bot is Live."

if __name__ == "__main__":
    # Render မှာ "Port scan timeout" မဖြစ်စေရန် Flask ကို Main Thread မှာပဲ Run ရပါမယ်
    Thread(target=handle_telegram, daemon=True).start()
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
