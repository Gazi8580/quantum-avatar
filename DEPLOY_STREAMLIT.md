# Deployment-Anleitung — Streamlit Community Cloud (kurz)

Wichtiger Hinweis vorab
- Entfernen Sie unbedingt alle Secrets (.env, .env.backup) aus dem Repo und spielen Sie geleakte API‑Keys sofort zurück (rotate/revoke), sonst wird GitHub Push Protection den Push blockieren.

1) Lokale Aufräum‑Schritte (empfohlen)
- Entfernen aus Index + .gitignore:
```bash
git rm --cached --ignore-unmatch .env .env.backup
echo ".env" >> .gitignore
git add .gitignore
git commit -m "Remove secrets from index and add .gitignore"
```
- Falls Secrets bereits in der Historie sind: benutzen Sie git‑filter-repo (sicherer als filter-branch)
```bash
python -m pip install --user git-filter-repo
git filter-repo --invert-paths --paths .env --paths .env.backup
```
- Alternative (wenn git-filter-repo nicht verfügbar): BFG Repo Cleaner (siehe BFG‑Dokumentation).

2) Pushen nach GitHub
- Authentifizieren (falls nötig):
```bash
gh auth login
```
- Pushen:
```bash
git remote add origin https://github.com/YOUR_USER/quantum-avatar.git   # falls noch nicht gesetzt
git branch -M main
git push -u origin main
```
- Bei Push‑Schutz: folgen Sie der Security‑URL in der GitHub‑Fehlermeldung oder säubern die Historie wie oben.

3) Streamlit Community Cloud — App erstellen
- Melden Sie sich an: https://share.streamlit.io
- New app → Connect GitHub → wählen Sie `Gazi8580/quantum-avatar` und Branch `main`.
- Main file: `new_dashboard.py` (oder `paypal_maximizer.py` falls Sie diese bevorzugen).
- Runtime: Python, Requirements: `requirements.txt` im Repo.
- Setzen Sie Secrets via Settings → Secrets (fügen Sie API_KEYS dort ein; nicht in Repo).

4) Tests & Troubleshooting
- Nach Deploy: öffnen Sie die App in Streamlit Cloud, prüfen Logs.
- Wenn Frontend JS‑Fehler (removeChild) auftreten:
  - Console-Log im Browser kopieren.
  - Streamlit Logs anschauen (Cloud logs / Terminal lokal).
  - Temporär unsafe_allow_html entfernen / Custom Components deaktivieren.
  - Neustart der App in Cloud durchführen.

5) Sicherheit
- Rotieren/Revoke aller geleakter Keys.
- Verwenden Sie `.gitignore` und vermeiden Sie Secrets im Repo.

Kurzbefehle (Zusammenfassung)
```bash
# Aufräumen
git rm --cached .env .env.backup
echo ".env" >> .gitignore
git add .gitignore
git commit -m "Remove secrets"
python -m pip install --user git-filter-repo
git filter-repo --invert-paths --paths .env --paths .env.backup
git push --force origin main

# Streamlit lokal testen
python -m streamlit run new_dashboard.py --server.port 8501 --server.address 127.0.0.1
```

Wenn Sie möchten, führe ich lokal die Bereinigung und den finalen Push durch — bestätige bitte, dass ich fortfahren darf (oder führen Sie die obenstehenden Befehle lokal aus).
