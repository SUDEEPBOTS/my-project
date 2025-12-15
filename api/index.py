from fastapi import FastAPI
from instagrapi import Client
from pymongo import MongoClient
import os

app = FastAPI()
cl = Client()

# --- ENVIRONMENT VARIABLES (Vercel Settings se aayenge) ---
MONGO_URL = os.getenv("MONGO_URL")
USERNAME = os.getenv("INSTA_USER")
PASSWORD = os.getenv("INSTA_PASS")
SESSION_ID = os.getenv("INSTA_SESSIONID")

# --- DATABASE CONNECTION ---
try:
    mongo_client = MongoClient(MONGO_URL)
    db = mongo_client["InstaStreamBot"]
    collection = db["session"]
    print("✅ MongoDB Connected")
except Exception as e:
    print(f"❌ DB Connection Error: {e}")

is_logged_in = False

def ensure_login():
    """Login status check aur handle karta hai"""
    global is_logged_in
    if is_logged_in:
        return True

    print("🔄 Connecting to Instagram...")

    # METHOD 1: Session ID (Sabse Fast & Safe)
    if SESSION_ID:
        try:
            print("🍪 Using Session ID from Env...")
            cl.login_by_sessionid(SESSION_ID)
            is_logged_in = True
            return True
        except Exception as e:
            print(f"⚠️ Session ID login failed: {e}")

    # METHOD 2: Saved Session from MongoDB
    session_data = collection.find_one({"_id": "insta_session"})
    if session_data:
        try:
            print("📂 Loading Session from Database...")
            settings = session_data.get("settings")
            cl.load_settings(settings)
            cl.login(USERNAME, PASSWORD)
            is_logged_in = True
            print("✅ Database Session Login Successful")
            return True
        except Exception as e:
            print(f"⚠️ Database Session expired: {e}")

    # METHOD 3: Password Login (Last Resort)
    try:
        print("🔑 Logging in with Password...")
        cl.login(USERNAME, PASSWORD)
        is_logged_in = True
        
        # Naya session DB mein save karo
        new_settings = cl.dump_settings()
        collection.update_one(
            {"_id": "insta_session"},
            {"$set": {"settings": new_settings}},
            upsert=True
        )
        print("✅ New Login Successful & Saved to DB")
        return True
    except Exception as e:
        print(f"❌ All Login Methods Failed: {e}")
        return False

@app.get("/")
def home():
    return {"status": "Online", "message": "Insta Reel API is Running"}

@app.get("/get_reels")
def get_reels():
    # 1. Login Ensure karo
    if not ensure_login():
        return {"status": "error", "message": "Login Failed on Server"}

    try:
        # --- THE FIX IS HERE ---
        # 'clips_suggested' hata diya. Ab hum 'trending' hashtag se videos mangayenge.
        # Ye tarika 100% stable hai.
        print("🔍 Fetching Trending Reels...")
        medias = cl.hashtag_medias_top("reels", amount=15) 
        
        data = []
        for media in medias:
            # Check: Hum sirf VIDEOS (Media Type 2) lenge
            if media.media_type == 2:
                data.append({
                    "video_url": media.video_url,
                    "caption": media.caption_text[:50] + "..." if media.caption_text else "Reel",
                    "username": media.user.username,
                    "pk": media.pk
                })
                
                # Hamein sirf 5 videos chahiye
                if len(data) >= 5:
                    break
        
        if not data:
            return {"status": "error", "message": "No videos found"}

        return {"status": "success", "data": data}

    except Exception as e:
        return {"status": "error", "message": str(e)}
        
