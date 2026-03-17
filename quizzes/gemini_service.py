import os
import json
import google.generativeai as genai
from django.conf import settings
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure Gemini
api_key = os.getenv("GOOGLE_API_KEY")
genai.configure(api_key=api_key)

def generate_quiz_questions(topic, difficulty, count):
    """
    Topic: The subcategory name
    Difficulty: 'easy', 'medium', or 'hard'
    Count: Number of questions
    """
    
    model_name = 'models/gemini-flash-latest'
    
    prompt = f"""
    Generate a quiz about {topic}.
    Difficulty level: {difficulty}.
    Number of questions: {count}.
    
    The response must be a valid JSON object with a single key "questions" which is a list of objects.
    Each question object must have:
    - "text": The question string.
    - "options": A list of exactly 4 strings.
    - "correct_answer": The exact string from the options list that is correct.
    - "explanation": A short explanation of why the answer is correct.
    
    Do not include any other text or markdown formatting in your response. Just the raw JSON.
    Important: Do NOT include question numbers in the "text" field.
    """

    try:
        model = genai.GenerativeModel(model_name,
                                      generation_config={"response_mime_type": "application/json"})
        
        print(f"Generating content for topic: {topic} using {model_name}...")
        
        # Simple retry logic for 429
        import time
        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = model.generate_content(prompt)
                break
            except Exception as e:
                if "429" in str(e) and attempt < max_retries - 1:
                    print(f"Quota exceeded. Retrying in {2**(attempt+1)} seconds...")
                    time.sleep(2**(attempt+1))
                else:
                    raise e
                    
        print("Response received from Gemini API.")
        
        content = response.text
        print(f"Content: {content}")
        data = json.loads(content)
        
        if "questions" in data:
            return data["questions"]
        else:
            print("Error: JSON response missing 'questions' key.")
            return None
            
    except Exception as e:
        import traceback
        error_msg = str(e)
        if "404" in error_msg:
            print(f"CRITICAL ERROR: Model '{model_name}' not found. Please check your API key permissions or model name.")
        elif "429" in error_msg:
            print(f"CRITICAL ERROR: API Quota exceeded. Please wait a minute or check your billing/limits.")
        else:
            traceback.print_exc()
            print(f"Error calling Gemini API: {e}")
        return None

def generate_subcategories(category_name):
    """
    Given a category name, generate 5 relevant subcategories.
    """
    model_name = 'models/gemini-flash-latest'
    
    prompt = f"""
    Suggest 5 specific quiz topics or subcategories for the general category: "{category_name}".
    Each suggestion should be interesting and distinct.
    
    The response must be a valid JSON object with a single key "subcategories" which is a list of objects.
    Each subcategory object must have:
    - "name": A short, catchy name for the topic.
    - "description": A brief one-sentence description.
    
    Do not include any other text or markdown formatting. Just the raw JSON.
    """

    try:
        model = genai.GenerativeModel(model_name,
                                      generation_config={"response_mime_type": "application/json"})
        
        response = model.generate_content(prompt)
        data = json.loads(response.text)
        
        if "subcategories" in data:
            return data["subcategories"]
        return None
    except Exception as e:
        print(f"Error generating subcategories: {e}")
        return None


if __name__ == "__main__":
    # Test script
    import sys
    # Mock django settings for standalone test if needed
    # (Actually we just need the environment variable)
    questions = generate_quiz_questions("Python Programming", "medium", 2)
    if questions:
        print(json.dumps(questions, indent=2))
    else:
        print("Failed to generate questions.")
