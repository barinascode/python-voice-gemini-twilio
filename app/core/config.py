import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
    TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
    TWILIO_PHONE_NUMBER = os.getenv("TWILIO_PHONE_NUMBER")
    
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    GEMINI_MODEL = "models/gemini-2.5-flash-native-audio-latest"
    
    PUBLIC_URL = os.getenv("PUBLIC_URL", "none")

settings = Settings()
