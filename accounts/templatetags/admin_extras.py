from django import template
from accounts.models import User
from exams.models import Subject, Question, StudyGuide

register = template.Library()

@register.simple_tag
def admin_user_count():
    return User.objects.count()

@register.simple_tag
def admin_subject_count():
    return Subject.objects.count()

@register.simple_tag
def admin_question_count():
    return Question.objects.count()

@register.simple_tag
def admin_guide_count():
    return StudyGuide.objects.filter(active=True).count()
