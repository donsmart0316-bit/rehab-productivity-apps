# Physio Tele-Rehab Deployment

Deploy this as two services:

- Backend: FastAPI service from `backend/`
- Frontend: Streamlit service from `frontend/`

## Backend

Build command:

```bash
pip install -r requirements.txt
```

Start command:

```bash
uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

Required production environment variables:

```text
SECRET_KEY=replace-with-a-long-random-secret
```

Optional environment variables:

```text
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@example.com
SMTP_PASSWORD=your-email-app-password
SMTP_FROM=your-email@example.com
TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_AUTH_TOKEN=your-twilio-auth-token
TWILIO_FROM_PHONE=+15551234567
PHYSIO_DB_PATH=physio.db
UPLOAD_DIR=uploads
TRANSLATION_PROVIDER=mymemory
```

SQLite is fine for a demo. For production clinical data, use managed storage/database, regular backups, and a privacy/security review before collecting real patient information.

## Frontend

Build command:

```bash
pip install -r requirements.txt
```

Start command:

```bash
streamlit run app.py --server.address 0.0.0.0 --server.port $PORT
```

Set `API_URL` to the deployed backend URL plus `/api`, for example:

```text
API_URL=https://physio-tele-rehab-api.example.com/api
```

## Deployment Order

1. Deploy the backend first.
2. Copy the backend public URL.
3. Deploy the frontend with `API_URL` pointing at the backend `/api` route.
4. Register a test user and verify login, onboarding, recommendations, appointments, and uploads.
