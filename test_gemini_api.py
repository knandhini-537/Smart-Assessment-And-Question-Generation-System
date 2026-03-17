import os
import json
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("GOOGLE_API_KEY")
genai.configure(api_key=api_key)

def test_generation():
    model_name = 'models/gemini-flash-latest'
    prompt = "Generate a quiz about Python. 2 questions. Return JSON with 'questions' key."
    
    try:
        model = genai.GenerativeModel(model_name, generation_config={"response_mime_type": "application/json"})
        response = model.generate_content(prompt)
        print(f"Status: SUCCESS")
        print(f"Response: {response.text}")
        return True
    except Exception as e:
        print(f"Status: FAILED")
        print(f"Error: {e}")
        return False

if __name__ == "__main__":
    test_generation()
