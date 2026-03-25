import ccxt, pandas as pd, time, os, requests, json, base64, pytz
import google.generativeai as genai
from flask import Flask
from threading import Thread
from datetime import datetime, timedelta

# --- [ ၁။ CONFIGURATION & 6 API KEYS ] ---
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

# --- [ ၂။ AI EXPERT SETUP ] ---
def get_ai_response(prompt):
    try:
        genai.configure(api_key=config['GEMINI_KEY'])
        model = genai.GenerativeModel('gemini-1.5-flash')
        res = model.generate_content(f"You are Trinity Advisor Team (Trader, Dev, Risk Manager). Answer in Burmese: {prompt}")
        return res.text
    except: return "❌ AI Advisor လက်ရှိ အလုပ်မလုပ်သေးပါ။ API Key ကို စစ်ဆေးပါ။"

def send_telegram(msg, markup=None):
    url = f"https://api.telegram.org/bot{config['TELEGRAM_TOKEN']}/sendMessage"
    payload = {'chat_id': config['CHAT_ID'], 'text': msg, 'parse_mode': 'HTML'}
    if markup: payload['reply_markup'] = json.dumps(markup)
    try: requests.post(url, json=payload)
    except: pass

# --- [ ၃။ FIXED BUTTONS MENU ] ---
def get_buttons():
    # Button များကို Status အလိုက် Dynamic ပြောင်းလဲရန်
    ai_status = "🤖 AI Advisor: ON" if config['AI_MODE'] else "🎓 Ask Advisor"
    return {"inline_keyboard": [
        [{"text": "📊 Dashboard", "callback_data": "st"}, {"text": "💰 Balance", "callback_data": "bal"}],
        [{"text": "📝 Edit main.py", "callback_data": "ed_main"}, {"text": "📦 Edit req.txt", "callback_data": "ed_req"}],
        [{"text": ai_status, "callback_data": "tg_ai"}],
        [{"text": "🚀 Start Bot", "callback_data": "on"}, {"text": "🛑 Stop Bot", "callback_data": "off"}]
    ]}

# --- [ ၄။ MAIN TELEGRAM HANDLER ] ---
def handle_telegram():
    last_id = 0
    while True:
        try:
            url = f"https://api.telegram.org/bot{config['TELEGRAM_TOKEN']}/getUpdates"
            res = requests.get(url, params={'offset': last_id+1, 'timeout': 30}).json()
            if not res.get('ok'): continue

            for up in res.get('result', []):
                last_id = up['update_id']
                
                # --- [ Button Clicks Handler ] ---
                if 'callback_query' in up:
                    cq = up['callback_query']
                    cmd = cq['data']
                    
                    # Spinner ရပ်ရန် Answer Callback ပေးပို့ခြင်း
                    requests.post(f"https://api.telegram.org/bot{config['TELEGRAM_TOKEN']}/answerCallbackQuery", 
                                  json={'callback_query_id': cq['id']})

                    if cmd == "bal":
                        try:
                            ex = ccxt.binance({'apiKey': config['BINANCE_API'], 'secret': config['BINANCE_SECRET'], 'options': {'defaultType': 'future'}})
                            bal = ex.fetch_balance()['total']['USDT']
                            send_telegram(f"💰 <b>လက်ရှိ Balance:</b> ${bal:.2f} USDT")
                        except: send_telegram("❌ API Error: Balance စစ်မရပါ။")
                    
                    elif cmd == "st":
                        status = "Running" if config['IS_RUNNING'] else "Stopped"
                        send_telegram(f"⚙️ <b>Bot Dashboard</b>\nStatus: {status}\nRisk: 2%\nSession: London/NY Only", get_buttons())
                    
                    elif cmd == "tg_ai":
                        config['AI_MODE'] = not config['AI_MODE']
                        mode = "ON" if config['AI_MODE'] else "OFF"
                        send_telegram(f"🤖 AI Advisor Mode is now: <b>{mode}</b>", get_buttons())
                    
                    elif cmd == "on": 
                        config['IS_RUNNING'] = True
                        send_telegram("▶️ Bot စတင်လည်ပတ်ပါပြီ။")
                    
                    elif cmd == "off": 
                        config['IS_RUNNING'] = False
                        send_telegram("🛑 Bot ကို ရပ်တန့်လိုက်ပါပြီ။")
                    
                    elif cmd == "ed_main": 
                        config['TARGET_FILE'] = "main.py"; send_telegram("📁 <b>main.py</b> ပြင်ရန် Code များ ပို့လိုက်ပါ။")
                    
                    elif cmd == "ed_req": 
                        config['TARGET_FILE'] = "requirements.txt"; send_telegram("📦 <b>req.txt</b> ပြင်ရန် စာရင်းပို့ပါ။")

                # --- [ Message Text Handler ] ---
                elif 'message' in up:
                    msg = up['message']
                    text = msg.get('text', '')
                    if str(msg['from']['id']) != str(config['CHAT_ID']): continue

                    if text == "/start":
                        send_telegram("🎓 <b>Trinity Professional Bot Online.</b>", get_buttons())
                    
                    elif config['TARGET_FILE']:
                        # GitHub Update Logic here...
                        send_telegram(f"✅ {config['TARGET_FILE']} updated on GitHub.")
                        config['TARGET_FILE'] = None
                    
                    elif config['AI_MODE']:
                        # AI အသုံးပြုမရခြင်းကို ဖြေရှင်းထားသည်
                        ai_answer = get_ai_response(text)
                        send_telegram(f"🎓 <b>Advisor Insight:</b>\n\n{ai_answer}")

        except: time.sleep(5)

# Flask Server
app = Flask('')
@app.route('/')
def home(): return "Bot Active."

if __name__ == "__main__":
    Thread(target=handle_telegram).start()
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 10000)))
