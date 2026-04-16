import pandas as pd
from datetime import datetime
from utils import log_message

class Backtester:
    def __init__(self, entry_time="09:30", exit_time="11:30"):
        self.entry_time_str = entry_time
        self.exit_time_str = exit_time
        self.trades = []

    def run(self, candles):
        """Processes candles and executes the time-based strategy."""
        if not candles:
            log_message("No candles to backtest.", "WARNING")
            return
        
        # Convert candles to DataFrame
        df = pd.DataFrame(candles)
        
        # Convert Unix timestamp (seconds) to datetime
        df['datetime'] = pd.to_datetime(df['timestamp'], unit='s')
        
        # Ensure we are working with naive datetimes to match entry_time strings
        # or localize appropriately. For the demo, we'll keep everything simple.
        df['datetime'] = df['datetime'].dt.floor('S') # Remove microseconds
        
        df.set_index('datetime', inplace=True)
        df.sort_index(inplace=True)
        
        # Group by date
        days = df.groupby(df.index.date)
        
        log_message(f"Starting backtest logic for {len(days)} trading days...")
        
        for date, day_data in days:
            try:
                # Find entry candle (closest to 09:30)
                # We look at the candle closing at or just after 09:30
                entry_time = datetime.strptime(f"{date} {self.entry_time_str}", "%Y-%m-%d %H:%M")
                exit_time = datetime.strptime(f"{date} {self.exit_time_str}", "%Y-%m-%d %H:%M")
                
                # Check if we have data for the day
                if day_data.empty:
                    continue
                
                # Get the candle close to the entry/exit time
                # We use a 2-minute window to be safe for entry (09:30 - 09:32)
                entry_window_end = entry_time + pd.Timedelta(minutes=5)
                exit_window_end = exit_time + pd.Timedelta(minutes=5)
                
                entry_candle = day_data[(day_data.index >= entry_time) & (day_data.index < entry_window_end)].head(1)
                exit_candle = day_data[(day_data.index >= exit_time) & (day_data.index < exit_window_end)].head(1)
                
                if not entry_candle.empty and not exit_candle.empty:
                    entry_price = entry_candle['close'].iloc[0]
                    exit_price = exit_candle['close'].iloc[0]
                    pnl = exit_price - entry_price
                    
                    self.trades.append({
                        "date": str(date),
                        "entry_time": entry_candle.index[0].strftime("%H:%M:%S"),
                        "exit_time": exit_candle.index[0].strftime("%H:%M:%S"),
                        "entry_price": round(entry_price, 2),
                        "exit_price": round(exit_price, 2),
                        "pnl": round(pnl, 2)
                    })
                else:
                    log_message(f"Missing entry or exit candle for {date}. Skipping day.", "WARNING")
                    
            except Exception as e:
                log_message(f"Error processing day {date}: {e}", "ERROR")

    def print_summary(self):
        """Prints the final performance report."""
        if not self.trades:
            print("\nNo trades executed during the backtest.")
            return

        total_pnl = sum(t['pnl'] for t in self.trades)
        wins = [t for t in self.trades if t['pnl'] > 0]
        win_rate = (len(wins) / len(self.trades)) * 100
        
        print("\n" + "="*50)
        print("          BACKTEST SUMMARY REPORT")
        print("="*50)
        print(f"Total Trades : {len(self.trades)}")
        print(f"Total PnL    : {round(total_pnl, 2)}")
        print(f"Win Rate     : {round(win_rate, 2)}%")
        print("-" * 50)
        print(f"{'Date':<12} | {'Entry':<8} | {'Exit':<8} | {'PnL':<8}")
        print("-" * 50)
        for t in self.trades:
            print(f"{t['date']:<12} | {t['entry_price']:<8} | {t['exit_price']:<8} | {t['pnl']:<8}")
        print("="*50)
