from django import forms

class QuizConfigForm(forms.Form):
    DIFFICULTY_CHOICES = [
        ('easy', 'Easy'),
        ('medium', 'Medium'),
        ('hard', 'Hard'),
    ]
    QUESTION_COUNT_CHOICES = [
        (5, '5 Questions'),
        (10, '10 Questions'),
        (15, '15 Questions'),
    ]
    
    difficulty = forms.ChoiceField(
        choices=DIFFICULTY_CHOICES, 
        widget=forms.RadioSelect(attrs={'class': 'btn-check'}),
        initial='medium'
    )
    question_count = forms.ChoiceField(
        choices=QUESTION_COUNT_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'}),
        initial=10
    )
    timer_enabled = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input', 'role': 'switch'}),
        initial=True,
        label="Enable Timer"
    )
