# Generated by Django 5.1 on 2025-01-08 05:44

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0003_ticket_name'),
    ]

    operations = [
        migrations.AlterField(
            model_name='user',
            name='role',
            field=models.CharField(choices=[('ATTENDANTS', 'Attendants'), ('ADMIN', 'Admin'), ('CLIENT', 'Client')], max_length=50),
        ),
    ]
