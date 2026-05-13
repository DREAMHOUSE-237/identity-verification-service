import uuid
from django.db import models


class VerificationStatus(models.TextChoices):
    PENDING  = 'pending',  'En attente'
    VERIFIED = 'verified', 'Vérifié'
    REJECTED = 'rejected', 'Rejeté'


class IdentityRecord(models.Model):
    """
    Stores CNI scan results submitted directly by the frontend.
    Identified by email only — no dependency on user service IDs.
    Fields extracted: nom, prenom, numero_cni only.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    email          = models.EmailField(unique=True, help_text="User's email — used to notify user service")
    requested_role = models.CharField(max_length=50, help_text="proprietaire or agence")

    # CNI images uploaded by the frontend
    cni_recto = models.ImageField(upload_to='cni/recto/', null=True, blank=True)
    cni_verso = models.ImageField(upload_to='cni/verso/', null=True, blank=True)

    # OCR extracted fields (simplified to 3 fields)
    nom_extrait    = models.CharField(max_length=150, blank=True, help_text="Nom extrait par OCR")
    prenom_extrait = models.CharField(max_length=150, blank=True, help_text="Prénom extrait par OCR")
    numero_cni     = models.CharField(max_length=100, blank=True, help_text="Numéro CNI extrait par OCR")

    # Raw OCR output (kept for debugging)
    raw_ocr_recto = models.TextField(blank=True)
    raw_ocr_verso = models.TextField(blank=True)

    # Status
    status = models.CharField(
        max_length=20,
        choices=VerificationStatus.choices,
        default=VerificationStatus.PENDING,
    )
    rejection_reason = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Identity Record"
        verbose_name_plural = "Identity Records"

    def __str__(self):
        return f"CNI {self.email} — {self.status}"


class ProcessedEvent(models.Model):
    event_id     = models.CharField(max_length=128, unique=True)
    processed_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.event_id
