import ccxt, pandas as pd, time, requests, os
from stockstats import StockDataFrame
from flask import Flask
from threading import Thread

# --- [ CONFIGURATION ] ---
MODE = 'DEMO' 
SYMBOLS = ['SOL/USDT', 'CAKE/USDT', 'LTC/USDT']
CAPITAL = 100.0
TARGET_POSITION_SIZE = 20.0 
LEVERAGE = 20 

app = Flask('')
@app.route('/')
def home(): return "Multi-Pair Bot: SOL, CAKE, LTC Active (Isolated)"

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
    try:
        ex.fapiPrivatePostMarginType({'symbol': symbol.replace('/', ''), 'marginType': 'ISOLATED'})
    except: pass
    try:
        ex.fapiPrivatePostLeverage({'symbol': symbol.replace('/', ''), 'leverage': LEVERAGE})
    except: pass

def trade_logic():
    ex = get_exchange()
    for s in SYMBOLS: setup_market(ex, s)
    
    active_positions = {s: False for s in SYMBOLS}
    
    while True:
        for symbol in SYMBOLS:
            try:
                bars = ex.fetch_ohlcv(symbol, timeframe='5m', limit=100)
                df = pd.DataFrame(bars, columns=['t', 'o', 'h', 'l', 'c', 'v'])
                stock = StockDataFrame.retype(df.copy())
                rsi = stock['rsi_14'].iloc[-1]
                price = df['c'].iloc[-1]
                atr = stock['atr_14'].iloc[-1]
                buffer = atr * 0.5

                if not active_positions[symbol]:
                    qty = TARGET_POSITION_SIZE / price
                    
                    if rsi < 30: # BUY
                        sl = df['l'].tail(10).min() - buffer
                        if (price - sl) * qty > (CAPITAL * 0.01):
                            sl = price - ((CAPITAL * 0.01) / qty)
                        tp1 = price + (2 * (price - sl))
                        
                        ex.create_market_buy_order(symbol, qty)
                        ex.create_order(symbol, 'STOP_MARKET', 'sell', qty, params={'stopPrice': sl})
                        ex.create_order(symbol, 'TAKE_PROFIT_MARKET', 'sell', qty/2, params={'stopPrice': tp1})
                        
                        active_positions[symbol] = "LONG"
                        print(f"🚀 {symbol} LONG Entry: {price} | SL: {sl:.2f}")

                    elif rsi > 70: # SELL
                        sl = df['h'].tail(10).max() + buffer
                        if (sl - price) * qty > (CAPITAL * 0.01):
                            sl = price + ((CAPITAL * 0.01) / qty)
                        tp1 = price - (2 * (sl - price))

                        ex.create_market_sell_order(symbol, qty)
                        ex.create_order(symbol, 'STOP_MARKET', 'buy', qty, params={'stopPrice': sl})
                        ex.create_order(symbol, 'TAKE_PROFIT_MARKET', 'buy', qty/2, params={'stopPrice': tp1})
                        
                        active_positions[symbol] = "SHORT"
                        print(f"📉 {symbol} SHORT Entry: {price} | SL: {sl:.2f}")

            except Exception as e:
                print(f"Error on {symbol}: {e}")
        
        time.sleep(60) # Pair တစ်ခုချင်းစီကို စစ်ဆေးရန် ခေတ္တနားမည်

if __name__ == "__main__":
    Thread(target=lambda: app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080)))).start()
    trade_logic()
