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
    
    questions = generate_quiz_questions(
        topic=settings_data['subcategory_name'],
        difficulty=settings_data['difficulty'],
        count=settings_data['question_count']
    )
    
    if questions:
        request.session['generated_questions'] = questions
        request.session['current_question_index'] = 0
        request.session['score'] = 0
        return JsonResponse({'status': 'success'})
    else:
        return JsonResponse({'status': 'error', 'message': 'Failed to generate questions'}, status=500)

@login_required
def play_quiz(request):
    questions = request.session.get('generated_questions')
    if not questions:
        return redirect('quizzes:category_list')
    
    index = request.session.get('current_question_index', 0)
    if index >= len(questions):
        return redirect('quizzes:quiz_results')
        
    question = questions[index]
    return render(request, 'quizzes/quiz_play.html', {
        'question': question,
        'index': index + 1,
        'total': len(questions),
        'settings': request.session.get('quiz_settings')
    })

@login_required
def submit_answer(request):
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Invalid request'}, status=400)
        
    import json
    data = json.loads(request.body)
    selected_option = data.get('answer')
    
    questions = request.session.get('generated_questions')
    index = request.session.get('current_question_index', 0)
    
    if not questions or index >= len(questions):
        return JsonResponse({'status': 'error', 'message': 'Quiz not in progress'}, status=400)
        
    current_question = questions[index]
    is_correct = selected_option == current_question['correct_answer']
    
    if is_correct:
        request.session['score'] = request.session.get('score', 0) + 1
        
    request.session['current_question_index'] = index + 1
    
    return JsonResponse({
        'status': 'success',
        'is_correct': is_correct,
        'correct_answer': current_question['correct_answer'],
        'explanation': current_question.get('explanation', '')
    })

@login_required
def quiz_results(request):
    settings = request.session.get('quiz_settings')
    score = request.session.get('score', 0)
    questions = request.session.get('generated_questions')
    
    if not questions:
        return redirect('quizzes:category_list')
        
    total = len(questions)
    percentage = (score / total) * 100 if total > 0 else 0
    
    context = {
        'settings': settings,
        'score': score,
        'total': total,
        'percentage': int(percentage)
    }
    
    return render(request, 'quizzes/quiz_results.html', context)
