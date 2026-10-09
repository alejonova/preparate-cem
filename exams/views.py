import random
from datetime import timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.conf import settings

from .models import ExamResult, Question, Subject
from accounts.models import User

EXAM_QUESTIONS = 40
EXAM_DURATION = timedelta(minutes=80)


def _active_exam(request):
    return request.session.get('active_exam')


@login_required
def home(request):
    if request.user.status == User.Status.PENDING and request.user.role != User.Role.ADMIN:
        return redirect('activation_portal')
    subjects = list(Subject.objects.filter(active=True).order_by('name'))
    results = list(ExamResult.objects.filter(user=request.user).select_related('subject').order_by('-finished_at'))
    best_by_subject = {}
    for result in results:
        current = best_by_subject.get(result.subject_id)
        if current is None or result.score > current.score:
            best_by_subject[result.subject_id] = result
    progress = []
    for subject in subjects:
        best = best_by_subject.get(subject.id)
        progress.append({
            'subject': subject,
            'score': float(best.score) if best else None,
        })
    attempted = [item for item in progress if item['score'] is not None]
    unattempted = [item for item in progress if item['score'] is None]
    recommendation = None
    if unattempted:
        recommendation = f"Te recomendamos comenzar por {unattempted[0]['subject'].name}, porque aún no has realizado ningún simulacro en esta materia."
    elif attempted:
        lowest = min(attempted, key=lambda item: item['score'])
        recommendation = f"Tu resultado más bajo corresponde a {lowest['subject'].name} ({lowest['score']:.2f}%). Te recomendamos practicar esta materia."
    return render(request, 'exams/home.html', {
        'progress': progress,
        'recommendation': recommendation,
    })


@login_required
def test_simulacro(request):
    if request.user.status == User.Status.PENDING and request.user.role != User.Role.ADMIN:
        return redirect('activation_portal')
    subjects = Subject.objects.filter(active=True).order_by('name')
    latest_by_subject = {}
    for result in ExamResult.objects.filter(user=request.user).select_related('subject'):
        latest_by_subject.setdefault(result.subject_id, result)
    return render(request, 'exams/test_simulacro.html', {
        'subjects': subjects,
        'latest_by_subject': latest_by_subject,
    })


@login_required
def activation_portal(request):
    if request.user.status != User.Status.PENDING or request.user.role == User.Role.ADMIN:
        return redirect('home')
    return render(request, 'registration/activation_portal.html', {'user': request.user, 'payment_breb_key': settings.PAYMENT_BREB_KEY})


@login_required
def subject_detail(request, subject_id):
    subject = get_object_or_404(Subject, pk=subject_id, active=True)
    results = list(
        ExamResult.objects.filter(user=request.user, subject=subject)
        .order_by('-finished_at')
    )
    latest_result = results[0] if results else None
    best_result = max(results, key=lambda result: (result.score, result.finished_at)) if results else None
    return render(request, 'exams/subject_detail.html', {
        'subject': subject,
        'results': results,
        'latest_result': latest_result,
        'best_result': best_result,
    })


@login_required
def start_exam(request, subject_id):
    if request.user.status != User.Status.ACTIVE and request.user.role != User.Role.ADMIN:
        return HttpResponseForbidden('Tu usuario aún no está habilitado para presentar exámenes.')
    subject = get_object_or_404(Subject, pk=subject_id, active=True)
    questions = list(Question.objects.filter(subject=subject))
    if len(questions) < EXAM_QUESTIONS:
        messages.error(request, 'Esta materia todavía no tiene 40 preguntas disponibles.')
        return redirect('home')

    selected = random.sample(questions, EXAM_QUESTIONS)
    shuffled_options = {}
    for question in selected:
        options = [
            {'text': question.option_a, 'original': 'A'},
            {'text': question.option_b, 'original': 'B'},
            {'text': question.option_c, 'original': 'C'},
            {'text': question.option_d, 'original': 'D'},
        ]
        random.shuffle(options)
        labels = ['A', 'B', 'C', 'D']
        shuffled_options[str(question.id)] = [
            {
                'label': label,
                'text': option['text'],
                'is_correct': option['original'] == question.correct_option,
            }
            for label, option in zip(labels, options)
        ]

    request.session['active_exam'] = {
        'subject_id': subject.id,
        'question_ids': [q.id for q in selected],
        'answers': {},
        'shuffled_options': shuffled_options,
        'current_position': 1,
        'started_at': timezone.now().isoformat(),
    }
    request.session.modified = True
    return redirect('exam_question', position=1)


def _remaining_seconds(exam):
    started = timezone.datetime.fromisoformat(exam['started_at'])
    if timezone.is_naive(started):
        started = timezone.make_aware(started, timezone.get_current_timezone())
    return max(0, int((started + EXAM_DURATION - timezone.now()).total_seconds()))


@login_required
def exam_question(request, position):
    exam = _active_exam(request)
    if not exam:
        return redirect('home')
    if position < 1 or position > EXAM_QUESTIONS:
        return redirect('finish_exam')

    # Una vez enviada una respuesta, la posición avanza y la anterior queda cerrada.
    # Esto también bloquea el botón Atrás del navegador para modificar preguntas previas.
    current_position = int(exam.get('current_position', 1))
    if position != current_position:
        if current_position <= EXAM_QUESTIONS:
            return redirect('exam_question', position=current_position)
        return redirect('finish_exam')

    remaining = _remaining_seconds(exam)
    if remaining <= 0:
        return redirect('finish_exam')

    qid = exam['question_ids'][position - 1]
    question = get_object_or_404(Question, pk=qid, subject_id=exam['subject_id'])
    options = exam.get('shuffled_options', {}).get(str(qid), [])

    if request.method == 'POST':
        answer = request.POST.get('answer', '')
        valid_answers = {option['label'] for option in options}
        if answer not in valid_answers:
            messages.error(request, 'Debes seleccionar una respuesta antes de continuar.')
            return render(request, 'exams/question.html', {
                'question': question,
                'subject': get_object_or_404(Subject, pk=exam['subject_id']),
                'position': position,
                'total': EXAM_QUESTIONS,
                'remaining_seconds': remaining,
                'options': options,
                'current': '',
            })

        # La respuesta queda registrada de forma definitiva al pulsar Siguiente.
        exam['answers'][str(qid)] = answer
        exam['current_position'] = position + 1
        request.session['active_exam'] = exam
        request.session.modified = True

        if _remaining_seconds(exam) <= 0 or position == EXAM_QUESTIONS:
            return redirect('finish_exam')
        return redirect('exam_question', position=position + 1)

    subject = get_object_or_404(Subject, pk=exam['subject_id'])
    return render(request, 'exams/question.html', {
        'question': question,
        'subject': subject,
        'position': position,
        'total': EXAM_QUESTIONS,
        'remaining_seconds': remaining,
        'options': options,
        'current': '',
    })


@login_required
def finish_exam(request):
    exam = _active_exam(request)
    if not exam:
        return redirect('home')
    subject = get_object_or_404(Subject, pk=exam['subject_id'])
    questions = list(Question.objects.filter(id__in=exam['question_ids'], subject=subject))
    by_id = {q.id: q for q in questions}
    answers = exam.get('answers', {})
    shuffled_options = exam.get('shuffled_options', {})
    correct = 0
    review = []
    for qid in exam['question_ids']:
        q = by_id[qid]
        selected = answers.get(str(qid), '')
        options = shuffled_options.get(str(qid), [])
        correct_label = next((option['label'] for option in options if option['is_correct']), '')
        is_correct = selected == correct_label
        correct += int(is_correct)
        review.append({
            'number': q.number,
            'text': q.text,
            'options': {option['label']: option['text'] for option in options},
            'selected': selected,
            'correct': correct_label,
            'is_correct': is_correct,
        })
    score = round((correct / EXAM_QUESTIONS) * 100, 2)
    result = ExamResult.objects.create(user=request.user, subject=subject,
                                       finished_at=timezone.now(), correct_answers=correct,
                                       total_questions=EXAM_QUESTIONS, score=score)
    request.session.pop('active_exam', None)
    request.session['last_review'] = {'result_id': result.id, 'subject': subject.name,
                                      'correct': correct, 'total': EXAM_QUESTIONS,
                                      'score': float(score), 'review': review}
    request.session.modified = True
    return redirect('exam_result')


@login_required
def exam_result(request):
    review = request.session.get('last_review')
    if not review:
        return redirect('home')
    request.session.pop('last_review', None)
    request.session.modified = True
    return render(request, 'exams/result.html', review)


@login_required
def history(request):
    results = ExamResult.objects.filter(user=request.user).select_related('subject')
    return render(request, 'exams/history.html', {'results': results})

@login_required
def study_guides(request):
    from .models import StudyGuide
    subjects = Subject.objects.filter(active=True).prefetch_related('study_guides')
    return render(request, 'exams/guides.html', {'subjects': subjects})


@login_required
def download_study_guide(request, guide_id):
    from django.http import FileResponse, Http404
    from .models import StudyGuide
    guide = get_object_or_404(StudyGuide, pk=guide_id, active=True, subject__active=True)
    if not guide.file or not guide.file.storage.exists(guide.file.name):
        raise Http404('La guía solicitada no está disponible.')
    response = FileResponse(guide.file.open('rb'), content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{guide.file.name.rsplit("/", 1)[-1]}"'
    return response
