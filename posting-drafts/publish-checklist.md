# Publish Checklist

Use a new or non-personal GitHub account if you do not want this tied to your main account.

## Create Repo

1. Create a new public GitHub repository.
2. Suggested name:
   - `roborock-qseries-map-bridge`
   - `roborock-q10-map-notes`
   - `roborock-qseries-map-poc`
3. Do not initialize with a README, license, or `.gitignore`; this folder already contains them.
4. Push this folder.

## After Publishing

1. Replace `<PUBLIC_REPO_URL>` in the posting drafts.
2. Open the python-roborock issue/discussion first.
3. Open the Home Assistant Community post second.
4. Open the vacuum map parser issue/discussion third.
5. Link the upstream discussions back in the repo README.

## Suggested Git Commands

Run these inside the public repo folder:

```powershell
git init
git add .
git commit -m "Initial Q-series map bridge proof of concept"
git branch -M main
git remote add origin <PUBLIC_REPO_URL>
git push -u origin main
```

