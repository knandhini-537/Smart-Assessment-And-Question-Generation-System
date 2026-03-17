import os
import django
import random
from datetime import timedelta
from django.utils import timezone

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.settings')
django.setup()

from django.contrib.auth.models import User
from quizzes.models import Category, Subcategory, QuizSession, QuizResult, Question, UserAnswer

def run():
    user = User.objects.first()
    if not user:
        user = User.objects.create_user('demo_user', 'demo@example.com', 'password123')
    
    print(f"Populating data for user: {user.username}")
    
    # Ensure categories and subcategories exist
    physics, _ = Subcategory.objects.get_or_create(
        name="Physics", 
        category=Category.objects.get_or_create(name="Academic")[0]
    )
    movies, _ = Subcategory.objects.get_or_create(
        name="Movies", 
        category=Category.objects.get_or_create(name="Entertainment")[0]
    )
    history, _ = Subcategory.objects.get_or_create(
        name="History", 
        category=Category.objects.get_or_create(name="General Knowledge")[0]
    )
    
    subcategories = [physics, movies, history]
    difficulties = ['easy', 'medium', 'hard']
    
    # Create 8 completed quiz sessions
    for i in range(8):
        sub = random.choice(subcategories)
        diff = random.choice(difficulties)
        
        # Quiz dates spread over last week
        completion_date = timezone.now() - timedelta(days=7-i, hours=random.randint(0, 23))
        
        session = QuizSession.objects.create(
            user=user,
            subcategory=sub,
            difficulty=diff,
            created_at=completion_date - timedelta(minutes=15),
            completed_at=completion_date,
            started_at=completion_date - timedelta(minutes=14),
            timer_duration=600
        )
        
        # Create questions
        total_questions = 5
        score = random.randint(3, 5)
        
        for j in range(total_questions):
            q = Question.objects.create(
                quiz_session=session,
                text=f"Sample question {j} for {sub.name}",
                options=["A", "B", "C", "D"],
                correct_answer="A"
            )
            
            # Create user answers
            UserAnswer.objects.create(
                quiz_session=session,
                question=q,
                selected_option="A" if j < score else "B",
                is_correct=(j < score)
            )
            
        percentage = (score / total_questions) * 100
        QuizResult.objects.create(
            quiz_session=session,
            score=score,
            total_questions=total_questions,
            percentage=percentage,
            passed=(percentage >= 60),
            time_taken=random.randint(200, 500)
        )
        
    # Create 2 incomplete sessions
    for i in range(2):
        sub = random.choice(subcategories)
        diff = random.choice(difficulties)
        QuizSession.objects.create(
            user=user,
            subcategory=sub,
            difficulty=diff,
            created_at=timezone.now() - timedelta(hours=i+1)
        )

    print("Mock data populated.")

if __name__ == "__main__":
    run()
