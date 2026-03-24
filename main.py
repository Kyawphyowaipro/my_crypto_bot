import ccxt, pandas as pd, time, os, pytz, requests, json
from datetime import datetime
from flask import Flask
from threading import Thread

# --- [ GLOBAL CONFIGURATION ] ---
# Telegram ကနေ ပြင်လို့ရမယ့် Settings များ
config = {
    'MODE': 'DEMO', # 'REAL' or 'DEMO'
    'SYMBOLS': ['SOL/USDT', 'CAKE/USDT', 'LTC/USDT'],
    'LEVERAGE': 20,
    'IS_RUNNING': True,
    'CAPITAL': 100.0,
    'POSITION_SIZE': 20.0
}

TELEGRAM_TOKEN = '7932915582:AAHT3p1J1gySMeWI5lJfVC2-hjqOR_KrgJ4'
CHAT_ID = '5020993606'
stats = {'total_trades': 0, 'wins': 0, 'losses': 0, 'total_pnl': 0.0, 'history': []}

app = Flask('')
@app.route('/')
def home(): return "Pro Trader Bot with Remote Control is Online!"

def send_telegram(msg, parse_mode="HTML"):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        params = {'chat_id': CHAT_ID, 'text': msg, 'parse_mode': parse_mode}
        requests.get(url, params=params)
    except: pass

# --- [ TELEGRAM INTERACTION (Remote Control) ] ---

def handle_telegram_commands():
    """Gemini လိုမျိုး Telegram ကနေ Command တွေနဲ့ Bot ကို ထိန်းချုပ်ခြင်း"""
    last_update_id = 0
    while True:
        try:
            url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getUpdates"
            params = {'offset': last_update_id + 1, 'timeout': 30}
            response = requests.get(url, params=params).json()
            
            for update in response.get('result', []):
                last_update_id = update['update_id']
                message = update.get('message', {})
                sender_id = str(message.get('from', {}).get('id'))
                text = message.get('text', '')

                # Security: မင်းဆီကလာတဲ့ စာမှသာ လက်ခံမည်
                if sender_id != CHAT_ID: continue

                if text == '/status':
                    msg = f"⚙️ <b>Current Bot Settings:</b>\n"
                    msg += f"Running: {'✅ ON' if config['IS_RUNNING'] else '🛑 PAUSED'}\n"
                    msg += f"Leverage: {config['LEVERAGE']}x\n"
                    msg += f"Mode: {config['MODE']}\n"
                    msg += f"Symbols: {config['SYMBOLS']}"
                    send_telegram(msg)

                elif text.startswith('/set_lev'):
                    try:
                        new_lev = int(text.split(' ')[1])
                        config['LEVERAGE'] = new_lev
                        send_telegram(f"✅ Leverage updated to {new_lev}x")
                    except: send_telegram("❌ Error: Use /set_lev 10")

                elif text == '/stop':
                    config['IS_RUNNING'] = False
                    send_telegram("🛑 Bot has been Paused. No new trades will open.")

                elif text == '/start':
                    config['IS_RUNNING'] = True
                    send_telegram("▶️ Bot Resumed. Scanning market...")

        except Exception as e: print(f"Telegram Controller Error: {e}")
        time.sleep(3)

# --- [ TRADING LOGIC & STRATEGY ] ---

def is_news_time():
    now_gmt = datetime.now(pytz.timezone('GMT'))
    return (12 <= now_gmt.hour <= 14) or (18 <= now_gmt.hour <= 20)

def get_pivot_points(ex, symbol):
    bars = ex.fetch_ohlcv(symbol, timeframe='1d', limit=15)
    df = pd.DataFrame(bars, columns=['t','o','h','l','c','v'])
    last = df.iloc[-1]
    pp = (last['h'] + last['l'] + last['c']) / 3
    return {'PP': pp, 'S1': (2*pp)-last['h'], 'R1': (2*pp)-last['l']}

def is_engulfing(df):
    curr, prev = df.iloc[-1], df.iloc[-2]
    if curr['c'] > curr['o'] and prev['c'] < prev['o'] and curr['c'] >= prev['o']: return "BULLISH"
    if curr['c'] < curr['o'] and prev['c'] > prev['o'] and curr['c'] <= prev['o']: return "BEARISH"
    return None

def trade_logic():
    ex = ccxt.binance({'apiKey': 'L48AM3ytDBa3QUfW9qeLZj5X9xTJK8GK80Vc9fR4ml2Eo8QNRcjNdKisiz6EWj8F', 'secret': 'EESYNU9Y4vwjHomlcGxglc25cvTpHU9jom88E2shCMW6q4xQyRCS833sBr26fORT', 'enableRateLimit': True, 'options': {'defaultType': 'future'}})
    if config['MODE'] == 'DEMO': ex.set_sandbox_mode(True)
    
    last_health = time.time()
    last_pause_reason = ""

    while True:
        if not config['IS_RUNNING']:
            time.sleep(10); continue

        # News Filter with Notification
        if is_news_time():
            if last_pause_reason != "NEWS":
                send_telegram("⚠️ <b>Bot Paused: News Volatility Time.</b>")
                last_pause_reason = "NEWS"
            time.sleep(600); continue
        
        if last_pause_reason != "":
            send_telegram("▶️ <b>Bot Resumed: Stable Market.</b>")
            last_pause_reason = ""

        # 15-Min Detailed Health Check
        if time.time() - last_health > 900:
            status_msg = "🟢 <b>[Health Check] Bot Active</b>\n"
            for s in config['SYMBOLS']:
                try:
                    bars_h = ex.fetch_ohlcv(s, timeframe='1h', limit=200)
                    ema200 = pd.DataFrame(bars_h)[4].ewm(span=200).mean().iloc[-1]
                    trend = "📈 UP" if bars_h[-1][4] > ema200 else "📉 DOWN"
                    status_msg += f"• {s}: {trend}\n"
                except: status_msg += f"• {s}: ⚠️ Sync Error\n"
            send_telegram(status_msg)
            last_health = time.time()

        # Market Scan
        for symbol in config['SYMBOLS']:
            try:
                # Triple Confirmation Logic
                bars_1h = ex.fetch_ohlcv(symbol, timeframe='1h', limit=200)
                ema200 = pd.DataFrame(bars_1h)[4].ewm(span=200).mean().iloc[-1]
                
                df_5m = pd.DataFrame(ex.fetch_ohlcv(symbol, timeframe='5m', limit=50), columns=['t','o','h','l','c','v'])
                price = df_5m['c'].iloc[-1]
                pivots = get_pivot_points(ex, symbol)
                pattern = is_engulfing(df_5m)
                vol_spike = df_5m['v'].iloc[-1] > (df_5m['v'].tail(20).mean() * 1.5)

                if pattern == "BULLISH" and price > ema200 and price > pivots['PP'] and vol_spike:
                    send_telegram(f"🚀 <b>LONG Entry: {symbol}</b>\nLeverage: {config['LEVERAGE']}x\nTrend: UP")
                    # [Order Execution Here]
                
                elif pattern == "BEARISH" and price < ema200 and price < pivots['PP'] and vol_spike:
                    send_telegram(f"📉 <b>SHORT Entry: {symbol}</b>\nLeverage: {config['LEVERAGE']}x\nTrend: DOWN")
                    # [Order Execution Here]

            except Exception as e: print(f"Error: {e}")
        time.sleep(60)

if __name__ == "__main__":
    # Remote Control Thread
    Thread(target=handle_telegram_commands).start()
    
    # Flask Web Server Thread (Render Fix)
    port = int(os.environ.get("PORT", 10000))
    Thread(target=lambda: app.run(host='0.0.0.0', port=port)).start()
    
    print(f"✅ Pro Bot starting on port {port}")
    trade_logic()
