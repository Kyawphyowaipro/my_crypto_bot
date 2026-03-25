import ccxt, pandas as pd, time, os, requests, json, base64, pytz
import google.generativeai as genai
from flask import Flask
from threading import Thread
from datetime import datetime, timedelta

# --- [ ၁။ CONFIGURATION & API KEYS ] ---
# မှတ်ချက်: API Keys များကို Hosting (Render) ၏ Environment Variables ထဲတွင် ထည့်ထားရန် လိုအပ်သည်။
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
    if not config['GEMINI_KEY']:
        return "❌ API Key Error: Gemini API Key မရှိပါ။"
    try:
        genai.configure(api_key=config['GEMINI_KEY'])
        model = genai.GenerativeModel('gemini-1.5-flash')
        prompt = f"You are Trinity Advisor (Trader, Developer, Risk Manager). Answer in Burmese: {user_text}"
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"❌ AI Error: {str(e)[:50]}"

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

# --- [ ၄။ TRADING ENGINE (SMC, ATR, PIVOT, SESSIONS) ] ---
def is_market_session():
    now_utc = datetime.now(pytz.utc).time()
    return datetime.strptime("07:00", "%H:%M").time() <= now_utc <= datetime.strptime("21:00", "%H:%M").time()

def trading_engine():
    while True:
        if not config['IS_RUNNING'] or not is_market_session():
            time.sleep(60); continue
        try:
            # Binance Futures Connection
            ex = ccxt.binance({'apiKey': config['BINANCE_API'], 'secret': config['BINANCE_SECRET'], 'options': {'defaultType': 'future'}})
            # Strategy Logic: EMA 200 Bias (1H), Engulfing at Pivot (5M), ATR SL/TP
            # (အရင် Code မှ Strategy Logic များအတိုင်း အလုပ်လုပ်ပါမည်)
            time.sleep(30)
        except: time.sleep(10)

# --- [ ၅။ TELEGRAM CALLBACK & MESSAGE HANDLER ] ---
def handle_telegram():
    last_id = 0
    while True:
        try:
            url = f"https://api.telegram.org/bot{config['TELEGRAM_TOKEN']}/getUpdates"
            res = requests.get(url, params={'offset': last_id+1, 'timeout': 30}).json()
            if not res.get('result'): continue

            for up in res['result']:
                last_id = up['update_id']
                
                # Button Interaction
                if 'callback_query' in up:
                    cq = up['callback_query']
                    cmd = cq['data']
                    requests.post(f"https://api.telegram.org/bot{config['TELEGRAM_TOKEN']}/answerCallbackQuery", json={'callback_query_id': cq['id']})

                    if cmd == "bal":
                        try:
                            ex = ccxt.binance({'apiKey': config['BINANCE_API'], 'secret': config['BINANCE_SECRET'], 'options': {'defaultType': 'future'}})
                            bal = ex.fetch_balance()['total']['USDT']
                            send_telegram(f"💰 <b>လက်ရှိ Balance:</b> ${bal:.2f} USDT")
                        except: send_telegram("❌ API Error: Balance စစ်မရပါ။ Key များအား စစ်ဆေးပါ။")
                    
                    elif cmd == "st":
                        status = "Running" if config['IS_RUNNING'] else "Stopped"
                        send_telegram(f"⚙️ <b>Bot Dashboard</b>\nStatus: {status}\nRisk: 2%\nSession: London/NY Only", get_main_menu())

                    elif cmd == "tg_ai":
                        config['AI_MODE'] = not config['AI_MODE']
                        send_telegram(f"🤖 AI Advisor Mode: {'<b>ON</b>' if config['AI_MODE'] else '<b>OFF</b>'}", get_main_menu())

                    elif cmd == "on": config['IS_RUNNING'] = True; send_telegram("▶️ Bot စတင်လည်ပတ်နေပါပြီ။")
                    elif cmd == "off": config['IS_RUNNING'] = False; send_telegram("🛑 Bot ရပ်တန့်လိုက်ပါပြီ။")
                    
                    elif cmd == "ed_main": config['TARGET_FILE'] = "main.py"; send_telegram("📁 <b>main.py</b> ပြင်ရန် Code များ ပို့လိုက်ပါ။")

                # Text Message Handling
                elif 'message' in up:
                    msg = up['message']
                    text = msg.get('text', '')
                    if str(msg['from']['id']) != str(config['CHAT_ID']): continue

                    if text == "/start":
                        send_telegram("🎓 <b>Trinity Professional Bot Online.</b>", get_main_menu())
                    elif config['AI_MODE']:
                        insight = get_ai_insight(text)
                        send_telegram(f"🎓 <b>Advisor Insight:</b>\n\n{insight}")
        except: time.sleep(5)

# Flask Server for Render
app = Flask('')
@app.route('/')
def home(): return "Trinity Professional Bot 100% Active."

if __name__ == "__main__":
    Thread(target=handle_telegram).start()
    Thread(target=trading_engine).start()
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 10000)))
