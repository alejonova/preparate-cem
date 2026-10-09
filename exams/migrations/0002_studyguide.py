from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [('exams', '0001_initial')]
    operations = [
        migrations.CreateModel(
            name='StudyGuide',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=200, verbose_name='título')),
                ('description', models.TextField(blank=True, verbose_name='descripción')),
                ('file', models.FileField(upload_to='guias/', verbose_name='archivo PDF')),
                ('active', models.BooleanField(default=True, verbose_name='activa')),
                ('uploaded_at', models.DateTimeField(auto_now_add=True, verbose_name='fecha de carga')),
                ('subject', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='study_guides', to='exams.subject', verbose_name='materia')),
            ],
            options={'ordering': ['subject', 'title']},
        ),
    ]
