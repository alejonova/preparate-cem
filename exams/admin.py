import csv
import io
import json

from django import forms
from django.contrib import admin, messages
from django.db import transaction
from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.urls import path, reverse

from .models import Subject, Question, ExamResult, StudyGuide
from accounts.email_utils import send_new_guide_email
from accounts.models import User


class QuestionImportForm(forms.Form):
    subject = forms.ModelChoiceField(
        label='Materia',
        queryset=Subject.objects.all().order_by('name'),
        help_text='Selecciona la materia a la que pertenecen las preguntas.'
    )
    file = forms.FileField(
        label='Archivo del banco',
        help_text='Formatos aceptados: JSON o CSV.'
    )
    update_existing = forms.BooleanField(
        label='Actualizar preguntas existentes',
        required=False,
        initial=True,
        help_text='Si está marcada, una pregunta con el mismo número será reemplazada por la versión importada.'
    )

    def clean_file(self):
        uploaded = self.cleaned_data['file']
        name = uploaded.name.lower()
        if not (name.endswith('.json') or name.endswith('.csv')):
            raise forms.ValidationError('El archivo debe tener extensión .json o .csv.')
        if uploaded.size > 10 * 1024 * 1024:
            raise forms.ValidationError('El archivo no puede superar 10 MB.')
        return uploaded

    def parse_questions(self):
        uploaded = self.cleaned_data['file']
        raw = uploaded.read()
        try:
            text = raw.decode('utf-8-sig')
        except UnicodeDecodeError:
            raise forms.ValidationError('El archivo debe estar codificado en UTF-8.')

        if uploaded.name.lower().endswith('.json'):
            try:
                data = json.loads(text)
            except json.JSONDecodeError as exc:
                raise forms.ValidationError(f'JSON inválido: {exc}')
            if not isinstance(data, list):
                raise forms.ValidationError('El JSON debe contener una lista de preguntas.')
        else:
            reader = csv.DictReader(io.StringIO(text))
            required = {'number', 'text', 'option_a', 'option_b', 'option_c', 'option_d', 'correct_option'}
            if not reader.fieldnames or not required.issubset(set(reader.fieldnames)):
                raise forms.ValidationError(
                    'El CSV debe incluir las columnas: number,text,option_a,option_b,option_c,option_d,correct_option.'
                )
            data = list(reader)

        normalized = []
        seen = set()
        for index, item in enumerate(data, start=1):
            if not isinstance(item, dict):
                raise forms.ValidationError(f'La entrada {index} no tiene un formato válido.')
            try:
                number = int(item.get('number'))
            except (TypeError, ValueError):
                raise forms.ValidationError(f'La entrada {index} tiene un número inválido.')
            if number <= 0:
                raise forms.ValidationError(f'La entrada {index} tiene un número inválido.')
            if number in seen:
                raise forms.ValidationError(f'El número de pregunta {number} está repetido en el archivo.')
            seen.add(number)

            values = {key: str(item.get(key, '')).strip() for key in ('text', 'option_a', 'option_b', 'option_c', 'option_d')}
            if any(not value for value in values.values()):
                raise forms.ValidationError(f'La pregunta {number} tiene campos de texto vacíos.')
            correct = str(item.get('correct_option', '')).strip().upper()
            if correct not in 'ABCD':
                raise forms.ValidationError(f'La pregunta {number} tiene una respuesta correcta inválida: {correct}.')
            normalized.append({**values, 'number': number, 'correct_option': correct})
        if not normalized:
            raise forms.ValidationError('El archivo no contiene preguntas.')
        return normalized


@admin.action(description='Habilitar usuarios seleccionados')
def activate_users(modeladmin, request, queryset):
    from accounts.models import User
    updated = queryset.update(status=User.Status.ACTIVE)
    messages.success(request, f'{updated} usuario(s) habilitado(s).')


@admin.action(description='Deshabilitar usuarios seleccionados')
def disable_users(modeladmin, request, queryset):
    from accounts.models import User
    updated = queryset.update(status=User.Status.DISABLED)
    messages.success(request, f'{updated} usuario(s) deshabilitado(s).')


class ImportableQuestionAdmin(admin.ModelAdmin):
    list_display = ('number', 'subject', 'question_preview', 'correct_option')
    list_filter = ('subject', 'correct_option')
    search_fields = ('text', 'option_a', 'option_b', 'option_c', 'option_d')
    ordering = ('subject', 'number')
    list_per_page = 30

    fieldsets = (
        ('Identificación', {'fields': ('subject', 'number')}),
        ('Pregunta', {'fields': ('text',)}),
        ('Opciones de respuesta', {'fields': ('option_a', 'option_b', 'option_c', 'option_d')}),
        ('Clave', {'fields': ('correct_option',)}),
    )

    def question_preview(self, obj):
        text = obj.text.replace('\n', ' ').strip()
        return text[:90] + ('…' if len(text) > 90 else '')
    question_preview.short_description = 'pregunta'

    def get_urls(self):
        urls = super().get_urls()
        custom = [
            path(
                'importar-banco/',
                self.admin_site.admin_view(self.import_bank),
                name='question_import_bank',
            ),
        ]
        return custom + urls

    def import_bank(self, request):
        if request.method == 'POST':
            form = QuestionImportForm(request.POST, request.FILES)
            if form.is_valid():
                try:
                    questions = form.parse_questions()
                except forms.ValidationError as exc:
                    form.add_error('file', exc)
                else:
                    subject = form.cleaned_data['subject']
                    update_existing = form.cleaned_data['update_existing']
                    created = updated = 0
                    if not update_existing:
                        duplicate_numbers = list(
                            Question.objects.filter(subject=subject, number__in=[item['number'] for item in questions])
                            .values_list('number', flat=True)
                        )
                        if duplicate_numbers:
                            form.add_error(
                                'file',
                                'Ya existen las preguntas: ' + ', '.join(map(str, sorted(duplicate_numbers))) + '. Activa la opción de actualización.'
                            )
                        else:
                            duplicate_numbers = []
                    if form.errors:
                        pass
                    else:
                        with transaction.atomic():
                            for item in questions:
                                existing = Question.objects.filter(subject=subject, number=item['number']).first()
                                if existing:
                                    for field in ('text', 'option_a', 'option_b', 'option_c', 'option_d', 'correct_option'):
                                        setattr(existing, field, item[field])
                                    existing.save(update_fields=['text', 'option_a', 'option_b', 'option_c', 'option_d', 'correct_option'])
                                    updated += 1
                                else:
                                    Question.objects.create(subject=subject, **item)
                                    created += 1
                        messages.success(request, f'Importación completada: {created} creadas y {updated} actualizadas en «{subject}».')
                        return HttpResponseRedirect(reverse('admin:exams_question_changelist'))
        else:
            form = QuestionImportForm()
        context = {
            **self.admin_site.each_context(request),
            'title': 'Importar banco de preguntas',
            'form': form,
            'opts': self.model._meta,
        }
        return render(request, 'admin/exams/question/import.html', context)


@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = ('name', 'question_count', 'active')
    list_filter = ('active',)
    search_fields = ('name', 'description')
    ordering = ('name',)
    list_per_page = 25

    fieldsets = (
        ('Materia', {'fields': ('name', 'description', 'active')}),
    )

    def question_count(self, obj):
        return obj.questions.count()
    question_count.short_description = 'preguntas'


@admin.register(Question)
class QuestionAdmin(ImportableQuestionAdmin):
    pass


# Los resultados son parte del funcionamiento interno de la aplicación y no se muestran
# en la interfaz administrativa de esta primera versión.
try:
    admin.site.unregister(ExamResult)
except admin.sites.NotRegistered:
    pass

@admin.register(StudyGuide)
class StudyGuideAdmin(admin.ModelAdmin):
    list_display = ('title', 'subject', 'active', 'uploaded_at')
    list_filter = ('subject', 'active')
    search_fields = ('title', 'description', 'subject__name')
    ordering = ('subject', 'title')
    list_per_page = 25
    fieldsets = (
        ('Guía de estudio', {'fields': ('subject', 'title', 'description', 'file', 'active')}),
    )

    def save_model(self, request, obj, form, change):
        is_new = not obj.pk
        super().save_model(request, obj, form, change)
        if is_new and obj.active:
            users = User.objects.filter(status=User.Status.ACTIVE, role=User.Role.USER).exclude(email='')
            failed = 0
            sent = 0
            for user in users:
                ok, _ = send_new_guide_email(user, obj)
                if ok:
                    sent += 1
                else:
                    failed += 1
            if sent:
                messages.success(request, f'Se notificó por correo a {sent} usuario(s) activos sobre la nueva guía.')
            if failed:
                messages.warning(request, f'{failed} correo(s) de notificación de la nueva guía no pudieron enviarse.')
