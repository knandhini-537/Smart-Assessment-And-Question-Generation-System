import os
import json
from openai import OpenAI
from django.conf import settings

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def generate_quiz_questions(topic, difficulty, count):
    """
    Topic: The subcategory name
    Difficulty: 'easy', 'medium', or 'hard'
    Count: Number of questions
    """
    
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
    """

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini", # or "gpt-3.5-turbo" depending on preference/cost
            messages=[
                {"role": "system", "content": "You are a quiz generation assistant that outputs only structured JSON."},
                {"role": "user", "content": prompt}
            ],
            response_format={ "type": "json_object" }
        )
        
        content = response.choices[0].message.content
        data = json.loads(content)
        
        if "questions" in data:
            return data["questions"]
        else:
            print("Error: JSON response missing 'questions' key.")
            return None
            
    except Exception as e:
        print(f"Error calling OpenAI API: {e}")
        return None
