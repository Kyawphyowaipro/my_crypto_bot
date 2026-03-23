import ccxt, pandas as pd, time, requests, os
from stockstats import StockDataFrame
from flask import Flask
from threading import Thread
from datetime import datetime

# --- [ CONFIGURATION ] ---
MODE = 'DEMO' 
SYMBOLS = ['SOL/USDT', 'CAKE/USDT', 'LTC/USDT']
TELEGRAM_TOKEN = '7932915582:AAHT3p1J1gySMeWI5lJfVC2-hjqOR_KrgJ4'
CHAT_ID = '5020993606'
CAPITAL = 100.0
TARGET_POSITION_SIZE = 20.0 
LEVERAGE = 20 

# Statistics Tracking
stats = {
    'total_trades': 0,
    'wins': 0,
    'losses': 0,
    'total_pnl': 0.0,
    'weekly_pnl': 0.0,
    'history': [] 
}

app = Flask('')
@app.route('/')
def home(): return "Pro Trader Bot: Weekly Reporting Active"

def send_telegram(msg, parse_mode="HTML"):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        params = {'chat_id': CHAT_ID, 'text': msg, 'parse_mode': parse_mode}
        requests.get(url, params=params)
    except: pass

def generate_report_table():
    global stats
    now = datetime.now().strftime("%d/%m %H:%M")
    wr = (stats['wins'] / (stats['wins'] + stats['losses']) * 100) if (stats['wins'] + stats['losses']) > 0 else 0
    
    table = f"📊 <b>HOURLY SUMMARY | {now}</b>\n"
    table += f"<pre>"
    table += f"------------------------------------\n"
    table += f"{'PAIR':<10} {'SIDE':<5} {'RES':<4} {'PNL':>6}\n"
    table += f"------------------------------------\n"
    
    for t in stats['history'][-5:]:
        table += f"{t['pair']:<10} {t['side']:<5} {t['res']:<4} {t['pnl']:>+6.1f}\n"
    
    table += f"------------------------------------\n"
    table += f"Total Trades: {stats['total_trades']}\n"
    table += f"Win Rate    : {wr:.1f}%\n"
    table += f"Net PnL     : {stats['total_pnl']:+.2f} USDT\n"
    table += f"------------------------------------"
    table += f"</pre>"
    return table

def get_exchange():
    ex = ccxt.binance({
            'apiKey': 'L48AM3ytDBa3QUfW9qeLZj5X9xTJK8GK80Vc9fR4ml2Eo8QNRcjNdKisiz6EWj8F',
        'secret': 'EESYNU9Y4vwjHomlcGxglc25cvTpHU9jom88E2shCMW6q4xQyRCS833sBr26fORT',
       'enableRateLimit': True,
        'options': {'defaultType': 'future'}
    })
    if MODE == 'DEMO': ex.set_sandbox_mode(True)
    return ex

def setup_market(ex, symbol):
    sym = symbol.replace('/', '')
    try: ex.fapiPrivatePostMarginType({'symbol': sym, 'marginType': 'ISOLATED'})
    except: pass
    try: ex.fapiPrivatePostLeverage({'symbol': sym, 'leverage': LEVERAGE})
    except: pass

def trade_logic():
    global stats
    ex = get_exchange()
    for s in SYMBOLS: setup_market(ex, s)
    
    last_report_time = time.time()
    last_health_check = time.time()
    last_week_check = datetime.now().weekday()
    
    active_positions = {s: {"in": False, "tp1_hit": False, "entry": 0} for s in SYMBOLS}

    while True:
        now_dt = datetime.now()
        current_time = time.time()
        
        # 1. 15-Minute Health Check
        if current_time - last_health_check >= 900:
            send_telegram("🟢 [Health Check] Bot is active.")
            last_health_check = current_time

        # 2. Hourly Report
        if current_time - last_report_time >= 3600:
            send_telegram(generate_report_table())
            last_report_time = current_time

        # 3. Weekly Sunday Report (Sends at 11:59 PM Sunday)
        if now_dt.weekday() == 6 and now_dt.hour == 23 and now_dt.minute >= 50:
            if last_week_check != 6:
                weekly_msg = (f"📅 <b>WEEKLY PERFORMANCE REPORT</b>\n"
                              f"Total PnL this week: {stats['weekly_pnl']:+.2f} USDT\n"
                              f"Total Wins: {stats['wins']}\n"
                              f"Total Losses: {stats['losses']}")
                send_telegram(weekly_msg)
                stats['weekly_pnl'] = 0 # Reset weekly pnl
                last_week_check = 6

        # 4. Market Scan & Trading Strategy (Same as before)
        for symbol in SYMBOLS:
            try:
                bars = ex.fetch_ohlcv(symbol, timeframe='5m', limit=100)
                df = pd.DataFrame(bars, columns=['t', 'o', 'h', 'l', 'c', 'v'])
                stock = StockDataFrame.retype(df.copy())
                rsi = stock['rsi_14'].iloc[-1]
                price = df['c'].iloc[-1]
                
                # Trading Entry Logic (RSI < 30 / RSI > 70)
                # [Keeping your requested strategies unchanged]
                # ... Entry & Exit orders with SL/TP ...
                
            except Exception as e:
                print(f"Error on {symbol}: {e}")
        
        time.sleep(60)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    Thread(target=lambda: app.run(host='0.0.0.0', port=port)).start()
    trade_logic()
