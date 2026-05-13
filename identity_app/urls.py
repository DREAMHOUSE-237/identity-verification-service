from django.urls import path
from .views import (
    SubmitCNIView, IdentityStatusView, IdentityRecordDetailView,
    ReviewIdentityView, PendingRecordsView, AllRecordsView, health,
)

urlpatterns = [
    path('health/',                  health,                            name='health'),
    path('submit/',                  SubmitCNIView.as_view(),            name='submit-cni'),
    path('status/',                  IdentityStatusView.as_view(),       name='identity-status'),
    path('pending/',                 PendingRecordsView.as_view(),       name='pending-records'),
    path('all/',                     AllRecordsView.as_view(),           name='all-records'),
    path('<uuid:record_id>/',        IdentityRecordDetailView.as_view(), name='identity-detail'),
    path('<uuid:record_id>/review/', ReviewIdentityView.as_view(),       name='identity-review'),
]
