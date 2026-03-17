from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from .models import Category, Subcategory
from .forms import QuizConfigForm
from django.contrib.auth.decorators import login_required
from django.contrib import messages

@login_required
def category_list(request):
    categories = Category.objects.all()
    return render(request, 'quizzes/category_list.html', {'categories': categories})

@login_required
def get_subcategories(request, category_id):
    category = get_object_or_404(Category, id=category_id)
    subcategories = category.subcategories.all().values('id', 'name', 'description')
    return JsonResponse(list(subcategories), safe=False)

@login_required
def quiz_setup(request, subcategory_id):
    subcategory = get_object_or_404(Subcategory, id=subcategory_id)
    
    if request.method == 'POST':
        form = QuizConfigForm(request.POST)
        if form.is_valid():
            request.session['quiz_settings'] = {
                'subcategory_id': subcategory.id,
                'subcategory_name': subcategory.name,
                'difficulty': form.cleaned_data['difficulty'],
                'question_count': int(form.cleaned_data['question_count']),
                'timer_enabled': form.cleaned_data['timer_enabled']
            }
            messages.success(request, f"Quiz configuration saved for {subcategory.name}!")
            # Clear any existing quiz session from django session
            if 'quiz_session_id' in request.session:
                del request.session['quiz_session_id']
            return redirect('quizzes:start_generation')
    else:
        form = QuizConfigForm()
        
    return render(request, 'quizzes/quiz_config.html', {
        'subcategory': subcategory,
        'form': form
    })

@login_required
def start_generation(request):
    settings = request.session.get('quiz_settings')
    if not settings:
        return redirect('quizzes:category_list')
    return render(request, 'quizzes/loading.html', {'settings': settings})

@login_required
def process_generation(request):
    settings_data = request.session.get('quiz_settings')
    if not settings_data:
        return JsonResponse({'status': 'error', 'message': 'No settings found'}, status=400)
    
    from .gemini_service import generate_quiz_questions
    from .models import QuizSession, Question, Subcategory
    
    subcategory = Subcategory.objects.get(id=settings_data['subcategory_id'])
    
    # Create a new Quiz Session
    quiz_session = QuizSession.objects.create(
        user=request.user,
        subcategory=subcategory,
        difficulty=settings_data['difficulty'],
        timer_duration=600 if settings_data.get('timer_enabled') else 0 # Default 10 mins if enabled
    )
    
    questions_data = generate_quiz_questions(
        topic=settings_data['subcategory_name'],
        difficulty=settings_data['difficulty'],
        count=settings_data['question_count']
    )
    
    if questions_data:
        # Save questions to DB
        for q in questions_data:
            # Handle potential AI-generated keys
            text = q.get('text') or q.get('question', '')
            options = q.get('options', [])
            correct_answer = q.get('correct_answer') or q.get('answer', '')
            explanation = q.get('explanation', '')
            
            # Basic cleanup: remove question numbers if AI included them (e.g. "1. Question text")
            import re
            text = re.sub(r'^\d+\.\s*', '', text)
            
            Question.objects.create(
                quiz_session=quiz_session,
                text=text,
                options=options,
                correct_answer=correct_answer,
                explanation=explanation
            )
        
        request.session['quiz_session_id'] = quiz_session.id
        request.session['current_question_index'] = 0
        request.session['score'] = 0
        return JsonResponse({'status': 'success'})
    else:
        quiz_session.delete() # Cleanup if generation fails
        return JsonResponse({'status': 'error', 'message': 'Failed to generate questions'}, status=500)

@login_required
def play_quiz(request):
    quiz_session_id = request.session.get('quiz_session_id')
    if not quiz_session_id:
        return redirect('quizzes:category_list')
    
    from .models import QuizSession
    from django.utils import timezone
    quiz_session = get_object_or_404(QuizSession, id=quiz_session_id)
    
    # Set started_at if not set (first question)
    if not quiz_session.started_at:
        quiz_session.started_at = timezone.now()
        quiz_session.save()
        
    questions = quiz_session.questions.all()
    
    index = request.session.get('current_question_index', 0)
    if index >= questions.count():
        return redirect('quizzes:quiz_results')
        
    # Calculate remaining time
    remaining_time = 0
    if quiz_session.timer_duration > 0:
        elapsed = (timezone.now() - quiz_session.started_at).total_seconds()
        remaining_time = max(0, int(quiz_session.timer_duration - elapsed))
        if remaining_time == 0:
            return redirect('quizzes:quiz_results')

    question = questions[index]
    return render(request, 'quizzes/quiz_play.html', {
        'question': question,
        'index': index + 1,
        'total': questions.count(),
        'settings': request.session.get('quiz_settings'),
        'quiz_session': quiz_session,
        'remaining_time': remaining_time
    })

@login_required
def submit_answer(request):
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Invalid request'}, status=400)
        
    import json
    data = json.loads(request.body)
    selected_option = data.get('answer')
    
    quiz_session_id = request.session.get('quiz_session_id')
    index = request.session.get('current_question_index', 0)
    
    from .models import QuizSession, UserAnswer
    quiz_session = QuizSession.objects.filter(id=quiz_session_id).first()
    
    if not quiz_session:
        return JsonResponse({'status': 'error', 'message': 'Quiz not in progress'}, status=400)
        
    questions = quiz_session.questions.all()
    if index >= questions.count():
        return JsonResponse({'status': 'error', 'message': 'No more questions'}, status=400)
        
    current_question = questions[index]
    is_correct = selected_option == current_question.correct_answer
    
    # Prevent multiple submissions for the same question
    if UserAnswer.objects.filter(quiz_session=quiz_session, question=current_question).exists():
        return JsonResponse({'status': 'error', 'message': 'Already answered'}, status=400)

    # Save user answer
    UserAnswer.objects.create(
        quiz_session=quiz_session,
        question=current_question,
        selected_option=selected_option,
        is_correct=is_correct
    )
    
    # Move to next question index
    request.session['current_question_index'] = index + 1
    request.session.modified = True
    
    return JsonResponse({
        'status': 'success',
        'is_correct': is_correct,
        'correct_answer': current_question.correct_answer,
        'explanation': current_question.explanation
    })

@login_required
def quiz_results(request):
    quiz_session_id = request.GET.get('session_id') or request.session.get('quiz_session_id')
    if not quiz_session_id:
        return redirect('quizzes:category_list')
        
    from .models import QuizSession, QuizResult
    from django.utils import timezone
    quiz_session = get_object_or_404(QuizSession, id=quiz_session_id)
    
    if not quiz_session.completed_at:
        quiz_session.completed_at = timezone.now()
        quiz_session.save()
    
    # Calculate score from DB instead of session to avoid 120% bugs
    score = quiz_session.user_answers.filter(is_correct=True).count()
    questions = quiz_session.questions.all()
    total = questions.count()
    percentage = (score / total) * 100 if total > 0 else 0
    passed = percentage >= 60
    
    time_taken = 0
    if quiz_session.completed_at and quiz_session.started_at:
        time_taken = (quiz_session.completed_at - quiz_session.started_at).total_seconds()
    
    result, created = QuizResult.objects.update_or_create(
        quiz_session=quiz_session,
        defaults={
            'score': score,
            'total_questions': total,
            'percentage': percentage,
            'passed': passed,
            'time_taken': int(time_taken)
        }
    )
    
    # Trend Analysis
    previous_result = QuizResult.objects.filter(
        quiz_session__user=request.user,
        quiz_session__subcategory=quiz_session.subcategory
    ).exclude(id=result.id).order_by('-quiz_session__completed_at').first()

    improvement_percentage = 0
    motivation_message = ""
    if previous_result:
        diff = result.percentage - previous_result.percentage
        if diff > 0:
            improvement_percentage = diff
        
        if diff > 10:
            motivation_message = "Look at that jump! You're crushing it! 🚀"
        elif diff > 0:
            motivation_message = "Stellar progress! Your hard work is paying off! ✨"
        elif result.percentage == 100:
            motivation_message = "Absolute Perfection! You're a legend! 🏆"
    elif result.percentage >= 80:
        motivation_message = "First try and already a pro? Impressive! 🌟"

    context = {
        'session': quiz_session,
        'result': result,
        'answers': quiz_session.user_answers.all().select_related('question'),
        'motivation_message': motivation_message,
        'improvement_percentage': improvement_percentage
    }
    
    return render(request, 'quizzes/quiz_results.html', context)
@login_required
def user_progress(request):
    from .models import QuizResult, QuizSession
    from django.db.models import Avg, Max, Count
    
    results = QuizResult.objects.filter(quiz_session__user=request.user).select_related('quiz_session', 'quiz_session__subcategory').order_by('-quiz_session__completed_at')
    
    stats = results.aggregate(
        avg_percentage=Avg('percentage'),
        max_percentage=Max('percentage'),
        total_quizzes=Count('id')
    )
    
    # Calculate pass rate
    total = stats['total_quizzes']
    passed = results.filter(passed=True).count()
    status_rate = (passed / total * 100) if total > 0 else 0
    
    context = {
        'results': results,
        'stats': stats,
        'pass_rate': round(status_rate, 1)
    }
    return render(request, 'quizzes/user_progress.html', context)

@login_required
def quiz_history(request):
    from .models import QuizResult, Category, Subcategory
    from django.core.paginator import Paginator
    from django.db.models import Q

    # Fetch filters from GET parameters
    category_id = request.GET.get('category')
    difficulty = request.GET.get('difficulty')
    sort_by = request.GET.get('sort', 'date_desc')
    search_query = request.GET.get('search', '')

    results = QuizResult.objects.filter(quiz_session__user=request.user).select_related(
        'quiz_session', 'quiz_session__subcategory', 'quiz_session__subcategory__category'
    )

    # Apply filters
    if category_id:
        results = results.filter(quiz_session__subcategory__category_id=category_id)
    if difficulty:
        results = results.filter(quiz_session__difficulty=difficulty)
    if search_query:
        results = results.filter(
            Q(quiz_session__subcategory__name__icontains=search_query) |
            Q(quiz_session__subcategory__category__name__icontains=search_query)
        )

    # Apply sorting
    valid_sorts = {
        'date_desc': '-quiz_session__completed_at',
        'date_asc': 'quiz_session__completed_at',
        'score_desc': '-percentage',
        'score_asc': 'percentage',
        'alpha': 'quiz_session__subcategory__name'
    }
    results = results.order_by(valid_sorts.get(sort_by, '-quiz_session__completed_at'))

    # Pagination
    paginator = Paginator(results, 10) # 10 per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    categories = Category.objects.all()

    context = {
        'page_obj': page_obj,
        'categories': categories,
        'current_category': category_id,
        'current_difficulty': difficulty,
        'current_sort': sort_by,
        'search_query': search_query,
    }
    return render(request, 'quizzes/history.html', context)

@login_required
def retake_quiz(request, session_id):
    from .models import QuizSession
    old_session = get_object_or_404(QuizSession, id=session_id, user=request.user)
    
    # Clone settings for a new session
    request.session['quiz_settings'] = {
        'subcategory_id': old_session.subcategory.id,
        'subcategory_name': old_session.subcategory.name,
        'difficulty': old_session.difficulty,
        'question_count': old_session.questions.count(),
        'timer_enabled': old_session.timer_duration > 0
    }
    
    # Clear active session
    if 'quiz_session_id' in request.session:
        del request.session['quiz_session_id']
        
    messages.info(request, f"Starting a retake for {old_session.subcategory.name}. New questions will be generated.")
    return redirect('quizzes:start_generation')

@login_required
def compare_attempts(request):
    from .models import QuizResult, Subcategory
    subcategory_id = request.GET.get('subcategory')
    difficulty = request.GET.get('difficulty')
    
    if not subcategory_id:
        return redirect('quizzes:quiz_history')
        
    subcategory = get_object_or_404(Subcategory, id=subcategory_id)
    results = QuizResult.objects.filter(
        quiz_session__user=request.user,
        quiz_session__subcategory=subcategory
    ).select_related('quiz_session').order_by('quiz_session__completed_at')
    
    if difficulty:
        results = results.filter(quiz_session__difficulty=difficulty)
        
    labels = [r.quiz_session.completed_at.strftime('%Y-%m-%d %H:%M') for r in results]
    scores = [r.percentage for r in results]
    times = [r.time_taken for r in results]
    
    context = {
        'subcategory': subcategory,
        'results': results,
        'labels': labels,
        'scores': scores,
        'times': times,
        'current_difficulty': difficulty
    }
    return render(request, 'quizzes/comparison.html', context)

@login_required
def leaderboard(request):
    from .models import QuizResult, Category
    from django.db.models import Sum, Q, Count, OuterRef, Subquery, Window, F
    from django.db.models.functions import Rank
    from django.contrib.auth.models import User
    
    category_id = request.GET.get('category')
    
    # Base queryset for users who want to be seen
    users = User.objects.filter(userprofile__show_on_leaderboard=True)
    
    # Aggregate scores
    rankings_query = users.annotate(
        total_score=Sum('quizsession__result__score', filter=Q(quizsession__completed_at__isnull=False)),
        quizzes_completed=Count('quizsession', filter=Q(quizsession__completed_at__isnull=False))
    ).filter(quizzes_completed__gt=0)
    
    if category_id:
        rankings_query = rankings_query.filter(quizsession__subcategory__category_id=category_id)
        # Re-calculate score/count specifically for this category if needed
        # For simplicity, we filter the sessions that contribute to the aggregate
        rankings_query = users.annotate(
            total_score=Sum('quizsession__result__score', filter=Q(quizsession__completed_at__isnull=False, quizsession__subcategory__category_id=category_id)),
            quizzes_completed=Count('quizsession', filter=Q(quizsession__completed_at__isnull=False, quizsession__subcategory__category_id=category_id))
        ).filter(quizzes_completed__gt=0)

    rankings = rankings_query.order_by('-total_score')[:10]
    
    # Find current user's rank
    user_rank = None
    if request.user.userprofile.show_on_leaderboard:
        # This is a bit expensive but okay for top users or small scale
        # Use window functions if possible (SQLite supports it in newer versions)
        all_rankings = rankings_query.order_by('-total_score')
        for i, u in enumerate(all_rankings):
            if u.id == request.user.id:
                user_rank = i + 1
                break
                
    categories = Category.objects.all()
    
    context = {
        'rankings': rankings,
        'user_rank': user_rank,
        'categories': categories,
        'current_category': category_id,
    }
    
    return render(request, 'quizzes/leaderboard.html', context)

@login_required
def toggle_leaderboard(request):
    profile = request.user.userprofile
    profile.show_on_leaderboard = not profile.show_on_leaderboard
    profile.save()
    messages.success(request, f"Leaderboard privacy updated. You are now {'visible' if profile.show_on_leaderboard else 'hidden'}.")
    return redirect('quizzes:leaderboard')

@login_required
def ai_generate_topics(request, category_id):
    category = get_object_or_404(Category, id=category_id)
    
    from .gemini_service import generate_subcategories
    from .models import Subcategory
    
    suggestions = generate_subcategories(category.name)
    
    if suggestions:
        new_topics = []
        for s in suggestions:
            # Avoid duplicates
            if not Subcategory.objects.filter(category=category, name=s['name']).exists():
                topic = Subcategory.objects.create(
                    category=category,
                    name=s['name'],
                    description=s['description']
                )
                new_topics.append({'id': topic.id, 'name': topic.name, 'description': topic.description})
        
        return JsonResponse({'status': 'success', 'topics': new_topics})
    
    return JsonResponse({'status': 'error', 'message': 'Failed to generate topics'}, status=500)

@login_required
def resume_quiz(request, session_id):
    from .models import QuizSession
    quiz_session = get_object_or_404(QuizSession, id=session_id, user=request.user)
    
    # Check if already completed
    if hasattr(quiz_session, 'result'):
        messages.info(request, "This quiz is already completed.")
        return redirect('quizzes:quiz_results')
    
    # Set session variables
    request.session['quiz_session_id'] = quiz_session.id
    from .models import UserAnswer
    completed_count = UserAnswer.objects.filter(quiz_session=quiz_session).count()
    request.session['current_question_index'] = completed_count
    request.session.modified = True
    
    return redirect('quizzes:play_quiz')

@login_required
def abandon_quiz(request, session_id):
    from .models import QuizSession
    quiz_session = get_object_or_404(QuizSession, id=session_id, user=request.user)
    
    if hasattr(quiz_session, 'result'):
        messages.error(request, "Cannot abandon a completed quiz.")
    else:
        quiz_session.delete()
        messages.success(request, "Quiz attempt abandoned.")
        # Clear session if it was the active one
        if request.session.get('quiz_session_id') == session_id:
            del request.session['quiz_session_id']
            del request.session['current_question_index']
    
    return redirect('dashboard')

@login_required
def delete_quiz(request, session_id):
    from .models import QuizSession
    quiz_session = get_object_or_404(QuizSession, id=session_id, user=request.user)
    quiz_session.delete()
    messages.success(request, "Quiz record deleted.")
    
    next_page = request.GET.get('next', 'dashboard')
    if next_page == 'history':
        return redirect('quizzes:quiz_history')
    return redirect('dashboard')
