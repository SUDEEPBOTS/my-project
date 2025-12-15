from fastapi import FastAPI
from instagrapi import Client
from pymongo import MongoClient
import os
import json

app = FastAPI()
cl = Client()

# --- ENV VARIABLES ---
MONGO_URL = os.getenv("MONGO_URL")
USERNAME = os.getenv("INSTA_USER")
PASSWORD = os.getenv("INSTA_PASS")
# Session ID Env se uthana sabse safe hai
SESSION_ID = os.getenv("INSTA_SESSIONID") 

# --- DB CONNECTION ---
try:
    mongo_client = MongoClient(MONGO_URL)
    db = mongo_client["InstaStreamBot"]
    collection = db["session"]
except Exception as e:
    print(f"❌ DB Error: {e}")

is_logged_in = False

def get_fixed_device_settings():
    """
    Ye function ek fake 'Samsung Phone' ki settings banata hai.
    Har baar same settings use karne se Instagram logout nahi karega.
    """
    # Ek unique seed bana rahe hain username se, taaki UUID humesha same rahe
    cl.set_seed(USERNAME) 
    
    # Android Device settings set kar rahe hain
    cl.set_device({
        "app_version": "269.0.0.18.75",
        "android_version": 26,
        "android_release": "8.0.0",
        "dpi": "480dpi",
        "resolution": "1080x1920",
        "manufacturer": "Samsung",
        "device": "SM-G960F",
        "model": "Galaxy S9",
        "cpu": "exynos9810",
        "version_code": "314572800"
    })
    print("📱 Device Spoofing: Activated (Galaxy S9)")

def ensure_login():
    global is_logged_in
    if is_logged_in:
        return True

    # Pehle Device ID fix karo
    get_fixed_device_settings()
    
    print("🔄 Connecting to Instagram...")

    # --- METHOD 1: Session ID (BEST) ---
    # Agar Env variable mein Session ID hai, toh usi se login karo.
    # Ye password login se 100 guna safe hai.
    if SESSION_ID:
        try:
            print("🍪 Using Session ID from Env...")
            cl.login_by_sessionid(SESSION_ID)
            is_logged_in = True
            print("✅ Login Successful via Session ID!")
            return True
        except Exception as e:
            print(f"⚠️ Session ID Expired: {e}")

    # --- METHOD 2: MongoDB Session ---
    session_data = collection.find_one({"_id": "insta_session"})
    if session_data:
        try:
            print("📂 Loading Session from Database...")
            settings = session_data.get("settings")
            cl.load_settings(settings)
            
            # Login call mat karo, bas verify karo
            # cl.login() call karne se IP check trigger hota hai
            try:
                cl.get_timeline_feed() # Halka check
                print("✅ Database Session is Valid")
                is_logged_in = True
                return True
            except:
                print("⚠️ Saved Session Invalid. Trying Re-login...")
                # Agar invalid hai tabhi login karo
                cl.login(USERNAME, PASSWORD)
                is_logged_in = True
                
                # Naya session save karo
                new_settings = cl.dump_settings()
                collection.update_one(
                    {"_id": "insta_session"},
                    {"$set": {"settings": new_settings}},
                    upsert=True
                )
                return True

        except Exception as e:
            print(f"⚠️ Database Login Failed: {e}")

    # --- METHOD 3: Password Login (Dangerous on Server) ---
    try:
        print("🔑 Logging in with Password (Risk of Challenge)...")
        cl.login(USERNAME, PASSWORD)
        is_logged_in = True
        
        # Save Session
        new_settings = cl.dump_settings()
        collection.update_one(
            {"_id": "insta_session"},
            {"$set": {"settings": new_settings}},
            upsert=True
        )
        print("✅ New Login Successful")
        return True
    except Exception as e:
        # Agar yahan fail hua, matlab account soft-ban hai
        print(f"❌ Login Blocked: {e}")
        return False

@app.get("/")
def home():
    return {"status": "Online", "message": "Insta API Running with Device Spoofing"}

@app.get("/get_reels")
def get_reels():
    if not ensure_login():
        return {"status": "error", "message": "Login Failed. Account might be flagged."}

    try:
        # Hashtag se reels utha rahe hain
        medias = cl.hashtag_medias_top("reels", amount=15)
        
        data = []
        for media in medias:
            if media.media_type == 2:
                data.append({
                    "video_url": media.video_url,
                    "caption": media.caption_text[:50] + "..." if media.caption_text else "Reel",
                    "username": media.user.username,
                    "pk": media.pk
                })
                if len(data) >= 5:
                    break
        
        if not data:
            return {"status": "error", "message": "No videos found"}

        return {"status": "success", "data": data}

    except Exception as e:
        global is_logged_in
        is_logged_in = False # Error aaya toh maano logout ho gaya
        return {"status": "error", "message": str(e)}
        
