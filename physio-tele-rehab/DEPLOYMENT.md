# Physio Tele-Rehab Deployment

Deploy this as two services:

- Backend: FastAPI service from `backend/`
- Frontend: Streamlit service from `frontend/`, or Streamlit Cloud entrypoint `physio_frontend/app.py`

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
SECRET_KEY=replace-with-a-long-random-secret-at-least-32-characters
DATABASE_URL=postgresql+psycopg://user:password@host:5432/postgres?sslmode=require
```

Use managed PostgreSQL for multi-user deployment. Supabase, Neon, and Render PostgreSQL all work as long as `DATABASE_URL` is set. `postgres://...` and `postgresql://...` URLs are automatically normalized to the `psycopg` SQLAlchemy driver.

Run migrations from the backend directory after setting `DATABASE_URL`:

```bash
alembic upgrade head
```

Optional environment variables:

```text
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@example.com
SMTP_PASSWORD=your-email-app-password
SMTP_FROM=your-email@example.com
SMTP_TRY_FALLBACK_PORTS=false
GROQ_API_KEY=your-groq-api-key
GROQ_MODEL=llama-3.1-8b-instant
TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_AUTH_TOKEN=your-twilio-auth-token
TWILIO_FROM_PHONE=+15551234567
UPLOAD_DIR=uploads
TRANSLATION_PROVIDER=mymemory
```

SQLite is still available only as a local fallback via `PHYSIO_DB_PATH`. Do not use the SQLite file for production or multiple users. For production clinical data, use managed PostgreSQL, backups, private storage for uploads, and a privacy/security review before collecting real patient information.

## Frontend

Build command:

```bash
pip install -r requirements.txt
```

Start command:

```bash
streamlit run app.py --server.address 0.0.0.0 --server.port $PORT
```

For Streamlit Community Cloud, use this main file path:

```text
physio_frontend/app.py
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
