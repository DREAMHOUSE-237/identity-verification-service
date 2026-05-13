from django.contrib import admin
from .models import IdentityRecord, ProcessedEvent


@admin.register(IdentityRecord)
class IdentityRecordAdmin(admin.ModelAdmin):
    list_display   = ('email', 'requested_role', 'status', 'numero_cni', 'nom_extrait', 'prenom_extrait', 'created_at')
    list_filter    = ('status', 'requested_role')
    search_fields  = ('email', 'numero_cni', 'nom_extrait', 'prenom_extrait')
    readonly_fields = (
        'id', 'raw_ocr_recto', 'raw_ocr_verso', 'created_at', 'updated_at',
    )
    # Fields that admin can fill in manually
    fields = (
        'id', 'email', 'requested_role', 'cni_recto', 'cni_verso',
        'nom_extrait', 'prenom_extrait', 'numero_cni',
        'raw_ocr_recto', 'raw_ocr_verso',
        'status', 'rejection_reason',
        'created_at', 'updated_at',
    )
    actions = ['approve_selected', 'reject_selected']

    def approve_selected(self, request, queryset):
        from .utils.rabbit import publish_identity_result
        from .models import VerificationStatus
        updated = queryset.filter(status=VerificationStatus.PENDING)
        count = 0
        for record in updated:
            if not record.numero_cni:
                self.message_user(
                    request,
                    f"⚠ {record.email}: impossible d'approuver sans numero_cni. Utilisez l'endpoint /review/.",
                    level='WARNING',
                )
                continue
            record.status = VerificationStatus.VERIFIED
            record.save()
            try:
                publish_identity_result(record)
            except Exception:
                pass
            count += 1
        if count:
            self.message_user(request, f"{count} record(s) approved.")
    approve_selected.short_description = "Approuver les CNI sélectionnés (numero_cni requis)"

    def reject_selected(self, request, queryset):
        from .utils.rabbit import publish_identity_result
        from .models import VerificationStatus
        updated = queryset.filter(status=VerificationStatus.PENDING)
        for record in updated:
            record.status = VerificationStatus.REJECTED
            record.rejection_reason = "Rejeté manuellement via l'admin"
            record.save()
            try:
                publish_identity_result(record)
            except Exception:
                pass
        self.message_user(request, f"{updated.count()} record(s) rejected.")
    reject_selected.short_description = "Rejeter les CNI sélectionnés"


@admin.register(ProcessedEvent)
class ProcessedEventAdmin(admin.ModelAdmin):
    list_display = ('event_id', 'processed_at')
