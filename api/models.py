from django.db import models
from django.contrib.auth.models import AbstractUser
import json


class User(AbstractUser):
    email = models.EmailField(unique=True)
    age = models.IntegerField(null=True, blank=True)
    gender = models.CharField(max_length=10, choices=[('M', 'Male'), ('F', 'Female'), ('O', 'Other')], null=True, blank=True)
    weight = models.FloatField(null=True, blank=True)
    height = models.FloatField(null=True, blank=True)
    blood_type = models.CharField(max_length=5, choices=[('A+', 'A+'), ('A-', 'A-'), ('B+', 'B+'), ('B-', 'B-'), ('AB+', 'AB+'), ('AB-', 'AB-'), ('O+', 'O+'), ('O-', 'O-')], null=True, blank=True)
    allergies = models.TextField(blank=True, default='')
    medical_conditions = models.TextField(blank=True, default='')
    phone = models.CharField(max_length=20, blank=True, default='')

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']


class Symptom(models.Model):
    name = models.CharField(max_length=200, unique=True)
    description = models.TextField(blank=True, default='')
    body_part = models.CharField(max_length=100, blank=True, default='')
    severity_level = models.CharField(max_length=10, choices=[('low', 'Low'), ('medium', 'Medium'), ('high', 'High')], default='medium')

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class Disease(models.Model):
    name = models.CharField(max_length=200, unique=True)
    description = models.TextField(blank=True, default='')
    causes = models.TextField(blank=True, default='')
    severity = models.CharField(max_length=10, choices=[('low', 'Low'), ('medium', 'Medium'), ('high', 'High'), ('urgent', 'Urgent')], default='medium')
    treatments = models.TextField(blank=True, default='')
    prevention = models.TextField(blank=True, default='')
    symptoms = models.ManyToManyField(Symptom, related_name='diseases', blank=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class Dataset(models.Model):
    name = models.CharField(max_length=200)
    file = models.FileField(upload_to='datasets/')
    description = models.TextField(blank=True, default='')
    row_count = models.IntegerField(default=0)
    column_count = models.IntegerField(default=0)
    uploaded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name


class TrainedModel(models.Model):
    ALGORITHM_CHOICES = [
        ('decision_tree', 'Decision Tree'),
        ('random_forest', 'Random Forest'),
        ('naive_bayes', 'Naive Bayes'),
        ('svm', 'SVM'),
        ('ensemble', 'Ensemble'),
    ]

    name = models.CharField(max_length=200)
    algorithm = models.CharField(max_length=20, choices=ALGORITHM_CHOICES)
    accuracy = models.FloatField(default=0)
    precision_score = models.FloatField(default=0)
    recall_score = models.FloatField(default=0)
    f1_score = models.FloatField(default=0)
    model_file = models.FileField(upload_to='models/')
    trained_on = models.DateTimeField(auto_now_add=True)
    trained_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    dataset_used = models.ForeignKey(Dataset, on_delete=models.SET_NULL, null=True)
    is_active = models.BooleanField(default=False)
    confusion_matrix = models.JSONField(default=dict)
    classification_report = models.JSONField(default=dict)
    training_duration = models.FloatField(default=0)

    class Meta:
        ordering = ['-trained_on']

    def __str__(self):
        return f"{self.name} ({self.algorithm}) - {self.accuracy:.2%}"


class DiagnosisHistory(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='diagnoses')
    symptoms_selected = models.JSONField(default=list)
    nlp_input = models.TextField(blank=True, default='')
    predicted_diseases = models.JSONField(default=list)
    confidence_scores = models.JSONField(default=list)
    model_used = models.ForeignKey(TrainedModel, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Diagnosis by {self.user.email} - {self.created_at}"


class ReportUpload(models.Model):
    REPORT_TYPES = [
        ('blood', 'Blood Test'),
        ('urine', 'Urine Test'),
        ('xray', 'X-Ray'),
        ('mri', 'MRI'),
        ('other', 'Other'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reports')
    file = models.FileField(upload_to='reports/')
    report_type = models.CharField(max_length=20, choices=REPORT_TYPES, default='blood')
    report_name = models.CharField(max_length=200, blank=True, default='')
    extracted_values = models.JSONField(default=dict)
    analysis_result = models.JSONField(default=dict)
    ai_suggestions = models.JSONField(default=list)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.report_name} - {self.user.email}"


class FoodRecommendation(models.Model):
    FOOD_TYPES = [
        ('eat', 'Eat'),
        ('avoid', 'Avoid'),
        ('moderate', 'Eat in Moderation'),
    ]

    disease = models.ForeignKey(Disease, on_delete=models.CASCADE, related_name='food_recommendations')
    food_name = models.CharField(max_length=200)
    food_type = models.CharField(max_length=10, choices=FOOD_TYPES)
    reason = models.TextField(blank=True, default='')
    nutritional_info = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['disease', 'food_type', 'food_name']

    def __str__(self):
        return f"{self.food_name} ({self.food_type}) for {self.disease.name}"


class MedicineRecommendation(models.Model):
    MEDICINE_TYPES = [
        ('otc', 'Over the Counter'),
        ('prescription', 'Prescription Required'),
        ('supplement', 'Supplement'),
    ]

    disease = models.ForeignKey(Disease, on_delete=models.CASCADE, related_name='medicine_recommendations')
    medicine_name = models.CharField(max_length=200)
    medicine_type = models.CharField(max_length=15, choices=MEDICINE_TYPES, default='otc')
    dosage = models.CharField(max_length=200, blank=True, default='')
    warnings = models.TextField(blank=True, default='')
    side_effects = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['disease', 'medicine_name']

    def __str__(self):
        return f"{self.medicine_name} for {self.disease.name}"


class SearchHistory(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='search_history')
    query = models.CharField(max_length=500)
    results_count = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = 'Search histories'

    def __str__(self):
        return f"{self.query} by {self.user.email}"
