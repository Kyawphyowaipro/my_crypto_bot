import ccxt, pandas as pd, time, os, requests, json, base64
import google.generativeai as genai
from flask import Flask
from threading import Thread

# --- [ CONFIGURATION ] ---
# Key ၆ ခုလုံးကို Environment ကနေ တိုက်ရိုက်ဖတ်ပါတယ်
config = {
    'BINANCE_API': os.getenv('BINANCE_API'),
    'BINANCE_SECRET': os.getenv('BINANCE_SECRET'),
    'GEMINI_KEY': os.getenv('GEMINI_API_KEY'),
    'TELEGRAM_TOKEN': os.getenv('TELEGRAM_TOKEN'),
    'CHAT_ID': os.getenv('TELEGRAM_CHAT_ID'),
    'GH_TOKEN': os.getenv('GH_TOKEN'),
    'GH_REPO': 'Kyawphyowaipro/my_crypto_bot', # မင်းရဲ့ Repo နာမည်
    'SYMBOL': ['SOL/USDT', 'CAKE/USDT', 'LTC/USDT'],
    'LEVERAGE': 20,
    'IS_RUNNING': True,
    'INITIAL_DEPOSIT': 0.0 # /deposit command နဲ့ သတ်မှတ်ရန်
}

# --- [ EXPERT AI SETUP ] ---
SYSTEM_PROMPT = """You are a 'Trinity Expert AI':
1. Senior Crypto Trader (Technical Analysis Expert)
2. Professional Developer (Python & API Expert)
3. Finance Advisor (Risk Management Expert)
Answer in Burmese or English concisely."""

try:
    if config['GEMINI_KEY']:
        genai.configure(api_key=config['GEMINI_KEY'])
        ai_model = genai.GenerativeModel('gemini-1.5-flash', system_instruction=SYSTEM_PROMPT)
    else:
        ai_model = None
except:
    ai_model = None

# --- [ WEB SERVER FOR RENDER ] ---
app = Flask('')
@app.route('/')
def home(): return "Trinity Bot is Active!"

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

# --- [ TELEGRAM FUNCTIONS ] ---
def send_telegram(msg, markup=None):
    if not config['CHAT_ID'] or not config['TELEGRAM_TOKEN']: return
    url = f"https://api.telegram.org/bot{config['TELEGRAM_TOKEN']}/sendMessage"
    payload = {'chat_id': config['CHAT_ID'], 'text': msg, 'parse_mode': 'HTML'}
    if markup: payload['reply_markup'] = json.dumps(markup)
    try: requests.post(url, json=payload, timeout=10)
    except: pass

def get_buttons():
    return {"inline_keyboard": [
        [{"text": "📊 Status", "callback_data": "st"}, {"text": "💰 Balance", "callback_data": "bal"}],
        [{"text": "🚀 Start", "callback_data": "on"}, {"text": "🛑 Stop", "callback_data": "off"}]
    ]}

# --- [ BINANCE TOOLS ] ---
def get_balance():
    try:
        ex = ccxt.binance({
            'apiKey': config['BINANCE_API'],
            'secret': config['BINANCE_SECRET'],
            'options': {'defaultType': 'future'}
        })
        bal = ex.fetch_balance()
        return float(bal['total']['USDT'])
    except: return None

# --- [ MONITORING THREAD (70% LOSS ALERT) ] ---
def monitor_account():
    alert_sent = False
    while True:
        try:
            if config['INITIAL_DEPOSIT'] > 0:
                current_bal = get_balance()
                if current_bal is not None:
                    # ၇၀% ကုန်သွားလျှင် (ဆိုလိုသည်မှာ ၃၀% ပဲကျန်တော့လျှင်)
                    if current_bal <= (config['INITIAL_DEPOSIT'] * 0.3) and not alert_sent:
                        send_telegram(f"🚨 <b>အရေးကြီး သတိပေးချက်!</b>\nမင်းရဲ့ Balance က ရင်းနှီးငွေရဲ့ 70% ကျော် ကုန်သွားပါပြီ။\nလက်ရှိ Balance: ${current_bal:.2f}")
                        config['IS_RUNNING'] = False
                        alert_sent = True
                    elif current_bal > (config['INITIAL_DEPOSIT'] * 0.3):
                        alert_sent = False
        except: pass
        time.sleep(300) # ၅ မိနစ်တစ်ခါ စစ်မယ်

# --- [ TELEGRAM CONTROLLER ] ---
def handle_telegram():
    last_id = 0
    while True:
        try:
            if not config['TELEGRAM_TOKEN']: 
                time.sleep(5); continue
            url = f"https://api.telegram.org/bot{config['TELEGRAM_TOKEN']}/getUpdates"
            res = requests.get(url, params={'offset': last_id+1, 'timeout': 30}).json()
            
            for up in res.get('result', []):
                last_id = up['update_id']
                if 'callback_query' in up:
                    cmd = up['callback_query']['data']
                    if cmd == "bal":
                        b = get_balance()
                        send_telegram(f"💰 <b>လက်ရှိ Balance:</b> ${b if b else 'Error'} USDT")
                    elif cmd == "st":
                        send_telegram(f"⚙️ Status: {'ON' if config['IS_RUNNING'] else 'OFF'}\nLev: {config['LEVERAGE']}x", get_buttons())
                    elif cmd == "on": config['IS_RUNNING'] = True; send_telegram("▶️ Bot Started.")
                    elif cmd == "off": config['IS_RUNNING'] = False; send_telegram("🛑 Bot Stopped.")

                elif 'message' in up:
                    msg = up['message']
                    text = msg.get('text', '')
                    sender_id = str(msg['from']['id'])
                    
                    if sender_id != str(config['CHAT_ID']): continue

                    if text.startswith('/deposit'):
                        try:
                            val = float(text.split(' ')[1])
                            config['INITIAL_DEPOSIT'] = val
                            send_telegram(f"✅ <b>Deposit သတ်မှတ်ပြီးပါပြီ:</b> ${val}\n၇၀% ကုန်ရင် သတိပေးပါ့မယ်။")
                        except: send_telegram("⚠️ Format: <code>/deposit 100</code>")
                    
                    elif text == "/balance":
                        b = get_balance()
                        send_telegram(f"💰 <b>လက်ရှိလက်ကျန်:</b> ${b if b else 'Error'} USDT")
                    
                    elif text == "/start":
                        send_telegram("🎓 Trinity Expert AI အဆင်သင့်ရှိပါသည်။", get_buttons())
                        
                    elif ai_model:
                        response = ai_model.generate_content(text)
                        send_telegram(f"🎓 <b>Expert Insight:</b>\n\n{response.text}")
        except: time.sleep(5)

# --- [ TRADING LOGIC ] ---
def trade_logic():
    while True:
        if not config['IS_RUNNING']: time.sleep(10); continue
        # Trading Scan Logic (1H-15M-5M) များကို ဤနေရာတွင် ထည့်သွင်းနိုင်သည်
        time.sleep(60)

if __name__ == "__main__":
    Thread(target=handle_telegram).start()
    Thread(target=monitor_account).start()
    Thread(target=trade_logic).start()
    run_flask()
