from django.db import migrations, models
import django.db.models.deletion

class Migration(migrations.Migration):
    initial = True
    dependencies = [
        ('accounts', '0001_initial'),
    ]
    operations = [
        migrations.CreateModel(
            name='Subject',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=150, unique=True, verbose_name='materia')),
                ('description', models.TextField(blank=True, verbose_name='descripción')),
                ('active', models.BooleanField(default=True, verbose_name='activa')),
            ],
        ),
        migrations.CreateModel(
            name='Question',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('number', models.PositiveIntegerField(verbose_name='número')),
                ('text', models.TextField(verbose_name='pregunta')),
                ('option_a', models.TextField(verbose_name='opción A')),
                ('option_b', models.TextField(verbose_name='opción B')),
                ('option_c', models.TextField(verbose_name='opción C')),
                ('option_d', models.TextField(verbose_name='opción D')),
                ('correct_option', models.CharField(choices=[('A', 'A'), ('B', 'B'), ('C', 'C'), ('D', 'D')], max_length=1, verbose_name='respuesta correcta')),
                ('subject', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='questions', to='exams.subject')),
            ],
            options={'ordering': ['subject', 'number']},
        ),
        migrations.CreateModel(
            name='ExamResult',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('finished_at', models.DateTimeField(verbose_name='fecha y hora')),
                ('correct_answers', models.PositiveIntegerField(verbose_name='respuestas correctas')),
                ('total_questions', models.PositiveIntegerField(default=40, verbose_name='total de preguntas')),
                ('score', models.DecimalField(decimal_places=2, max_digits=5, verbose_name='puntaje')),
                ('subject', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='results', to='exams.subject')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='exam_results', to='accounts.user')),
            ],
            options={'ordering': ['-finished_at']},
        ),
        migrations.AddConstraint(
            model_name='question',
            constraint=models.UniqueConstraint(fields=('subject', 'number'), name='unique_question_number_per_subject'),
        ),
    ]
