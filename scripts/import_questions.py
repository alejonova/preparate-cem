#!/usr/bin/env python
import json
import sys
from pathlib import Path

import django

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from exams.models import Question, Subject

DEFAULT_DATA_DIR = BASE_DIR / 'data'


def import_file(path):
    data = json.loads(path.read_text(encoding='utf-8'))
    subject, _ = Subject.objects.get_or_create(
        name=data['subject'],
        defaults={'description': data.get('description', 'Banco de preguntas.')},
    )
    if data.get('description') and not subject.description:
        subject.description = data['description']
        subject.save(update_fields=['description'])

    created = updated = 0
    for item in data['questions']:
        obj, was_created = Question.objects.update_or_create(
            subject=subject,
            number=item['number'],
            defaults={
                'text': item['text'],
                'option_a': item['option_a'],
                'option_b': item['option_b'],
                'option_c': item['option_c'],
                'option_d': item['option_d'],
                'correct_option': item['correct_option'],
            },
        )
        if was_created:
            created += 1
        else:
            updated += 1
    print(f'Materia: {subject.name} | creadas: {created} | actualizadas: {updated} | total: {Question.objects.filter(subject=subject).count()}')


def main():
    if len(sys.argv) > 1:
        paths = [Path(sys.argv[1])]
    else:
        paths = sorted(DEFAULT_DATA_DIR.glob('banco_*.json'))

    if not paths:
        raise SystemExit('No se encontraron bancos JSON en data/.')

    for path in paths:
        import_file(path)


if __name__ == '__main__':
    main()
