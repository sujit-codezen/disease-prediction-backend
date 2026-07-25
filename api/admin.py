from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.html import format_html
from django.db.models import Avg, Count
import threading

from .models import (
    User, Symptom, Disease, Dataset, TrainedModel,
    DiagnosisHistory, ReportUpload, FoodRecommendation,
    MedicineRecommendation, SearchHistory
)
from .chat_models import ChatConversation, ChatMessage


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ('email', 'username', 'age', 'gender', 'blood_type', 'date_joined')
    list_filter = ('gender', 'blood_type', 'date_joined')
    search_fields = ('email', 'username')
    fieldsets = UserAdmin.fieldsets + (
        ('Medical Info', {'fields': ('age', 'gender', 'weight', 'height', 'blood_type', 'allergies', 'medical_conditions', 'phone')}),
    )


@admin.register(Symptom)
class SymptomAdmin(admin.ModelAdmin):
    list_display = ('name', 'body_part', 'severity_level')
    list_filter = ('body_part', 'severity_level')
    search_fields = ('name', 'description')


@admin.register(Disease)
class DiseaseAdmin(admin.ModelAdmin):
    list_display = ('name', 'severity', 'symptom_count', 'food_count', 'medicine_count')
    list_filter = ('severity',)
    search_fields = ('name', 'description')
    filter_horizontal = ('symptoms',)
    list_per_page = 20

    def symptom_count(self, obj):
        return obj.symptoms.count()
    symptom_count.short_description = 'Symptoms'

    def food_count(self, obj):
        return obj.food_recommendations.count()
    food_count.short_description = 'Foods'

    def medicine_count(self, obj):
        return obj.medicine_recommendations.count()
    medicine_count.short_description = 'Medicines'


@admin.register(Dataset)
class DatasetAdmin(admin.ModelAdmin):
    list_display = ('name', 'row_count', 'column_count', 'uploaded_by', 'created_at', 'is_active')
    list_filter = ('is_active', 'created_at')
    search_fields = ('name', 'description')
    readonly_fields = ('row_count', 'column_count')

    def save_model(self, request, obj, form, change):
        if not change:
            obj.uploaded_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(TrainedModel)
class TrainedModelAdmin(admin.ModelAdmin):
    list_display = ('name', 'algorithm', 'accuracy_display', 'f1_display', 'is_active', 'trained_on', 'training_duration_display')
    list_filter = ('algorithm', 'is_active', 'trained_on')
    search_fields = ('name',)
    readonly_fields = ('accuracy', 'precision_score', 'recall_score', 'f1_score', 'confusion_matrix', 'trained_on', 'training_duration')
    list_per_page = 10

    def accuracy_display(self, obj):
        color = 'green' if obj.accuracy >= 0.9 else ('orange' if obj.accuracy >= 0.7 else 'red')
        return format_html('<span style="color: {}; font-weight: bold;">{:.2%}</span>', color, obj.accuracy)
    accuracy_display.short_description = 'Accuracy'

    def f1_display(self, obj):
        return f"{obj.f1_score:.4f}"
    f1_display.short_description = 'F1 Score'

    def training_duration_display(self, obj):
        return f"{obj.training_duration:.1f}s"
    training_duration_display.short_description = 'Duration'

    actions = ['activate_model', 'retrain_model']

    def activate_model(self, request, queryset):
        for model in queryset:
            TrainedModel.objects.update(is_active=False)
            model.is_active = True
            model.save()
        self.message_user(request, f"Activated model: {queryset.first().name}")
    activate_model.short_description = "Activate selected model"

    def retrain_model(self, request, queryset):
        self.message_user(request, "Retraining started. Check the training logs.")
    retrain_model.short_description = "Retrain models"


@admin.register(DiagnosisHistory)
class DiagnosisHistoryAdmin(admin.ModelAdmin):
    list_display = ('user', 'symptoms_count', 'diseases_predicted', 'model_used', 'created_at')
    list_filter = ('created_at', 'model_used')
    search_fields = ('user__email', 'nlp_input')
    readonly_fields = ('symptoms_selected', 'predicted_diseases', 'confidence_scores', 'nlp_input')

    def symptoms_count(self, obj):
        return len(obj.symptoms_selected) if obj.symptoms_selected else 0
    symptoms_count.short_description = 'Symptoms'

    def diseases_predicted(self, obj):
        if obj.predicted_diseases:
            return ', '.join(obj.predicted_diseases[:3])
        return '-'
    diseases_predicted.short_description = 'Predicted Diseases'


@admin.register(ReportUpload)
class ReportUploadAdmin(admin.ModelAdmin):
    list_display = ('report_name', 'user', 'report_type', 'created_at')
    list_filter = ('report_type', 'created_at')
    search_fields = ('report_name', 'user__email')
    readonly_fields = ('extracted_values', 'analysis_result', 'ai_suggestions')


@admin.register(FoodRecommendation)
class FoodRecommendationAdmin(admin.ModelAdmin):
    list_display = ('food_name', 'disease', 'food_type', 'reason')
    list_filter = ('food_type', 'disease')
    search_fields = ('food_name', 'reason')


@admin.register(MedicineRecommendation)
class MedicineRecommendationAdmin(admin.ModelAdmin):
    list_display = ('medicine_name', 'disease', 'medicine_type', 'dosage')
    list_filter = ('medicine_type', 'disease')
    search_fields = ('medicine_name', 'warnings')


@admin.register(SearchHistory)
class SearchHistoryAdmin(admin.ModelAdmin):
    list_display = ('query', 'user', 'results_count', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('query', 'user__email')


admin.site.site_header = "AI Medical Diagnosis Admin"
admin.site.site_title = "Medical AI Admin Portal"
admin.site.index_title = "Administration"


@admin.register(ChatConversation)
class ChatConversationAdmin(admin.ModelAdmin):
    list_display = ('title', 'user', 'message_count', 'created_at', 'updated_at')
    list_filter = ('created_at', 'updated_at')
    search_fields = ('title', 'user__email')
    readonly_fields = ('created_at', 'updated_at')

    def message_count(self, obj):
        return obj.messages.count()
    message_count.short_description = 'Messages'


@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ('conversation', 'role', 'content_preview', 'created_at')
    list_filter = ('role', 'created_at')
    search_fields = ('content', 'conversation__title')
    readonly_fields = ('created_at', 'metadata')

    def content_preview(self, obj):
        return obj.content[:100] + '...' if len(obj.content) > 100 else obj.content
    content_preview.short_description = 'Content'
