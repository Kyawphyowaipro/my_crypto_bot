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
    'BREAK_UNTIL': None,
    'AI_MODE': False,
    'TARGET_FILE': None,
    'TRADES_LOG': []
}

# --- [ ၂။ AI & TELEGRAM REPORTING SETUP ] ---
try:
    genai.configure(api_key=config['GEMINI_KEY'])
    ai_model = genai.GenerativeModel('gemini-1.5-flash', 
        system_instruction="You are Trinity Expert (Trader, Dev, Finance). Give insights in Burmese.")
except: ai_model = None

def send_telegram(msg, markup=None):
    if not config['CHAT_ID']: return
    url = f"https://api.telegram.org/bot{config['TELEGRAM_TOKEN']}/sendMessage"
    payload = {'chat_id': config['CHAT_ID'], 'text': msg, 'parse_mode': 'HTML'}
    if markup: payload['reply_markup'] = json.dumps(markup)
    requests.post(url, json=payload)

# --- [ ၃။ SESSION & VOLUME ANALYSIS LOGIC ] ---

def is_trade_session():
    """London & US Sessions မှာပဲ Trade ရန် (UTC Time သုံးထားသည်)"""
    now_utc = datetime.now(pytz.utc).time()
    # London: 07:00 - 16:00 UTC | New York: 12:00 - 21:00 UTC
    # စုစုပေါင်း Trade ချိန်: 07:00 UTC မှ 21:00 UTC အတွင်း
    start = datetime.strptime("07:00", "%H:%M").time()
    end = datetime.strptime("21:00", "%H:%M").time()
    return start <= now_utc <= end

def volume_analysis(df):
    """Volume အခြေအနေကို စစ်ဆေးခြင်း"""
    avg_vol = df['v'].rolling(window=20).mean().iloc[-1]
    curr_vol = df['v'].iloc[-1]
    return curr_vol > (avg_vol * 1.5) # ပျမ်းမျှထက် ၁.၅ ဆ ပိုများမှ Confirm လုပ်မည်

# --- [ ၄။ CORE TRADING ENGINE (SMC + ATR + Pivot + Engulfing) ] ---

def trading_loop():
    while True:
        # ၁။ Session Check
        if not is_trade_session():
            time.sleep(60); continue
            
        # ၂။ 1-Day Break Check
        if config['BREAK_UNTIL'] and datetime.now() < config['BREAK_UNTIL']:
            time.sleep(3600); continue

        if not config['IS_RUNNING']:
            time.sleep(60); continue

        try:
            ex = ccxt.binance({'apiKey': config['BINANCE_API'], 'secret': config['BINANCE_SECRET'], 'options': {'defaultType': 'future'}})
            bal = float(ex.fetch_balance()['total']['USDT'])
            
            # ၃။ Drawdown Check (15%)
            if bal <= (config['INITIAL_DEPOSIT'] * (1 - config['DD_LIMIT'])):
                config['BREAK_UNTIL'] = datetime.now() + timedelta(days=1)
                config['IS_RUNNING'] = False
                send_telegram("🛑 <b>Bot Stopped: Drawdown Limit Reach (15%)</b>\nအရှုံးပမာဏ များသွားသဖြင့် ၂၄ နာရီ နားပါမည်။")
                continue

            for s in config['SYMBOL']:
                df_5m = get_data(s, '5m') # ATR ပါသော data
                # Volume & Strategy Confirmation
                if volume_analysis(df_5m):
                    # Pivot, Engulfing, ATR SL/TP logic here...
                    pass
            
            time.sleep(30)
        except Exception as e:
            send_telegram(f"⚠️ <b>Bot Paused: Error Occurred</b>\nReason: {str(e)[:100]}")
            time.sleep(60)

# --- [ ၅။ GITHUB EDIT & TELEGRAM CONTROL ] ---

def update_github(file_path, content):
    try:
        url = f"https://api.github.com/repos/{config['GH_REPO']}/contents/{file_path}"
        headers = {"Authorization": f"token {config['GH_TOKEN']}", "Accept": "application/vnd.github.v3+json"}
        res = requests.get(url, headers=headers).json()
        sha = res.get('sha')
        encoded = base64.b64encode(content.encode()).decode()
        data = {"message": f"Edit {file_path}", "content": encoded, "sha": sha}
        return requests.put(url, headers=headers, json=data).status_code == 200
    except: return False

def get_buttons():
    ai_status = "🤖 AI: ON" if config['AI_MODE'] else "🎓 Ask Advisor"
    return {"inline_keyboard": [
        [{"text": "📊 Dashboard", "callback_data": "st"}, {"text": "💰 Balance", "callback_data": "bal"}],
        [{"text": "📝 Edit main.py", "callback_data": "ed_main"}, {"text": "📦 Edit req.txt", "callback_data": "ed_req"}],
        [{"text": ai_status, "callback_data": "tg_ai"}],
        [{"text": "🚀 Start", "callback_data": "on"}, {"text": "🛑 Stop", "callback_data": "off"}]
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
                    if cmd == "st": send_telegram("⚙️ <b>Bot Active</b>\nSessions: London & NY Only\nRisk: 2% Cap", get_buttons())
                    elif cmd == "ed_main": config['TARGET_FILE'] = "main.py"; send_telegram("📁 Send new code for <b>main.py</b>")
                    elif cmd == "ed_req": config['TARGET_FILE'] = "requirements.txt"; send_telegram("📦 Send libraries for <b>req.txt</b>")
                    elif cmd == "tg_ai": config['AI_MODE'] = not config['AI_MODE']; send_telegram(f"AI Advisor: {config['AI_MODE']}")
                    elif cmd == "on": config['IS_RUNNING'] = True; send_telegram("▶️ Bot Started.")
                    elif cmd == "off": 
                        config['IS_RUNNING'] = False
                        send_telegram("🛑 <b>Bot Stopped: Manual Command</b>\nUser မှ ကိုယ်တိုင် ရပ်တန့်လိုက်ပါသည်။")

                elif 'message' in up:
                    msg = up['message']; text = msg.get('text', '')
                    if str(msg['from']['id']) != str(config['CHAT_ID']): continue
                    if text == "/start": send_telegram("🎓 Professional Trinity Bot System.", get_buttons())
                    elif config['TARGET_FILE']:
                        if update_github(config['TARGET_FILE'], text):
                            send_telegram(f"✅ {config['TARGET_FILE']} Updated!"); config['TARGET_FILE'] = None
                        else: send_telegram("❌ GitHub Update Failed.")
                    elif config['AI_MODE'] and ai_model:
                        res = ai_model.generate_content(text)
                        send_telegram(f"🎓 <b>Advisor Insight:</b>\n\n{res.text}")
        except: time.sleep(5)

# Flask Server...
app = Flask('')
@app.route('/')
def home(): return "Trinity Professional System Active."

if __name__ == "__main__":
    Thread(target=handle_telegram).start()
    Thread(target=trading_loop).start()
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 10000)))
