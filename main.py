import config
from xts_auth import XTSAuthenticator
from data_fetch import DataFetcher
from backtest import Backtester
from utils import print_banner, log_message

def main():
    """Main function to run the backtest project."""
    print_banner()
    
    # 1. Initialize Authentication
    auth = XTSAuthenticator()
    
    # 2. Login
    if config.MOCK_MODE:
        log_message("Running in MOCK_MODE. Bypassing real login for demonstration.")
        success = True
    else:
        success = auth.login()
    
    if not success:
        log_message("Unable to proceed without successful login. Please update API keys in config.py.", "ERROR")
        # For the sake of the demo, we could print a mock message here 
        # but following production-like logic, we stop.
        return

    # 3. Initialize Fetcher and Backtester
    fetcher = DataFetcher(auth)
    backtester = Backtester(entry_time=config.ENTRY_TIME, exit_time=config.EXIT_TIME)
    
    # 4. Fetch Data
    candles = fetcher.fetch_historical_data(
        segment=config.SEGMENT,
        instrument_id=config.INSTRUMENT_ID,
        start_date=config.START_DATE,
        end_date=config.END_DATE
    )
    
    # 5. Run Backtest
    if candles:
        backtester.run(candles)
        
        # 6. Output Summary
        backtester.print_summary()
    else:
        log_message("Backtest aborted: No data available.", "ERROR")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nExiting...")
    except Exception as e:
        log_message(f"Fatal error: {e}", "CRITICAL")
