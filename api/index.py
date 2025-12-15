from fastapi import FastAPI
from instagrapi import Client
from pymongo import MongoClient
import os
import traceback # Error trace karne ke liye

app = FastAPI()
cl = Client()

# --- ENV VARIABLES ---
MONGO_URL = os.getenv("MONGO_URL")
SESSION_ID = os.getenv("INSTA_SESSIONID")
USERNAME = os.getenv("INSTA_USER")
PASSWORD = os.getenv("INSTA_PASS")

@app.get("/")
def home():
    # Ye check karega ki Vercel tak variables pahunch rahe hain ya nahi
    return {
        "status": "Online",
        "debug_info": {
            "mongo_url_present": bool(MONGO_URL),
            "session_id_present": bool(SESSION_ID),
            "username_present": bool(USERNAME)
        }
    }

@app.get("/get_reels")
def get_reels():
    try:
        # 1. Check Variables
        if not MONGO_URL or not SESSION_ID:
            return {"status": "error", "message": "Environment Variables Missing on Vercel!"}

        # 2. Connect DB
        try:
            client = MongoClient(MONGO_URL, serverSelectionTimeoutMS=5000) # 5 sec timeout
            db = client["InstaStreamBot"]
            # Test connection
            client.server_info()
        except Exception as e:
            return {"status": "error", "message": f"MongoDB Connection Failed: {str(e)}"}

        # 3. Login with Session
        try:
            print("Login try kar raha hoon...")
            cl.login_by_sessionid(SESSION_ID)
        except Exception as e:
            return {"status": "error", "message": f"Instagram Login Failed: {str(e)}"}

        # 4. Fetch Reels
        try:
            medias = cl.hashtag_medias_top("reels", amount=10)
            data = []
            for media in medias:
                if media.media_type == 2:
                    data.append({
                        "video_url": media.video_url,
                        "username": media.user.username
                    })
                    if len(data) >= 5: break
            
            return {"status": "success", "data": data}
        except Exception as e:
            return {"status": "error", "message": f"Fetching Reels Failed: {str(e)}"}

    except Exception as e:
        # Ye critical error ko pakad ke screen pe dikhayega
        return {
            "status": "critical_error", 
            "message": str(e), 
            "trace": traceback.format_exc()
        }
        
