from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import (
    Symptom, Disease, Dataset, TrainedModel, DiagnosisHistory,
    ReportUpload, FoodRecommendation, MedicineRecommendation, SearchHistory
)

User = get_user_model()


class UserRegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=6)
    password2 = serializers.CharField(write_only=True, min_length=6)

    class Meta:
        model = User
        fields = ['email', 'username', 'password', 'password2', 'age', 'gender', 'weight', 'height', 'blood_type', 'allergies', 'medical_conditions']

    def validate(self, attrs):
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError({'password': 'Passwords do not match'})
        return attrs

    def create(self, validated_data):
        validated_data.pop('password2')
        user = User.objects.create_user(**validated_data)
        return user


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'email', 'username', 'age', 'gender', 'weight', 'height', 'blood_type', 'allergies', 'medical_conditions', 'phone', 'date_joined']


class SymptomSerializer(serializers.ModelSerializer):
    class Meta:
        model = Symptom
        fields = ['id', 'name', 'description', 'body_part', 'severity_level']


class DiseaseSerializer(serializers.ModelSerializer):
    symptoms = SymptomSerializer(many=True, read_only=True)
    food_count = serializers.SerializerMethodField()
    medicine_count = serializers.SerializerMethodField()

    class Meta:
        model = Disease
        fields = ['id', 'name', 'description', 'causes', 'severity', 'treatments', 'prevention', 'symptoms', 'food_count', 'medicine_count']

    def get_food_count(self, obj):
        return obj.food_recommendations.count()

    def get_medicine_count(self, obj):
        return obj.medicine_recommendations.count()


class DiseaseListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Disease
        fields = ['id', 'name', 'severity', 'description']


class DatasetSerializer(serializers.ModelSerializer):
    uploaded_by_name = serializers.CharField(source='uploaded_by.username', read_only=True)

    class Meta:
        model = Dataset
        fields = ['id', 'name', 'file', 'description', 'row_count', 'column_count', 'uploaded_by_name', 'created_at', 'is_active']


class TrainedModelSerializer(serializers.ModelSerializer):
    trained_by_name = serializers.CharField(source='trained_by.username', read_only=True)
    dataset_name = serializers.CharField(source='dataset_used.name', read_only=True)

    class Meta:
        model = TrainedModel
        fields = ['id', 'name', 'algorithm', 'accuracy', 'precision_score', 'recall_score', 'f1_score', 'model_file', 'trained_on', 'trained_by_name', 'dataset_name', 'is_active', 'confusion_matrix', 'training_duration']


class DiagnosisHistorySerializer(serializers.ModelSerializer):
    symptoms_count = serializers.SerializerMethodField()

    class Meta:
        model = DiagnosisHistory
        fields = ['id', 'symptoms_selected', 'nlp_input', 'predicted_diseases', 'confidence_scores', 'model_used', 'created_at', 'symptoms_count']

    def get_symptoms_count(self, obj):
        return len(obj.symptoms_selected) if obj.symptoms_selected else 0


class ReportUploadSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReportUpload
        fields = ['id', 'file', 'report_type', 'report_name', 'extracted_values', 'analysis_result', 'ai_suggestions', 'created_at']
        read_only_fields = ['extracted_values', 'analysis_result', 'ai_suggestions']


class FoodRecommendationSerializer(serializers.ModelSerializer):
    class Meta:
        model = FoodRecommendation
        fields = ['id', 'disease', 'food_name', 'food_type', 'reason', 'nutritional_info']


class MedicineRecommendationSerializer(serializers.ModelSerializer):
    class Meta:
        model = MedicineRecommendation
        fields = ['id', 'disease', 'medicine_name', 'medicine_type', 'dosage', 'warnings', 'side_effects']


class SearchHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = SearchHistory
        fields = ['id', 'query', 'results_count', 'created_at']
