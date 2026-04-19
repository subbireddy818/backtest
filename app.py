import os
from flask import Flask, render_template, request, jsonify
import yfinance as yf
import pandas as pd
from datetime import datetime

app = Flask(__name__)

def run_backtest(strategy, symbol, start_date_str, end_date_str, interval="1m"):
    try:
        # yfinance uses 'YYYY-MM-DD' format, so we need to ensure formatting
        start_dt = datetime.strptime(start_date_str, "%Y-%m-%d")
        end_dt = datetime.strptime(end_date_str, "%Y-%m-%d")
        
        # Buffer calculations for RSI warm-up
        # 1m data is limit to 7 days, 5m data is limited to 60 days.
        buffer_days = 5
        if interval == "1m":
            days_since_start = (datetime.now() - start_dt).days
            buffer_days = min(2, max(0, 6 - days_since_start))
        
        fetch_start_dt = start_dt - pd.Timedelta(days=buffer_days)
        yf_start = fetch_start_dt.strftime("%Y-%m-%d")
        # Add one day to end_date because yfinance end date is exclusive
        yf_end = (end_dt + pd.Timedelta(days=1)).strftime("%Y-%m-%d")
        
        # Fetch data
        print(f"Fetching data buffer starting from {yf_start} for RSI warmup")
        data = yf.download(symbol, start=yf_start, end=yf_end, interval=interval, progress=False)
        
        if data.empty:
            return {"error": "No data found for the given dates and symbol. Note: 1-minute data is only available for the last 7 days."}
            
        # Convert index timezone (yfinance returns UTC or local depending on the ticker, 
        # but typically UTC for crypto and local exchange time for stocks. Let's ensure it handles TZ)
        if data.index.tz is not None:
            data.index = data.index.tz_convert('Asia/Kolkata').tz_localize(None)
        
        df = data.copy()
        
        # Flatten columns if multi-index (yfinance behavior)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
            
        # Calculate wilder's RSI (14)
        delta = df['Close'].diff()
        gain = delta.clip(lower=0)
        loss = -1 * delta.clip(upper=0)
        avg_gain = gain.ewm(com=13, adjust=False).mean()
        avg_loss = loss.ewm(com=13, adjust=False).mean()
        rs = avg_gain / avg_loss
        df['RSI'] = 100 - (100 / (1 + rs))
        
        # Ensure sorting and remove timezone for Strategy 2 compatibility
        df = df.sort_index()
        df.index = df.index.tz_localize(None) if df.index.tz else df.index
        
        trades = []
        if strategy == "strategy2":
            # --- STRATEGY 2: RSI DROP PRODUCTION LOGIC ---
            state = "RESET_WAITING"
            in_trade = False
            active_trade = None
            
            for i in range(1, len(df)):
                row = df.iloc[i]
                prev_row = df.iloc[i-1]
                
                if pd.isna(row['RSI']) or pd.isna(prev_row['RSI']):
                    continue
                
                curr_rsi = float(row['RSI'])
                prev_rsi = float(prev_row['RSI'])
                curr_close = round(float(row['Close']), 2)
                curr_time = df.index[i]
                
                # STATE: RESET_WAITING (Wait for RSI cross above 40)
                if state == "RESET_WAITING":
                    if prev_rsi < 40 and curr_rsi > 40:
                        state = "READY_TO_ENTER"
                
                # STATE: READY_TO_ENTER (Wait for RSI cross below 30)
                elif state == "READY_TO_ENTER":
                    if not in_trade and prev_rsi > 30 and curr_rsi < 30:
                        active_trade = {
                            "entry_time": curr_time,
                            "entry_price": curr_close,
                            "entry_rsi": curr_rsi,
                            "strong_entry": curr_rsi < 20
                        }
                        in_trade = True
                        state = "IN_TRADE"
                        continue # Skip same-candle exit
                
                # STATE: IN_TRADE (Handle exit)
                elif state == "IN_TRADE" and in_trade:
                    # Multi-day Carry Prevention
                    if curr_time.date() != active_trade['entry_time'].date():
                        in_trade = False
                        state = "RESET_WAITING"
                        active_trade = None
                        continue

                    hold_seconds = (curr_time - active_trade['entry_time']).total_seconds()
                    
                    # No exit allowed before 5 minutes
                    if hold_seconds < 300:
                        continue
                        
                    exit_triggered = False
                    exit_reason = ""
                    
                    # PRIORITY 1: STOP LOSS (RSI < 16)
                    if curr_rsi < 16:
                        exit_triggered = True
                        exit_reason = "Stop Loss (RSI < 16)"
                    # PRIORITY 2: TAKE PROFIT (RSI cross above 40)
                    elif prev_rsi < 40 and curr_rsi > 40:
                        exit_triggered = True
                        exit_reason = "Take Profit (RSI > 40 Cross)"
                        
                    if exit_triggered:
                        pnl = curr_close - active_trade['entry_price']
                        # FORMAT DURATION (MM:SS.mmm)
                        mins = int(hold_seconds // 60)
                        secs = int(hold_seconds % 60)
                        millis = int((hold_seconds * 1000) % 1000)
                        duration_fmt = f"{mins:02}:{secs:02}.{millis:03}"
                        
                        # ONLY RECORD TRADES THAT STARTED AFTER USER START DATE
                        if active_trade['entry_time'] >= start_dt:
                            trades.append({
                                "entry_time": active_trade['entry_time'].strftime("%Y-%m-%d %H:%M"),
                                "exit_time": curr_time.strftime("%Y-%m-%d %H:%M"),
                                "entry_price": active_trade['entry_price'],
                                "exit_price": curr_close,
                                "pnl": round(pnl, 2),
                                "exit_reason": exit_reason,
                                "entry_rsi": round(active_trade['entry_rsi'], 2),
                                "exit_rsi": round(curr_rsi, 2),
                                "strong_entry": active_trade['strong_entry'],
                                "duration_formatted": duration_fmt
                            })
                        # RESET ALL FLAGS
                        in_trade = False
                        active_trade = None
                        state = "RESET_WAITING"
        else:
            # --- STRATEGY 1: EXISTING LOGIC ---
            active_trade = None
            for idx, row in df.iterrows():
                if pd.isna(row['RSI']): continue
                close_price = round(float(row['Close']), 2)
                current_rsi = float(row['RSI'])
                
                allowed_entry = idx.hour < 15 or (idx.hour == 15 and idx.minute <= 15)
                force_close = idx.hour == 15 and idx.minute >= 28
                
                if active_trade is None:
                    if current_rsi < 30 and allowed_entry:
                        active_trade = {"entry_time": idx, "entry_price": close_price}
                else:
                    hold_minutes = (idx - active_trade['entry_time']).total_seconds() / 60
                    if hold_minutes >= 5:
                        if current_rsi > 40 or current_rsi < 16 or force_close:
                            pnl = close_price - active_trade['entry_price']
                            reason = "EOD Force Close" if force_close else ("Take Profit" if current_rsi > 40 else "Stop Loss")
                            
                            # ONLY RECORD TRADES THAT STARTED AFTER USER START DATE
                            if active_trade['entry_time'] >= start_dt:
                                trades.append({
                                    "entry_time": active_trade['entry_time'].strftime("%Y-%m-%d %H:%M"),
                                    "exit_time": idx.strftime("%Y-%m-%d %H:%M"),
                                    "entry_price": active_trade['entry_price'],
                                    "exit_price": close_price,
                                    "pnl": round(pnl, 2),
                                    "exit_reason": reason
                                })
                            active_trade = None
                            
        total_pnl = sum(t['pnl'] for t in trades)
        wins = len([t for t in trades if t['pnl'] > 0])
        win_rate = (wins / len(trades) * 100) if trades else 0
        
        return {
            "success": True,
            "total_trades": len(trades),
            "total_pnl": round(total_pnl, 2),
            "win_rate": round(win_rate, 2),
            "trades": trades
        }
    except Exception as e:
        return {"error": str(e)}
@app.route("/")
def index():
    return render_template("index.html")

@app.route("/backtest", methods=["POST"])
def backtest_endpoint():
    data = request.json
    strategy = data.get("strategy", "strategy1")
    symbol = data.get("symbol")
    start_date = data.get("start_date")
    end_date = data.get("end_date")
    interval = data.get("interval", "1m")
    
    if not all([symbol, start_date, end_date]):
        return jsonify({"error": "Missing input parameters"}), 400
        
    result = run_backtest(strategy, symbol, start_date, end_date, interval)
    
    return jsonify(result)

if __name__ == "__main__":
    app.run(debug=True, port=5000)
