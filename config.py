# XTS API Credentials
API_KEY = "43c16d3b7ded22c8d13480"
SECRET_KEY = "Htmn831@IS"
ROOT_URL = "https://xts.rmoneyindia.co.in:3000"
SOURCE = "CTCL"

# Strategy Parameters
INSTRUMENT_ID = 2885          # Reliance Index ID (Usually 2885 in XTS NSECM)
SEGMENT = "NSECM"             # Exchange Segment
START_DATE = "01-04-2024"     # Format: DD-MM-YYYY
END_DATE = "15-04-2024"       # Format: DD-MM-YYYY

# Strategy Configuration
ENTRY_TIME = "09:30"
EXIT_TIME = "11:30"
INTERVAL = "1minute"          # Use '1minute' for XTS API

# Demo Mode
MOCK_MODE = True              # Set to False to use real API
