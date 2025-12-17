import requests
import os
from pathlib import Path

def load_keys():
    keys = {}
    for filename in ['env.ini', '.env']:
        try:
            if os.path.exists(filename):
                with open(filename, 'r', encoding='utf-8') as f:
                    for line in f:
                        if '=' in line and not line.strip().startswith('#'):
                            k, v = line.strip().split('=', 1)
                            # Clean value (remove quotes and whitespace)
                            clean_v = v.strip().strip('"').strip("'")
                            keys[k.strip()] = clean_v
                print(f"✅ Loaded {filename}")
                return keys
        except Exception as e:
            print(f"❌ Error reading {filename}: {e}")
    return keys

def test_auth(client_id, client_secret, env_name):
    base_url = "https://api-m.paypal.com" if env_name == "Live" else "https://api-m.sandbox.paypal.com"
    url = f"{base_url}/v1/oauth2/token"
    
    print(f"\nTesting {env_name} Environment...")
    print(f"URL: {url}")
    print(f"Client ID: {client_id[:5]}...{client_id[-5:] if len(client_id)>5 else ''}")
    
    try:
        response = requests.post(
            url,
            headers={"Accept": "application/json", "Accept-Language": "en_US"},
            data={"grant_type": "client_credentials"},
            auth=(client_id, client_secret),
            timeout=10
        )
        
        if response.status_code == 200:
            print(f"✅ SUCCESS! These are valid {env_name} keys.")
            return True
        else:
            print(f"❌ FAILED ({response.status_code})")
            print(f"Error: {response.text}")
            return False
    except Exception as e:
        print(f"❌ CONNECTION ERROR: {e}")
        return False

print("="*60)
print("PAYPAL KEY VALIDATOR")
print("="*60)

keys = load_keys()
cid = keys.get('PAYPAL_CLIENT_ID')
sec = keys.get('PAYPAL_CLIENT_SECRET')

if not cid or not sec:
    print("❌ ERROR: Could not find PAYPAL_CLIENT_ID or PAYPAL_CLIENT_SECRET in env.ini")
else:
    print("\nChecking keys against PayPal servers...")
    
    # Test Sandbox
    is_sandbox = test_auth(cid, sec, "Sandbox")
    
    # Test Live
    is_live = test_auth(cid, sec, "Live")
    
    print("\n" + "="*60)
    print("RESULT:")
    if is_live:
        print("✅ Your keys are VALID for LIVE mode.")
        print("👉 Set the Dashboard switch to 'Live'.")
    elif is_sandbox:
        print("✅ Your keys are VALID for SANDBOX mode.")
        print("👉 Set the Dashboard switch to 'Sandbox'.")
    else:
        print("❌ Your keys are INVALID for both environments.")
        print("👉 Please check your PayPal Developer Dashboard and copy new keys.")

print("="*60)
input("\nPress Enter to exit...")
