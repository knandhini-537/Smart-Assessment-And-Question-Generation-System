from django.db import models
from django.contrib.auth.models import User

class Category(models.Model):
    name = models.CharField(max_length=100)
    icon = models.CharField(max_length=50, help_text="FontAwesome icon class name (e.g., fa-book)", blank=True)
    image = models.ImageField(upload_to='category_images/', blank=True, null=True)
    description = models.TextField(blank=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name_plural = "Categories"

class Subcategory(models.Model):
    category = models.ForeignKey(Category, related_name='subcategories', on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)

    def __str__(self):
        return f"{self.category.name} - {self.name}"

    class Meta:
        verbose_name_plural = "Subcategories"

class QuizSession(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    subcategory = models.ForeignKey(Subcategory, on_delete=models.CASCADE)
    difficulty = models.CharField(max_length=20)
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    timer_duration = models.IntegerField(default=0) # in seconds
    started_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Quiz Session - {self.user.username} - {self.subcategory.name}"

class Question(models.Model):
    quiz_session = models.ForeignKey(QuizSession, related_name='questions', on_delete=models.CASCADE)
    text = models.TextField()
    options = models.JSONField() # Store list of options as JSON
    correct_answer = models.CharField(max_length=255)
    explanation = models.TextField(blank=True)

    def __str__(self):
        return f"Question for {self.quiz_session}"

class QuizResult(models.Model):
    quiz_session = models.OneToOneField(QuizSession, on_delete=models.CASCADE, related_name='result')
    score = models.IntegerField()
    total_questions = models.IntegerField()
    percentage = models.FloatField()
    passed = models.BooleanField()
    time_taken = models.IntegerField() # in seconds

    def __str__(self):
        return f"Result for {self.quiz_session}"

class UserAnswer(models.Model):
    quiz_session = models.ForeignKey(QuizSession, related_name='user_answers', on_delete=models.CASCADE)
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    selected_option = models.CharField(max_length=255)
    is_correct = models.BooleanField()

    def __str__(self):
        return f"Answer by {self.quiz_session.user.username} for {self.question}"
