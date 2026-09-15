"""
Helper script to generate authorization URL for cTrader Open API and retrieve tokens/accounts.
"""

import sys
import re
from pathlib import Path
from app.config.settings import get_settings
from app.broker.ctrader.auth import CTraderAuth


def update_env(key: str, val: str, env_path: str = ".env"):
    p = Path(env_path)
    if not p.exists():
        return
    content = p.read_text(encoding="utf-8")
    pattern = rf"^{key}=.*$"
    if re.search(pattern, content, flags=re.MULTILINE):
        content = re.sub(pattern, f"{key}={val}", content, flags=re.MULTILINE)
    else:
        content += f"\n{key}={val}\n"
    p.write_text(content, encoding="utf-8")


def main():
    settings = get_settings()
    auth = CTraderAuth(settings)

    print("\n=======================================================")
    print("      Spotware cTrader Open API Authorization Wizard")
    print("=======================================================\n")
    print(f"Current Client ID: {settings.ctrader_client_id}")

    if not settings.ctrader_client_id:
        print("[!] ERROR: CTRADER_CLIENT_ID is not configured in .env.")
        return

    redirect_uri = input("\nEnter Redirect URI configured in your cTrader App [default: http://localhost:8080/callback]: ").strip()
    if not redirect_uri:
        redirect_uri = "http://localhost:8080/callback"

    auth_url = auth.get_authorization_url(redirect_uri=redirect_uri)

    print("\n--- STEP 1: Authorize Application ---")
    print("Open the following link in your browser:")
    print(f"\n{auth_url}\n")
    print("Log in with your cTrader ID (cTID), select your trading account(s), and click 'Allow Access'.")

    print("\n--- STEP 2: Enter Authorization Result ---")
    print("After allowing access, your browser will redirect to your redirect URI.")
    print("Example: http://localhost:8080/callback?code=YOUR_AUTH_CODE")
    print("(Or if you generated an Access Token directly on openapi.ctrader.com, you can paste it below)\n")

    user_input = input("Paste redirected URL, Auth Code, OR direct Access Token: ").strip()
    if not user_input:
        print("[!] No input received. Aborting.")
        return

    access_token = ""
    refresh_token = ""

    if "code=" in user_input:
        import urllib.parse
        parsed = urllib.parse.urlparse(user_input)
        params = urllib.parse.parse_qs(parsed.query)
        code = params.get("code", [user_input])[0]
        print(f"\n[*] Extracted Authorization Code: {code}")
        print("[*] Exchanging code for Access & Refresh tokens...")
        try:
            tokens = auth.exchange_code_for_token(code=code, redirect_uri=redirect_uri)
            access_token = tokens.get("accessToken") or tokens.get("access_token", "")
            refresh_token = tokens.get("refreshToken") or tokens.get("refresh_token", "")
            print("[+] Successfully received tokens from Spotware!")
        except Exception as e:
            print(f"[!] Error exchanging code: {e}")
            return
    elif len(user_input) > 20 and not user_input.startswith("http"):
        # Could be direct access token or auth code
        try:
            accounts = auth.get_trading_accounts(user_input)
            access_token = user_input
            print("[+] Access token verified with Spotware!")
        except Exception:
            try:
                tokens = auth.exchange_code_for_token(code=user_input, redirect_uri=redirect_uri)
                access_token = tokens.get("accessToken") or tokens.get("access_token", "")
                refresh_token = tokens.get("refreshToken") or tokens.get("refresh_token", "")
                print("[+] Successfully exchanged code for tokens!")
            except Exception:
                access_token = user_input
    else:
        print("[!] Unrecognized input format.")
        return

    if access_token:
        update_env("CTRADER_ACCESS_TOKEN", access_token)
        print(f"[+] Saved CTRADER_ACCESS_TOKEN to .env")
    if refresh_token:
        update_env("CTRADER_REFRESH_TOKEN", refresh_token)
        print(f"[+] Saved CTRADER_REFRESH_TOKEN to .env")

    # Fetch and select account
    print("\n--- STEP 3: Discover Trading Accounts ---")
    try:
        accounts_data = auth.get_trading_accounts(access_token)
        accounts = accounts_data if isinstance(accounts_data, list) else accounts_data.get("data", [])
        if accounts:
            print("\nAvailable Accounts:")
            for idx, acc in enumerate(accounts):
                acc_id = acc.get("accountId") or acc.get("accountNumber") or acc.get("traderRegistrationId")
                is_live = acc.get("live", False)
                broker = acc.get("brokerName", "Unknown")
                print(f"  [{idx+1}] Account ID: {acc_id} | Live: {is_live} | Broker: {broker}")

            choice = input(f"\nSelect account number [1-{len(accounts)}] (default: 1): ").strip()
            chosen_idx = int(choice) - 1 if (choice.isdigit() and 1 <= int(choice) <= len(accounts)) else 0
            selected_acc = accounts[chosen_idx]
            selected_id = str(selected_acc.get("accountId") or selected_acc.get("accountNumber"))
            is_live = selected_acc.get("live", False)

            update_env("CTRADER_ACCOUNT_ID", selected_id)
            env_mode = "live" if is_live else "demo"
            update_env("CTRADER_ENVIRONMENT", env_mode)
            print(f"[+] Saved CTRADER_ACCOUNT_ID={selected_id} to .env")
            print(f"[+] Saved CTRADER_ENVIRONMENT={env_mode} to .env")
        else:
            print("[*] Spotware accounts query returned empty.")
            acc_id = input("Enter your cTrader Account ID manually: ").strip()
            if acc_id:
                update_env("CTRADER_ACCOUNT_ID", acc_id)
                print(f"[+] Saved CTRADER_ACCOUNT_ID={acc_id} to .env")
    except Exception as e:
        print(f"[*] Note: Could not auto-query accounts ({e}).")
        acc_id = input("Enter your cTrader Account ID manually: ").strip()
        if acc_id:
            update_env("CTRADER_ACCOUNT_ID", acc_id)
            print(f"[+] Saved CTRADER_ACCOUNT_ID={acc_id} to .env")

    print("\n=======================================================")
    print(" Setup Complete! Your .env has been updated.")
    print(" To start trading with real cTrader API:")
    print("   1. Verify your TRADING_MODE in .env (paper, demo, or live)")
    print("   2. Run: python main.py run --mode demo (or --mode live)")
    print("=======================================================\n")


if __name__ == "__main__":
    main()
