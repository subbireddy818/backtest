import requests
import config
from utils import log_message, format_date_for_api

class DataFetcher:
    def __init__(self, authenticator):
        self.auth = authenticator
        self.root_url = config.ROOT_URL

    def fetch_historical_data(self, segment, instrument_id, start_date, end_date):
        """
        Fetches 1-minute historical OHLC data.
        Dates should be in DD-MM-YYYY format.
        """
        if config.MOCK_MODE:
            log_message("XTS LIVE API is restricted. Pulling real data via Yahoo Finance fallback...", "INFO")
            return self._fetch_yfinance_data(instrument_id)

        # Format dates for API (e.g., 01042024 09:15:00)
        start_time = f"{format_date_for_api(start_date)} 091500"
        end_time = f"{format_date_for_api(end_date)} 153000"
        
        url = f"{self.root_url}/marketdata/instruments/ohlc"
        
        params = {
            "exchangeSegment": segment,
            "exchangeInstrumentID": int(instrument_id),
            "startTime": start_time,
            "endTime": end_time,
            "compressionValue": 60  # 60 seconds = 1 minute
        }
        
        log_message(f"Fetching historical data for ID {instrument_id} from {start_date} to {end_date}...")
        
        headers = self.auth.get_headers()
        
        try:
            response = requests.get(url, params=params, headers=headers)
            data = response.json()
            
            if data.get("type") == "success":
                # The data is usually a CSV string in 'result' for some XTS versions, 
                # or a list of dictionaries. We'll handle both common formats.
                raw_data = data.get("result", {}).get("dataReponse", "")
                
                if not raw_data:
                    log_message("No data received for the given range.", "WARNING")
                    return []
                
                # Parsing XTS format: "Time|Open|High|Low|Close|Volume|OI"
                candles = []
                lines = raw_data.split(",")
                for line in lines:
                    if not line: continue
                    parts = line.split("|")
                    if len(parts) >= 5:
                        candles.append({
                            "timestamp": int(parts[0]), # Unix timestamp or formatted string
                            "open": float(parts[1]),
                            "high": float(parts[2]),
                            "low": float(parts[3]),
                            "close": float(parts[4]),
                            "volume": int(parts[5]) if len(parts) > 5 else 0
                        })
                
                log_message(f"Successfully fetched {len(candles)} candles.")
                return candles
            else:
                log_message(f"Data fetch failed: {data.get('description', 'Unknown error')}", "ERROR")
                return []
                
        except Exception as e:
            log_message(f"An error occurred during data fetch: {e}", "ERROR")
            return []

    def _fetch_yfinance_data(self, instrument_id):
        """Fetches real data via yfinance as a fallback using a ticker map."""
        import yfinance as yf
        import pandas as pd
        from datetime import datetime
        
        # Map XTS IDs to Yahoo Finance Tickers
        ticker_map = {
            1: "^NSEI",          # Nifty 50
            2885: "RELIANCE.NS"  # Reliance Industries
        }
        
        yf_ticker = ticker_map.get(int(instrument_id), "^NSEI")
        
        try:
            log_message(f"Fetching last 2 days of 1-minute data for {yf_ticker} from yfinance...")
            data = yf.download(yf_ticker, period='2d', interval='1m', progress=False)
            
            if data.empty:
                return []
                
            mock_candles = []
            
            # yfinance returns UTC datetime index; convert to IST naive for our Backtester
            data.index = data.index.tz_convert('Asia/Kolkata').tz_localize(None)
            
            for index, row in data.iterrows():
                # Extract float values cleanly, avoiding multi-index issues with yfinance DataFrame format
                try:
                    open_price = float(row['Open'].iloc[0]) if isinstance(row['Open'], pd.Series) else float(row['Open'])
                    high_price = float(row['High'].iloc[0]) if isinstance(row['High'], pd.Series) else float(row['High'])
                    low_price  = float(row['Low'].iloc[0]) if isinstance(row['Low'], pd.Series) else float(row['Low'])
                    close_price = float(row['Close'].iloc[0]) if isinstance(row['Close'], pd.Series) else float(row['Close'])
                except AttributeError:
                    open_price = float(row['Open'])
                    high_price = float(row['High'])
                    low_price = float(row['Low'])
                    close_price = float(row['Close'])
                
                # Create epoch timestamp based on IST naive (simple parsing format used in backtester)
                ts = int((index - datetime(1970, 1, 1)).total_seconds())
                
                mock_candles.append({
                    "timestamp": ts,
                    "open": round(open_price, 2),
                    "high": round(high_price, 2),
                    "low": round(low_price, 2),
                    "close": round(close_price, 2),
                    "volume": 0
                })
                
            return mock_candles
        except Exception as e:
            log_message(f"Failed to fetch fallback real data: {e}", "ERROR")
            return []
