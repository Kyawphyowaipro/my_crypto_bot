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
    'CHAT_ID': os.getenv('TELEGRAM_CHAT_ID'),
    'GH_TOKEN': os.getenv('GH_TOKEN'),
    'GH_REPO': 'Kyawphyowaipro/my_crypto_bot',
    'SYMBOL': ['SOL/USDT', 'CAKE/USDT', 'LTC/USDT'],
    'LEVERAGE': 20,
    'IS_RUNNING': True,
    'INITIAL_DEPOSIT': 0.0,
    'AI_MODE': False # AI နှင့် စကားပြောရန် Mode
}

# --- [ AI SETUP ] ---
SYSTEM_PROMPT = "You are a Trinity Expert AI (Trader, Dev, Finance Advisor). Provide professional advice in Burmese."
try:
    if config['GEMINI_KEY']:
        genai.configure(api_key=config['GEMINI_KEY'])
        ai_model = genai.GenerativeModel('gemini-1.5-flash', system_instruction=SYSTEM_PROMPT)
    else: ai_model = None
except: ai_model = None

app = Flask('')
@app.route('/')
def home(): return "Bot is Online and Healthy!"

# --- [ GITHUB EDIT LOGIC ] ---
def update_github(file_path, content):
    try:
        url = f"https://api.github.com/repos/{config['GH_REPO']}/contents/{file_path}"
        headers = {"Authorization": f"token {config['GH_TOKEN']}", "Accept": "application/vnd.github.v3+json"}
        res = requests.get(url, headers=headers).json()
        sha = res.get('sha')
        encoded_content = base64.b64encode(content.encode()).decode()
        data = {"message": "Update via Telegram Bot", "content": encoded_content, "sha": sha}
        return requests.put(url, headers=headers, json=data).status_code == 200
    except: return False

# --- [ BINANCE TOOLS ] ---
def get_balance():
    try:
        ex = ccxt.binance({'apiKey': config['BINANCE_API'], 'secret': config['BINANCE_SECRET'], 'options': {'defaultType': 'future'}})
        bal = ex.fetch_balance()
        return float(bal['total']['USDT'])
    except Exception as e: return f"Error: {str(e)[:30]}"

# --- [ MONITORING LOGIC (70% Loss Alert) ] ---
def monitor_account():
    alert_sent = False
    while True:
        try:
            if config['INITIAL_DEPOSIT'] > 0:
                current_bal = get_balance()
                if isinstance(current_bal, float):
                    if current_bal <= (config['INITIAL_DEPOSIT'] * 0.3) and not alert_sent:
                        send_telegram(f"🚨 <b>Alert!</b> 70% Loss ဖြစ်သွားပါပြီ။ Balance: ${current_bal:.2f}")
                        config['IS_RUNNING'] = False
                        alert_sent = True
                    elif current_bal > (config['INITIAL_DEPOSIT'] * 0.3): alert_sent = False
        except: pass
        time.sleep(300)

# --- [ TELEGRAM CONTROLLER ] ---
def send_telegram(msg, markup=None):
    if not config['CHAT_ID']: return
    url = f"https://api.telegram.org/bot{config['TELEGRAM_TOKEN']}/sendMessage"
    payload = {'chat_id': config['CHAT_ID'], 'text': msg, 'parse_mode': 'HTML'}
    if markup: payload['reply_markup'] = json.dumps(markup)
    try: requests.post(url, json=payload, timeout=10)
    except: pass

def get_buttons():
    # AI Mode အပေါ်မူတည်ပြီး Button နာမည်ပြောင်းပေးပါမယ်
    ai_btn_text = "🤖 AI Mode: ON" if config['AI_MODE'] else "🎓 Talk to AI"
    return {"inline_keyboard": [
        [{"text": "📊 Status", "callback_data": "st"}, {"text": "💰 Balance", "callback_data": "bal"}],
        [{"text": ai_btn_text, "callback_data": "ai_toggle"}],
        [{"text": "🚀 Start Bot", "callback_data": "on"}, {"text": "🛑 Stop Bot", "callback_data": "off"}]
    ]}

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
                    if cmd == "bal": send_telegram(f"💰 Balance: {get_balance()} USDT")
                    elif cmd == "st": send_telegram(f"⚙️ Status: {'ON' if config['IS_RUNNING'] else 'OFF'}\n🤖 AI: {'Enabled' if config['AI_MODE'] else 'Disabled'}", get_buttons())
                    elif cmd == "on": config['IS_RUNNING'] = True; send_telegram("▶️ Bot Started.")
                    elif cmd == "off": config['IS_RUNNING'] = False; send_telegram("🛑 Bot Stopped.")
                    elif cmd == "ai_toggle":
                        config['AI_MODE'] = not config['AI_MODE']
                        status = "ပိတ်" if not config['AI_MODE'] else "ဖွင့်"
                        send_telegram(f"🤖 AI Chat Mode ကို {status}လိုက်ပါပြီ။", get_buttons())

                elif 'message' in up:
                    msg = up['message']
                    text = msg.get('text', '')
                    if str(msg['from']['id']) != str(config['CHAT_ID']): continue

                    if text == "/start":
                        send_telegram("🎓 Trinity Expert AI အဆင်သင့်ရှိပါသည်။", get_buttons())
                    elif text.startswith('/edit'):
                        parts = text.split(' ', 2)
                        if update_github(parts[1], parts[2]): send_telegram(f"✅ {parts[1]} Updated!")
                        else: send_telegram("❌ Update failed.")
                    elif text.startswith('/deposit'):
                        try:
                            config['INITIAL_DEPOSIT'] = float(text.split(' ')[1])
                            send_telegram(f"✅ Deposit ${config['INITIAL_DEPOSIT']} သတ်မှတ်ပြီး။")
                        except: send_telegram("Format: /deposit 100")
                    elif config['AI_MODE'] and ai_model:
                        response = ai_model.generate_content(text)
                        send_telegram(f"🎓 <b>AI Insight:</b>\n\n{response.text}")
        except: time.sleep(5)

if __name__ == "__main__":
    Thread(target=handle_telegram).start()
    Thread(target=monitor_account).start()
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
