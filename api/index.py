from fastapi import FastAPI
from instagrapi import Client
from pymongo import MongoClient
import os

app = FastAPI()
cl = Client()

# --- ENVIRONMENT VARIABLES ---
# Vercel Dashboard me set karna hoga
MONGO_URL = os.getenv("MONGO_URL")
USERNAME = os.getenv("INSTA_USER")
PASSWORD = os.getenv("INSTA_PASS")

# --- DB CONNECTION ---
try:
    mongo_client = MongoClient(MONGO_URL)
    db = mongo_client["InstaStreamBot"]
    collection = db["session"]
    print("✅ MongoDB Connected")
except Exception as e:
    print(f"❌ DB Error: {e}")

# Global variable to check login status inside serverless function
is_logged_in = False

def ensure_login():
    """Serverless function me har request pe check karega ki login hai ya nahi"""
    global is_logged_in
    if is_logged_in:
        return True

    print("🔄 Connecting to Instagram...")
    
    # 1. MongoDB se Session dhoondo
    session_data = collection.find_one({"_id": "insta_session"})
    
    if session_data:
        try:
            settings = session_data.get("settings")
            cl.load_settings(settings)
            cl.login(USERNAME, PASSWORD)
            is_logged_in = True
            print("✅ Logged in via Session")
            return True
        except Exception as e:
            print(f"⚠️ Session expired: {e}")

    # 2. Fresh Login
    try:
        cl.login(USERNAME, PASSWORD)
        new_settings = cl.dump_settings()
        collection.update_one(
            {"_id": "insta_session"},
            {"$set": {"settings": new_settings}},
            upsert=True
        )
        is_logged_in = True
        print("✅ New Login Successful & Saved")
        return True
    except Exception as e:
        print(f"❌ Login Failed: {e}")
        return False

@app.get("/")
def home():
    return {"status": "Vercel API Running"}

@app.get("/get_reels")
def get_reels():
    # Login check karega
    if not ensure_login():
        return {"status": "error", "message": "Login Failed"}

    try:
        reels = cl.clips_suggested(amount=5)
        data = []
        for reel in reels:
            data.append({
                "video_url": reel.video_url,
                "caption": reel.caption_text[:50] if reel.caption_text else "Reel",
                "username": reel.user.username
            })
        return {"status": "success", "data": data}
    except Exception as e:
        return {"status": "error", "message": str(e)}
      
