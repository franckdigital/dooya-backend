from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('categories', '0001_initial'),
        ('users', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='user',
            name='role',
            field=models.CharField(
                choices=[
                    ('admin', 'Administrateur'),
                    ('vendor', 'Vendeur'),
                    ('customer', 'Client'),
                    ('delivery', 'Livreur'),
                    ('affiliate', 'Affilié'),
                    ('commercial', 'Commercial'),
                    ('assistance', 'Assistance'),
                ],
                default='customer',
                max_length=20,
            ),
        ),
        migrations.CreateModel(
            name='CommercialProfile',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('notes', models.TextField(blank=True)),
                ('is_active', models.BooleanField(default=True)),
                ('user', models.OneToOneField(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='commercial_profile',
                    to=settings.AUTH_USER_MODEL,
                )),
                ('categories', models.ManyToManyField(
                    blank=True,
                    related_name='commercials',
                    to='categories.category',
                )),
            ],
            options={
                'verbose_name': 'Profil commercial',
                'db_table': 'commercial_profiles',
            },
        ),
    ]
