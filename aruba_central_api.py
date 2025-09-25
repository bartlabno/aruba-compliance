import os
import sys
import json
import requests
import time
from dotenv import load_dotenv

class ArubaCentralAPI:
    """A class to interact with the Aruba Central API."""

    def __init__(self, group_name=None):
        """
        Initializes the API client and handles authentication.
        Prioritizes group_name passed as argument over environment variable.
        """
        load_dotenv()
        self.base_url = os.getenv("ARUBA_BASE_URL")
        self.client_id = os.getenv("ARUBA_CLIENT_ID")
        self.client_secret = os.getenv("ARUBA_CLIENT_SECRET")
        self.group_name = group_name or os.getenv("ARUBA_GROUP_NAME")
        self.token_file = 'token.json'
        
        # Try to get a token, but don't exit if it fails immediately.
        self.access_token = self._get_access_token()

        if not self.base_url:
            print("Error: Missing ARUBA_BASE_URL environment variable.", file=sys.stderr)
            sys.exit(2)
        
        if not self.group_name:
            print("Warning: No group name specified. Most API calls will fail.", file=sys.stderr)


    def _get_access_token(self):
        """
        Retrieves a valid access token.
        1. Returns cached token if still valid (less than 2 hours old).
        2. Refreshes token if expired.
        3. Authenticates for a new token if no other option.
        """
        token_data = self._load_token_data()

        # Case 1: We have a valid, non-expired access token in the cache.
        if token_data.get("access_token") and token_data.get("timestamp"):
            token_age = time.time() - token_data.get("timestamp", 0)
            if token_age < 7200:  # 2 hours in seconds
                print("Found valid access token in cache.")
                return token_data["access_token"]
            # If token is older than 2 hours, fall through to refresh it.

        # Case 2: We have a refresh token (and the access token is either missing or expired).
        if token_data.get("refresh_token"):
            if token_data.get("access_token"):  # This implies it's expired from the check above
                 print("Access token expired, forcing refresh...")
            else:
                 print("Found refresh token, attempting to refresh...")
            return self._refresh_token(token_data["refresh_token"])

        # Case 3: No valid access token, no refresh token. Need to authenticate from scratch.
        if not self.client_id or not self.client_secret:
            print("Error: No valid token and no credentials. Please provide ARUBA_CLIENT_ID and ARUBA_CLIENT_SECRET.", file=sys.stderr)
            return None

        print("No valid token found, authenticating with client credentials...")
        return self._authenticate_new_token()

    def _load_token_data(self):
        """Loads token data from the JSON file."""
        try:
            with open(self.token_file, 'r') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {}

    def _save_token_data(self, token_response):
        """Saves relevant token data, credentials, and a timestamp to the JSON file."""
        data_to_save = {
            "refresh_token": token_response.get("refresh_token"),
            "access_token": token_response.get("access_token"),
            "timestamp": time.time(),
            "client_id": self.client_id,
            "client_secret": self.client_secret
        }
        with open(self.token_file, 'w') as f:
            json.dump(data_to_save, f)

    def _refresh_token(self, refresh_token):
        """Refreshes the access token using a refresh token."""
        url = f"{self.base_url}/oauth2/token"
        payload = {
            'grant_type': 'refresh_token',
            'refresh_token': refresh_token
        }
        if self.client_id and self.client_secret:
            payload['client_id'] = self.client_id
            payload['client_secret'] = self.client_secret

        try:
            response = requests.post(url, data=payload)
            response.raise_for_status()
            token_response = response.json()
            self._save_token_data(token_response)
            return token_response.get("access_token")
        except requests.exceptions.RequestException as e:
            print(f"Error refreshing token: {e}", file=sys.stderr)
            return self._authenticate_new_token()

    def _authenticate_new_token(self):
        """Authenticates to get a new access and refresh token."""
        url = f"{self.base_url}/oauth2/token"
        payload = {
            'grant_type': 'client_credentials',
            'client_id': self.client_id,
            'client_secret': self.client_secret
        }
        try:
            response = requests.post(url, data=payload)
            response.raise_for_status()
            token_response = response.json()
            self._save_token_data(token_response)
            return token_response.get("access_token")
        except requests.exceptions.RequestException as e:
            print(f"Error authenticating: {e}", file=sys.stderr)
            return None

    def call_api(self, endpoint):
        """Makes an authenticated API call."""
        if not self.access_token:
            print("Error: No valid access token. Cannot make API call.", file=sys.stderr)
            return None
            
        headers = {'Authorization': f'Bearer {self.access_token}'}
        url = f"{self.base_url}{endpoint}"
        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            print(f"HTTP Error calling API endpoint {endpoint}: {e.response.status_code} {e.response.text}", file=sys.stderr)
        except requests.exceptions.RequestException as e:
            print(f"Request Error calling API endpoint {endpoint}: {e}", file=sys.stderr)
        except json.JSONDecodeError:
            print(f"Error: Could not decode JSON response from endpoint {endpoint}", file=sys.stderr)
        return None

    def get_group_level_config(self):
        """Get the configuration for the entire group."""
        if not self.group_name:
            print("Error: Cannot get group-level config without a group name.", file=sys.stderr)
            return None
        encoded_group = requests.utils.quote(self.group_name)
        endpoint = f"/caasapi/v1/showcommand/object/effective?group_name={encoded_group}"
        return self.call_api(endpoint)

    def get_device_override_config(self, mac_address):
        """Get the configuration for a specific device's local override."""
        if not self.group_name:
            print("Error: Cannot get device config without a group name.", file=sys.stderr)
            return None
        
        encoded_group = requests.utils.quote(self.group_name)
        # The API endpoint requires the MAC address to be appended to the group name
        combined_name = f"{encoded_group}/{mac_address}"
        endpoint = f"/caasapi/v1/showcommand/object/committed?group_name={combined_name}"
        return self.call_api(endpoint)


