# Generated by Django 5.1.3 on 2024-11-25 11:54

from django.db import migrations, models

def clear_invalid_json(apps, schema_editor):
    FileAnalysis = apps.get_model('core', 'FileAnalysis')
    TagList = apps.get_model('core', 'TagList')
    
    # Czyścimy wszystkie keywords w FileAnalysis
    FileAnalysis.objects.all().update(keywords=None)
    
    # Usuwamy wszystkie TagList
    TagList.objects.all().delete()

class Migration(migrations.Migration):

    dependencies = [
        ('core', '0003_fileanalysis_raw_content'),  # Zmieniamy zależność na istniejącą migrację
    ]

    operations = [
        # Najpierw czyścimy dane
        migrations.RunPython(clear_invalid_json),
        
        # Następnie zmieniamy typ pól
        migrations.AlterField(
            model_name='fileanalysis',
            name='keywords',
            field=models.JSONField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='taglist',
            name='tags',
            field=models.JSONField(),
        ),
    ]
