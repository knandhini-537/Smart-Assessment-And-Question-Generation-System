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
            Question.objects.create(
                quiz_session=quiz_session,
                text=q['text'],
                options=q['options'],
                correct_answer=q['correct_answer'],
                explanation=q.get('explanation', '')
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
    
    # Save user answer
    UserAnswer.objects.create(
        quiz_session=quiz_session,
        question=current_question,
        selected_option=selected_option,
        is_correct=is_correct
    )
    
    if is_correct:
        request.session['score'] = request.session.get('score', 0) + 1
        
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
    quiz_session_id = request.session.get('quiz_session_id')
    if not quiz_session_id:
        return redirect('quizzes:category_list')
        
    from .models import QuizSession, QuizResult
    from django.utils import timezone
    quiz_session = get_object_or_404(QuizSession, id=quiz_session_id)
    
    if not quiz_session.completed_at:
        quiz_session.completed_at = timezone.now()
        quiz_session.save()
    
    score = request.session.get('score', 0)
    questions = quiz_session.questions.all()
    total = questions.count()
    percentage = (score / total) * 100 if total > 0 else 0
    passed = percentage >= 60
    
    time_taken = (quiz_session.completed_at - quiz_session.started_at).total_seconds()
    
    result, created = QuizResult.objects.get_or_create(
        quiz_session=quiz_session,
        defaults={
            'score': score,
            'total_questions': total,
            'percentage': percentage,
            'passed': passed,
            'time_taken': int(time_taken)
        }
    )
    
    context = {
        'session': quiz_session,
        'result': result,
        'answers': quiz_session.user_answers.all().select_related('question')
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
def leaderboard(request):
    from .models import QuizResult
    from django.db.models import Sum, Q, Count
    from django.contrib.auth.models import User
    
    # Rank users by total score (simple ranking)
    rankings = User.objects.annotate(
        total_score=Sum('quizsession__result__score'),
        quizzes_completed=Count('quizsession', filter=Q(quizsession__completed_at__isnull=False))
    ).filter(quizzes_completed__gt=0).order_by('-total_score')[:10]
    
    return render(request, 'quizzes/leaderboard.html', {'rankings': rankings})

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
