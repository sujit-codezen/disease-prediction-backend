import groq
from decouple import config
from .models import Symptom, Disease, FoodRecommendation, MedicineRecommendation

client = None

def get_client():
    global client
    if client is None:
        client = groq.Client(api_key=config('GROQ_API_KEY'))
    return client


SYSTEM_PROMPT = """You are MedDiagnosis AI, a medical AI assistant. You help users understand their health symptoms and provide helpful health information.

RULES:
1. Always be empathetic and caring in your responses
2. If database results are provided, use them as the primary source and explain them clearly
3. If no database results, use your medical knowledge but always add a disclaimer
4. Always recommend consulting a doctor for proper diagnosis and treatment
5. For food questions, suggest healthy options related to the condition
6. For medicine questions, suggest OTC options only (never prescribe prescription drugs)
7. Use markdown formatting for readability (bold, lists, headers)
8. Include severity levels when available
9. Keep responses concise but thorough
10. Always end with a health disclaimer when providing medical information

RESPONSE FORMAT:
- Use **bold** for important terms
- Use numbered lists for multiple items
- Use bullet points for sub-items
- Keep paragraphs short
- Always include a disclaimer at the end for medical advice"""

FOOD_PROMPT = """You are a nutrition advisor. Provide healthy food recommendations based on the user's condition.
- Suggest foods that help with the condition
- Mention foods to avoid
- Include portion guidance when relevant
- Keep responses practical and actionable"""

MEDICINE_PROMPT = """You are a pharmacy guide. Provide OTC medicine information based on the user's condition.
- Suggest common OTC medicines
- Mention dosage guidelines (standard adult dosage)
- Include side effects to watch for
- Always recommend consulting a pharmacist or doctor
- Never suggest prescription medications"""


def search_database(symptoms):
    """Search DB for matching diseases based on symptoms"""
    if not symptoms:
        return []

    matching_diseases = []
    for disease in Disease.objects.prefetch_related('symptoms').all():
        disease_symptoms = [s.name.lower() for s in disease.symptoms.all()]
        matches = [s for s in symptoms if s.lower() in disease_symptoms]
        if matches:
            matching_diseases.append({
                'disease': disease.name,
                'description': disease.description,
                'severity': disease.severity,
                'causes': disease.causes,
                'treatments': disease.treatments,
                'prevention': disease.prevention,
                'matched_symptoms': matches,
                'match_score': len(matches) / len(disease_symptoms) if disease_symptoms else 0
            })

    return sorted(matching_diseases, key=lambda x: x['match_score'], reverse=True)[:5]


def get_food_from_db(disease_name):
    """Get food recommendations from database"""
    foods = FoodRecommendation.objects.filter(disease__name__iexact=disease_name)
    if foods.exists():
        return [
            {'name': f.food_name, 'type': f.food_type, 'reason': f.reason}
            for f in foods[:10]
        ]
    return None


def get_medicine_from_db(disease_name):
    """Get medicine recommendations from database"""
    meds = MedicineRecommendation.objects.filter(disease__name__iexact=disease_name)
    if meds.exists():
        return [
            {'name': m.medicine_name, 'type': m.medicine_type, 'dosage': m.dosage, 'warnings': m.warnings}
            for m in meds[:10]
        ]
    return None


def extract_symptoms_from_message(message):
    """Extract symptom names from user message"""
    symptoms = Symptom.objects.all()
    found = []
    msg_lower = message.lower()
    for symptom in symptoms:
        if symptom.name.lower() in msg_lower:
            found.append(symptom.name)
    return found


def classify_intent(message):
    """Classify user intent from message"""
    msg_lower = message.lower()

    food_keywords = ['food', 'diet', 'eat', 'nutrition', 'meal', 'fruit', 'vegetable', 'protein', 'vitamin']
    medicine_keywords = ['medicine', 'drug', 'pill', 'tablet', 'medication', 'treatment', 'cure', 'remedy']
    symptom_keywords = ['symptom', 'feel', 'pain', 'ache', 'sick', 'ill', 'fever', 'cough', 'headache', 'nausea']
    general_keywords = ['what is', 'tell me', 'explain', 'define', 'meaning']

    if any(kw in msg_lower for kw in food_keywords):
        return 'food'
    if any(kw in msg_lower for kw in medicine_keywords):
        return 'medicine'
    if any(kw in msg_lower for kw in symptom_keywords):
        return 'symptom'
    if any(kw in msg_lower for kw in general_keywords):
        return 'general'
    return 'chat'


def chat_with_llm(user_message, conversation_history, db_context=None, intent='chat'):
    """Send message to Groq Llama 3.1"""
    get_client()

    if intent == 'food':
        system = FOOD_PROMPT
    elif intent == 'medicine':
        system = MEDICINE_PROMPT
    else:
        system = SYSTEM_PROMPT

    messages = [{"role": "system", "content": system}]

    if db_context:
        messages.append({
            "role": "system",
            "content": f"DATABASE SEARCH RESULTS:\n{db_context}\n\nUse these results to inform your response. If results are provided, prioritize them over your general knowledge."
        })

    for msg in conversation_history[-20:]:
        messages.append({
            "role": msg['role'],
            "content": msg['content']
        })

    messages.append({"role": "user", "content": user_message})

    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=messages,
        max_tokens=1024,
        temperature=0.7,
        top_p=0.9
    )

    return response.choices[0].message.content


def process_message(user_message, conversation_history=None):
    """Main entry point: search DB first, then LLM"""
    if conversation_history is None:
        conversation_history = []

    intent = classify_intent(user_message)
    symptoms = extract_symptoms_from_message(user_message)
    db_results = search_database(symptoms) if symptoms else []

    db_context = None
    if db_results:
        context_parts = []
        for r in db_results[:3]:
            part = f"**{r['disease']}** (Severity: {r['severity']})\n"
            part += f"Description: {r['description']}\n"
            if r['treatments']:
                part += f"Treatments: {r['treatments']}\n"
            if r['prevention']:
                part += f"Prevention: {r['prevention']}\n"
            part += f"Matched symptoms: {', '.join(r['matched_symptoms'])}\n"
            context_parts.append(part)
        db_context = "\n\n".join(context_parts)

    if intent == 'food' and db_results:
        for r in db_results[:2]:
            foods = get_food_from_db(r['disease'])
            if foods:
                db_context += f"\n\nFood recommendations for {r['disease']}:\n"
                for f in foods:
                    db_context += f"- {f['name']} ({f['type']}): {f['reason']}\n"

    if intent == 'medicine' and db_results:
        for r in db_results[:2]:
            meds = get_medicine_from_db(r['disease'])
            if meds:
                db_context += f"\n\nMedicine recommendations for {r['disease']}:\n"
                for m in meds:
                    db_context += f"- {m['name']} ({m['type']}): {m['dosage']}\n"

    response = chat_with_llm(user_message, conversation_history, db_context, intent)

    return {
        'response': response,
        'db_results': db_results,
        'symptoms_found': symptoms,
        'intent': intent
    }
