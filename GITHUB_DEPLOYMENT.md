# Publish To GitHub

Use `python-projects/MY PROJECTS` as the repository root.

## Option A: GitHub Desktop

1. Open GitHub Desktop.
2. Choose `File > Add local repository`.
3. Select `python-projects/MY PROJECTS`.
4. If prompted, create a repository.
5. Commit the files.
6. Click `Publish repository`.
7. Make sure `Keep this code private` is unchecked if you want everyone to see the code.

## Option B: Terminal

From `python-projects/MY PROJECTS`:

```bash
git init
git add .
git commit -m "Prepare public deployment"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO_NAME.git
git push -u origin main
```

## Make The Apps Public

After the repo is public:

1. Deploy `Productivity & Recovery` on Streamlit Community Cloud with entrypoint `productivity_recovery/Home.py`.
2. Deploy `Exercise recommender` on Streamlit Community Cloud with entrypoint `exercise_recommender/app.py`, or on a Python/container host.
3. Deploy `physio-tele-rehab/backend` on a web service host.
4. Deploy the Physio frontend on Streamlit Cloud with entrypoint `physio_frontend/app.py`, or deploy `physio-tele-rehab/frontend` on a Python/container host.
5. Set `API_URL` in the frontend host to the backend URL plus `/api`.

GitHub Pages is not enough for these apps because they run Python servers.
