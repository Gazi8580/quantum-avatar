# Quantum Avatar — Streamlit Dashboard

Kurz: Lokales Streamlit‑Dashboard für das Quantum Avatar Projekt mit Desktop‑Launcher und Anweisungen für sicheres Deployment.

## Übersicht
Dieses Repo enthält das Streamlit‑Dashboard (new_dashboard.py) und Hilfs‑Skripts für lokales Starten und Deployment. Sensible Keys wurden aus dem Repo entfernt — trage sie als Secrets ein.

## Schnellstart (lokal)
1. Abhängigkeiten installieren:
```bash
pip install --user -r requirements.txt
```
2. App starten:
```bash
python -m streamlit run new_dashboard.py --server.port 8501 --server.address 127.0.0.1
```
3. Öffnen: http://localhost:8501

Desktop‑Launcher:
- Datei: %USERPROFILE%\Desktop\KLICK_MICH_ZUR_INSTALLATION.bat
- Startet Streamlit via `python -m streamlit run` und fällt bei Fehlern auf CLI‑Fallback (CORE_LOGIC.py) zurück.

## Deployment (Streamlit Community Cloud)
- Repository verbinden → Branch `main` auswählen.
- Hauptdatei: `new_dashboard.py`
- In Settings → Secrets: alle API‑Keys als Umgebungsvariablen hinzufügen (z. B. CLAUDE_API_KEY, GROK_API_KEY, OPENROUTER_API_KEY, BLACKBOX_API_KEY, AMAZON_Q_API_KEY).
- Deploy starten und Logs prüfen.

## Sicherheit / Geheimnisse
WICHTIG:
- Revoke/Renew sofort alle geleakten Keys, die in alten Dateien auftauchten (env.ini, .env, paypal_maximizer.py).
- Niemals API‑Keys ins Repo committen.
- Verwende git‑filter‑repo um Historie zu bereinigen (bereinigter Clone: https://github.com/Gazi8580/quantum-avatar-cleaned).
- Trage neue Keys nur in Secrets (Streamlit Cloud / GitHub Actions / CI) oder OS‑Environment ein.

## Troubleshooting
- Streamlit CLI nicht gefunden → verwende `python -m streamlit run`.
- Frontend DOM-Fehler (removeChild) → App neu starten; im Cloud‑Deployment Logs prüfen; ggf. Patch in `new_dashboard.py` (try/except um transient UI‑Updates).

## Nützliche Befehle
```bash
# lokale Version prüfen
python -m streamlit --version

# bereinigten Repo pushen (force, nur wenn autorisiert)
git push --force origin main
```

## Kontakt / Hinweise
- Repo (bereinigt): https://github.com/Gazi8580/quantum-avatar-cleaned
- Original (nicht überschreiben, history wurde gesichert): https://github.com/Gazi8580/quantum-avatar
