import requests
import json

# FastAPI server manzili
SERVER_URL = "http://localhost:8000/api/leads"

# Sinov uchun mijoz ma'lumotlari
sample_lead = {
    "full_name": "Aziz Rahimov",
    "instagram_username": "aziz_rahimov",
    "phone_number": "+998901234567"
}

def send_test_lead():
    print(f"Serverga sinov ma'lumoti yuborilmoqda: {SERVER_URL}")
    print(f"Ma'lumot: {json.dumps(sample_lead, indent=2, ensure_ascii=False)}")
    
    try:
        response = requests.post(SERVER_URL, json=sample_lead)
        print(f"\nStatus kodi: {response.status_code}")
        print("Server javobi:")
        print(json.dumps(response.json(), indent=2, ensure_ascii=False))
    except Exception as e:
        print(f"\nUlanishda xatolik yuz berdi: {e}")
        print("Iltimos, avval serverni `python run.py` buyrug'i orqali ishga tushiring!")

if __name__ == "__main__":
    send_test_lead()

