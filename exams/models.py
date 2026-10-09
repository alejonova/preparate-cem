from django.conf import settings
from django.db import models
from django.core.validators import FileExtensionValidator


class Subject(models.Model):
    name = models.CharField('materia', max_length=150, unique=True)
    description = models.TextField('descripción', blank=True)
    active = models.BooleanField('activa', default=True)

    def __str__(self):
        return self.name


class Question(models.Model):
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='questions')
    number = models.PositiveIntegerField('número')
    text = models.TextField('pregunta')
    option_a = models.TextField('opción A')
    option_b = models.TextField('opción B')
    option_c = models.TextField('opción C')
    option_d = models.TextField('opción D')
    correct_option = models.CharField('respuesta correcta', max_length=1, choices=[(x, x) for x in 'ABCD'])

    class Meta:
        ordering = ['subject', 'number']
        constraints = [models.UniqueConstraint(fields=['subject', 'number'], name='unique_question_number_per_subject')]

    def __str__(self):
        return f'{self.subject} — pregunta {self.number}'


class ExamResult(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='exam_results')
    subject = models.ForeignKey(Subject, on_delete=models.PROTECT, related_name='results')
    finished_at = models.DateTimeField('fecha y hora')
    correct_answers = models.PositiveIntegerField('respuestas correctas')
    total_questions = models.PositiveIntegerField('total de preguntas', default=40)
    score = models.DecimalField('puntaje', max_digits=5, decimal_places=2)

    class Meta:
        ordering = ['-finished_at']

    def __str__(self):
        return f'{self.user} — {self.subject} — {self.score}'


class StudyGuide(models.Model):
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='study_guides', verbose_name='materia')
    title = models.CharField('título', max_length=200)
    description = models.TextField('descripción', blank=True)
    file = models.FileField('archivo PDF', upload_to='guias/', validators=[FileExtensionValidator(['pdf'])])
    active = models.BooleanField('activa', default=True)
    uploaded_at = models.DateTimeField('fecha de carga', auto_now_add=True)

    class Meta:
        ordering = ['subject', 'title']

    def __str__(self):
        return f'{self.subject} — {self.title}'
