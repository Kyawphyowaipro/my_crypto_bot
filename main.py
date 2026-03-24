import ccxt, pandas as pd, time, os, requests, json, base64
import google.generativeai as genai
from flask import Flask
from threading import Thread

# --- [ CONFIGURATION ] ---
# Render Environment Variables ထဲက နာမည်တွေနဲ့ တိုက်ရိုက်ချိတ်ဆက်ထားပါတယ်
config = {
    'BINANCE_API': os.getenv('BINANCE_API'),
    'BINANCE_SECRET': os.getenv('BINANCE_SECRET'),
    'GEMINI_KEY': os.getenv('GEMINI_API_KEY'),
    'TELEGRAM_TOKEN': os.getenv('TELEGRAM_TOKEN'),
    'GH_TOKEN': os.getenv('GH_TOKEN'),
    'GH_REPO': 'Kyaw/my-crypto-bot', # မင်းရဲ့ GitHub username/repo ပြောင်းပေးပါ
    'SYMBOLS': ['SOL/USDT', 'CAKE/USDT', 'LTC/USDT'],
    'LEVERAGE': 20,
    'IS_RUNNING': True
}

# Chat ID ကိုတော့ Variable ထဲမှာပဲ ထည့်ထားပါ (သို့မဟုတ် Environment ထဲထည့်ပါ)
CHAT_ID = 'YOUR_TELEGRAM_CHAT_ID'

# --- [ EXPERT AI SETUP ] ---
SYSTEM_PROMPT = """You are a Trinity Expert AI (Senior Trader, Dev, and Finance Advisor). 
Provide professional advice in Burmese or English. Be concise and mentor-like."""

try:
    if config['GEMINI_KEY']:
        genai.configure(api_key=config['GEMINI_KEY'])
        ai_model = genai.GenerativeModel('gemini-1.5-flash', system_instruction=SYSTEM_PROMPT)
    else:
        ai_model = None
except:
    ai_model = None

# --- [ FLASK FOR RENDER PORT BINDING ] ---
app = Flask('')
@app.route('/')
def home(): return "Expert Bot is Live and Healthy!"

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

# --- [ TELEGRAM CONTROLLER ] ---
def send_telegram(msg, markup=None):
    try:
        url = f"https://api.telegram.org/bot{config['TELEGRAM_TOKEN']}/sendMessage"
        data = {'chat_id': CHAT_ID, 'text': msg, 'parse_mode': 'HTML'}
        if markup: data['reply_markup'] = json.dumps(markup)
        requests.post(url, json=data, timeout=10)
    except: pass

def get_buttons():
    return {"inline_keyboard": [[{"text": "📊 Status", "callback_data": "st"}, {"text": "🚀 Start", "callback_data": "on"}],
                                [{"text": "🛑 Stop", "callback_data": "off"}]]}

def handle_telegram():
    last_id = 0
    while True:
        try:
            url = f"https://api.telegram.org/bot{config['TELEGRAM_TOKEN']}/getUpdates"
            res = requests.get(url, params={'offset': last_id+1, 'timeout': 30}).json()
            for up in res.get('result', []):
                last_id = up['update_id']
                if 'callback_query' in up:
                    cmd = up['callback_query']['data']
                    if cmd == "st": send_telegram(f"⚙️ Status: {'ON' if config['IS_RUNNING'] else 'OFF'}\nLev: {config['LEVERAGE']}x", get_buttons())
                    elif cmd == "on": config['IS_RUNNING'] = True; send_telegram("▶️ Bot စတင်လည်ပတ်ပါပြီ။")
                    elif cmd == "off": config['IS_RUNNING'] = False; send_telegram("🛑 Bot ကို ရပ်တန့်လိုက်ပါပြီ။")
                elif 'message' in up:
                    text = up['message'].get('text', '')
                    if text == "/start": send_telegram("🎓 Trinity Expert AI အဆင်သင့်ရှိပါသည်။ ဘာကူညီပေးရမလဲ?", get_buttons())
                    elif ai_model:
                        response = ai_model.generate_content(text)
                        send_telegram(f"🎓 <b>Expert Insight:</b>\n\n{response.text}")
        except: time.sleep(5)

# --- [ TRADING ENGINE (1H-15M-5M) ] ---
def trade_logic():
    try:
        ex = ccxt.binance({'apiKey': config['BINANCE_API'], 'secret': config['BINANCE_SECRET'], 'enableRateLimit': True, 'options': {'defaultType': 'future'}})
    except: return

    while True:
        if not config['IS_RUNNING']: time.sleep(10); continue
        for s in config['SYMBOLS']:
            try:
                # 1H Trend Confirmation
                bars = ex.fetch_ohlcv(s, '1h', limit=200)
                df = pd.DataFrame(bars)
                ema200 = df[4].ewm(span=200).mean().iloc[-1]
                price = bars[-1][4]

                # Simple Strategy Trigger (Example)
                if price > ema200:
                    # 15M/5M Logic can be added here
                    pass
            except: pass
        time.sleep(60)

if __name__ == "__main__":
    # Thread များခွဲ၍ Run ခြင်းဖြင့် Port Binding Error ကို ဖြေရှင်းပါသည်
    Thread(target=handle_telegram).start()
    Thread(target=trade_logic).start()
    run_flask()
