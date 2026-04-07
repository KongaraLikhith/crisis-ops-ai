import os
from tools.slack_tool import post_to_slack
from dotenv import load_dotenv

load_dotenv()

def test_slack():
    token = os.getenv("SLACK_BOT_TOKEN")
    channel = os.getenv("SLACK_CHANNEL_ID")
    
    print(f"--- Slack Verification ---")
    print(f"Token: {token[:10]}... (hidden)")
    print(f"Channel ID: {channel}")
    
    if not token or not channel or channel == "your_channel_id":
        print("\n[ERROR] Slack is not fully configured.")
        print("Please set a real SLACK_CHANNEL_ID in your .env file.")
        return

    result = post_to_slack("🚀 *CrisisOps AI* connectivity test successful!")
    print(f"\nResult: {result}")

if __name__ == "__main__":
    test_slack()
