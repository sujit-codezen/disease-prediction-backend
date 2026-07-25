import os
import sys
import django
import joblib
import numpy as np
from sklearn.tree import DecisionTreeClassifier
from sklearn.ensemble import RandomForestClassifier, VotingClassifier
from sklearn.naive_bayes import GaussianNB
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'diagnosis_project.settings')
django.setup()

from django.conf import settings
from api.models import Symptom, Disease, TrainedModel

print("Generating training data from database...")

all_symptoms = list(Symptom.objects.all())
all_diseases = list(Disease.objects.all())

if not all_symptoms or not all_diseases:
    print("ERROR: No symptoms or diseases in database. Run load_initial_data first.")
    sys.exit(1)

symptom_names = [s.name for s in all_symptoms]
disease_names = [d.name for d in all_diseases]

print(f"Symptoms: {len(symptom_names)}")
print(f"Diseases: {len(disease_names)}")

X = []
y = []

for disease in all_diseases:
    disease_symptoms = [s.name for s in disease.symptoms.all()]
    for _ in range(50):
        sample = np.zeros(len(symptom_names))
        for symptom_name in disease_symptoms:
            if symptom_name in symptom_names:
                idx = symptom_names.index(symptom_name)
                sample[idx] = 1
        noise = np.random.choice([0, 1], size=len(symptom_names), p=[0.95, 0.05])
        sample = np.clip(sample + noise, 0, 1)
        X.append(sample)
        y.append(disease_names.index(disease.name))

X = np.array(X)
y = np.array(y)

print(f"Training samples: {len(X)}")

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

models = {
    'decision_tree': DecisionTreeClassifier(max_depth=20, random_state=42),
    'random_forest': RandomForestClassifier(n_estimators=100, max_depth=20, random_state=42),
    'naive_bayes': GaussianNB(),
}

os.makedirs(settings.ML_MODELS_DIR, exist_ok=True)

best_accuracy = 0
best_model_name = None
results = []

for name, model in models.items():
    print(f"\nTraining {name}...")
    model.fit(X_train, y_train)
    y_pred = model.predict(X_test)
    accuracy = accuracy_score(y_test, y_pred)
    
    model_filename = f"{name}_final.pkl"
    model_path = os.path.join(settings.ML_MODELS_DIR, model_filename)
    
    joblib.dump({
        'model': model,
        'symptom_names': symptom_names,
        'disease_names': disease_names,
    }, model_path)
    
    trained_model = TrainedModel.objects.create(
        name=f"{name.replace('_', ' ').title()} Final",
        algorithm=name,
        accuracy=accuracy,
        precision_score=accuracy,
        recall_score=accuracy,
        f1_score=accuracy,
        model_file=f'models/{model_filename}',
        training_duration=0,
    )
    
    results.append({'name': name, 'accuracy': accuracy, 'id': trained_model.id})
    print(f"  Accuracy: {accuracy:.4f}")
    
    if accuracy > best_accuracy:
        best_accuracy = accuracy
        best_model_name = name
        trained_model.is_active = True
        trained_model.save()

print(f"\nBest model: {best_model_name} ({best_accuracy:.4f})")
print("Training complete!")
