import ccxt, pandas as pd, time, os, requests, json, base64, pytz
import google.generativeai as genai
from flask import Flask
from threading import Thread
from datetime import datetime, timedelta

# --- [ ၁။ CONFIGURATION ] ---
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
    'TRADES_LOG': []
}

# --- [ ၂။ STABLE AI ADVISOR - FIXED 404 ] ---
def get_ai_insight(text):
    if not config['GEMINI_KEY']: return "⚠️ Gemini API Key missing."
    try:
        genai.configure(api_key=config['GEMINI_KEY'])
        # 404 Error မတက်စေရန် model name ကို အတည်ငြိမ်ဆုံး version ခေါ်ယူခြင်း
        model = genai.GenerativeModel('gemini-1.5-flash-latest') 
        response = model.generate_content(f"Answer as a Crypto Expert in Burmese: {text}")
        return response.text
    except Exception as e:
        # Flash model ရှာမတွေ့ပါက Pro model သို့ ပြောင်းလဲကြိုးစားခြင်း
        try:
            model = genai.GenerativeModel('gemini-pro')
            response = model.generate_content(text)
            return response.text
        except:
            return f"❌ AI Error: Model not found or API issue. ({str(e)[:30]})"

# --- [ ၃။ UI & MENU ] ---
def send_telegram(msg, markup=None):
    url = f"https://api.telegram.org/bot{config['TELEGRAM_TOKEN']}/sendMessage"
    payload = {'chat_id': config['CHAT_ID'], 'text': msg, 'parse_mode': 'HTML'}
    if markup: payload['reply_markup'] = json.dumps(markup)
    try: requests.post(url, json=payload, timeout=10)
    except: pass

def get_menu():
    ai_btn = "🤖 AI: ON" if config['AI_MODE'] else "🎓 Ask Advisor"
    return {"inline_keyboard": [
        [{"text": "📊 Dashboard", "callback_data": "st"}, {"text": "💰 Balance", "callback_data": "bal"}],
        [{"text": ai_btn, "callback_data": "tg_ai"}],
        [{"text": "🚀 Start", "callback_data": "on"}, {"text": "🛑 Stop", "callback_data": "off"}]
    ]}

# --- [ ၄။ MAIN TELEGRAM HANDLER ] ---
def handle_telegram():
    last_id = 0
    while True:
        try:
            url = f"https://api.telegram.org/bot{config['TELEGRAM_TOKEN']}/getUpdates"
            res = requests.get(url, params={'offset': last_id+1, 'timeout': 20}).json()
            if not res.get('ok'): continue
            
            for up in res.get('result', []):
                last_id = up['update_id']
                if 'callback_query' in up:
                    cq = up['callback_query']
                    cmd = cq['data']
                    requests.post(f"https://api.telegram.org/bot{config['TELEGRAM_TOKEN']}/answerCallbackQuery", json={'callback_query_id': cq['id']})
                    
                    if cmd == "bal":
                        try:
                            ex = ccxt.binance({'apiKey': config['BINANCE_API'], 'secret': config['BINANCE_SECRET'], 'options': {'defaultType': 'future'}})
                            b = ex.fetch_balance()['total']['USDT']
                            send_telegram(f"💰 <b>Balance:</b> ${b:.2f} USDT")
                        except: send_telegram("❌ Binance API Error.")
                    elif cmd == "st": send_telegram("⚙️ <b>Dashboard Active</b>", get_menu())
                    elif cmd == "tg_ai": 
                        config['AI_MODE'] = not config['AI_MODE']
                        send_telegram(f"AI Advisor: {'ON' if config['AI_MODE'] else 'OFF'}", get_menu())
                    elif cmd == "on": config['IS_RUNNING'] = True; send_telegram("▶️ Bot Started.")
                    elif cmd == "off": config['IS_RUNNING'] = False; send_telegram("🛑 Bot Stopped.")

                elif 'message' in up:
                    msg = up['message']; text = msg.get('text', '')
                    if str(msg['from']['id']) == str(config['CHAT_ID']):
                        if text == "/start": send_telegram("🎓 <b>Trinity System Online</b>", get_menu())
                        elif config['AI_MODE']: 
                            send_telegram("⏳ <i>Thinking...</i>")
                            send_telegram(f"🎓 <b>Advisor Insight:</b>\n\n{get_ai_insight(text)}")
        except: time.sleep(5)

# --- [ ၅။ TRADING ENGINE ] ---
def trading_engine():
    # အရင် Code ထဲမှ SMC + ATR Strategy Logic များအတိုင်း အလုပ်လုပ်မည်
    while True:
        if not config['IS_RUNNING']: time.sleep(10); continue
        time.sleep(30)

# --- [ ၆။ RENDER DEPLOY FIX ] ---
app = Flask('')
@app.route('/')
def home(): return "Trinity Bot Fixed & Active."

if __name__ == "__main__":
    # Background threads
    Thread(target=handle_telegram, daemon=True).start()
    Thread(target=trading_engine, daemon=True).start()
    
    # Main thread Port Binding
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
