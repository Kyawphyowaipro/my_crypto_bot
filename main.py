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
    'AI_MODE': False,
    'TRADES_LOG': []
}

# --- [ ၂။ STABLE AI ADVISOR ] ---
def get_ai_insight(text):
    if not config['GEMINI_KEY']: return "⚠️ Gemini API Key missing in Render."
    try:
        genai.configure(api_key=config['GEMINI_KEY'])
        model = genai.GenerativeModel('gemini-2.0-flash')
        # AI ကို ပိုမိုမြန်ဆန်စေရန် system prompt အတိုပဲ သုံးထားသည်
        response = model.generate_content(f"Trader Advisor: {text}")
        return response.text
    except Exception as e:
        return f"❌ AI Error: {str(e)[:40]}"

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
                        except Exception as e:
                            send_telegram(f"❌ API Error: {str(e)[:60]}")
                    elif cmd == "st": send_telegram("⚙️ <b>Dashboard Active</b>", get_menu())
                    elif cmd == "tg_ai": 
                        config['AI_MODE'] = not config['AI_MODE']
                        send_telegram(f"AI Mode: {'ON' if config['AI_MODE'] else 'OFF'}", get_menu())
                    elif cmd == "on": config['IS_RUNNING'] = True; send_telegram("▶️ Bot Started.")
                    elif cmd == "off": config['IS_RUNNING'] = False; send_telegram("🛑 Bot Stopped.")

                elif 'message' in up:
                    msg = up['message']; text = msg.get('text', '')
                    if str(msg['from']['id']) == str(config['CHAT_ID']):
                        if text == "/start": send_telegram("🎓 <b>Trinity Professional Bot</b>", get_menu())
                        elif config['AI_MODE']: send_telegram(f"🎓 <b>Advisor:</b>\n\n{get_ai_insight(text)}")
        except: time.sleep(5)

# --- [ ၅။ TRADING ENGINE ] ---
def trading_engine():
    while True:
        if not config['IS_RUNNING']: time.sleep(10); continue
        # Your SMC + ATR Strategy logic here
        time.sleep(30)

# --- [ ၆။ RENDER PORT FIX & FLASK ] ---
app = Flask('')
@app.route('/')
def home(): return "Bot is Online."

if __name__ == "__main__":
    # Thread များကို daemon=True ဖြင့် Background မှာ ပို့ထားမည်
    Thread(target=handle_telegram, daemon=True).start()
    Thread(target=trading_engine, daemon=True).start()
    
    # Render အိပ်မပျော်စေရန် Main Thread တွင် Flask ကို Port 10000 ဖြင့် run မည်
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
