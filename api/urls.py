from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from . import views
from .chat_views import ChatView, ChatReportView, ConversationListView, ConversationDetailView

urlpatterns = [
    path('auth/register', views.RegisterView.as_view(), name='register'),
    path('auth/login', views.LoginView.as_view(), name='login'),
    path('auth/refresh', TokenRefreshView.as_view(), name='token_refresh'),
    path('auth/profile', views.ProfileView.as_view(), name='profile'),

    path('symptoms', views.SymptomListView.as_view(), name='symptom-list'),
    path('symptoms/search', views.SymptomSearchView.as_view(), name='symptom-search'),

    path('diseases', views.DiseaseListView.as_view(), name='disease-list'),
    path('diseases/<int:pk>', views.DiseaseDetailView.as_view(), name='disease-detail'),

    path('diagnose', views.DiagnoseView.as_view(), name='diagnose'),
    path('diagnose-text', views.DiagnoseTextView.as_view(), name='diagnose-text'),

    path('upload-report', views.UploadReportView.as_view(), name='upload-report'),
    path('reports', views.ReportListView.as_view(), name='report-list'),
    path('reports/<int:pk>', views.ReportDetailView.as_view(), name='report-detail'),

    path('diet/<str:disease_name>', views.DietRecommendationView.as_view(), name='diet-recommendation'),
    path('medicines/<str:disease_name>', views.MedicineRecommendationView.as_view(), name='medicine-recommendation'),

    path('history', views.DiagnosisHistoryView.as_view(), name='diagnosis-history'),
    path('search-history', views.SearchHistoryView.as_view(), name='search-history'),

    path('hospitals', views.HospitalSearchView.as_view(), name='hospital-search'),

    path('admin/stats', views.AdminStatsView.as_view(), name='admin-stats'),
    path('admin/datasets', views.AdminDatasetListView.as_view(), name='admin-datasets'),
    path('admin/train', views.AdminTrainModelView.as_view(), name='admin-train'),
    path('admin/models', views.AdminModelListView.as_view(), name='admin-models'),
    path('admin/model/<int:pk>/activate', views.AdminModelActivateView.as_view(), name='admin-model-activate'),

    path('chat', ChatView.as_view(), name='chat'),
    path('chat/report', ChatReportView.as_view(), name='chat-report'),
    path('chat/conversations', ConversationListView.as_view(), name='conversation-list'),
    path('chat/conversations/<int:pk>', ConversationDetailView.as_view(), name='conversation-detail'),
]
