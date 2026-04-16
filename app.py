import os
from flask import Flask, render_template, request, jsonify
import yfinance as yf
import pandas as pd
from datetime import datetime

app = Flask(__name__)

def run_backtest(symbol, entry_time_str, exit_time_str, start_date_str, end_date_str):
    try:
        # yfinance uses 'YYYY-MM-DD' format, so we need to ensure formatting
        start_dt = datetime.strptime(start_date_str, "%Y-%m-%d")
        end_dt = datetime.strptime(end_date_str, "%Y-%m-%d")
        
        # Format for yfinance
        yf_start = start_dt.strftime("%Y-%m-%d")
        # Add one day to end_date because yfinance end date is exclusive
        yf_end = (end_dt + pd.Timedelta(days=1)).strftime("%Y-%m-%d")
        
        # Fetch data
        print(f"Fetching data for {symbol} from {yf_start} to {yf_end}")
        data = yf.download(symbol, start=yf_start, end=yf_end, interval="1m", progress=False)
        
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
            
        days = df.groupby(df.index.date)
        
        trades = []
        
        for date, day_data in days:
            # Parse target times
            entry_time = datetime.strptime(f"{date} {entry_time_str}", "%Y-%m-%d %H:%M")
            exit_time = datetime.strptime(f"{date} {exit_time_str}", "%Y-%m-%d %H:%M")
            
            # Windows
            entry_window_end = entry_time + pd.Timedelta(minutes=5)
            exit_window_end = exit_time + pd.Timedelta(minutes=5)
            
            entry_candle = day_data[(day_data.index >= entry_time) & (day_data.index < entry_window_end)].head(1)
            exit_candle = day_data[(day_data.index >= exit_time) & (day_data.index < exit_window_end)].head(1)
            
            if not entry_candle.empty and not exit_candle.empty:
                try:
                    entry_price = float(entry_candle['Close'].iloc[0])
                    exit_price = float(exit_candle['Close'].iloc[0])
                    
                    pnl = exit_price - entry_price
                    
                    trades.append({
                        "date": str(date),
                        "entry": round(entry_price, 2),
                        "exit": round(exit_price, 2),
                        "pnl": round(pnl, 2)
                    })
                except Exception as e:
                    print(f"Error extracting prices for {date}: {e}")
                    
        total_pnl = sum(t['pnl'] for t in trades)
        wins = [t for t in trades if t['pnl'] > 0]
        win_rate = (len(wins) / len(trades) * 100) if trades else 0
        
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
    symbol = data.get("symbol")
    entry_time = data.get("entry_time")
    exit_time = data.get("exit_time")
    start_date = data.get("start_date")
    end_date = data.get("end_date")
    
    if not all([symbol, entry_time, exit_time, start_date, end_date]):
        return jsonify({"error": "Missing input parameters"}), 400
        
    result = run_backtest(symbol, entry_time, exit_time, start_date, end_date)
    
    return jsonify(result)

if __name__ == "__main__":
    app.run(debug=True, port=5000)
