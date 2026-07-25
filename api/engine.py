import os
import sys
import joblib
import numpy as np

_model_cache = {}


def load_active_model():
    if 'active' in _model_cache:
        return _model_cache['active']

    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'diagnosis_project.settings')

    import django
    django.setup()

    from api.models import TrainedModel
    from django.conf import settings

    active = TrainedModel.objects.filter(is_active=True).first()
    if not active:
        return None

    model_path = os.path.join(settings.ML_MODELS_DIR, str(active.model_file).replace('models/', ''))
    if not os.path.exists(model_path):
        return None

    data = joblib.load(model_path)
    _model_cache['active'] = data
    return data


def predict_diseases(symptom_names, top_n=5):
    data = load_active_model()
    if not data:
        return []

    model = data['model']
    symptom_cols = data.get('symptom_names') or data.get('symptom_cols', [])
    disease_names = data.get('disease_names') or data.get('label_encoder', None)

    input_vector = np.zeros(len(symptom_cols))
    for symptom in symptom_names:
        clean = symptom.strip().replace('_', ' ').title()
        for i, col in enumerate(symptom_cols):
            if col.lower() == clean.lower() or clean.lower() in col.lower():
                input_vector[i] = 1
                break

    input_vector = input_vector.reshape(1, -1)

    probabilities = model.predict_proba(input_vector)[0]
    top_indices = probabilities.argsort()[-top_n:][::-1]

    results = []
    for idx in top_indices:
        if hasattr(disease_names, 'inverse_transform'):
            disease_name = disease_names.inverse_transform([idx])[0]
        else:
            disease_name = disease_names[idx]
        
        confidence = float(probabilities[idx])
        if confidence > 0.01:
            results.append({
                'disease': disease_name,
                'confidence': round(confidence * 100, 2),
            })

    return results


def get_disease_details(disease_name):
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'diagnosis_project.settings')

    import django
    django.setup()

    from api.models import Disease

    try:
        disease = Disease.objects.get(name__iexact=disease_name)
        return {
            'name': disease.name,
            'description': disease.description,
            'causes': disease.causes,
            'severity': disease.severity,
            'treatments': disease.treatments,
            'prevention': disease.prevention,
            'symptoms': [s.name for s in disease.symptoms.all()],
        }
    except Disease.DoesNotExist:
        return {'name': disease_name, 'description': '', 'severity': 'medium'}


def clear_model_cache():
    _model_cache.clear()
