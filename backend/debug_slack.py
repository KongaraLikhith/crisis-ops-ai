import os
import requests
from dotenv import load_dotenv

load_dotenv()
token = os.getenv("SLACK_BOT_TOKEN")
channel_id = os.getenv("SLACK_CHANNEL_ID")

print(f"Testing Slack Token: {token[:10]}...")
print(f"Target Channel ID: {channel_id}")

# 1. Test auth
res = requests.get("https://slack.com/api/auth.test", headers={"Authorization": f"Bearer {token}"})
print(f"Auth Test: {res.json()}")

# 2. List channels the bot is in
res = requests.get("https://slack.com/api/conversations.list", 
                   headers={"Authorization": f"Bearer {token}"},
                   params={"types": "public_channel,private_channel"})
data = res.json()
if data.get("ok"):
    print("\nAccessible Channels:")
    for c in data.get("channels", []):
        print(f" - {c['name']} ({c['id']})")
else:
    print(f"\nFailed to list channels: {data.get('error')}")
