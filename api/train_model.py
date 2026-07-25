import pandas as pd
import numpy as np
import joblib
import time
import os
import sys
import django

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'diagnosis_project.settings')
django.setup()

from django.conf import settings
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
from sklearn.tree import DecisionTreeClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.naive_bayes import GaussianNB
from sklearn.svm import SVC
from sklearn.ensemble import VotingClassifier
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, confusion_matrix
from api.models import Symptom, Disease, Dataset, TrainedModel


def load_diseases_symptoms_dataset(csv_path):
    df = pd.read_csv(csv_path)
    print(f"Loaded dataset: {df.shape[0]} rows, {df.shape[1]} columns")
    print(f"Columns: {list(df.columns)}")

    all_symptoms = set()
    disease_symptom_map = {}

    for _, row in df.iterrows():
        disease = str(row.iloc[0]).strip()
        symptoms_str = str(row.iloc[1]) if len(row) > 1 else ''
        treatments = str(row.iloc[2]) if len(row) > 2 else ''

        symptoms = [s.strip() for s in symptoms_str.replace(';', ',').split(',') if s.strip()]
        all_symptoms.update(symptoms)
        disease_symptom_map[disease] = {'symptoms': symptoms, 'treatments': treatments}

    return df, disease_symptom_map, sorted(all_symptoms)


def load_training_dataset(csv_path):
    df = pd.read_csv(csv_path)
    print(f"Loaded training dataset: {df.shape[0]} rows, {df.shape[1]} columns")
    return df


def sync_symptoms_to_db(all_symptoms):
    created = 0
    for symptom_name in all_symptoms:
        clean_name = symptom_name.strip().replace('_', ' ').title()
        _, was_created = Symptom.objects.get_or_create(
            name=clean_name,
            defaults={'description': f'Symptom: {clean_name}'}
        )
        if was_created:
            created += 1
    print(f"Synced {len(all_symptoms)} symptoms to DB ({created} new)")


def sync_diseases_to_db(disease_symptom_map):
    created = 0
    for disease_name, info in disease_symptom_map.items():
        clean_name = disease_name.strip().title()
        disease, was_created = Disease.objects.get_or_create(
            name=clean_name,
            defaults={
                'description': f'Disease: {clean_name}',
                'treatments': info.get('treatments', ''),
                'severity': 'medium'
            }
        )
        if was_created:
            created += 1
        for symptom_name in info['symptoms']:
            clean_symptom = symptom_name.strip().replace('_', ' ').title()
            symptom, _ = Symptom.objects.get_or_create(
                name=clean_symptom,
                defaults={'description': f'Symptom: {clean_symptom}'}
            )
            disease.symptoms.add(symptom)
    print(f"Synced {len(disease_symptom_map)} diseases to DB ({created} new)")


def train_models(csv_path, dataset_id=None, user=None):
    start_time = time.time()

    try:
        df, disease_map, all_symptoms = load_diseases_symptoms_dataset(csv_path)
    except Exception:
        df = load_training_dataset(csv_path)
        if 'prognosis' in df.columns:
            target_col = 'prognosis'
        elif 'Disease' in df.columns:
            target_col = 'Disease'
        else:
            target_col = df.columns[-1]

        all_symptoms = [c for c in df.columns if c != target_col]
        disease_map = {}
        for _, row in df.iterrows():
            disease = str(row[target_col])
            if disease not in disease_map:
                disease_map[disease] = {'symptoms': [], 'treatments': ''}
            symptoms = [c for c in all_symptoms if row[c] == 1]
            disease_map[disease]['symptoms'].extend(symptoms)

    sync_symptoms_to_db(all_symptoms)
    sync_diseases_to_db(disease_map)

    if 'prognosis' in df.columns or 'Disease' in df.columns or df.columns[-1] in disease_map:
        target_col = 'prognosis' if 'prognosis' in df.columns else ('Disease' if 'Disease' in df.columns else df.columns[-1])
        symptom_cols = [c for c in df.columns if c != target_col]
        X = df[symptom_cols].values
        y = df[target_col].values
    else:
        symptom_list = sorted(all_symptoms)
        X = np.zeros((len(df), len(symptom_list)))
        y = np.zeros(len(df), dtype=int)

        disease_to_idx = {d: i for i, d in enumerate(disease_map.keys())}
        for i, (_, row) in enumerate(df.iterrows()):
            disease = str(row.iloc[0])
            y[i] = disease_to_idx.get(disease, 0)
            symptoms_str = str(row.iloc[1]) if len(row) > 1 else ''
            symptoms = [s.strip() for s in symptoms_str.replace(';', ',').split(',')]
            for s in symptoms:
                if s in symptom_list:
                    X[i, symptom_list.index(s)] = 1

        symptom_cols = symptom_list

    le = LabelEncoder()
    y_encoded = le.fit_transform(y)

    X_train, X_test, y_train, y_test = train_test_split(X, y_encoded, test_size=0.2, random_state=42)

    models = {
        'decision_tree': DecisionTreeClassifier(random_state=42, max_depth=20),
        'random_forest': RandomForestClassifier(n_estimators=100, random_state=42, max_depth=20),
        'naive_bayes': GaussianNB(),
        'svm': SVC(kernel='rbf', probability=True, random_state=42),
    }

    dataset_obj = None
    if dataset_id:
        try:
            dataset_obj = Dataset.objects.get(id=dataset_id)
        except Dataset.DoesNotExist:
            pass

    best_accuracy = 0
    best_model_name = None
    results = []

    for name, model in models.items():
        print(f"\nTraining {name}...")
        model_start = time.time()

        model.fit(X_train, y_train)
        y_pred = model.predict(X_test)

        accuracy = accuracy_score(y_test, y_pred)
        precision = precision_score(y_test, y_pred, average='weighted', zero_division=0)
        recall = recall_score(y_test, y_pred, average='weighted', zero_division=0)
        f1 = f1_score(y_test, y_pred, average='weighted', zero_division=0)
        cm = confusion_matrix(y_test, y_pred).tolist()

        duration = time.time() - model_start

        model_filename = f"{name}_{int(time.time())}.pkl"
        model_path = os.path.join(settings.ML_MODELS_DIR, model_filename)
        os.makedirs(settings.ML_MODELS_DIR, exist_ok=True)

        joblib.dump({
            'model': model,
            'label_encoder': le,
            'symptom_cols': symptom_cols,
            'disease_map': disease_map,
        }, model_path)

        trained_model = TrainedModel.objects.create(
            name=f"{name.replace('_', ' ').title()} Model",
            algorithm=name,
            accuracy=accuracy,
            precision_score=precision,
            recall_score=recall,
            f1_score=f1,
            model_file=f'models/{model_filename}',
            trained_by=user,
            dataset_used=dataset_obj,
            confusion_matrix=cm,
            training_duration=duration,
        )

        results.append({
            'name': name,
            'accuracy': accuracy,
            'precision': precision,
            'recall': recall,
            'f1': f1,
            'duration': duration,
            'id': trained_model.id,
        })

        print(f"  Accuracy: {accuracy:.4f}")
        print(f"  Precision: {precision:.4f}")
        print(f"  Recall: {recall:.4f}")
        print(f"  F1: {f1:.4f}")
        print(f"  Duration: {duration:.2f}s")

        if accuracy > best_accuracy:
            best_accuracy = accuracy
            best_model_name = name

    ensemble_model = VotingClassifier(
        estimators=[(name, model) for name, model in models.items()],
        voting='soft'
    )
    print(f"\nTraining ensemble...")
    ensemble_start = time.time()
    ensemble_model.fit(X_train, y_train)
    y_pred_ensemble = ensemble_model.predict(X_test)

    ensemble_accuracy = accuracy_score(y_test, y_pred_ensemble)
    ensemble_precision = precision_score(y_test, y_pred_ensemble, average='weighted', zero_division=0)
    ensemble_recall = recall_score(y_test, y_pred_ensemble, average='weighted', zero_division=0)
    ensemble_f1 = f1_score(y_test, y_pred_ensemble, average='weighted', zero_division=0)
    ensemble_cm = confusion_matrix(y_test, y_pred_ensemble).tolist()
    ensemble_duration = time.time() - ensemble_start

    ensemble_filename = f"ensemble_{int(time.time())}.pkl"
    ensemble_path = os.path.join(settings.ML_MODELS_DIR, ensemble_filename)

    joblib.dump({
        'model': ensemble_model,
        'label_encoder': le,
        'symptom_cols': symptom_cols,
        'disease_map': disease_map,
    }, ensemble_path)

    ensemble_trained = TrainedModel.objects.create(
        name="Ensemble Voting Model",
        algorithm='ensemble',
        accuracy=ensemble_accuracy,
        precision_score=ensemble_precision,
        recall_score=ensemble_recall,
        f1_score=ensemble_f1,
        model_file=f'models/{ensemble_filename}',
        trained_by=user,
        dataset_used=dataset_obj,
        confusion_matrix=ensemble_cm,
        training_duration=ensemble_duration,
    )

    results.append({
        'name': 'ensemble',
        'accuracy': ensemble_accuracy,
        'precision': ensemble_precision,
        'recall': ensemble_recall,
        'f1': ensemble_f1,
        'duration': ensemble_duration,
        'id': ensemble_trained.id,
    })

    if ensemble_accuracy > best_accuracy:
        best_accuracy = ensemble_accuracy
        best_model_name = 'ensemble'

    best_result = next(r for r in results if r['name'] == best_model_name)
    TrainedModel.objects.filter(id=best_result['id']).update(is_active=True)
    TrainedModel.objects.exclude(id=best_result['id']).update(is_active=False)

    total_duration = time.time() - start_time

    print(f"\n{'='*60}")
    print(f"TRAINING COMPLETE")
    print(f"{'='*60}")
    print(f"Total duration: {total_duration:.2f}s")
    print(f"Best model: {best_model_name} ({best_accuracy:.4f})")
    print(f"Results saved to database")

    return results


if __name__ == '__main__':
    csv_path = os.path.join(settings.ML_DATA_DIR, 'Diseases_Symptoms.csv')
    if not os.path.exists(csv_path):
        print(f"Dataset not found at {csv_path}")
        print("Please place Diseases_Symptoms.csv in the data/ directory")
        sys.exit(1)

    train_models(csv_path)
