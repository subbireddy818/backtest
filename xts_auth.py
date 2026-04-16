import requests
import config
from utils import log_message

class XTSAuthenticator:
    def __init__(self):
        self.root_url = config.ROOT_URL
        self.api_key = config.API_KEY
        self.secret_key = config.SECRET_KEY
        self.source = config.SOURCE
        self.token = None
        self.user_id = None
        self.headers = {
            "Content-Type": "application/json"
        }

    def login(self):
        """Perform Market Data login and store token."""
        url = f"{self.root_url}/marketdata/auth/login"
        payload = {
            "secretKey": self.secret_key,
            "appKey": self.api_key,
            "source": self.source
        }
        
        log_message("Attempting to login to XTS Market Data API...")
        
        try:
            # Note: For demo purposes, we handle the request. In a real scenario, valid keys are required.
            response = requests.post(url, json=payload, headers=self.headers)
            data = response.json()
            
            if data.get("type") == "success":
                self.token = data["result"]["token"]
                self.user_id = data["result"]["userID"]
                self.headers["authorization"] = self.token
                log_message(f"Login successful! User ID: {self.user_id}")
                return True
            else:
                log_message(f"Login failed: {data.get('description', 'Unknown error')}", "ERROR")
                return False
                
        except Exception as e:
            log_message(f"An error occurred during login: {e}", "ERROR")
            return False

    def get_headers(self):
        """Return headers with authorization token."""
        return self.headers
