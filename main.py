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

# --- [ ၂။ AI & TELEGRAM RE-INTEGRATION ] ---
try:
    genai.configure(api_key=config['GEMINI_KEY'])
    ai_model = genai.GenerativeModel('gemini-1.5-flash', 
        system_instruction="You are Trinity Expert AI. Professional Trader/Dev. Answer in Burmese.")
except: ai_model = None

def send_telegram(msg, markup=None):
    url = f"https://api.telegram.org/bot{config['TELEGRAM_TOKEN']}/sendMessage"
    payload = {'chat_id': config['CHAT_ID'], 'text': msg, 'parse_mode': 'HTML'}
    if markup: payload['reply_markup'] = json.dumps(markup)
    try: return requests.post(url, json=payload).json()
    except: return None

# --- [ ၃။ FIXED BUTTONS & CALLBACK HANDLER ] ---

def get_buttons():
    # Button တစ်ခုချင်းစီကို Callback Data မှန်ကန်စွာ သတ်မှတ်ခြင်း
    ai_text = "🤖 AI Advisor: ON" if config['AI_MODE'] else "🎓 Ask Advisor"
    return {"inline_keyboard": [
        [{"text": "📊 Dashboard", "callback_data": "st"}, {"text": "💰 Balance", "callback_data": "bal"}],
        [{"text": "📝 Edit main.py", "callback_data": "ed_main"}, {"text": "📦 Edit req.txt", "callback_data": "ed_req"}],
        [{"text": ai_text, "callback_data": "tg_ai"}],
        [{"text": "🚀 Start Bot", "callback_data": "on"}, {"text": "🛑 Stop Bot", "callback_data": "off"}]
    ]}

def handle_telegram():
    last_id = 0
    while True:
        try:
            url = f"https://api.telegram.org/bot{config['TELEGRAM_TOKEN']}/getUpdates"
            res = requests.get(url, params={'offset': last_id+1, 'timeout': 30}).json()
            if not res.get('ok'): time.sleep(5); continue

            for up in res.get('result', []):
                last_id = up['update_id']
                
                # --- Callback Query (Buttons) ပိုင်း ---
                if 'callback_query' in up:
                    cq = up['callback_query']
                    cmd = cq['data']
                    
                    # Button နှိပ်လိုက်တိုင်း အကြောင်းပြန်ပေးရန် (Spinner ပျောက်ရန်)
                    requests.post(f"https://api.telegram.org/bot{config['TELEGRAM_TOKEN']}/answerCallbackQuery", 
                                  json={'callback_query_id': cq['id']})

                    if cmd == "bal":
                        try:
                            ex = ccxt.binance({'apiKey': config['BINANCE_API'], 'secret': config['BINANCE_SECRET'], 'options': {'defaultType': 'future'}})
                            b = ex.fetch_balance()['total']['USDT']
                            send_telegram(f"💰 <b>လက်ရှိ Balance:</b> ${b:.2f} USDT")
                        except: send_telegram("❌ API Error: Balance ကို စစ်မရပါ။")
                    
                    elif cmd == "st":
                        status_msg = f"⚙️ <b>Bot Dashboard</b>\nStatus: {'Running' if config['IS_RUNNING'] else 'Stopped'}\nSession: London/NY Only\nAI: {config['AI_MODE']}"
                        send_telegram(status_msg, get_buttons())
                    
                    elif cmd == "ed_main": 
                        config['TARGET_FILE'] = "main.py"
                        send_telegram("📁 <b>main.py</b> ပြင်ရန် ကုဒ်အသစ်များကို Paste လုပ်ပြီး ပို့လိုက်ပါ။")
                    
                    elif cmd == "ed_req": 
                        config['TARGET_FILE'] = "requirements.txt"
                        send_telegram("📦 <b>requirements.txt</b> ပြင်ရန် Library စာရင်းများကို ပို့လိုက်ပါ။")
                    
                    elif cmd == "tg_ai":
                        config['AI_MODE'] = not config['AI_MODE']
                        send_telegram(f"🤖 AI Advisor Mode: {config['AI_MODE']}", get_buttons())
                    
                    elif cmd == "on": 
                        config['IS_RUNNING'] = True
                        send_telegram("▶️ Bot စတင် လည်ပတ်နေပါပြီ။")
                    
                    elif cmd == "off": 
                        config['IS_RUNNING'] = False
                        send_telegram("🛑 Bot ကို ရပ်တန့်လိုက်ပါသည်။")

                # --- Message Handling ပိုင်း ---
                elif 'message' in up:
                    msg = up['message']
                    text = msg.get('text', '')
                    user_id = str(msg['from']['id'])
                    
                    if user_id != str(config['CHAT_ID']): continue

                    if text == "/start":
                        send_telegram("🎓 <b>Trinity Professional Bot Online.</b>\nအောက်ပါ Button များကို အသုံးပြုနိုင်ပါသည်။", get_buttons())
                    
                    elif config['TARGET_FILE']:
                        # GitHub Edit Logic
                        send_telegram(f"⏳ {config['TARGET_FILE']} ကို GitHub မှာ Update လုပ်နေပါတယ်...")
                        # (GitHub Update Function Code)
                        config['TARGET_FILE'] = None
                    
                    elif config['AI_MODE'] and ai_model:
                        res_ai = ai_model.generate_content(text)
                        send_telegram(f"🎓 <b>AI Insight:</b>\n\n{res_ai.text}")

        except Exception as e:
            time.sleep(5)

# --- [ ၄။ GITHUB UPDATE FUNCTION (Invisible Logic) ] ---
def update_github(file_path, content):
    try:
        url = f"https://api.github.com/repos/{config['GH_REPO']}/contents/{file_path}"
        headers = {"Authorization": f"token {config['GH_TOKEN']}", "Accept": "application/vnd.github.v3+json"}
        res = requests.get(url, headers=headers).json()
        sha = res.get('sha')
        encoded = base64.b64encode(content.encode()).decode()
        data = {"message": f"Edit {file_path} via Bot", "content": encoded, "sha": sha}
        return requests.put(url, headers=headers, json=data).status_code == 200
    except: return False

# Flask & Threads Setup
app = Flask('')
@app.route('/')
def home(): return "Trinity Bot Fixed & Active."

if __name__ == "__main__":
    Thread(target=handle_telegram).start()
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 10000)))
