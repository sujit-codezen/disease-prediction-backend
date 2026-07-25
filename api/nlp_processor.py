import re
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'diagnosis_project.settings')

import django
django.setup()

from api.models import Symptom


SYMPTOM_KEYWORDS_MAP = {
    'head': ['headache', 'head pain', 'head ache', 'migraine'],
    'fever': ['fever', 'high temperature', 'feverish', 'hot', 'temperature'],
    'cough': ['cough', 'coughing', 'hacking'],
    'cold': ['cold', 'runny nose', 'stuffy nose', 'nasal congestion', 'sneezing'],
    'throat': ['sore throat', 'throat pain', 'scratchy throat'],
    'chest': ['chest pain', 'chest tightness', 'chest discomfort'],
    'stomach': ['stomach ache', 'stomach pain', 'abdominal pain', 'belly pain'],
    'nausea': ['nausea', 'nauseous', 'sick to stomach', 'queasy'],
    'vomiting': ['vomiting', 'throwing up', 'puking'],
    'diarrhea': ['diarrhea', 'loose stools', 'watery stools'],
    'fatigue': ['fatigue', 'tired', 'exhausted', 'weakness', 'weak', 'lethargic'],
    'dizziness': ['dizziness', 'dizzy', 'lightheaded', 'vertigo'],
    'back': ['back pain', 'backache', 'lower back pain'],
    'joint': ['joint pain', 'joint ache', 'arthritic', 'stiff joints'],
    'muscle': ['muscle pain', 'muscle ache', 'body ache', 'muscle soreness'],
    'skin': ['rash', 'skin rash', 'itching', 'itchy skin', 'hives'],
    'eye': ['eye pain', 'blurry vision', 'vision problems', 'eye infection'],
    'ear': ['ear pain', 'earache', 'ringing in ears', 'tinnitus'],
    'breathing': ['difficulty breathing', 'shortness of breath', 'breathless', 'wheezing'],
    'anxiety': ['anxiety', 'anxious', 'nervous', 'panic', 'restless'],
    'depression': ['depressed', 'depression', 'sad', 'hopeless'],
    'insomnia': ['insomnia', 'can\'t sleep', 'trouble sleeping', 'sleeplessness'],
    'appetite': ['loss of appetite', 'not hungry', 'no appetite', 'overeating'],
    'weight': ['weight loss', 'weight gain', 'unexplained weight change'],
    'heart': ['heart palpitations', 'rapid heartbeat', 'irregular heartbeat', 'palpitations'],
    'blood': ['blood in urine', 'blood in stool', 'bloody urine', 'bloody stool'],
    'urination': ['painful urination', 'frequent urination', 'burning urination'],
    'swelling': ['swelling', 'swollen', 'edema', 'inflammation'],
    'chills': ['chills', 'shivering', 'rigors'],
    'sweating': ['sweating', 'night sweats', 'excessive sweating'],
    'confusion': ['confusion', 'disoriented', 'memory loss', 'forgetful'],
    'seizure': ['seizure', 'convulsion', 'fits'],
    'numbness': ['numbness', 'tingling', 'pins and needles'],
    'constipation': ['constipation', 'hard stools', 'difficulty passing stool'],
    'bloating': ['bloating', 'bloated', 'gas', 'flatulence'],
    'jaw': ['jaw pain', 'jaw ache', 'tmj'],
    'neck': ['neck pain', 'stiff neck', 'neck stiffness'],
    'shoulder': ['shoulder pain', 'shoulder ache'],
    'knee': ['knee pain', 'knee ache'],
    'foot': ['foot pain', 'heel pain', 'plantar fasciitis'],
    'hair': ['hair loss', 'balding', 'thinning hair'],
    'nail': ['brittle nails', 'nail problems', 'discolored nails'],
}


def extract_symptoms_from_text(text):
    if not text:
        return []

    text_lower = text.lower()
    found_symptoms = set()

    for key, phrases in SYMPTOM_KEYWORDS_MAP.items():
        for phrase in phrases:
            if phrase in text_lower:
                found_symptoms.add(key)
                break

    db_symptoms = Symptom.objects.all()
    for symptom in db_symptoms:
        name_lower = symptom.name.lower()
        words = name_lower.split()
        if len(words) >= 2:
            if name_lower in text_lower:
                found_symptoms.add(symptom.name)
        else:
            if name_lower in text_lower.split():
                found_symptoms.add(symptom.name)

    return sorted(list(found_symptoms))


def suggest_related_symptoms(symptoms):
    related = set()
    mapping = {
        'headache': ['nausea', 'dizziness', 'fatigue', 'vision problems'],
        'fever': ['chills', 'sweating', 'fatigue', 'body ache'],
        'cough': ['sore throat', 'cold', 'shortness of breath'],
        'stomach ache': ['nausea', 'vomiting', 'diarrhea', 'bloating'],
        'fatigue': ['weakness', 'dizziness', 'loss of appetite'],
        'chest pain': ['shortness of breath', 'anxiety', 'heart palpitations'],
        'joint pain': ['swelling', 'stiffness', 'muscle pain'],
    }

    for symptom in symptoms:
        if symptom.lower() in mapping:
            related.update(mapping[symptom.lower()])

    related -= set(symptoms)
    return sorted(list(related))
