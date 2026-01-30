import tweepy
import os
from dotenv import load_dotenv
from fetcher import get_latest_nav

# Load passwords from .env file
load_dotenv()

def post_to_x():
    # 1. Authenticate to X
    client = tweepy.Client(
        consumer_key=os.getenv("API_KEY"),
        consumer_secret=os.getenv("API_SECRET"),
        access_token=os.getenv("ACCESS_TOKEN"),
        access_token_secret=os.getenv("ACCESS_SECRET")
    )

    # 2. Get the Message
    message = get_latest_nav()

    # 3. Post it
    try:
        response = client.create_tweet(text=message)
        print(f"✅ Tweet sent! ID: {response.data['id']}")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    post_to_x()