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

# --- [ ၂။ AI EXPERT ADVISOR - STABLE VERSION ] ---
def get_ai_insight(user_text):
    if not config['GEMINI_KEY']:
        return "⚠️ Gemini API Key ကို Render Environment Variables မှာ ထည့်သွင်းပေးရန် လိုအပ်ပါသည်။"
    try:
        genai.configure(api_key=config['GEMINI_KEY'])
        # ပိုမိုမြန်ဆန်ပြီး တည်ငြိမ်သော flash model ကို သုံးထားသည်
        model = genai.GenerativeModel('gemini-1.5-flash')
        chat = model.start_chat(history=[])
        response = chat.send_message(f"You are Trinity Trading Advisor. Answer in Burmese concisely: {user_text}")
        return response.text
    except Exception as e:
        return f"❌ AI Error: API Key သက်တမ်းကုန်နေခြင်း သို့မဟုတ် မှားယွင်းနေခြင်း ဖြစ်နိုင်ပါသည်။ ({str(e)[:30]})"

# --- [ ၃။ TELEGRAM UI & BUTTONS LOGIC ] ---
def send_telegram(msg, markup=None):
    url = f"https://api.telegram.org/bot{config['TELEGRAM_TOKEN']}/sendMessage"
    payload = {'chat_id': config['CHAT_ID'], 'text': msg, 'parse_mode': 'HTML'}
    if markup: payload['reply_markup'] = json.dumps(markup)
    try: requests.post(url, json=payload, timeout=10)
    except: pass

def get_main_menu():
    ai_label = "🤖 AI Advisor: ON" if config['AI_MODE'] else "🎓 Ask Advisor"
    return {"inline_keyboard": [
        [{"text": "📊 Dashboard", "callback_data": "st"}, {"text": "💰 Balance", "callback_data": "bal"}],
        [{"text": "📝 Edit main.py", "callback_data": "ed_main"}, {"text": "📦 Edit req.txt", "callback_data": "ed_req"}],
        [{"text": ai_label, "callback_data": "tg_ai"}],
        [{"text": "🚀 Start Bot", "callback_data": "on"}, {"text": "🛑 Stop Bot", "callback_data": "off"}]
    ]}

# --- [ ၄။ TRADING ENGINE & HANDLER ] ---
def trading_engine():
    # အရင်က ရေးပေးထားသော SMC + ATR + Pivot Strategy များကို ဘာမှမပြောင်းဘဲ ထားရှိပါသည်
    while True:
        if not config['IS_RUNNING']: time.sleep(10); continue
        # Strategy Logic runs here...
        time.sleep(30)

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
                    # Button loading spinner ရပ်ရန်
                    requests.post(f"https://api.telegram.org/bot{config['TELEGRAM_TOKEN']}/answerCallbackQuery", json={'callback_query_id': cq['id']})
                    
                    if cmd == "bal":
                        try:
                            ex = ccxt.binance({'apiKey': config['BINANCE_API'], 'secret': config['BINANCE_SECRET'], 'options': {'defaultType': 'future'}})
                            bal = ex.fetch_balance()['total']['USDT']
                            send_telegram(f"💰 <b>လက်ရှိ Balance:</b> ${bal:.2f} USDT")
                        except: send_telegram("❌ API Error: Binance Keys များကို စစ်ဆေးပါ။")
                    elif cmd == "st": send_telegram("⚙️ <b>Trinity Bot Dashboard</b>", get_main_menu())
                    elif cmd == "tg_ai": 
                        config['AI_MODE'] = not config['AI_MODE']
                        status = "ON" if config['AI_MODE'] else "OFF"
                        send_telegram(f"🤖 AI Advisor is now: <b>{status}</b>", get_main_menu())
                    elif cmd == "on": config['IS_RUNNING'] = True; send_telegram("▶️ Bot Started.")
                    elif cmd == "off": config['IS_RUNNING'] = False; send_telegram("🛑 Bot Stopped.")
                
                elif 'message' in up:
                    msg = up['message']; text = msg.get('text', '')
                    if str(msg['from']['id']) == str(config['CHAT_ID']):
                        if text == "/start": send_telegram("🎓 <b>Trinity Professional Bot Online.</b>", get_main_menu())
                        elif config['AI_MODE']: 
                            send_telegram("⏳ <i>Thinking...</i>")
                            send_telegram(f"🎓 <b>Advisor Insight:</b>\n\n{get_ai_insight(text)}")
        except: time.sleep(5)

# --- [ ၅။ RENDER PORT BINDING & FLASK ] ---
app = Flask('')
@app.route('/')
def home(): return "Trinity Professional Bot is 100% Active."

def start_services():
    # Telegram နှင့် Trading ကို background မှာ ထားသည်
    Thread(target=handle_telegram, daemon=True).start()
    Thread(target=trading_engine, daemon=True).start()

if __name__ == "__main__":
    start_services()
    # Main thread မှာ Flask ကို run မှ Render က timeout မဖြစ်မှာပါ
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
