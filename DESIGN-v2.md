# DESIGN v2 — GTD (Allen) + FNV gamification — fresh design (old DESIGN.md stays as reference)

Status: Prozess wird entlang Allens Buch erarbeitet, noch KEINE technischen Entscheidungen.

## GTD-Prozess (aus dem Buch, Stand: Capture-Schritt besprochen)

Workflow: **Capture → Clarify → Organize → Reflect → Engage**.

- **Capture:** alles typ-los in die Inbox, nur Titel nötig, nie bewerten/sortieren beim Erfassen.
- **Clarify (3 Fragen):** actionable? → nein: Trash / Someday-Maybe / Reference; ja: ≤2 Min → sofort tun; sonst: delegieren (Waiting For + „wen“ + Nachfass-Datum) oder nächster physischer Schritt; >1 Schritt = Projekt.
- **Organize-Buckets:** Kalender (Datum+Uhrzeit, „heilig“), Next Actions (mit Kontext), Waiting For, Projects (mit gewünschtem Ergebnis + Schritten), Someday/Maybe, Reference.
- **Reflect:** täglich Next Actions; wöchentlich Weekly Review mit fester Checkliste (Inbox→0, vergangener/kommender Kalender, Waiting For, Projektliste, Next Actions, Someday, Referenz, Trigger-Liste). Horizons of Focus: 6 Ebenen (Kalender/Aktionen, Projekte, Verantwortungsbereiche, 1–2-J-Ziele, 3–5-J-Vision, Zweck/Prinzipien).
- **Engage:** Next Action nach Kontext / Zeit / Energie / Priorität wählen.

## Reference — eigene, offene Ablage (User-Entscheidung, festgehalten)

Reference ist NICHT „nicht actionable Rest“, sondern **alles, was als Referenz dienen kann**:
Bücher, Webseiten, eigene Notizen und Ideen, Dateien, Links … — bezogen auf Aufgaben,
Projekte oder beliebiges. Fast ein eigenes Teilprojekt (eigenes Modell, Verknüpfungen,
Durchsuchbarkeit).

- Unterscheidung zu Someday/Maybe: Someday = kann actionable werden (Idee inkubieren);
  Reference = Nachschlage-Material (nicht handeln, nur nachschlagen).
- Eine Referenz kann trotzdem eine Action auslösen („Artikel lesen“ → Next Action / Someday).
- Mögliche Felder: Titel, Inhalt/Notiz, Art (Buch/Webseite/Notiz/Idee/Datei/Link), URL/Dateipfad,
  Tags, Verknüpfungen zu Projekt/Task.
- Wird in der Weekly Review mit durchgesehen.

## Offene Verständnisfragen (aus der Prozess-Diskussion)

1. Kalender — ENTSCHIEDEN: Termine brauchen keine eigene Logik im System. Ein Termin in der Inbox wird beim Clarify wie eine 2-Minuten-Action behandelt ("Termin im Kalender eintragen" -> done). Das Kalender-System bleibt extern (User: Google Kalender). Items können weiterhin `due`+`due_time` tragen, damit Reminder/Summary feuern; ein HA-Kalender-Spiegel ist optional/später.
   User nutzt aktuell Google Kalender und will Kalender-Funktionalität MIT GTD-Workflow-Anbindung.
   Faktenlage HA: (a) interne `calendar.*`-Entities (z. B. Local Calendar, Google/CalDAV-Integration) — Events via UI oder Service `calendar.create_event` anlegbar, in HA-Frontend + Companion-App (Dashboard-Kalenderkarte) sichtbar; (b) externe Apps: nur über CalDAV/CardDAV-Backends (Google via CalDAV-App-Passwort, Nextcloud …) — HA ist dann nur ein Client, externe Apps syncen direkt; HA-Local-Calendar ist NICHT via CalDAV exponiert, nur via HA-API/Websocket.
   GTD-Sicht: Kalender bleibt das „heilige“ System für hart zeitgebundene Termine; Items mit Datum+Uhrzeit können gespiegelt werden.
2. Horizons of Focus — ENTSCHIEDEN: später klären. v1: nur Projekte + Someday/Maybe; Horizons of Focus als eigenes Thema vorgemerkt.
3. Trigger-Liste — ENTSCHIEDEN: (b) keine eigene Liste; Trigger-Ideen sind normale Someday/Maybe-Einträge (ggf. mit Tag). Entspricht dem Vorgehen von Toodledo (Someday + Saved Searches in der Review, keine Trigger-Liste) und NirvanaHQ (Someday/Maybe mit Tags, Review-Checkliste).
4. Natural Planning — ENTSCHIEDEN: nur das gewünschte Ergebnis (desired outcome) pro Projekt wird im System festgehalten; der Weg dahin (Zweck/Vision/Brainstorming/Struktur) ist fürs System nicht relevant. Projekte = Name + desired_outcome + Schritte (Actions mit Projekt-Ref).

## Clarify/Organize — Abhängigkeiten & Wiederholungen (aus der Prozess-Diskussion)

- **Abhängige Aufgaben — ENTSCHIEDEN:** prozessual ein **"on hold"-Status** (blockierte Action
  ist keine Next Action, bleibt aber sichtbar, z. B. im Projekt). Ein `depends_on`-Feld mit
  automatischer Freigabe wäre eine mögliche technische Umsetzung — wird später technisch
  besprochen.
- **Wiederkehrende Aufgaben — ENTSCHIEDEN:** Repeat-Regeln an der Action (techn. Umsetzung später);
  Wiederholungen sind etwas anderes als Termine (Termine = Kalender/2-Min-Action, s. Frage 1).
- **Weekly Review:** wird besprochen, nachdem alle Phasen (Capture, Clarify, Organize, Reflect, Engage) durchgesprochen sind.

## Organize — ENTSCHIEDEN (aus der Prozess-Diskussion)

- (a) **Kontexte:** freie Liste mit Standardvorgaben (z. B. @Telefon, @Computer, @Büro, @Errands,
  @Anywhere), Nutzer kann ändern/löschen/ergänzen.
- (b) Ein Item kann **mehrere Kontexte** haben (Liste, nicht einzelner Wert).
- (c) Alle „Buckets“ sind prozessual **Status-Angaben des Items** (inbox / next_action /
  waiting_for / on_hold / someday / reference / done …) — „on hold“ ist damit ein eigener Status/Bucket.
- (d) **Stalled Projects** (aktives Projekt ohne offene Next Action) werden markiert (für die spätere Review).

## Reflect & Engage im Detail (Prozess komplettiert)

- **Reflect täglich:** Next Actions kurz durchsehen, on-the-fly re-priorisieren.
- **Reflect wöchentlich (Weekly Review, Get Clear → Get Current → Get Creative):**
  1. Get Clear: lose Materialien einsammeln, ALLE Inboxes auf null, Kopf leeren (alles → Inbox)
  2. Get Current: vergangener Kalender (1 Woche), kommender Kalender (2–3 Wochen),
     Waiting-For (aktuell? Nachfass-Termine?), Projektliste (aktiv? outcome klar? mind. 1 offene
     Next Action, sonst = STALLED markieren), Next Actions (noch „next“? Kontexte ok?),
     Someday/Maybe (aktivieren/löschen), Reference (grob ordnen), Trigger-Ideen (→ Inbox)
  3. Get Creative: brainstormen, neue Projekte/Ideen
  - Horizons of Focus: regelmäßig mitprüfen (viertel-/jährlich) — bei uns später (Frage 2)
- **Engage:** on the fly nach 4 Kriterien wählen: **Kontext, verfügbare Zeit, verfügbare Energie,
  Priorität**. Next Actions sind nach Kontext gruppiert; erledigte Actions abhaken
  (Gamification/XP später).
