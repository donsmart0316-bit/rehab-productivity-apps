# Rehab, Telehealth, and Recovery Apps

This repository contains three Python apps:

- `Exercise recommender`: Streamlit rehab exercise recommendation app.
- `Productivity & Recovery`: Streamlit productivity, recovery, and burnout-prevention coach.
- `physio-tele-rehab`: FastAPI backend plus Streamlit frontend for tele-rehabilitation workflows.

## Public Access Deployment

GitHub makes the code public, but these apps need Python servers. GitHub Pages only hosts static HTML/CSS/JavaScript, so use GitHub as the public source repository and connect the repo to app hosting:

- Streamlit apps: Streamlit Community Cloud, Render, Railway, Hugging Face Spaces, or another Python container host.
- FastAPI backend: Render, Railway, Fly.io, Azure App Service, or another web service host.

Start with [../DEPLOYMENT.md](../DEPLOYMENT.md), then follow each project-specific guide:

- [Exercise recommender deployment](Exercise%20recommender/DEPLOYMENT.md)
- [Productivity & Recovery deployment](Productivity%20%26%20Recovery/DEPLOYMENT.md)
- [Physio Tele-Rehab deployment](physio-tele-rehab/DEPLOYMENT.md)

## What Is Not Committed

The public repo intentionally excludes:

- API keys and `.env` files.
- SQLite databases, uploads, logs, and user history/feedback.
- Large textbook PDFs and generated FAISS vectorstores.
- Local caches and Python bytecode.

For public demos, configure secrets in the hosting platform and attach large/private assets through approved storage.
