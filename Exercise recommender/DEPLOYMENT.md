# Exercise Recommender Deployment

## Streamlit Community Cloud

1. Push this folder to GitHub.
2. Create a Streamlit app with `recommender.py` as the main file.
3. Add this secret:

```toml
GROQ_API_KEY = "your-groq-api-key"
```

4. Include `rehab_recommender.xlsx` and either `textbook_vectorstore/` or the `textbooks/` PDFs in the deployed repo/storage.

The prebuilt `textbook_vectorstore/` is faster at startup. If you deploy without it, the app will build the FAISS index from `textbooks/` on first run, which can take several minutes and may fail on low-memory free tiers.

## Render Or Docker Host

Use the included `Procfile` for a Python web service, or the included `Dockerfile` for a container service.

Build command:

```bash
pip install -r requirements.txt
```

Start command:

```bash
streamlit run recommender.py --server.address 0.0.0.0 --server.port $PORT
```

Environment variables:

```text
GROQ_API_KEY=your-groq-api-key
GROQ_MODEL=llama-3.1-8b-instant
```
