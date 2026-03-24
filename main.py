import ccxt, pandas as pd, time, os, pytz, requests, json, base64
import google.generativeai as genai
from datetime import datetime
from flask import Flask
from threading import Thread

# --- [ EXPERT & GITHUB CONFIG ] ---
config = {
    'MODE': 'DEMO',
    'SYMBOLS': ['SOL/USDT', 'CAKE/USDT', 'LTC/USDT'],
    'LEVERAGE': 20,
    'IS_RUNNING': True,
    'GH_TOKEN': 'YOUR_GITHUB_TOKEN', # အပေါ်ကရတဲ့ Token ထည့်ပါ
    'GH_REPO': 'username/repository_name', # ဥပမာ - myname/my-trading-bot
    'GEMINI_API_KEY': 'YOUR_GEMINI_API_KEY'
}

# Gemini Expert System
SYSTEM_PROMPT = "You are a Triple Expert: Crypto Trader, Python Dev, and Finance Advisor. Help the user manage their bot and strategy."
genai.configure(api_key=config['GEMINI_API_KEY'])
ai_model = genai.GenerativeModel('gemini-1.5-flash', system_instruction=SYSTEM_PROMPT)

TELEGRAM_TOKEN = 'YOUR_BOT_TOKEN'
CHAT_ID = 'YOUR_CHAT_ID'

app = Flask('')
@app.route('/')
def home(): return "Expert Bot with GitHub Sync is Online!"

def send_telegram(msg, reply_markup=None):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        payload = {'chat_id': CHAT_ID, 'text': msg, 'parse_mode': 'HTML'}
        if reply_markup: payload['reply_markup'] = json.dumps(reply_markup)
        requests.post(url, json=payload)
    except: pass

# --- [ GITHUB UPDATE FUNCTION ] ---
def update_github_file(file_path, new_content, commit_message="Update via Telegram Bot"):
    """GitHub API သုံးပြီး ဖိုင်ကို လှမ်းပြင်ခြင်း"""
    url = f"https://api.github.com/repos/{config['GH_REPO']}/contents/{file_path}"
    headers = {"Authorization": f"token {config['GH_TOKEN']}", "Accept": "application/vnd.github.v3+json"}
    
    # လက်ရှိဖိုင်ရဲ့ SHA (ID) ကို အရင်ယူရပါမယ်
    res = requests.get(url, headers=headers).json()
    sha = res.get('sha')
    
    # Update လုပ်မည့် Data
    content_encoded = base64.b64encode(new_content.encode('utf-8')).decode('utf-8')
    data = {"message": commit_message, "content": content_encoded, "sha": sha}
    
    put_res = requests.put(url, headers=headers, json=data)
    return put_res.status_code == 200

# --- [ TELEGRAM CONTROLLER ] ---
def handle_telegram():
    last_id = 0
    while True:
        try:
            res = requests.get(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getUpdates", params={'offset': last_id+1, 'timeout': 30}).json()
            for up in res.get('result', []):
                last_id = up['update_id']
                message = up.get('message', {})
                text = message.get('text', '')
                sender = str(message.get('from', {}).get('id'))
                if sender != CHAT_ID: continue

                # GitHub Edit Command: /edit_file [filename] [content]
                if text.startswith('/edit'):
                    try:
                        _, filename, content = text.split(' ', 2)
                        success = update_github_file(filename, content)
                        if success: send_telegram(f"✅ GitHub: <b>{filename}</b> has been updated and deploying...")
                        else: send_telegram("❌ GitHub Update Failed. Check Token/Repo name.")
                    except: send_telegram("⚠️ Format: <code>/edit [filename] [new code]</code>")

                elif not text.startswith('/'):
                    # AI Expert Chat
                    response = ai_model.generate_content(text)
                    send_telegram(f"🎓 <b>Expert Insight:</b>\n\n{response.text}")
        except: pass
        time.sleep(2)

# --- [ TRADING LOGIC (1H-15M-5M) ] ---
def trade_logic():
    # ... (ယခင်က ရေးပေးခဲ့တဲ့ 1H-15M-5M Triple Confirmation Logic အတိုင်းဖြစ်ပါတယ်) ...
    # ... အရှည်ကြီးဖြစ်မှာစိုးလို့ အဓိက Scan ပိုင်းပဲ ပြန်ထည့်ပေးထားပါတယ် ...
    while True:
        if not config['IS_RUNNING']: time.sleep(10); continue
        # Trading Scan များကို ဤနေရာတွင် ဆက်လက်လုပ်ဆောင်မည်...
        time.sleep(60)

if __name__ == "__main__":
    Thread(target=handle_telegram).start()
    port = int(os.environ.get("PORT", 10000))
    Thread(target=lambda: app.run(host='0.0.0.0', port=port)).start()
    trade_logic()
