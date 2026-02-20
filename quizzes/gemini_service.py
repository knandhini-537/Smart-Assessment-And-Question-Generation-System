import os
import json
import google.generativeai as genai
from django.conf import settings

# Configure Gemini
api_key = os.getenv("GOOGLE_API_KEY")
genai.configure(api_key=api_key)

def generate_quiz_questions(topic, difficulty, count):
    """
    Topic: The subcategory name
    Difficulty: 'easy', 'medium', or 'hard'
    Count: Number of questions
    """
    
    # Initialize the model
    model = genai.GenerativeModel('gemini-2.5-flash',
                                  generation_config={"response_mime_type": "application/json"})
    
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
        response = model.generate_content(prompt)
        
        content = response.text
        data = json.loads(content)
        
        if "questions" in data:
            return data["questions"]
        else:
            print("Error: JSON response missing 'questions' key.")
            return None
            
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"Error calling Gemini API: {e}")
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
