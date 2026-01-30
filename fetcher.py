import requests
import json

# Example: Axis Bluechip Fund (Scheme Code: 120465)
# You can find codes on the AMFI website or MFapi.in
SCHEME_CODE = "120465" 

def get_latest_nav():
    url = f"https://api.mfapi.in/mf/{SCHEME_CODE}"
    response = requests.get(url)
    
    if response.status_code == 200:
        data = response.json()
        fund_name = data['meta']['scheme_name']
        latest_nav = data['data'][0]['nav']
        date = data['data'][0]['date']
        
        return f"🚨 UPDATE: {fund_name}\n📅 Date: {date}\n💰 NAV: ₹{latest_nav}"
    else:
        return "Error fetching data"

# Test it locally
if __name__ == "__main__":
    print(get_latest_nav())