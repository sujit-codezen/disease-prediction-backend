# AI Medical Diagnosis — Backend

Django REST API for AI-powered medical diagnosis. Uses scikit-learn ML models for symptom-based prediction, Groq Llama 3.1 for conversational health chat, NLP symptom extraction, and OCR report analysis.

## Tech Stack

- **Framework:** Django 4.2 + Django REST Framework
- **ML:** scikit-learn (Random Forest classifier), pandas, numpy, joblib
- **LLM:** Groq API — Llama 3.1 8B Instant (free, fast)
- **NLP:** Custom keyword-based symptom extraction
- **OCR:** Pillow + PyTesseract for lab report analysis
- **Auth:** JWT via djangorestframework-simplejwt
- **Config:** python-decouple

## Setup

```bash
# Activate venv
source ../../django-venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your GROQ_API_KEY

# Run migrations
python manage.py migrate

# Seed symptom database
python manage.py seed_symptoms

# Create admin user
python manage.py createsuperuser

# Start server (port 8001)
python manage.py runserver 8001
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/predict/` | Predict disease from symptoms |
| POST | `/api/chat/` | Chat with AI health assistant |
| POST | `/api/chat/upload-report/` | Upload & analyze lab report |
| GET | `/api/chat/history/` | List chat conversations |
| GET | `/api/chat/history/{id}/` | Get conversation messages |
| GET | `/api/symptoms/` | List all symptoms by body part |
| GET | `/api/diet/{disease}/` | Get diet recommendations |
| GET | `/api/medicine/{disease}/` | Get medicine guide |
| POST | `/api/auth/register/` | Register new user |
| POST | `/api/auth/login/` | Login (get JWT tokens) |

## Chat System

The chat uses a two-tier approach:
1. **DB search first** — checks symptoms, diseases, diet, and medicine tables
2. **LLM fallback** — if no DB match, Groq Llama 3.1 answers from medical knowledge with disclaimer

Intent classification routes queries to specialized system prompts:
- **symptom** → disease suggestions from DB
- **food** → diet recommendations
- **medicine** → medication guidance
- **general** → general health advice
- **chat** → friendly conversation

## Project Structure

```
backend/
├── api/
│   ├── models.py          # Symptom, Disease, Diet, Medicine models
│   ├── chat_models.py     # ChatConversation, ChatMessage
│   ├── views.py           # Prediction, symptom, diet, medicine endpoints
│   ├── chat_views.py      # Chat, report upload, history endpoints
│   ├── serializers.py     # DRF serializers
│   ├── llm_service.py     # Groq Llama 3.1 integration
│   ├── engine.py          # ML prediction engine
│   ├── nlp_processor.py   # NLP symptom extraction
│   ├── report_analyzer.py # OCR report analysis
│   ├── diet_planner.py    # Diet recommendations
│   └── medicine_guide.py  # Medicine recommendations
├── models/                # Trained ML model files
├── data/                  # Seed data (symptoms, diseases, diets, medicines)
├── manage.py
└── requirements.txt
```
