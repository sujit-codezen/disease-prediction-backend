import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'diagnosis_project.settings')

import django
django.setup()

from api.models import Disease, MedicineRecommendation


DEFAULT_MEDICINE_DATA = {
    'Diabetes': {
        'medicines': [
            ('Metformin', 'prescription', '500mg twice daily', 'May cause GI upset', 'Nausea, diarrhea'),
            ('Glipizide', 'prescription', '5mg once daily', 'Risk of hypoglycemia', 'Weight gain, dizziness'),
            ('Insulin', 'prescription', 'As prescribed', 'Monitor blood sugar', 'Hypoglycemia, weight gain'),
            ('Alpha-Lipoic Acid', 'supplement', '600mg daily', 'May lower blood sugar', 'Rare allergic reactions'),
        ],
        'otc': [
            ('Blood Glucose Monitor', 'supplement', 'As needed', 'Regular monitoring', 'N/A'),
            ('Glucose Tablets', 'otc', '15g for low blood sugar', 'For hypoglycemia episodes', 'N/A'),
        ],
    },
    'Hypertension': {
        'medicines': [
            ('Lisinopril', 'prescription', '10mg once daily', 'Monitor kidney function', 'Dry cough, dizziness'),
            ('Amlodipine', 'prescription', '5mg once daily', 'May cause swelling', 'Ankle swelling, headache'),
            ('Losartan', 'prescription', '50mg once daily', 'Avoid during pregnancy', 'Dizziness, fatigue'),
        ],
        'otc': [
            ('Aspirin', 'otc', '81mg daily', 'Consult doctor first', 'Stomach bleeding'),
            ('Fish Oil', 'supplement', '1000mg daily', 'Blood thinning effect', 'Fishy aftertaste'),
            ('CoQ10', 'supplement', '100mg daily', 'May interact with BP meds', 'Rare insomnia'),
        ],
    },
    'Asthma': {
        'medicines': [
            ('Albuterol Inhaler', 'prescription', '2 puffs every 4-6 hours', 'Rescue inhaler only', 'Tremors, rapid heartbeat'),
            ('Fluticasone Inhaler', 'prescription', '1-2 puffs twice daily', 'Rinse mouth after use', 'Oral thrush'),
            ('Montelukast', 'prescription', '10mg once daily', 'Take in evening', 'Headache, dizziness'),
        ],
        'otc': [
            ('Bronkaid', 'otc', '1-2 tablets every 4 hours', 'Contains ephedrine', 'Insomnia, nervousness'),
            ('Primatene', 'otc', 'As directed', 'Mild relief only', 'Nausea, trembling'),
        ],
    },
    'Arthritis': {
        'medicines': [
            ('Ibuprofen', 'otc', '400-800mg every 6-8 hours', 'Take with food', 'Stomach upset, kidney issues'),
            ('Naproxen', 'otc', '220mg twice daily', 'Longer lasting', 'Stomach bleeding risk'),
            ('Methotrexate', 'prescription', 'Once weekly', 'Monitor liver function', 'Nausea, fatigue'),
        ],
        'otc': [
            ('Glucosamine', 'supplement', '1500mg daily', 'May take 4-8 weeks', 'Mild GI upset'),
            ('Turmeric', 'supplement', '500mg twice daily', 'Natural anti-inflammatory', 'Rare allergic reactions'),
            ('Topical Capsaicin', 'otc', 'Apply 3-4 times daily', 'For joint pain', 'Burning sensation'),
        ],
    },
    'Migraine': {
        'medicines': [
            ('Sumatriptan', 'prescription', '50mg at onset', 'Max 200mg/day', 'Tingling, drowsiness'),
            ('Rizatriptan', 'prescription', '10mg at onset', 'Fast acting', 'Dizziness, fatigue'),
        ],
        'otc': [
            ('Ibuprofen', 'otc', '400mg at onset', 'Best taken early', 'Stomach upset'),
            ('Excedrin Migraine', 'otc', '2 tablets at onset', 'Contains caffeine', 'Caffeine dependence'),
            ('Magnesium', 'supplement', '400mg daily', 'Prevention', 'Loose stools'),
        ],
    },
    'Common Cold': {
        'medicines': [
            ('Acetaminophen', 'otc', '500mg every 6 hours', 'For fever/pain', 'Liver damage at high doses'),
            ('Dextromethorphan', 'otc', '30mg every 6-8 hours', 'Cough suppressant', 'Drowsiness'),
            ('Guaifenesin', 'otc', '200-400mg every 4 hours', 'Expectorant', 'Nausea, dizziness'),
        ],
        'otc': [
            ('Vitamin C', 'supplement', '1000mg daily', 'Supports immune system', 'GI upset at high doses'),
            ('Zinc', 'supplement', '30mg daily', 'May reduce duration', 'Nausea if taken empty stomach'),
            ('Saline Nasal Spray', 'otc', 'As needed', 'Non-medicated', 'None'),
        ],
    },
}


def get_medicine_recommendations(disease_name):
    try:
        disease = Disease.objects.get(name__iexact=disease_name)
        db_meds = MedicineRecommendation.objects.filter(disease=disease)
        if db_meds.exists():
            prescription = [{'name': m.medicine_name, 'type': m.medicine_type, 'dosage': m.dosage,
                           'warnings': m.warnings, 'side_effects': m.side_effects}
                          for m in db_meds.filter(medicine_type='prescription')]
            otc = [{'name': m.medicine_name, 'type': m.medicine_type, 'dosage': m.dosage,
                   'warnings': m.warnings, 'side_effects': m.side_effects}
                  for m in db_meds.filter(medicine_type='otc')]
            supplements = [{'name': m.medicine_name, 'type': m.medicine_type, 'dosage': m.dosage,
                          'warnings': m.warnings, 'side_effects': m.side_effects}
                         for m in db_meds.filter(medicine_type='supplement')]
            return {'prescription': prescription, 'otc': otc, 'supplements': supplements, 'source': 'database'}
    except Disease.DoesNotExist:
        pass

    for key in DEFAULT_MEDICINE_DATA:
        if key.lower() in disease_name.lower() or disease_name.lower() in key.lower():
            data = DEFAULT_MEDICINE_DATA[key]
            prescription = [{'name': m[0], 'type': m[1], 'dosage': m[2], 'warnings': m[3], 'side_effects': m[4]}
                          for m in data.get('medicines', []) if m[1] == 'prescription']
            otc = [{'name': m[0], 'type': m[1], 'dosage': m[2], 'warnings': m[3], 'side_effects': m[4]}
                  for m in data.get('otc', []) + data.get('medicines', []) if m[1] == 'otc']
            supplements = [{'name': m[0], 'type': m[1], 'dosage': m[2], 'warnings': m[3], 'side_effects': m[4]}
                         for m in data.get('medicines', []) + data.get('otc', []) if m[1] == 'supplement']
            return {'prescription': prescription, 'otc': otc, 'supplements': supplements, 'source': 'default'}

    return {
        'prescription': [],
        'otc': [{'name': 'Consult a Doctor', 'type': 'prescription', 'dosage': 'N/A',
                'warnings': 'Always consult healthcare provider', 'side_effects': 'N/A'}],
        'supplements': [],
        'source': 'fallback'
    }
