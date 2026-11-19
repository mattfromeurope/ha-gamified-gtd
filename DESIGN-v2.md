# DESIGN v2 — GTD (David Allen) in Home Assistant + FNV-Gamification

**Fresh design.** Das bisherige Design (`DESIGN.md`, Branch `vibe/dev-5adb24`) bleibt als
Referenz erhalten und wird hier nicht übernommen, sondern nur als Erfahrungsquelle genutzt.
Technische Umsetzung siehe `TECH-v2.md`.

Grundlage: David Allens „Getting Things Done“ (2. Auflage). Alle Prozess-Aussagen below
sind dem Buch entnommen; eigene Entscheidungen sind als **ENtschieden** markiert.

---

## 0.0 OBERSTES DESIGNPRINZIP (User, neurodivers — ADHS + Autismus): minimale Reibung

**Je niedriger die Hürde/der Aufwand, desto eher wird das System benutzt und desto eher
halten die GTD-Prinzipien.** Umgekehrt: jeder zusätzliche Klick/jedes Pflichtfeld ist ein
„Schmerzfaktor“, der bei ADHS/Autismus schnell zum Abbruch führt.

Daraus abgeleitete Regeln für ALLE Phasen (Capture→Erledigung) und die gesamte Technik/UI:
- Capture: **ein** Feld (Titel) genügt, überall 1-Tap/1-Satz (Card, App, Widget, Assist);
  sofortiges Feedback („erfasst ✓“), keine Dialog-Ketten, keine Pflichtfelder außer Titel
- Clarify: geleitet, **ein Schritt nach dem anderen**, Defaults vorausgefüllt, nie alles auf einmal
- Listen/Ansichten: ruhig, klar gegliedert, keine Informations-Überflutung; „Fokus“-Ansichten
- Review: geführte Checkliste statt Blanko-Seite
- Benachrichtigungen: hilfreich, nie spammy; leicht snoozen/ausblenden
- Gamification (später) darf motivieren, aber nie zusätzliche Pflicht-Schritte erzeugen
- Generell: keine versteckten Mehrklick-Aktionen, konsistente Patterns, forgiving (undo/„trash“ statt löschen)

## 0. Grundprinzipien von GTD (warum das System so aufgebaut ist)

1. **Open Loops** — alles, was deine Aufmerksamkeit bindet, aber noch nicht „erledigt/abgelegt"
   ist, belastet den Kopf. GTD löst das, indem JEDER offene Punkt in ein **„trusted system“**
   wandert. Erst dann kann das Gehirn abschalten.
2. **Capture alles** — ungefiltert, ohne zu bewerten. Bewerten/Sortieren passiert erst später
   (Clarify).
3. **Klar definierte Listen/Buckets** — jedes Item hat nach dem Clarify genau einen Ort.
4. **Regelmäßige Review** — das Weekly Review ist laut Allen der „critical factor for success“:
   ohne Review verliert das System das Vertrauen („trusted“) und kollabiert.
5. **Engage on the fly** — Ausführen entscheidet man situativ nach Kontext/Zeit/Energie/Priorität,
   nicht in einer großen Planungsrunde.

Der zentrale Workflow:

```
CAPTURE → CLARIFY → ORGANIZE → REFLECT → ENGAGE
(Inbox)  (3 Fragen) (Buckets)   (Review)   (ausführen)
```

---

## 1. Capture (Erfassen)

**Prinzip:** Alles, was einem einfällt/auffällt, landet sofort und ungefiltert in der **Inbox** —
Gedanken, Aufgaben, Termine, Ideen, Unterlagen, physische Dinge. Beim Erfassen wird NICHT
entschieden, was es ist.

- **ENtschiedene HARTREGEL:** ausnahmslos JEDE Erfassung landet zuallererst in der Inbox —
  egal über welchen Weg (Service, todo-Entity, Card, Widget, Assist). Auch ein direkt in einer
  anderen Liste angelegtes todo-Item wird intern in die Inbox umgeleitet. Typ-los: Status wird
  erst beim Clarify entschieden.
  Typ/Status wird erst beim Clarify entschieden.
- **ENtschieden (Capture-Felder, Friction-Prinzip §0.0):** Pflicht = **Titel** allein;
  optional direkt beim Capture: **Notiz** und **Datum** (`due`). Nichts sonst.
- **Zukünftige Ideen (NICHT v1):** Capture von Fotos/PDFs (physische Notizen/Papiere) und
  Audioaufnahmen + Transkription — ausdrücklich für v1 ausgeschlossen, nur vorgemerkt.
- Beim ersten Einrichten: **„Mind Sweep“** — alle offenen Punkte einmalig aufsammeln und in die
  Inbox kippen (Buch: Kapitel „Getting Everything Out of Your Head“).
- Capture-Quellen: alles, was schnell geht — HA-App, Widget, Service, Sprachassistent,
  Companion-App (todo-Entity), geteilte Inbox.

**Beispiele:** „Zahnarzt anrufen“, „Idee: App für Pflanzen“, „Termin Zahnarzt 12.5. 10:00“,
„Buch ‚Deep Work‘ ausleihen“, „Rechnung bezahlen“.

---

## 2. Clarify (Klären) — der Entscheidungsbaum

Pro Inbox-Item werden genau diese Fragen in dieser Reihenfolge durchgegangen:

```
1. Ist es actionable (handlungsfähig)?
   ├─ NEIN ─┬─ Trash (Papierkorb: weg)
   │        ├─ Someday/Maybe (Inkubieren: „könnte ich mal machen“)
   │        └─ Reference (nur nachschlagen: Buch, Link, Notiz, Idee als Material …)
   └─ JA ── 2. Dauert es < 2 Minuten? (2-Minuten-Regel)
              ├─ JA → sofort erledigen (done), nicht auf Liste
              └─ NEIN ── 3. Bin ich die richtige Person?
                         ├─ NEIN → delegieren → Waiting For (+ „wen“ + Nachfass-Datum)
                         └─ JA ── 4. Was ist der nächste physische, sichtbare Schritt?
                                    (z. B. „X anrufen“, NICHT „Vertrag abschließen“)
                                    ├─ Ergebnis braucht > 1 Schritt → PROJECT
                                    │   (Projekt mit ergebnisorientiertem Namen anlegen + erster Schritt
                                    │    als Next Action mit Projekt-Referenz)
- **ENtschieden (A1/Project):** Wird ein Item an ein **bestehendes** Projekt angehängt, bleibt dessen
  Name/Notizen unangetastet. Stattdessen kann ein **Projekt-Clarify** angestoßen werden
  (Projektdetails prüfen/bearbeiten, wenn ein Projekt eine neue Aufgabe erhält) — dieser Schritt
  ist in den **Integrations-Optionen ein-/ausschaltbar** (z. B. `project_clarify_on_new_task`).
                                    └─ sonst → Next Action (+ Kontext, ggf. Fälligkeit/Tickler)
```

Quer durch den Baum: **hartes Datum/Uhrzeit?** → Termin.

- **ENtschieden (Kalender, Frage 1):** Termine brauchen keine eigene System-Logik. Ein Termin
  in der Inbox wird beim Clarify wie eine 2-Minuten-Action behandelt („Termin im Kalender
  eintragen“ → done). Der Kalender bleibt extern (User: Google Kalender). Das Item kann
  zusätzlich `due`/`due_time` tragen, damit interne Reminder/Summary feuern. Kein HA-Kalender-
  Spiegel nötig (optional/später).
- **Delegation:** Waiting For MIT „wen“ (`waiting_for`) und Nachfass-Datum (`follow_up_on`) —
  ohne beides verrottet die Liste (Allen).
- **ENtschieden (A3):** `follow_up_on` ist beim Delegieren **PFLICHT**; gibt der Nutzer keins an,
  greift ein Default von **+7 Tagen**, der in den **Integrations-Optionen** änderbar ist
  (Option z. B. `default_follow_up_days`).
- **2-Minuten-Regel:** sofort tun; landet als `done` im System (sichtbar, später XP).
- **Next Action:** muss ein physischer, sichtbarer Schritt sein, den man „sehen“ kann.
- **Project:** jedes gewünschte Ergebnis mit mehr als einem Action-Schritt.

### 2.1 Abhängige Aufgaben (ergänzend aus unserer Diskussion)
- **ENtschieden:** prozessual ein **„on hold“-Status**: eine blockierte Action ist keine Next
  Action, bleibt aber sichtbar (z. B. im Projekt). Ein `depends_on`-Feld mit automatischer
  Freigabe wäre eine mögliche technische Umsetzung — technische Umsetzung später.
- Allen selbst löst das strukturell: nur der nächste nicht blockierte Schritt ist eine Next
  Action; abhängige Schritte bleiben im Projektplan.

### 2.2 Wiederkehrende Aufgaben (Hausarbeiten etc.)
- **ENtschieden:** Repeat-Regeln an der Action (techn. Umsetzung später). Wiederholungen sind
  etwas ANDERES als Termine (Termine = Kalender, s. Frage 1).
- Umsetzung: beim Erledigen einer Action mit Repeat-Regel wird automatisch die nächste Instanz
  mit verschobenem Datum angelegt; die alte bleibt als `done` sichtbar. Alternativ
  Tickler/Kalender-Eintrag (z. B. „jeden Montag“).

---

## 3. Organize (Organisieren) — die Buckets

- **ENtschieden (Frage c):** Alle Buckets sind prozessual **Status-Angaben des Items** — das Item
  hat einen Status, die „Listen“ sind Sichten auf Status. Status: `inbox`, `next_action`,
  `waiting_for`, `on_hold`, `someday_maybe`, `reference`, `done`.

| Status/Bucket | Inhalt | Pflicht/Regeln |
|---|---|---|
| `inbox` | rohes, unentschiedenes Capture | nur Titel nötig |
| `next_action` | nächste physische Schritte | **Kontext(e)**; bei Projekt: Projekt-Ref; optional due/defer_until |
| `waiting_for` | delegiert | `waiting_for` (wen) + `follow_up_on` (Nachfass-Datum) |
| `on_hold` | blockiert/abhängig | Grund/Vorgänger notieren |
| `someday_maybe` | inkubierte Ideen + Trigger-Ideen | – |
| `reference` | Nachschlage-Material | siehe §3.1 |
| `done` | erledigt | bleibt sichtbar (History, später XP) |

- **ENtschieden (a):** Kontexte = **freie Liste mit Standardvorgaben** (@Telefon, @Computer,
  @Büro, @Errands, @Anywhere …), Nutzer kann ändern/löschen/ergänzen (in den Optionen).
- **ENtschieden (b):** ein Item kann **mehrere Kontexte** haben (Liste).
- **Projekte:** eigenes Objekt mit `name`, **`notes`** (frei: Vision/Support-Material; Projektname = Ergebnis, s. u.), `due?`,
  Status, `task_ids` (die Actions des Projekts).
  **ENtschieden (Frage 4 + Folgefrage):** Natural Planning im System = nur der **Projektname**
  (ergebnisorientiert, das IS das gewünschte Ergebnis bei Allen); es gibt **kein `desired_outcome`-Feld** —
  Vision/Detail/Support kommt in die Projekt-**Notizen**. Zweck/Prinzipien/Brainstorming/Struktur
  bleiben bewusst außerhalb des Systems.
- **ENtschieden (d):** **Stalled Projects** (aktives Projekt ohne offene next_action) werden
  markiert → Review-Punkt.
- Tickler: `defer_until` („nicht actionable vor Datum“) — getrennt von `due` (Fälligkeit).

### 3.1 Reference — eigene, offene Ablage (ENtschieden)
Reference ist NICHT „nicht actionable Rest“, sondern **alles, was als Referenz für Aufgaben,
Projekte oder was auch immer dienen kann**: Bücher, Webseiten, eigene Notizen/Ideen, Dateien,
Links … — bezogen auf Tasks/Projekte/beliebiges. Fast ein eigenes Teilprojekt (eigenes Modell,
Verknüpfungen, Durchsuchbarkeit).
- Abgrenzung zu Someday/Maybe: Someday = *könnte* actionable werden; Reference = Nachschlagen.
- Eine Referenz kann trotzdem eine Action auslösen („Artikel lesen“ → next_action/someday).
- Mögliche Felder: Titel, Inhalt/Notiz, Art (Buch/Webseite/Notiz/Idee/Datei/Link/…), URL/Datei,
  Tags, Verknüpfungen zu Projekt/Task.
- Wird in der Weekly Review mit durchgesehen.

---

## 4. Reflect (Reflektieren)

- **Täglich:** Next Actions kurz durchsehen, on-the-fly re-priorisieren.
- **Wöchentlich (Weekly Review)** — fester Ablauf aus dem Buch („Get Clear → Get Current →
  Get Creative“):
  1. **Get Clear:** lose Materialien einsammeln, ALLE Inboxes auf null, „Kopf leeren“ (alles → Inbox)
  2. **Get Current:**
     - vergangener Kalender (letzte Woche) — was ist passiert/verschoben?
     - kommender Kalender (nächste 2–3 Wochen) — Vorbereitung nötig?
     - **Waiting For** — noch aktuell? Nachfass-Termine ok?
     - **Projektliste** — jedes Projekt aktiv? outcome klar? mind. 1 offene Next Action? (sonst STALLED)
     - **Next Actions** — jede noch „next“? Kontexte aktuell?
     - **Someday/Maybe** — durchsehen, aktivieren oder löschen
     - **Reference** — grob prüfen/ordnen
     - **Trigger-Ideen** (bei uns: Someday/Maybe mit Tag) → ggf. neue Items in die Inbox
  3. **Get Creative:** brainstormen — neue Projekte/Ideen
- **Horizons of Focus** (Allen: 6 Ebenen — Kalender/Aktionen, Projekte, Verantwortungsbereiche,
  1–2-J-Ziele, 3–5-J-Vision, Zweck/Prinzipien): regelmäßig mitprüfen (viertel-/jährlich).
  **ENtschieden (Frage 2):** bei uns SPÄTER klären; v1 = nur Projekte + Someday/Maybe.
- **Trigger-Liste:** **ENtschieden (Frage 3):** keine eigene Liste; Trigger-Ideen sind normale
  Someday/Maybe-Einträge (ggf. mit Tag) — entspricht dem Vorgehen von Toodledo (Someday +
  Saved Searches in der Review) und NirvanaHQ (Someday/Maybe mit Tags, geführte Review-
  Checkliste).

---

## 5. Engage (Ausführen)

Kein großes Planungsmodell — Allen wählt on the fly nach **vier Kriterien**:
1. **Kontext** (wo bin ich / was habe ich zur Hand?)
2. **verfügbare Zeit** (bis zum nächsten Termin)
3. **verfügbare Energie** (fit vs. Routine)
4. **Priorität** (Fälligkeit/Bedeutung)

Next Actions sind nach Kontext gruppiert; man pickt sich etwas Passendes. Erledigte Actions
werden abgehakt (`done`) — bei uns später mit XP/Caps (Gamification, eigenes Kapitel).

---

## 6. Entscheidungs-Log (alles ENtschiedene)

| # | Thema | Entscheidung |
|---|---|---|
| 1 | Kalender/Termine | Termin = Inbox-Item, Clarify wie 2-Min-Action („in Kalender eintragen“); Kalender extern (Google); Item kann `due`/`due_time` für Reminder |
| 2 | Horizons of Focus | später klären; v1 nur Projekte + Someday/Maybe |
| 3 | Trigger-Liste | keine eigene Liste; Trigger-Ideen = Someday/Maybe (ggf. mit Tag) — wie Toodledo/NirvanaHQ |
| 4 | Natural Planning | Projektname = gewünschtes Ergebnis (Allen); KEIN desired_outcome-Feld, stattdessen Projekt-`notes` |
| 5 | Inbox | typ-los: nur Titel Pflicht, landet immer in der Inbox |
| 6 | Abhängigkeiten | on-hold-Status (blockiert sichtbar); depends_on-Auto-Freigabe erst technisch später |
| 7 | Wiederholungen | Repeat-Regeln an der Action; ≠ Termine; neue Instanz beim Erledigen |
| 8 | Kontexte | freie Liste + Defaults, änderbar; mehrere Kontexte pro Item |
| 9 | Buckets | Buckets = Status des Items (inbox/next_action/waiting_for/on_hold/someday_maybe/reference/done) |
| 10 | Stalled Projects | aktive Projekte ohne offene Next Action werden markiert |
| 11 | Reference | eigene offene Ablage (Buch/Link/Notiz/Idee/Datei …), Verknüpfungen, in Review mitgeprüft |
| 12 | Weekly Review | nach allen Phasen besprochen (hier in §4 detailliert) |

## 7. Nicht-Ziele (Scope-Grenzen v1)
- Kein HA-Kalender-Abgleich/Spiegel (Kalender extern)
- Keine Horizons-of-Focus-Objekte (später)
- Keine E-Mail-/Messenger-Integration als Capture-Quelle (nur HA-interne Quellen)
- v1 KEIN Foto/PDF-Capture, KEIN Audio/Transkription (nur als zukünftige Idee vorgemerkt)
- Gamification (FNV) ist eigenes Kapitel in TECH-v2, kommt nach der reinen GTD-Umsetzung

## 8. Glossar
- **Open Loop:** offener Punkt, der Aufmerksamkeit bindet
- **Trusted System:** das System, dem man vertraut, dass nichts verloren geht (hier: unsere Integration)
- **Next Action:** nächster physischer, sichtbarer Schritt
- **Project:** gewünschtes Ergebnis mit > 1 Action-Schritt
- **Context:** Ort/Werkzeug („@Telefon“), unter dem eine Action ausführbar ist
- **Waiting For:** delegierte Action + „wen“ + Nachfass-Datum
- **Tickler:** `defer_until` — „nicht vor Datum X actionable“
- **Stalled Project:** aktives Projekt ohne offene Next Action
- **Weekly Review:** wöchentliches Durch-checken aller Listen (Vertrauensanker)
