from fastapi import FastAPI
from instagrapi import Client
from pymongo import MongoClient
import os

app = FastAPI()
cl = Client()

# --- ENV VARIABLES ---
MONGO_URL = os.getenv("MONGO_URL")
USERNAME = os.getenv("INSTA_USER")
PASSWORD = os.getenv("INSTA_PASS")
SESSION_ID = os.getenv("INSTA_SESSIONID")  # <-- Ye naya hai

# --- DB CONNECTION ---
try:
    mongo_client = MongoClient(MONGO_URL)
    db = mongo_client["InstaStreamBot"]
    collection = db["session"]
except Exception as e:
    print(f"❌ DB Error: {e}")

is_logged_in = False

def ensure_login():
    global is_logged_in
    if is_logged_in:
        return True

    print("🔄 Connecting to Instagram...")

    # --- METHOD 1: Direct Session ID from Vercel Env (BEST) ---
    if SESSION_ID:
        try:
            print(f"🍪 Using Session ID from Env...")
            cl.login_by_sessionid(SESSION_ID)
            is_logged_in = True
            print("✅ Login Successful via Session ID!")
            
            # Future ke liye DB mein bhi save kar dete hain
            try:
                collection.update_one(
                    {"_id": "insta_session"},
                    {"$set": {"settings": cl.dump_settings()}},
                    upsert=True
                )
            except:
                pass
            return True
        except Exception as e:
            print(f"⚠️ Session ID Env failed: {e}")

    # --- METHOD 2: Check MongoDB ---
    session_data = collection.find_one({"_id": "insta_session"})
    if session_data:
        try:
            settings = session_data.get("settings")
            cl.load_settings(settings)
            cl.login(USERNAME, PASSWORD)
            is_logged_in = True
            print("✅ Logged in via DB Session")
            return True
        except Exception as e:
            print(f"⚠️ DB Session expired: {e}")

    # --- METHOD 3: Password Login (Last Option) ---
    try:
        print("🔑 Trying Password Login...")
        cl.login(USERNAME, PASSWORD)
        collection.update_one(
            {"_id": "insta_session"},
            {"$set": {"settings": cl.dump_settings()}},
            upsert=True
        )
        is_logged_in = True
        return True
    except Exception as e:
        print(f"❌ All Login Methods Failed: {e}")
        return False

@app.get("/")
def home():
    return {"status": "Vercel API Running"}

@app.get("/get_reels")
def get_reels():
    if not ensure_login():
        return {"status": "error", "message": "Login Failed. Check Vercel Logs."}

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
        
