from django.db import migrations, models
import uuid


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name='ProcessedEvent',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('event_id', models.CharField(max_length=128, unique=True)),
                ('processed_at', models.DateTimeField(auto_now_add=True)),
            ],
        ),
        migrations.CreateModel(
            name='IdentityRecord',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('email', models.EmailField(help_text="User's email — used to notify user service", unique=True)),
                ('requested_role', models.CharField(help_text='proprietaire or agence', max_length=50)),
                ('cni_recto', models.ImageField(blank=True, null=True, upload_to='cni/recto/')),
                ('cni_verso', models.ImageField(blank=True, null=True, upload_to='cni/verso/')),
                ('nom_extrait', models.CharField(blank=True, help_text='Nom extrait par OCR', max_length=150)),
                ('prenom_extrait', models.CharField(blank=True, help_text='Prénom extrait par OCR', max_length=150)),
                ('numero_cni', models.CharField(blank=True, help_text='Numéro CNI extrait par OCR', max_length=100)),
                ('raw_ocr_recto', models.TextField(blank=True)),
                ('raw_ocr_verso', models.TextField(blank=True)),
                ('status', models.CharField(
                    choices=[('pending', 'En attente'), ('verified', 'Vérifié'), ('rejected', 'Rejeté')],
                    default='pending', max_length=20,
                )),
                ('rejection_reason', models.TextField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={'verbose_name': 'Identity Record', 'verbose_name_plural': 'Identity Records'},
        ),
    ]
