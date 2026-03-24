import ccxt, pandas as pd, time, os, requests, json, base64
import google.generativeai as genai
from flask import Flask
from threading import Thread

# --- [ CONFIGURATION ] ---
config = {
    'BINANCE_API': os.getenv('BINANCE_API'),
    'BINANCE_SECRET': os.getenv('BINANCE_SECRET'),
    'GEMINI_KEY': os.getenv('GEMINI_API_KEY'),
    'TELEGRAM_TOKEN': os.getenv('TELEGRAM_TOKEN'),
    'GH_TOKEN': os.getenv('GH_TOKEN'),
    'GH_REPO': 'Kyawphyowaipro/my_crypto_bot', # မင်းရဲ့ Repo နာမည် အမှန်
    'SYMBOL': ['SOL/USDT', 'CAKE/USDT', 'LTC/USDT'],
    'LEVERAGE': 20,
    'IS_RUNNING': True
}

CHAT_ID = 'မင်းရဲ့_Telegram_ID' 

# --- [ AI SETUP ] ---
SYSTEM_PROMPT = "You are a Trinity Expert AI (Trader, Dev, Finance Advisor). Help the user professionally."
genai.configure(api_key=config['GEMINI_KEY'])
ai_model = genai.GenerativeModel('gemini-1.5-flash', system_instruction=SYSTEM_PROMPT)

app = Flask('')
@app.route('/')
def home(): return "Bot is Online with GitHub Sync!"

# --- [ GITHUB EDIT FUNCTION ] ---
def update_github(file_path, content):
    try:
        url = f"https://api.github.com/repos/{config['GH_REPO']}/contents/{file_path}"
        headers = {"Authorization": f"token {config['GH_TOKEN']}", "Accept": "application/vnd.github.v3+json"}
        res = requests.get(url, headers=headers).json()
        sha = res.get('sha')
        data = {"message": "Update via Bot", "content": base64.b64encode(content.encode()).decode(), "sha": sha}
        return requests.put(url, headers=headers, json=data).status_code == 200
    except: return False

def send_telegram(msg, markup=None):
    url = f"https://api.telegram.org/bot{config['TELEGRAM_TOKEN']}/sendMessage"
    payload = {'chat_id': CHAT_ID, 'text': msg, 'parse_mode': 'HTML'}
    if markup: payload['reply_markup'] = json.dumps(markup)
    requests.post(url, json=payload)

def handle_telegram():
    last_id = 0
    while True:
        try:
            url = f"https://api.telegram.org/bot{config['TELEGRAM_TOKEN']}/getUpdates"
            res = requests.get(url, params={'offset': last_id+1, 'timeout': 30}).json()
            for up in res.get('result', []):
                last_id = up['update_id']
                if 'message' in up:
                    text = up['message'].get('text', '')
                    if text.startswith('/edit'):
                        parts = text.split(' ', 2)
                        if len(parts) == 3 and update_github(parts[1], parts[2]):
                            send_telegram(f"✅ GitHub: {parts[1]} updated!")
                        else:
                            send_telegram("❌ Update failed.")
                    elif ai_model:
                        response = ai_model.generate_content(text)
                        send_telegram(f"🎓 <b>Expert Insight:</b>\n\n{response.text}")
        except: time.sleep(5)

if __name__ == "__main__":
    Thread(target=handle_telegram).start()
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
