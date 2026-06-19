# Productivity & Recovery Deployment

## Streamlit Community Cloud

1. Push this folder to GitHub.
2. Create a Streamlit app with `app/Home.py` as the main file.
3. Keep `requirements.txt`, `models/`, and the required `data/` artifacts in the deployed repository or attached storage.
4. Add optional LLM secrets:

```toml
GROQ_API_KEY = "your-groq-api-key"
GROQ_MODEL = "llama-3.1-8b-instant"
```

The app has deterministic fallback explanations, so it can run without a Groq key.

## Render Or Docker Host

Use the included `Procfile` for a Python web service, or the included `Dockerfile` for a container service.

Build command:

```bash
pip install -r requirements.txt
```

Start command:

```bash
streamlit run app/Home.py --server.address 0.0.0.0 --server.port $PORT
```

Environment variables:

```text
GROQ_API_KEY=your-groq-api-key
GROQ_MODEL=llama-3.1-8b-instant
PYTHONPATH=.
```
