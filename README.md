# hl-tracker

Webbasierte Dienstplanung mit Logins für Assistenzen und einen Adminzugang. Nutzer
können offene Spät- und Nachtdienste unter der Woche sowie Früh-, Nacht- und
Visitendienste am Wochenende übernehmen oder wieder freigeben. Admins können
Schichten anlegen und verbleibende offene Dienste zuweisen.

## Schnellstart

1. **Abhängigkeiten installieren** (Empfehlung: virtuelles Environment nutzen):
   ```bash
   pip install -r requirements.txt
   ```
2. **Datenbank einmalig befüllen** (legt Beispiel-User und Schichten der nächsten 7 Tage an):
   ```bash
   python app.py --init-db
   ```
3. **Server starten**:
   ```bash
   python app.py
   ```
4. **Im Browser öffnen**: http://localhost:5000

### Beispiel-Logins
- Admin: `admin@example.com` / `admin123`
- Assistent:innen: `anna@example.com` / `anna123`, `ben@example.com` / `ben123`

## Funktionen
- **Login & Registrierung** für Assistenzen
- **Schichtübernahme & Freigabe** direkt im Dashboard
- **Adminbereich** zum Anlegen neuer Schichten und manuellem Zuweisen offener
  Dienste (z. B. wenn niemand sich einträgt)
- **Schichttypen**: Spätdienst (Woche), Nachtdienst (Woche), Frühdienst
  (Wochenende), Nachtdienst (Wochenende), Visitendienst (Wochenende)

## Bestehende Skripte
Das frühere CLI-Tool zur fairen Dienstplanung (`schedule_planner.py`) sowie das
kleine Beispiel `hello_world.py` sind weiterhin im Repository enthalten, werden
aber von der Web-App nicht benötigt.
