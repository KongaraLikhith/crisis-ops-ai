import os
import requests
from dotenv import load_dotenv

load_dotenv()
token = os.getenv("SLACK_BOT_TOKEN")
channel_id = "C0ARCK9MW0Z"

# 1. Try to join
res = requests.post("https://slack.com/api/conversations.join", 
                    headers={"Authorization": f"Bearer {token}"},
                    json={"channel": channel_id})
print(f"Join Result: {res.json()}")

# 2. Try to post
res = requests.post("https://slack.com/api/chat.postMessage", 
                    headers={"Authorization": f"Bearer {token}"},
                    json={"channel": channel_id, "text": "Test from debug script"})
print(f"Post Result: {res.json()}")
