"""
cTrader Open API OAuth 2.0 Authentication.
Section 5 and 6 of project.md.
"""

from typing import Dict, Any, Optional, List
import urllib.parse
from loguru import logger

from app.config.settings import Settings, get_settings


class CTraderAuth:
    """
    Manages cTrader Open API OAuth 2.0 authorization URL and token exchange.
    """

    AUTH_URL = "https://openapi.ctrader.com/apps/auth"
    TOKEN_URL = "https://openapi.ctrader.com/apps/token"

    def __init__(self, settings: Optional[Settings] = None):
        self.settings = settings or get_settings()

    def get_authorization_url(self, redirect_uri: str = "http://localhost:8080/callback") -> str:
        """
        Generate browser URL for user to grant account permissions.
        Scopes: 'trading' and 'accounts'.
        """
        params = {
            "client_id": self.settings.ctrader_client_id,
            "redirect_uri": redirect_uri,
            "scope": "trading",
        }
        url = f"{self.AUTH_URL}?{urllib.parse.urlencode(params)}"
        logger.info(f"Generated cTrader authorization URL: {url}")
        return url

    def exchange_code_for_token(self, code: str, redirect_uri: str = "http://localhost:8080/callback") -> Dict[str, Any]:
        """
        Exchange OAuth authorization code for Access Token and Refresh Token.
        """
        import json
        import urllib.request

        params = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": redirect_uri,
            "client_id": self.settings.ctrader_client_id,
            "client_secret": self.settings.ctrader_client_secret,
        }
        query_str = urllib.parse.urlencode(params)
        url = f"{self.TOKEN_URL}?{query_str}"
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data

    def refresh_access_token(self, refresh_token: str) -> Dict[str, Any]:
        """
        Refresh an expired access token using the refresh token.
        """
        import json
        import urllib.request

        params = {
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            "client_id": self.settings.ctrader_client_id,
            "client_secret": self.settings.ctrader_client_secret,
        }
        query_str = urllib.parse.urlencode(params)
        url = f"{self.TOKEN_URL}?{query_str}"
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data

    def get_trading_accounts(self, access_token: str) -> List[Dict[str, Any]]:
        """
        Fetch list of connected trading accounts authorized under this access token.
        """
        import json
        import urllib.request

        url = f"https://api.spotware.com/connect/tradingaccounts?oauth_token={access_token}"
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data

