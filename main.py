import ccxt, pandas as pd, time, os, pytz, requests, json, base64
import google.generativeai as genai
from datetime import datetime
from flask import Flask
from threading import Thread

# --- [ CONFIGURATION ] ---
# Render Environment Variables ထဲမှာ သွားထည့်ပေးရမယ့် နာမည်များ
config = {
    'BINANCE_API': os.getenv('BINANCE_API', 'L48AM3ytDBa3QUfW9qeLZj5X9xTJK8GK80Vc9fR4ml2Eo8QNRcjNdKisiz6EWj8F'),
    'BINANCE_SECRET': os.getenv('BINANCE_SECRET', 'EESYNU9Y4vwjHomlcGxglc25cvTpHU9jom88E2shCMW6q4xQyRCS833sBr26fORT'),
    'GEMINI_KEY': os.getenv('GEMINI_API_KEY', 'AIzaSyA8v-Q10qakjCIrDRxaIPyWqTxVvw9sDoA'),
    'GH_TOKEN': os.getenv('GH_TOKEN', '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'),
    'GH_REPO': 'Kyawphyowaipro/my_crypto_bot', # မင်းရဲ့ GitHub Repo နာမည် ပြောင်းပေးပါ
    'SYMBOL': ['SOL/USDT', 'CAKE/USDT', 'LTC/USDT'],
    'LEVERAGE': 20,
    'IS_RUNNING': True
}

TELEGRAM_TOKEN = '7932915582:AAHT3p1J1gySMeWI5lJfVC2-hjqOR_KrgJ4'
CHAT_ID = '5020993606'

# Gemini AI Setup with Expert Trinity Persona
SYSTEM_PROMPT = """You are a Hybrid Expert: 
1. Senior Crypto Trader (TA & Psychology)
2. Professional Developer (Python & CCXT)
3. Finance Advisor (Risk Management)
Answer concisely in Burmese or English. Use your expert knowledge to guide the user."""

try:
    genai.configure(api_key=config['GEMINI_KEY'])
    ai_model = genai.GenerativeModel('gemini-1.5-flash', system_instruction=SYSTEM_PROMPT)
except Exception as e:
    print(f"Gemini AI Error: {e}")
    ai_model = None

app = Flask('')
@app.route('/')
def home(): return "Expert Bot is Running!"

def send_telegram(msg, reply_markup=None):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        payload = {'chat_id': CHAT_ID, 'text': msg, 'parse_mode': 'HTML'}
        if reply_markup: payload['reply_markup'] = json.dumps(reply_markup)
        requests.post(url, json=payload)
    except: pass

def get_buttons():
    return {"inline_keyboard": [[{"text": "📊 Status", "callback_data": "st"}, {"text": "🚀 Start", "callback_data": "on"}],
                                [{"text": "🛑 Stop", "callback_data": "off"}]]}

# --- [ GITHUB REMOTE EDIT ] ---
def update_github(file_path, content):
    try:
        url = f"https://api.github.com/repos/{config['GH_REPO']}/contents/{file_path}"
        headers = {"Authorization": f"token {config['GH_TOKEN']}", "Accept": "application/vnd.github.v3+json"}
        res = requests.get(url, headers=headers).json()
        sha = res.get('sha')
        data = {"message": "Update via Bot", "content": base64.b64encode(content.encode()).decode(), "sha": sha}
        return requests.put(url, headers=headers, json=data).status_code == 200
    except: return False

# --- [ CONTROL CENTER ] ---
def handle_telegram():
    last_id = 0
    while True:
        try:
            updates = requests.get(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getUpdates", params={'offset': last_id+1, 'timeout': 30}).json()
            for up in updates.get('result', []):
                last_id = up['update_id']
                if 'callback_query' in up:
                    cmd = up['callback_query']['data']
                    if cmd == "st": send_telegram(f"⚙️ Running: {config['IS_RUNNING']}\nLev: {config['LEVERAGE']}x", get_buttons())
                    elif cmd == "on": config['IS_RUNNING'] = True; send_telegram("▶️ Bot Started.")
                    elif cmd == "off": config['IS_RUNNING'] = False; send_telegram("🛑 Bot Stopped.")
                elif 'message' in up:
                    text = up['message'].get('text', '')
                    if text.startswith('/edit'):
                        parts = text.split(' ', 2)
                        if len(parts) == 3 and update_github(parts[1], parts[2]): send_telegram("✅ GitHub Updated!")
                    elif ai_model:
                        res = ai_model.generate_content(text)
                        send_telegram(f"🎓 <b>Expert Insight:</b>\n\n{res.text}")
        except: time.sleep(5)

# --- [ TRADING LOGIC: 1H-15M-5M ] ---
def trade_logic():
    try:
        ex = ccxt.binance({'apiKey': config['BINANCE_API'], 'secret': config['BINANCE_SECRET'], 'enableRateLimit': True, 'options': {'defaultType': 'future'}})
        if config['MODE'] == 'DEMO': ex.set_sandbox_mode(True)
    except: return

    last_h = 0
    while True:
        if not config['IS_RUNNING']: time.sleep(30); continue
        
        # 15-Min Health Check
        if time.time() - last_h > 900:
            status = "🟢 <b>Health Check</b>\n"
            for s in config['SYMBOL']:
                try:
                    p = ex.fetch_ohlcv(s, '1h', limit=200)
                    ema = pd.DataFrame(p)[4].ewm(span=200).mean().iloc[-1]
                    status += f"• {s}: {'📈 UP' if p[-1][4] > ema else '📉 DOWN'}\n"
                except: pass
            send_telegram(status); last_h = time.time()

        for s in config['SYMBOL']:
            try:
                # Triple Confirmation Logic
                p1h = ex.fetch_ohlcv(s, '1h', limit=200)
                ema200 = pd.DataFrame(p1h)[4].ewm(span=200).mean().iloc[-1]
                p15 = ex.fetch_ohlcv(s, '15m', limit=2)
                p5 = pd.DataFrame(ex.fetch_ohlcv(s, '5m', limit=10), columns=['t','o','h','l','c','v'])
                
                bull = p5.iloc[-1]['c'] > p5.iloc[-1]['o'] and p5.iloc[-2]['c'] < p5.iloc[-2]['o']
                if bull and p15[-1][4] > ema200:
                    send_telegram(f"🚀 <b>LONG Entry: {s}</b>\nLeverage: {config['LEVERAGE']}x")
            except: pass
        time.sleep(60)

if __name__ == "__main__":
    Thread(target=handle_telegram).start()
    port = int(os.environ.get("PORT", 10000))
    # Flask ကို Thread ထဲမထည့်ဘဲ ပင်မ Thread မှာ Run မှ Render က Port ကို ရှာတွေ့မှာဖြစ်ပါတယ်
    Thread(target=trade_logic).start()
    app.run(host='0.0.0.0', port=port)
