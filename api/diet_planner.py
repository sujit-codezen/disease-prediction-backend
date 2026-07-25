import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'diagnosis_project.settings')

import django
django.setup()

from api.models import Disease, FoodRecommendation


DEFAULT_FOOD_DATA = {
    'Diabetes': {
        'eat': [
            ('Leafy Greens', 'Rich in vitamins, low calories', 'Vitamin K, A, C'),
            ('Fatty Fish', 'Omega-3 reduces inflammation', 'Omega-3, Protein'),
            ('Berries', 'Low GI, high antioxidants', 'Antioxidants, Fiber'),
            ('Whole Grains', 'Fiber helps blood sugar', 'Fiber, B Vitamins'),
            ('Nuts', 'Healthy fats, blood sugar control', 'Healthy Fats, Magnesium'),
        ],
        'avoid': [
            ('Sugary Drinks', 'Spikes blood sugar', 'High Sugar'),
            ('White Bread', 'High glycemic index', 'Refined Carbs'),
            ('Pastries', 'High sugar and fat', 'Sugar, Saturated Fat'),
            ('Fried Foods', 'High calories, unhealthy fats', 'Trans Fats'),
            ('Processed Meats', 'High sodium, nitrates', 'Sodium, Nitrates'),
        ],
    },
    'Hypertension': {
        'eat': [
            ('Bananas', 'High potassium lowers BP', 'Potassium'),
            ('Beets', 'Nitric oxide dilates blood vessels', 'Nitrates'),
            ('Oats', 'Beta-glucan reduces cholesterol', 'Fiber, Beta-glucan'),
            ('Berries', 'Anthocyanins improve vascular health', 'Antioxidants'),
            ('Fatty Fish', 'Omega-3 reduces inflammation', 'Omega-3'),
        ],
        'avoid': [
            ('Salty Foods', 'Increases blood pressure', 'Sodium'),
            ('Processed Foods', 'Hidden sodium', 'Sodium, Preservatives'),
            ('Alcohol', 'Raises blood pressure', 'Alcohol'),
            ('Caffeine', 'Temporary BP spike', 'Caffeine'),
            ('Red Meat', 'High saturated fat', 'Saturated Fat'),
        ],
    },
    'Asthma': {
        'eat': [
            ('Ginger', 'Anti-inflammatory properties', 'Gingerols'),
            ('Garlic', 'Reduces airway inflammation', 'Allicin'),
            ('Honey', 'Soothes throat, antibacterial', 'Antioxidants'),
            ('Fatty Fish', 'Omega-3 reduces inflammation', 'Omega-3'),
            ('Apples', 'Quercetin reduces inflammation', 'Quercetin'),
        ],
        'avoid': [
            ('Sulfites', 'Trigger asthma attacks', 'Sulfites'),
            ('Gas-producing Foods', 'Bloating presses lungs', 'FODMAPs'),
            ('Dairy', 'May increase mucus', 'Casein'),
            ('Fried Foods', 'Inflammation trigger', 'Trans Fats'),
            ('Preservatives', 'Can trigger symptoms', 'BHT, BHA'),
        ],
    },
    'Arthritis': {
        'eat': [
            ('Fatty Fish', 'Omega-3 reduces joint inflammation', 'Omega-3'),
            ('Olive Oil', 'Anti-inflammatory properties', 'Oleocanthal'),
            ('Berries', 'Antioxidants reduce inflammation', 'Anthocyanins'),
            ('Broccoli', 'Sulforaphane blocks enzyme damage', 'Sulforaphane'),
            ('Turmeric', 'Curcumin reduces inflammation', 'Curcumin'),
        ],
        'avoid': [
            ('Sugar', 'Triggers inflammation', 'Sugar'),
            ('Refined Carbs', 'Increase inflammation', 'High GI'),
            ('Red Meat', 'Arachidonic acid worsens symptoms', 'Arachidonic Acid'),
            ('Fried Foods', 'Trans fats increase inflammation', 'Trans Fats'),
            ('Alcohol', 'Worsens inflammation', 'Alcohol'),
        ],
    },
    'Migraine': {
        'eat': [
            ('Almonds', 'Magnesium reduces frequency', 'Magnesium'),
            ('Watermelon', 'Hydration prevents headaches', 'Water, Electrolytes'),
            ('Ginger', 'Reduces nausea and pain', 'Gingerols'),
            ('Fatty Fish', 'Omega-3 reduces inflammation', 'Omega-3'),
            ('Dark Chocolate', 'Small amounts can help', 'Magnesium'),
        ],
        'avoid': [
            ('Aged Cheese', 'Tyramine triggers migraines', 'Tyramine'),
            ('Red Wine', 'Histamine and sulfites', 'Histamine'),
            ('Processed Meats', 'Nitrates trigger headaches', 'Nitrates'),
            ('Caffeine', 'Withdrawal causes migraines', 'Caffeine'),
            ('Chocolate', 'Contains tyramine', 'Tyramine'),
        ],
    },
    'Gastritis': {
        'eat': [
            ('Yogurt', 'Probiotics help digestion', 'Probiotics'),
            ('Oatmeal', 'Soothes stomach lining', 'Fiber'),
            ('Ginger', 'Anti-inflammatory, aids digestion', 'Gingerols'),
            ('Bananas', 'Natural antacid', 'Potassium'),
            ('Aloe Vera', 'Soothes stomach lining', 'Acemannan'),
        ],
        'avoid': [
            ('Spicy Foods', 'Irritates stomach lining', 'Capsaicin'),
            ('Citrus Fruits', 'Increases stomach acid', 'Citric Acid'),
            ('Coffee', 'Stimulates acid production', 'Caffeine'),
            ('Alcohol', 'Damages stomach lining', 'Alcohol'),
            ('Fried Foods', 'Hard to digest', 'Saturated Fat'),
        ],
    },
}


def get_food_recommendations(disease_name):
    try:
        disease = Disease.objects.get(name__iexact=disease_name)
        db_foods = FoodRecommendation.objects.filter(disease=disease)
        if db_foods.exists():
            eat = [{'name': f.food_name, 'reason': f.reason, 'nutrition': f.nutritional_info}
                   for f in db_foods.filter(food_type='eat')]
            avoid = [{'name': f.food_name, 'reason': f.reason, 'nutrition': f.nutritional_info}
                     for f in db_foods.filter(food_type='avoid')]
            moderate = [{'name': f.food_name, 'reason': f.reason, 'nutrition': f.nutritional_info}
                        for f in db_foods.filter(food_type='moderate')]
            return {'eat': eat, 'avoid': avoid, 'moderate': moderate, 'source': 'database'}
    except Disease.DoesNotExist:
        pass

    for key in DEFAULT_FOOD_DATA:
        if key.lower() in disease_name.lower() or disease_name.lower() in key.lower():
            data = DEFAULT_FOOD_DATA[key]
            return {
                'eat': [{'name': f[0], 'reason': f[1], 'nutrition': f[2]} for f in data['eat']],
                'avoid': [{'name': f[0], 'reason': f[1], 'nutrition': f[2]} for f in data['avoid']],
                'moderate': [],
                'source': 'default'
            }

    return {
        'eat': [{'name': 'Balanced Diet', 'reason': 'General health', 'nutrition': 'Various'}],
        'avoid': [{'name': 'Processed Foods', 'reason': 'Low nutritional value', 'nutrition': 'High sodium'}],
        'moderate': [],
        'source': 'fallback'
    }
