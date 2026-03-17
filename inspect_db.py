import os
import django
import json

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.settings')
django.setup()

from quizzes.models import Question, QuizSession, QuizResult, UserAnswer

print("--- Quiz Results ---")
results = QuizResult.objects.all().order_by('-id')[:5]
for r in results:
    print(f"Session ID: {r.quiz_session.id}, Subcategory: {r.quiz_session.subcategory.name}")
    print(f"Score: {r.score}/{r.total_questions}, Percentage: {r.percentage}%")
    print("-" * 10)

print("\n--- Recent Questions ---")
questions = Question.objects.all().order_by('-id')[:5]
for q in questions:
    print(f"ID: {q.id}, Text: {q.text[:50]}...")
    print(f"Options Type: {type(q.options)}")
    print(f"Options: {q.options}")
    print(f"Correct: {q.correct_answer}")
    print("-" * 10)

print("\n--- User Answers ---")
answers = UserAnswer.objects.all().order_by('-id')[:5]
for a in answers:
    print(f"Session ID: {a.quiz_session.id}, Question ID: {a.question.id}, Correct: {a.is_correct}")
