import ccxt, pandas as pd, time, requests, os
from stockstats import StockDataFrame
from flask import Flask
from threading import Thread

# --- [ CONFIGURATION ] ---
MODE = 'DEMO' # 'REAL' or 'DEMO'
SYMBOLS = ['SOL/USDT', 'CAKE/USDT', 'LTC/USDT']
TELEGRAM_TOKEN = '7932915582:AAHT3p1J1gySMeWI5lJfVC2-hjqOR_KrgJ4'
CHAT_ID = '5020993606'
CAPITAL = 100.0
TARGET_POSITION_SIZE = 20.0 
LEVERAGE = 20 

# Statistics Tracking
trade_history = []
wins = 0
losses = 0
total_pnl = 0.0

app = Flask('')
@app.route('/')
def home(): return "Multi-Pair Pro Bot is Live!"

def send_telegram(msg):
    try: requests.get(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage?chat_id={CHAT_ID}&text={msg}")
    except: pass

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
    global total_pnl, wins, losses
    ex = get_exchange()
    for s in SYMBOLS: setup_market(ex, s)
    
    last_report_time = time.time()
    last_health_check = time.time()

    while True:
        current_time = time.time()
        
        # 1. 15-Minute Health Check (Bot အသက်ရှင်နေကြောင်း စစ်ဆေးခြင်း)
        if current_time - last_health_check >= 900: # 15 mins
            send_telegram("🟢 [Health Check] Bot is running smoothly.")
            last_health_check = current_time

        # 2. Hourly Statistics Report (PnL, Win Rate)
        if current_time - last_report_time >= 3600: # 1 hour
            wr = (wins / (wins+losses) * 100) if (wins+losses) > 0 else 0
            report = (f"📊 --- HOURLY PERFORMANCE ---\n"
                      f"Current PnL: {total_pnl:.2f} USDT\n"
                      f"Win Rate: {wr:.1f}%\n"
                      f"Total Trades: {len(trade_history)}\n"
                      f"Active Pairs: {', '.join(SYMBOLS)}")
            send_telegram(report)
            last_report_time = current_time

        # 3. Trading Loop for each Pair
        for symbol in SYMBOLS:
            try:
                bars = ex.fetch_ohlcv(symbol, timeframe='5m', limit=100)
                df = pd.DataFrame(bars, columns=['t', 'o', 'h', 'l', 'c', 'v'])
                stock = StockDataFrame.retype(df.copy())
                rsi = stock['rsi_14'].iloc[-1]
                price = df['c'].iloc[-1]
                atr = stock['atr_14'].iloc[-1]
                buffer = atr * 0.5

                qty = TARGET_POSITION_SIZE / price
                
                # Simple Strategy Logic with Telegram Alerts
                if rsi < 30:
                    sl = df['l'].tail(10).min() - buffer
                    if (price - sl) * qty > (CAPITAL * 0.01): sl = price - ((CAPITAL * 0.01) / qty)
                    tp1 = price + (2 * (price - sl))
                    
                    ex.create_market_buy_order(symbol, qty)
                    ex.create_order(symbol, 'STOP_MARKET', 'sell', qty, params={'stopPrice': sl})
                    ex.create_order(symbol, 'TAKE_PROFIT_MARKET', 'sell', qty/2, params={'stopPrice': tp1})
                    
                    msg = f"🚀 LONG ENTRY: {symbol}\nPrice: {price}\nSL: {sl:.2f}\nTP1: {tp1:.2f}"
                    send_telegram(msg)
                    trade_history.append(msg)

                elif rsi > 70:
                    sl = df['h'].tail(10).max() + buffer
                    if (sl - price) * qty > (CAPITAL * 0.01): sl = price + ((CAPITAL * 0.01) / qty)
                    tp1 = price - (2 * (sl - price))

                    ex.create_market_sell_order(symbol, qty)
                    ex.create_order(symbol, 'STOP_MARKET', 'buy', qty, params={'stopPrice': sl})
                    ex.create_order(symbol, 'TAKE_PROFIT_MARKET', 'buy', qty/2, params={'stopPrice': tp1})
                    
                    msg = f"📉 SHORT ENTRY: {symbol}\nPrice: {price}\nSL: {sl:.2f}\nTP1: {tp1:.2f}"
                    send_telegram(msg)
                    trade_history.append(msg)

            except Exception as e:
                print(f"Error on {symbol}: {e}")
        
        time.sleep(60)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    Thread(target=lambda: app.run(host='0.0.0.0', port=port)).start()
    trade_logic()
