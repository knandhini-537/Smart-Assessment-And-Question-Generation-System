from django.urls import path
from django.views.generic import RedirectView
from . import views

app_name = 'quizzes'

urlpatterns = [
    path('', RedirectView.as_view(pattern_name='quizzes:category_list', permanent=False)),
    path('categories/', views.category_list, name='category_list'),
    path('subcategories/<int:category_id>/', views.get_subcategories, name='get_subcategories'),
    path('configure/<int:subcategory_id>/', views.quiz_setup, name='quiz_setup'),
    path('generate/', views.start_generation, name='start_generation'),
    path('process-generation/', views.process_generation, name='process_generation'),
    path('play/', views.play_quiz, name='play_quiz'),
    path('submit-answer/', views.submit_answer, name='submit_answer'),
    path('results/', views.quiz_results, name='quiz_results'),
    path('progress/', views.user_progress, name='user_progress'),
    path('history/', views.quiz_history, name='quiz_history'),
    path('leaderboard/', views.leaderboard, name='leaderboard'),
    path('ai-suggest-topics/<int:category_id>/', views.ai_generate_topics, name='ai_suggest_topics'),
    path('resume/<int:session_id>/', views.resume_quiz, name='resume_quiz'),
    path('abandon/<int:session_id>/', views.abandon_quiz, name='abandon_quiz'),
    path('retake/<int:session_id>/', views.retake_quiz, name='retake_quiz'),
    path('compare/', views.compare_attempts, name='compare_attempts'),
    path('leaderboard/toggle/', views.toggle_leaderboard, name='toggle_leaderboard'),
    path('delete/<int:session_id>/', views.delete_quiz, name='delete_quiz'),
]
