# AI Medical Diagnosis — Backend

Django REST API for AI-powered medical diagnosis. Scikit-learn ML prediction, Groq Llama 3.1 conversational chat, NLP symptom extraction, and OCR report analysis.

## Tech Stack

- **Framework:** Django 4.2 + Django REST Framework
- **ML:** scikit-learn (Random Forest, Decision Tree, Naive Bayes, SVM, Ensemble), pandas, numpy, joblib
- **LLM:** Groq API — Llama 3.1 8B Instant (free)
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

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/api/auth/register` | No | Register new user |
| POST | `/api/auth/login` | No | Login (get JWT tokens) |
| POST | `/api/auth/refresh` | No | Refresh access token |
| GET | `/api/auth/profile` | Yes | Get user profile |
| GET | `/api/symptoms` | No | List all symptoms by body part |
| GET | `/api/symptoms/search?q=` | No | Search symptoms |
| GET | `/api/diseases` | No | List all diseases |
| GET | `/api/diseases/<id>` | No | Disease detail |
| POST | `/api/diagnose` | Yes | Predict disease from selected symptoms |
| POST | `/api/diagnose-text` | Yes | NLP text-based diagnosis |
| POST | `/api/chat` | Yes | Chat with AI health assistant |
| POST | `/api/chat/report` | Yes | Upload & analyze lab report |
| GET | `/api/chat/conversations` | Yes | List chat conversations |
| GET | `/api/chat/conversations/<id>` | Yes | Get conversation messages |
| DELETE | `/api/chat/conversations/<id>` | Yes | Delete conversation |
| GET | `/api/diet/<disease>` | No | Diet recommendations |
| GET | `/api/medicines/<disease>` | No | Medicine recommendations |
| POST | `/api/upload-report` | Yes | Upload lab report (OCR) |
| GET | `/api/reports` | No | List uploaded reports |
| GET | `/api/reports/<id>` | No | Report detail |
| GET | `/api/history` | Yes | Diagnosis history |
| GET | `/api/search-history?q=` | No | Search history |
| GET | `/api/hospitals?lat=&lng=` | No | Nearby hospitals |
| GET | `/api/admin/stats` | Yes | Admin dashboard stats |
| GET | `/api/admin/datasets` | Yes | List uploaded datasets |
| POST | `/api/admin/train` | Yes | Train ML models |
| GET | `/api/admin/models` | Yes | List trained models |
| POST | `/api/admin/model/<id>/activate` | Yes | Activate a model |

## Chat System

Two-tier approach:
1. **DB search first** — matches symptoms, diseases, diet, medicine tables
2. **LLM fallback** — Groq Llama 3.1 answers from medical knowledge with disclaimer

Intent classification routes to specialized system prompts:
- **symptom** → disease suggestions from DB
- **food** → diet recommendations
- **medicine** → medication guidance
- **general** → general health advice
- **chat** → friendly conversation

## Project Structure

```
backend/
├── api/
│   ├── models.py          # Symptom, Disease, Diet, Medicine, Dataset, TrainedModel
│   ├── chat_models.py     # ChatConversation, ChatMessage
│   ├── views.py           # Prediction, symptom, diet, medicine, admin endpoints
│   ├── chat_views.py      # Chat, report upload, conversation history
│   ├── serializers.py     # DRF serializers
│   ├── llm_service.py     # Groq Llama 3.1 integration, intent classification
│   ├── engine.py          # ML prediction engine (train, predict, cache)
│   ├── nlp_processor.py   # NLP symptom extraction
│   ├── report_analyzer.py # OCR report analysis
│   ├── diet_planner.py    # Diet recommendations
│   └── medicine_guide.py  # Medicine recommendations
├── models/                # Trained ML model files (.pkl)
├── data/                  # Seed data (symptoms, diseases, diets, medicines)
├── manage.py
└── requirements.txt
```

## Requirements

```
Django>=4.2,<5.1
djangorestframework>=3.14,<3.16
djangorestframework-simplejwt>=5.3,<6.0
django-cors-headers>=4.3,<5.0
python-decouple>=3.8
scikit-learn>=1.3,<2.0
pandas>=2.0,<3.0
numpy>=1.24,<3.0
joblib>=1.3,<2.0
groq>=0.4.0
pillow>=10.0,<12.0
pytesseract>=0.3.10,<1.0
requests>=2.31,<3.0
```
