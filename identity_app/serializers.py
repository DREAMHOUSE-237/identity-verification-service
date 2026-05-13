from rest_framework import serializers
from .models import IdentityRecord


class IdentityRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model  = IdentityRecord
        fields = '__all__'
        read_only_fields = [
            'id', 'nom_extrait', 'prenom_extrait', 'numero_cni',
            'raw_ocr_recto', 'raw_ocr_verso', 'status',
            'created_at', 'updated_at',
        ]


class SubmitCNISerializer(serializers.Serializer):
    """Received directly from the frontend — CNI submission (optional)."""
    email          = serializers.EmailField()
    requested_role = serializers.ChoiceField(choices=['proprietaire', 'agence'])
    cni_recto      = serializers.ImageField(required=False)
    cni_verso      = serializers.ImageField(required=False)


class ReviewSerializer(serializers.Serializer):
    """
    Admin manual review payload.
    When action='approve' and OCR had failed, admin must provide the 3 CNI fields.
    """
    action           = serializers.ChoiceField(choices=['approve', 'reject'])
    rejection_reason = serializers.CharField(required=False, allow_blank=True)
    # Fields required when admin manually approves a pending record
    nom              = serializers.CharField(required=False, allow_blank=True)
    prenom           = serializers.CharField(required=False, allow_blank=True)
    numero_cni       = serializers.CharField(required=False, allow_blank=True)

    def validate(self, attrs):
        if attrs.get('action') == 'approve':
            # If manually approving, admin must provide the 3 CNI fields
            missing = [f for f in ['nom', 'prenom', 'numero_cni'] if not attrs.get(f)]
            if missing:
                raise serializers.ValidationError(
                    {f: f"Ce champ est requis pour l'approbation manuelle." for f in missing}
                )
        if attrs.get('action') == 'reject' and not attrs.get('rejection_reason'):
            raise serializers.ValidationError(
                {"rejection_reason": "La raison du rejet est requise."}
            )
        return attrs
