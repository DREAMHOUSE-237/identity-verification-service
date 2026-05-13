import logging
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.permissions import AllowAny
from django.http import JsonResponse

from .models import IdentityRecord, VerificationStatus
from .serializers import SubmitCNISerializer, IdentityRecordSerializer, ReviewSerializer
from .services.ocr_service import OCRService
from .utils.rabbit import publish_identity_result

logger = logging.getLogger(__name__)
ocr = OCRService()


def health(request):
    return JsonResponse({"status": "UP", "service": "identity-service"})


class SubmitCNIView(APIView):
    """
    POST /identity/submit/
    Called by the frontend after registration (optional — client is NOT forced to identify).
    Body (multipart/form-data):
      - email          : the user's email
      - requested_role : "proprietaire" or "agence"
      - cni_recto      : image file (optional)
      - cni_verso      : image file (optional)

    Flow:
      - OCR extracts: nom, prenom, numero_cni
      - If numero_cni found → auto-verified, user_service notified via RabbitMQ
      - If numero_cni NOT found → status=pending, admin must validate manually
    """
    permission_classes = [AllowAny]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def post(self, request):
        serializer = SubmitCNISerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        data           = serializer.validated_data
        email          = data['email']
        requested_role = data['requested_role']
        cni_recto      = data.get('cni_recto')
        cni_verso      = data.get('cni_verso')

        # Idempotent — don't process the same email twice
        existing = IdentityRecord.objects.filter(email=email).first()
        if existing:
            return Response(
                {
                    "message": "Une demande de vérification existe déjà pour cet email.",
                    "record_id": str(existing.id),
                    "status": existing.status,
                },
                status=status.HTTP_200_OK,
            )

        # Create record and save images
        record = IdentityRecord.objects.create(
            email=email,
            requested_role=requested_role,
            cni_recto=cni_recto,
            cni_verso=cni_verso,
            status=VerificationStatus.PENDING,
        )

        # Run OCR and auto-approve if numero_cni was extracted
        self._process(record)

        return Response(
            {
                "message": "CNI soumis. Vérification en cours.",
                "record_id": str(record.id),
                "status": record.status,
                "nom":        record.nom_extrait,
                "prenom":     record.prenom_extrait,
                "numero_cni": record.numero_cni,
            },
            status=status.HTTP_201_CREATED,
        )

    def _process(self, record: IdentityRecord):
        """Run OCR, extract nom/prenom/numero_cni, auto-approve if numero_cni found."""
        recto_text = ocr.extract_text(record.cni_recto.path) if record.cni_recto else ""
        verso_text = ocr.extract_text(record.cni_verso.path) if record.cni_verso else ""

        fields = ocr.parse_cni_fields(recto_text, verso_text)

        record.raw_ocr_recto  = recto_text
        record.raw_ocr_verso  = verso_text
        record.nom_extrait    = fields.get("nom", "")
        record.prenom_extrait = fields.get("prenom", "")
        record.numero_cni     = fields.get("numero_cni", "")

        if record.numero_cni:
            # Auto-approve: OCR successfully read the CNI number
            record.status = VerificationStatus.VERIFIED
            record.save()
            self._notify(record)
            logger.info("[identity] Auto-approved %s (numero_cni=%s)", record.email, record.numero_cni)
        else:
            # Pending: admin must validate manually
            record.status = VerificationStatus.PENDING
            record.save()
            logger.info("[identity] Pending manual review for %s — numero_cni not extracted", record.email)

    def _notify(self, record):
        try:
            publish_identity_result(record)
        except Exception as exc:
            logger.warning("Could not publish identity result: %s", exc)


class IdentityStatusView(APIView):
    """
    GET /identity/status/?email=<email>
    Frontend polls this to know if their verification is done.
    """
    permission_classes = [AllowAny]

    def get(self, request):
        email = request.query_params.get('email')
        if not email:
            return Response({"error": "email query param required."}, status=400)
        try:
            record = IdentityRecord.objects.get(email=email)
        except IdentityRecord.DoesNotExist:
            return Response({"error": "No verification request found for this email."}, status=404)
        return Response({
            "email":      record.email,
            "status":     record.status,
            "role":       record.requested_role,
            "record_id":  str(record.id),
            "nom":        record.nom_extrait,
            "prenom":     record.prenom_extrait,
            "numero_cni": record.numero_cni,
        })


class IdentityRecordDetailView(APIView):
    """GET /identity/<id>/ — Full record details (admin use)."""
    permission_classes = [AllowAny]

    def get(self, request, record_id):
        try:
            record = IdentityRecord.objects.get(id=record_id)
        except IdentityRecord.DoesNotExist:
            return Response({"error": "Record not found."}, status=404)
        return Response(IdentityRecordSerializer(record).data)


class ReviewIdentityView(APIView):
    """
    POST /identity/<id>/review/
    Admin manually validates a PENDING record.

    For APPROVAL: admin must provide nom, prenom, numero_cni
    Body: {
        "action": "approve",
        "nom": "DUPONT",
        "prenom": "Jean",
        "numero_cni": "123456789"
    }

    For REJECTION:
    Body: {
        "action": "reject",
        "rejection_reason": "Document illisible"
    }
    """
    permission_classes = [AllowAny]

    def post(self, request, record_id):
        try:
            record = IdentityRecord.objects.get(id=record_id)
        except IdentityRecord.DoesNotExist:
            return Response({"error": "Record not found."}, status=404)

        if record.status != VerificationStatus.PENDING:
            return Response(
                {"error": f"Record already '{record.status}'. Cannot review again."},
                status=400,
            )

        serializer = ReviewSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=400)

        action = serializer.validated_data['action']

        if action == 'approve':
            # Admin fills in the 3 fields manually
            record.nom_extrait    = serializer.validated_data['nom']
            record.prenom_extrait = serializer.validated_data['prenom']
            record.numero_cni     = serializer.validated_data['numero_cni']
            record.status         = VerificationStatus.VERIFIED
            record.rejection_reason = ""
        else:
            record.status           = VerificationStatus.REJECTED
            record.rejection_reason = serializer.validated_data.get('rejection_reason', '')

        record.save()

        try:
            publish_identity_result(record)
        except Exception as exc:
            logger.warning("Could not publish review result: %s", exc)

        return Response({
            "message":    f"Record {action}d.",
            "status":     record.status,
            "nom":        record.nom_extrait,
            "prenom":     record.prenom_extrait,
            "numero_cni": record.numero_cni,
        })


class PendingRecordsView(APIView):
    """GET /identity/pending/ — All pending records for admin dashboard."""
    permission_classes = [AllowAny]

    def get(self, request):
        records = IdentityRecord.objects.filter(
            status=VerificationStatus.PENDING
        ).order_by('created_at')
        return Response(IdentityRecordSerializer(records, many=True).data)


class AllRecordsView(APIView):
    """GET /identity/all/ — All identity records (admin use)."""
    permission_classes = [AllowAny]

    def get(self, request):
        status_filter = request.query_params.get('status')
        qs = IdentityRecord.objects.all().order_by('-created_at')
        if status_filter:
            qs = qs.filter(status=status_filter)
        return Response(IdentityRecordSerializer(qs, many=True).data)
