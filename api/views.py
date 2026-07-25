from rest_framework import status, generics, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate, get_user_model
from django.db.models import Q
import os
import threading

from .models import (
    Symptom, Disease, Dataset, TrainedModel, DiagnosisHistory,
    ReportUpload, FoodRecommendation, MedicineRecommendation, SearchHistory
)
from .serializers import (
    UserRegisterSerializer, UserSerializer, SymptomSerializer, DiseaseSerializer,
    DiseaseListSerializer, DatasetSerializer, TrainedModelSerializer,
    DiagnosisHistorySerializer, ReportUploadSerializer, FoodRecommendationSerializer,
    MedicineRecommendationSerializer, SearchHistorySerializer
)
from .engine import predict_diseases, get_disease_details, clear_model_cache
from .nlp_processor import extract_symptoms_from_text, suggest_related_symptoms
from .report_analyzer import analyze_report
from .diet_planner import get_food_recommendations
from .medicine_guide import get_medicine_recommendations

User = get_user_model()


class RegisterView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = UserRegisterSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            refresh = RefreshToken.for_user(user)
            return Response({
                'user': UserSerializer(user).data,
                'tokens': {
                    'refresh': str(refresh),
                    'access': str(refresh.access_token),
                }
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class LoginView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        email = request.data.get('email')
        password = request.data.get('password')
        user = authenticate(email=email, password=password)
        if user:
            refresh = RefreshToken.for_user(user)
            return Response({
                'user': UserSerializer(user).data,
                'tokens': {
                    'refresh': str(refresh),
                    'access': str(refresh.access_token),
                }
            })
        return Response({'error': 'Invalid credentials'}, status=status.HTTP_401_UNAUTHORIZED)


class ProfileView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        return Response(UserSerializer(request.user).data)

    def put(self, request):
        serializer = UserSerializer(request.user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class SymptomListView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        symptoms = Symptom.objects.all()
        search = request.query_params.get('search', '')
        body_part = request.query_params.get('body_part', '')

        if search:
            symptoms = symptoms.filter(name__icontains=search)
        if body_part:
            symptoms = symptoms.filter(body_part__icontains=body_part)

        serializer = SymptomSerializer(symptoms, many=True)
        return Response(serializer.data)


class SymptomSearchView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        query = request.query_params.get('q', '')
        if not query:
            return Response([])

        symptoms = Symptom.objects.filter(name__icontains=query)[:20]
        serializer = SymptomSerializer(symptoms, many=True)
        return Response(serializer.data)


class DiseaseListView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        diseases = Disease.objects.all()
        search = request.query_params.get('search', '')
        severity = request.query_params.get('severity', '')

        if search:
            diseases = diseases.filter(name__icontains=search)
        if severity:
            diseases = diseases.filter(severity=severity)

        serializer = DiseaseListSerializer(diseases, many=True)
        return Response(serializer.data)


class DiseaseDetailView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request, pk):
        try:
            disease = Disease.objects.get(pk=pk)
            serializer = DiseaseSerializer(disease)
            data = serializer.data
            data['food_recommendations'] = get_food_recommendations(disease.name)
            data['medicine_recommendations'] = get_medicine_recommendations(disease.name)
            return Response(data)
        except Disease.DoesNotExist:
            return Response({'error': 'Disease not found'}, status=status.HTTP_404_NOT_FOUND)


class DiagnoseView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        symptoms = request.data.get('symptoms', [])
        if not symptoms:
            return Response({'error': 'No symptoms provided'}, status=status.HTTP_400_BAD_REQUEST)

        predictions = predict_diseases(symptoms, top_n=5)

        for pred in predictions:
            details = get_disease_details(pred['disease'])
            pred.update(details)

        model = TrainedModel.objects.filter(is_active=True).first()

        DiagnosisHistory.objects.create(
            user=request.user,
            symptoms_selected=symptoms,
            predicted_diseases=[p['disease'] for p in predictions],
            confidence_scores=[p['confidence'] for p in predictions],
            model_used=model,
        )

        return Response({
            'predictions': predictions,
            'symptoms': symptoms,
        })


class DiagnoseTextView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        text = request.data.get('text', '')
        if not text:
            return Response({'error': 'No text provided'}, status=status.HTTP_400_BAD_REQUEST)

        symptoms = extract_symptoms_from_text(text)
        if not symptoms:
            return Response({
                'error': 'Could not identify symptoms from text',
                'extracted': [],
            }, status=status.HTTP_400_BAD_REQUEST)

        predictions = predict_diseases(symptoms, top_n=5)

        for pred in predictions:
            details = get_disease_details(pred['disease'])
            pred.update(details)

        related = suggest_related_symptoms(symptoms)
        model = TrainedModel.objects.filter(is_active=True).first()

        DiagnosisHistory.objects.create(
            user=request.user,
            symptoms_selected=symptoms,
            nlp_input=text,
            predicted_diseases=[p['disease'] for p in predictions],
            confidence_scores=[p['confidence'] for p in predictions],
            model_used=model,
        )

        SearchHistory.objects.create(
            user=request.user,
            query=text,
            results_count=len(predictions),
        )

        return Response({
            'predictions': predictions,
            'extracted_symptoms': symptoms,
            'related_symptoms': related,
            'original_text': text,
        })


class UploadReportView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        file = request.FILES.get('file')
        report_type = request.data.get('report_type', 'blood')
        report_name = request.data.get('report_name', 'Untitled Report')

        if not file:
            return Response({'error': 'No file provided'}, status=status.HTTP_400_BAD_REQUEST)

        report = ReportUpload.objects.create(
            user=request.user,
            file=file,
            report_type=report_type,
            report_name=report_name,
        )

        file_path = report.file.path
        analysis = analyze_report(file_path, report_type)

        report.extracted_values = analysis.get('values', {})
        report.analysis_result = analysis.get('analysis', {})
        report.ai_suggestions = analysis.get('suggestions', [])
        report.save()

        return Response(ReportUploadSerializer(report).data, status=status.HTTP_201_CREATED)


class ReportListView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        reports = ReportUpload.objects.filter(user=request.user)
        serializer = ReportUploadSerializer(reports, many=True)
        return Response(serializer.data)


class ReportDetailView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk):
        try:
            report = ReportUpload.objects.get(pk=pk, user=request.user)
            serializer = ReportUploadSerializer(report)
            return Response(serializer.data)
        except ReportUpload.DoesNotExist:
            return Response({'error': 'Report not found'}, status=status.HTTP_404_NOT_FOUND)


class DietRecommendationView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request, disease_name):
        recommendations = get_food_recommendations(disease_name)
        return Response(recommendations)


class MedicineRecommendationView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request, disease_name):
        recommendations = get_medicine_recommendations(disease_name)
        return Response(recommendations)


class DiagnosisHistoryView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        history = DiagnosisHistory.objects.filter(user=request.user)
        serializer = DiagnosisHistorySerializer(history, many=True)
        return Response(serializer.data)


class SearchHistoryView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        history = SearchHistory.objects.filter(user=request.user)
        serializer = SearchHistorySerializer(history, many=True)
        return Response(serializer.data)


class HospitalSearchView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        lat = request.query_params.get('lat', 0)
        lng = request.query_params.get('lng', 0)
        try:
            lat = float(lat)
            lng = float(lng)
        except (TypeError, ValueError):
            return Response([])

        import requests
        query = f"""
        [out:json];
        (
          node["amenity"="hospital"](around:10000,{lat},{lng});
          node["amenity"="clinic"](around:10000,{lat},{lng});
        );
        out body;
        """

        try:
            response = requests.get('https://overpass-api.de/api/interpreter', params={'data': query}, timeout=10)
            data = response.json()
            hospitals = []
            for element in data.get('elements', []):
                hospitals.append({
                    'id': element.get('id'),
                    'name': element.get('tags', {}).get('name', 'Hospital'),
                    'lat': element.get('lat'),
                    'lng': element.get('lon'),
                    'address': element.get('tags', {}).get('addr:full', ''),
                    'phone': element.get('tags', {}).get('phone', ''),
                    'website': element.get('tags', {}).get('website', ''),
                })
            return Response(hospitals)
        except Exception:
            return Response([])


class AdminStatsView(APIView):
    permission_classes = [permissions.IsAdminUser]

    def get(self, request):
        return Response({
            'total_users': User.objects.count(),
            'total_symptoms': Symptom.objects.count(),
            'total_diseases': Disease.objects.count(),
            'total_diagnoses': DiagnosisHistory.objects.count(),
            'total_reports': ReportUpload.objects.count(),
            'total_models': TrainedModel.objects.count(),
            'active_model': TrainedModelSerializer(TrainedModel.objects.filter(is_active=True).first()).data if TrainedModel.objects.filter(is_active=True).exists() else None,
        })


class AdminTrainModelView(APIView):
    permission_classes = [permissions.IsAdminUser]

    def post(self, request):
        dataset_id = request.data.get('dataset_id')
        if not dataset_id:
            return Response({'error': 'dataset_id required'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            dataset = Dataset.objects.get(id=dataset_id)
        except Dataset.DoesNotExist:
            return Response({'error': 'Dataset not found'}, status=status.HTTP_404_NOT_FOUND)

        from django.conf import settings
        csv_path = os.path.join(settings.MEDIA_ROOT, str(dataset.file))
        if not os.path.exists(csv_path):
            return Response({'error': 'Dataset file not found'}, status=status.HTTP_404_NOT_FOUND)

        def train_in_background():
            from .train_model import train_model
            train_models(csv_path, dataset_id=dataset_id, user=request.user)

        thread = threading.Thread(target=train_in_background, daemon=True)
        thread.start()

        return Response({'message': 'Training started in background', 'dataset': dataset.name})


def train_models(csv_path, dataset_id=None, user=None):
    from .train_model import train_models as do_train
    do_train(csv_path, dataset_id=dataset_id, user=user)


class AdminDatasetListView(APIView):
    permission_classes = [permissions.IsAdminUser]

    def get(self, request):
        datasets = Dataset.objects.all()
        serializer = DatasetSerializer(datasets, many=True)
        return Response(serializer.data)

    def post(self, request):
        file = request.FILES.get('file')
        name = request.data.get('name', 'Untitled Dataset')
        description = request.data.get('description', '')

        if not file:
            return Response({'error': 'No file provided'}, status=status.HTTP_400_BAD_REQUEST)

        import pandas as pd
        try:
            df = pd.read_csv(file)
            row_count = len(df)
            column_count = len(df.columns)
        except Exception:
            row_count = 0
            column_count = 0

        dataset = Dataset.objects.create(
            name=name,
            file=file,
            description=description,
            row_count=row_count,
            column_count=column_count,
            uploaded_by=request.user,
        )

        return Response(DatasetSerializer(dataset).data, status=status.HTTP_201_CREATED)


class AdminModelListView(APIView):
    permission_classes = [permissions.IsAdminUser]

    def get(self, request):
        models = TrainedModel.objects.all()
        serializer = TrainedModelSerializer(models, many=True)
        return Response(serializer.data)


class AdminModelActivateView(APIView):
    permission_classes = [permissions.IsAdminUser]

    def post(self, request, pk):
        try:
            model = TrainedModel.objects.get(pk=pk)
            TrainedModel.objects.update(is_active=False)
            model.is_active = True
            model.save()
            clear_model_cache()
            return Response({'message': f'Activated {model.name}'})
        except TrainedModel.DoesNotExist:
            return Response({'error': 'Model not found'}, status=status.HTTP_404_NOT_FOUND)
