from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Avg, Max, Count
from quizzes.models import QuizResult, QuizSession, Category
from datetime import datetime

@login_required
def index(request):
    user = request.user
    
    # Basic statistics
    results = QuizResult.objects.filter(quiz_session__user=user)
    total_quizzes = results.count()
    avg_score = results.aggregate(Avg('percentage'))['percentage__avg'] or 0
    best_score = results.aggregate(Max('percentage'))['percentage__max'] or 0
    
    # Recent activity (Last 5 completed quizzes)
    recent_quizzes = results.select_related('quiz_session__subcategory__category').order_by('-quiz_session__completed_at')[:5]
    
    # Incomplete quizzes
    incomplete_quizzes = QuizSession.objects.filter(
        user=user, 
        result__isnull=True
    ).select_related('subcategory__category').order_by('-created_at')[:5]
    
    # Chart Data: Category-wise distribution
    category_data = results.values('quiz_session__subcategory__category__name').annotate(
        count=Count('id')
    ).order_by('-count')
    
    category_labels = [item['quiz_session__subcategory__category__name'] for item in category_data]
    category_counts = [item['count'] for item in category_data]
    
    # Chart Data: Score Trends (Last 10 quizzes)
    trend_results = results.order_by('quiz_session__completed_at')
    if trend_results.count() > 10:
        trend_results = trend_results[trend_results.count()-10:]
    
    trend_labels = [r.quiz_session.completed_at.strftime('%m/%d') if r.quiz_session.completed_at else 'N/A' for r in trend_results]
    trend_scores = [r.percentage for r in trend_results]

    from users.models import UserProfile
    profile, created = UserProfile.objects.get_or_create(user=user)
    
    context = {
        'profile': profile,
        'total_quizzes': total_quizzes,
        'avg_score': round(avg_score, 1),
        'best_score': round(best_score, 1),
        'recent_quizzes': recent_quizzes,
        'incomplete_quizzes': incomplete_quizzes,
        'category_labels': category_labels,
        'category_counts': category_counts,
        'trend_labels': trend_labels,
        'trend_scores': trend_scores,
    }
    
    return render(request, 'dashboard/index.html', context)
