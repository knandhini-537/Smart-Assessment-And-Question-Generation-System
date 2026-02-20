from quizzes.models import Category, Subcategory

def run():
    # Categories
    academic, created = Category.objects.get_or_create(
        name="Academic",
        defaults={"icon": "fa-graduation-cap", "description": "Knowledge related to education and science."}
    )
    entertainment, created = Category.objects.get_or_create(
        name="Entertainment",
        defaults={"icon": "fa-film", "description": "Movies, music, and pop culture."}
    )
    general_knowledge, created = Category.objects.get_or_create(
        name="General Knowledge",
        defaults={"icon": "fa-globe", "description": "General facts and trivia."}
    )

    # Subcategories for Academic
    Subcategory.objects.get_or_create(category=academic, name="Physics")
    Subcategory.objects.get_or_create(category=academic, name="Chemistry")
    Subcategory.objects.get_or_create(category=academic, name="Mathematics")
    Subcategory.objects.get_or_create(category=academic, name="Biology")

    # Subcategories for Entertainment
    Subcategory.objects.get_or_create(category=entertainment, name="Movies")
    Subcategory.objects.get_or_create(category=entertainment, name="Music")
    Subcategory.objects.get_or_create(category=entertainment, name="Television")

    # Subcategories for General Knowledge
    Subcategory.objects.get_or_create(category=general_knowledge, name="Geography")
    Subcategory.objects.get_or_create(category=general_knowledge, name="History")
    Subcategory.objects.get_or_create(category=general_knowledge, name="Sports")

    print("Initial data populated successfully.")

if __name__ == "__main__":
    import django
    import os
    import sys
    
    # Add the current directory to sys.path
    sys.path.append(os.getcwd())
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.settings')
    django.setup()
    run()
