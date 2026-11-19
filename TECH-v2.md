# TECH v2 — technisches Umsetzungskonzept: GTD in Home Assistant (+ FNV-Gamification später)

Basis: `DESIGN-v2.md` (GTD-Prozess + Entscheidungs-Log). Referenz für bewährte Patterns und
Hard-Learned-Lessons: alte Implementierung auf `vibe/dev-5adb24` (DESIGN.md, README,
`custom_components/gamified_gtd/`). Dieser Branch hier enthält bewusst nur Doku.

---

## 1. Ziele / Nicht-Ziele

Ziele: möglichst originalgetreue GTD-Umsetzung als HA-Custom-Integration; alles auch ohne
eigene Cards bedienbar (Services, todo-Entities, Sensoren, Events); Multi-User über
`person.*`; Gamification (FNV) als eigene Schicht später.
Nicht-Ziele v1: kein Kalender-Spiegel (Kalender extern), keine Horizons-Objekte, keine
E-Mail-Integration, keine FNV-Original-Icons (Copyright — Drop-in-Ordner + Fallbacks).

## 2. Was HA nativ bietet (Inventar)

| capability | HA-Mechanismus | GTD-Nutzung |
|---|---|---|
| Config Entry + Options Flow | `config_flow.py`, `OptionsFlow`, Selectoren | Setup: Personen, Kontexte (Default-Liste), Defaults (time_estimate/energy), Benachrichtigungs-Services, Summary-Zeit |
| Services | `hass.services.async_register` + `services.yaml` (mit Selektoren) | kompletter Schreibzugriff (Capture, Clarify, …) |
| Entities | `todo.*` (Features CREATE/UPDATE/DELETE/SET_DUE…), `sensor.*`, `binary_sensor` | Listen/Sichten; todo-Entities halten Companion-App kompatibel |
| Events | `hass.bus.async_fire` | UI-Updates, Automationen für den User |
| Persistenz | `homeassistant.helpers.storage.Store` (JSON in `.storage/`) | Single Source of Truth |
| Personen | `person.*`-Entities (user_id, Zonen-Tracking) | Multi-User, assigned_to, Zonen-Reminder |
| Zonen | `zone.*` + State-Änderungen | ortsbasierte „held“-Reminder |
| Kalender | `calendar.*`-Entities (lesen) | optional später; v1 extern |
| Benachrichtigung | `notify.*`-Services, `persistent_notification` | Reminder, Summary, Review-Hinweis |
| Websocket/REST API | HA built-in | externe Capture-Apps, LLM-Tools |
| Frontend | Lovelace custom cards, `async_register_static_paths`, extra module URLs | eigene Cards (theme-aware) |
| Automationen | User-seitig auf unsere Events | z. B. „bei quest_completed → …“ |
| HACS | `hacs.json`, manifest | Distribution |

## 3. Architektur-Entscheidungen (offen — morgen im Detail)

1. **Entity-Mapping** (Kernfrage):
   - **A) Geteilte todo-Entities pro Bucket** (`todo.gtd_inbox`, `todo.gtd_next_actions`, …):
     + Companion-App/HA-Todo-Card kompatibel, Schreibzugriff nativ (create/update/delete item)
     + bewährt in v1 (Better-ToDo-Modell)
     − GTD-Status (welcher Bucket) muss als Attribut gepflegt werden; Buckets = Status des
       Items (Design-Entscheidung 9) passt besser zu B/C
   - **B) Eine todo-Entity**, Bucket als Attribut `status` (z. B. `todo.gamified_gtd`): Buckets
     = Status (Design-konform), aber Companion-App sieht alles in einer Liste
   - **C) Keine todo-Entities**, nur Sensoren + Services + eigene Cards: maximal design-konform,
     aber keine native App-Unterstützung
   - Empfehlung: **A** (todo-Entities pro Bucket) mit GTD-Status als Attribut — Kompatibilität
     + saubere Sichten; ODER B wenn „Buckets = Status“ strikt umgesetzt werden soll. Morgen entscheiden.
2. **Storage:** eine `Store`-JSON (`gamified_gtd`) als Single Source of Truth; Entities als
   schreibbarer Spiegel (Write-Through via Services). Alternative: nur HA-Entities/Storage.
3. **Multi-User:** geteilte Listen + `assigned_to` (v1-Ansatz) vs. pro Person getrennte
   Bereiche. Empfehlung: geteilt + assigned_to (GTD ist prinzipiell teilbar).
4. **Schreibpfade:** Services (immer) + todo-Entity-Operationen (Write-Through in den Manager).
5. **UI-Umfang:** eigene Cards (v1: 10 Typen) vs. HA-Built-ins (todo-Card, calendar) + wenige
   eigene. Prinzip bleibt: thin frontend — alles geht auch ohne Cards.

## 4. Domänenmodell (Daten)

### 4.1 Item (ein erfasstes Ding)
```json
{
  "id": "uuid", "title": "…", "notes": "…",
  "status": "inbox|next_action|waiting_for|on_hold|someday_maybe|reference|done",
  "contexts": ["@telefon"],            // mehrere erlaubt (Entsch. 8b)
  "project_id": null, "assigned_to": "person.x|null",
  "due": null, "due_time": null,       // Fälligkeit (Reminder-Quelle)
  "defer_until": null,                 // Tickler: nicht actionable vor Datum
  "waiting_for": null, "follow_up_on": null,   // Delegation (Entsch. Waiting For)
  "repeat": null,                      // {"rule": "daily|weekly|monthly|yearly|weekdays", …}
  "hold_reason": null,                 // on_hold: warum blockiert (depends_on später)
  "time_estimate": 15, "energy": 3, "priority": 3,   // für Engage (4 Kriterien)
  "tags": [], "source": "card|app|service|…",
  "created_at": "…", "updated_at": "…", "completed_at": null,
  "reminders": [60, 1440], "overdue_repeat": null, "location": {"zone": "zone.home", "mode": "inside"}
}
```
Invarianten: `waiting_for` ⇒ `waiting_for`-Whom gesetzt; `on_hold` ⇒ `hold_reason`;
`status=done` ⇒ `completed_at`; Repeat ⇒ beim complete neue Instanz (Entsch. 7).

### 4.2 Project
```json
{"id": "…", "name": "…", "desired_outcome": "…", "due": null,
 "status": "active|done", "task_ids": [], "created_at": "…", "updated_at": "…", "completed_at": null}
```
`stalled` = berechnet: aktiv UND keine offene `next_action` unter task_ids (Entsch. 10).

### 4.3 Review
```json
{"id": "…", "person": "person.x", "started_at": "…", "completed_at": null,
 "checklist": {"inbox_empty": bool, "waiting_for_followed_up": bool, "projects_reviewed": bool,
               "next_actions_current": bool, "someday_reviewed": bool, "reference_reviewed": bool,
               "calendar_checked": bool /* manuell */}}
```
Checkliste berechnet aus Timestamps (7-Tage-Fenster, `updated_at`) — v1-Ansatz aus der
alten Implementierung übernehmen (war dort schon korrekt), erweitert um reference.

### 4.4 Status-Machine (Item)
```
inbox ──clarify──▶ next_action | waiting_for | someday_maybe | reference | on_hold | done
                            ▲          │                │
next_action/on_hold ──set_status──▶ … (jeder Bucket-Wechsel erlaubt)
waiting_for ──(Nachfass-Datum erreicht/fällig)──▶ next_action (manuell oder Reminder)
* ──complete──▶ done   (Repeat ⇒ neue Instanz im Ausgangszustand)
* ──remove──▶ (gelöscht)
```

## 5. Service-Katalog (prozessnah)

| Service | Payload (Kern) | Effekt / Events |
|---|---|---|
| `capture` | `title` + optional notes u. a. | Item mit `status=inbox` (immer Inbox, Entsch. 5); Event `item_added` |
| `clarify` | `item_id`, `decision` (next_action/project/waiting_for/someday_maybe/reference/trash/done), + `contexts`, `project_id`/`project_name`+`desired_outcome`, `waiting_for`, `follow_up_on`, `due`, `defer_until` | Status setzen, ggf. Projekt anlegen, 2-Min-Regel (`done` → complete); Events |
| `set_status` / `move` | `item_id`, `status` | Bucket-Wechsel; Event |
| `update_item` | `item_id` + Felder | Update + `updated_at`; Event |
| `complete` | `item_id` | → `done`, `completed_at`; Repeat → neue Instanz; später XP; Event `item_completed` |
| `delegate` | `item_id`, `waiting_for`, `follow_up_on` | → `waiting_for`; Event |
| `remove` | `item_id` | löschen; Event |
| `create_project` / `update_project` / `remove_project` / `complete_project` | Projekt-Felder | Projekt-CRUD; `complete_project` → Rewards (Gamification später); stalled-Berechnung; Event `project_*` |
| `start_review` / `complete_review` | `person` | Review-Objekt + Checkliste; Event `review_completed` |
| `get_state` | `person?` | Snapshot (für Cards/LLM) |
| (Gamification später) `submit_goat`, `allocate_skill_points`, `choose_perk`, `reset_profile`, `redeem_reward` … | | eigene Schicht |

Events: `gamified_gtd_data_updated` (zentral für UI), `item_added/completed/removed`,
`project_created/updated/completed`, `review_started/completed`, Reminder-Events. **Wichtig
(Lesson v1):** Listener-Signatur MUSS das Event-Argument akzeptieren (`def h(self, event)`),
sonst läuft der Listener nie (TypeError im Log).

## 6. Benachrichtigungs-Schicht (Reminder/Summary)
- Eigener Scheduler auf `due`+`due_time`: mehrere Vorlauf-Reminder (`reminders: [60, 1440]`),
  `overdue_repeat` (Wiederholung bei Überfällig), tägliche Summary (konfigurierbare Zeit,
  optional persistent_notification).
- Ortsbasiert: `location {zone, mode}` — Reminder wird „gehalten“, bis die Person in der Zone
  ist (zone/person-State-Tracking, Better-ToDo-Mechanik).
- Alles pro Person über deren `notify.*`-Service; Zonen-Tracking über `person.*`.
- **Lesson v1:** Event feuern BEFORE disk write (debounced), sonst UI-Lag; `should_poll=False`
  bei event-getriebenen Entities.

## 7. Frontend (Cards) — später im Detail, Prinzipien jetzt
- Theme-aware (CSS-Variablen des HA-Themes), look like built-in cards; FNV-Look nur via
  Content + Drop-in-Icons (nie Original-Icons ausliefern).
- Technisch bewährt (Lessons v1): `lit` per dynamischem `import("lit")` + vendored Fallback-
  Bundle (kein statischer lit-Import — killt sonst das ganze Modul auf HA ohne lit-Importmap);
  `async_register_static_paths` (plural, API ab 2025.7); `ServiceCall(hass, …)` (hass zuerst);
  Manifest-Version bei JEDEM JS-Change bumpen (`?v=` Cache-Bust); Card-Editor-Contract:
  `getConfigElement()` + Editor mit `setConfig()` UND `config`-Property + `config-changed`
  mit **vollständiger** Config feuern (sonst verschwinden Optionen aus dem YAML).
- Card-Inventar (v1 hatte 10): Capture/Inbox, Listen-Ansicht (Bucket/Kontext-Filter),
  Projekte (Pip-Boy-Split: Liste links, Detail rechts), Reference, Review, + Gamification-Cards
  später (Stats/SPECIAL/Skills/Perks/Levelup/GOAT/Shop).
- Thin frontend: alles auch ohne Cards über Services/todo-Entities/Sensoren/Events.

## 8. Gamification (FNV 1:1) — Schicht nach GTD (Design später im Detail)
Hooks: XP bei `complete` (auch überfällig; on-time +25 %; Karma ±10 %), Quest-Rewards auto
(Schritt-XP + 25/Schritt + 25 % on-time; Caps = XP/10), SPECIAL (7) → 13 Skills (FNV-Formel,
Tag!-Skills via G.O.A.T.), 88 Perks alle 2 Level, GECK-XP-Kurve, Level-Cap 30/50,
HP = 95 + 20×END + 5×Level, Karma, Caps-Shop. Profile je `person.*`.
Formeln/Daten: siehe Referenz-Implementierung `gamification.py`/`perks_data.py` auf
`vibe/dev-5adb24` (werden bei der Gamification-Phase neu aufgesetzt, nicht kopiert).

## 9. Persistenz, Versionierung, Migration
- Eine `Store` (`gamified_gtd`, `version: 1`), JSON-Schema siehe §4; Migration bei
  `version`-Bump; Repair-Routine beim Laden (z. B. Projekt↔Task-Verknüpfungen — Lesson v1:
  task_ids-Sync bugfix).
- Store-Writes debounced (`async_delay_save`), UI-Event sofort (Lesson v1).

## 10. Testing & CI
- Unit-Tests (pure Logik: Gamification, GOAT, Manager mit Mock-hass), Import-Smoke mit echtem
  `homeassistant`-Paket, Frontend-Marker-Tests (Cards parsen, keine statischen lit-Imports,
  Editor-Contract), `validate_integration.py` (services.yaml ↔ consts ↔ strings),
  `node --check` für www-JS. CI: 4 Jobs (wie v1).
- Workflow (aktuell mit User abgestimmt): ein Dev-Branch (`vibe/dev-5adb24`), PRs sofort
  „ready for review“, User testet im HA Integration Tester und merged selbst; Python-Änderungen
  brauchen vollen HA-Neustart (nicht nur Reload) — Doku-Hinweis.

## 11. Offene Fragen für morgen (mit Optionen + Empfehlung)
1. Entity-Mapping: A (todo-Entity pro Bucket + status-Attribut) / B (eine todo-Entity) / C (nur Sensoren+Services) — **Empfehlung A**
2. Storage: Store-JSON + Entity-Spiegel (empfohlen) vs. nur Entities
3. Multi-User: geteilt + assigned_to (empfohlen) vs. pro Person getrennt
4. Schreibpfade: Services + todo-Write-Through (empfohlen)
5. UI-Umfang: eigene Cards wie v1 vs. mehr HA-Built-ins
6. Review-Checkliste: welche Punkte berechnet vs. manuell (calendar manuell)
7. GTD-Status als Attribut vs. HA-todo-status mapping (needs_action/completed nur)

---

## 12. Detail-Checkliste fürs kleinteilige Durchgehen (JEDER Punkt wird einzeln entschieden)

### A. Prozess-Feinheiten / Edge Cases (GTD-Ebene)
- [ ] A1 Clarify: exakte Felder pro `decision` (next_action: contexts+due?; project: name/outcome; waiting_for: whom+follow_up_on; done/trash/reference/someday: was jeweils gesetzt wird)
- [ ] A2 2-Minuten-Regel: `done` sofort — Historie sichtbar? XP später ja
- [ ] A3 Delegation: `follow_up_on` — Reminder automatisch? was passiert am Nachfass-Tag (Status-Wechsel? nur Reminder)?
- [ ] A4 Repeat-Regeln: Syntax (daily/weekly/monthly/yearly/weekdays/custom-intervall?), Wann neue Instanz (beim complete), wie wird `due` verschoben, was bei offenem Repeat-Task?
- [ ] A5 `defer_until` (Tickler): wo wird es "versteckt" (nicht in next_action-Ansicht), Reminder trotzdem?
- [ ] A6 on_hold: Freigabe manuell oder automatisch (depends_on später)? hold_reason Pflicht?
- [ ] A7 Projekt: auto-complete wenn alle Schritte done? (v1: ja) oder nur manuell?
- [ ] A8 stalled: exakte Definition (aktiv + keine offene next_action), Anzeige/Markierung wo?
- [ ] A9 Weekly Review: Checkliste — jeder Punkt: berechnet aus welchen Feldern (7-Tage-Fenster?) oder manuell; Reihenfolge; Review-Fälligkeit (7 Tage); was passiert bei überfälliger Review (Karma später)
- [ ] A10 Reference: Felder (kind, url, file, tags, links zu projekt/task), Suche/Filter, Review-Punkt
- [ ] A11 Kontexte: Default-Liste, editierbar wo (Optionen), mehrere pro Item, Filter-Logik in Ansichten
- [ ] A12 Capture-Quellen: Service, todo-Entity, App — gleiche Logik?
- [ ] A13 `due` vs `defer_until` vs `follow_up_on`: Semantik-Grenzen, Reminder-Verhalten je Feld
- [ ] A14 Priorität/Energie/Zeit: Defaults (Optionen), Skalen (1–5), wo sichtbar (Engage-Ansicht)

### B. Datenmodell (feldweise)
- [ ] B1 Item: jedes Feld — Name, Typ, Default, Pflicht, Validierung, wo exponiert (Entity-Attribut? Sensor?)
- [ ] B2 Status-Enum + erlaubte Transitionen (Tabelle) + Event je Transition
- [ ] B3 Project: Felder + Invarianten (task_ids-Sync beidseitig! Lesson v1)
- [ ] B4 Review: Felder + Checklisten-Logik pro Punkt
- [ ] B5 IDs (uuid4?), Timestamps (ISO local, tz), created_at/updated_at — wer setzt updated_at (Lesson v1: _touch)
- [ ] B6 Profile (Gamification später): Felder grob

### C. Services (jeder einzeln: Schema, Selektoren, Validierung, Response, Events, Side Effects, Fehlerfälle)
- [ ] C1 capture  C2 clarify  C3 set_status/move  C4 update_item  C5 complete  C6 delegate  C7 remove
- [ ] C8 create_project  C9 update_project  C10 remove_project  C11 complete_project  C12 add_to_project?
- [ ] C13 start_review  C14 complete_review  C15 get_state
- [ ] C16 todo-Entity-Write-Through (create/update/delete item → interner Service-Aufruf; Lesson v1: ServiceCall(hass, …))
- [ ] C17 (später) Gamification-Services

### D. Entities
- [ ] D1 Welche Entities (todo pro Bucket vs. eine vs. Sensoren) — siehe §3
- [ ] D2 Attribute je Entity (todo_items-Dict + Metadaten; Lesson v1: HA exponiert todo_items NICHT selbst)
- [ ] D3 should_poll=False + Event-Listener MIT Event-Argument (Lesson v1!)
- [ ] D4 unique_id, device_info, Icons
- [ ] D5 Sensoren pro Person (Level später; GTD: quest log, review state…)

### E. Events (Katalog mit Payload-Schema)
- [ ] E1 data_updated (zentral)  E2 item_*  E3 project_*  E4 review_*  E5 reminder_*

### F. Benachrichtigungen
- [ ] F1 Scheduler: wann armen/neu armen (data_updated), Timer-Logik
- [ ] F2 due-Reminder (Offsets), F3 overdue_repeat, F4 follow_up_on-Reminder, F5 Tickler-Reminder
- [ ] F6 Zonen-"held"-Reminder (person betritt/verlässt Zone)
- [ ] F7 tägliche Summary (Zeit, Inhalt, notify vs persistent_notification)
- [ ] F8 notify-Mapping pro Person (Optionen)

### G. Storage
- [ ] G1 Store-Key/Version, Schema, Migration, Repair beim Laden (Lesson v1: task_ids-Sync)
- [ ] G2 Save-Strategie: Event sofort, Disk debounced (Lesson v1), Flush bei Shutdown

### H. Config Flow / Optionen
- [ ] H1 Setup-Schritte: Personen (multi), Kontexte (Default editierbar), Defaults (time/energy), notify-Services, Summary an/aus+Zeit, Level-Cap (Gamification später)
- [ ] H2 Validierung, H3 Options-Änderung live (reload?

### I. Frontend (Cards)
- [ ] I1 Card-Inventar + je Card: Layout, Config, GUI-Editor (Lesson v1: setConfig + config + config-changed mit VOLLER Config)
- [ ] I2 lit-Lade-Mechanik (dynamic import + vendored Fallback, Lesson v1), static path (plural), ?v= Cache-Bust bei jedem JS-Change (Lesson v1)
- [ ] I3 theme-aware CSS, Icon-Drop-in-Policy (nie FNV-Originale)
- [ ] I4 HA-Built-ins zusätzlich nutzbar (todo-Card, calendar)

### J. Multi-User
- [ ] J1 assigned_to-Semantik, "me"-Auflösung (user_id→person), unassigned = alle?
- [ ] J2 geteilte vs. pro-Person-Bereiche (Empfehlung: geteilt + assigned_to)
- [ ] J3 Review pro Person

### K. Sicherheit/Privacy
- [ ] K1 Storage private, keine externen Calls, Icon-Policy

### L. Testing/CI/Doku/Rollout
- [ ] L1 Unit/Smoke/Frontend-Marker/validate + CI-Jobs, L2 README/DESIGN/CONTRIBUTING/services.yaml-Strings, L3 HACS, Versionsschema, L4 Branch-/PR-Workflow (Dev-Branch, PR sofort ready, User merged nach Test; Python braucht HA-Neustart)

### N. Nutzungsfreundlichkeit / geringe Reibung (oberstes Prinzip, siehe DESIGN-v2 §0.0)
- [ ] N1 Capture: 1-Tap/1-Satz von überall (Service, todo-Entity, Card, Widget, Assist), nur Titel Pflicht, sofortiges Feedback
- [ ] N2 Clarify: Schritt-für-Schritt-Dialog, Defaults vorausgefüllt, keine Sammel-Formulare
- [ ] N3 Ansichten: ruhig/klar, Fokus-Ansicht („jetzt“), keine Überflutung
- [ ] N4 Review: geführte Checkliste
- [ ] N5 Benachrichtigungen: nie spammy, snooze/einfach ausblendbar
- [ ] N6 Gamification später: motivierend, nie zusätzliche Pflicht-Schritte
- [ ] N7 forgiving: Trash statt hart löschen, Undo wo möglich, konsistente Patterns
