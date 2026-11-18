# TECH v2 — technisches Umsetzungskonzept (GTD in HA + FNV-Gamification)

Basis: `DESIGN-v2.md` (GTD-Prozess + Entscheidungen). Alte Implementierung bleibt als
Referenz (Branch `vibe/dev-5adb24`, DESIGN.md) — dieser Stand ist ein FRESH DESIGN,
nicht die Übernahme des Alten. Gamification (FNV) ist eigener Abschnitt weiter unten.

## 1. HA-Bordmittel → GTD-Begriffe (was HA nativ kann)

| GTD-Begriff | HA-Bordmittel | Bemerkung |
|---|---|---|
| Inbox / Buckets als Status | `todo.*`-Entities + eigenes Status-Attribut | HA todo hat nur needs_action/completed; unser GTD-Status (inbox/next_action/waiting_for/on_hold/someday/reference) ist Zusatz-Attribut |
| Listen | eine `todo.*`-Entity pro Bucket (geteilte Listen) ODER eine Entity + Listen-Attribut | Entscheidung offen (§3) |
| Termine | externer Kalender (Google des Users); Item trägt `due`/`due_time` | kein HA-Kalender-Spiegel nötig (entschieden) |
| Kontexte | eigenes Attribut `contexts: [...]` + konfigurierbare Liste in den Optionen | freie Liste mit Defaults, mehrere pro Item (entschieden) |
| Personen/Zuordnung | `person.*`-Entities, Feld `assigned_to` | Multi-User über person-Entities |
| Reminder/Fälligkeit | eigene Scheduler-Logik (Timer auf due/due_time, overdue_repeat) + `notify` | HA hat keine Task-Reminder nativ |
| Ortsbasierte Reminder | `zone.*`-Entities + State-Change-Tracking (person in Zone) | wie Better ToDo |
| Tägliche Summary | eigene Logik (Timer) + notify / persistent_notification | |
| Speicherung | `Store` (JSON in .storage) als Single Source of Truth, Entities als schreibbarer Spiegel | oder direkt Entities — Entscheidung offen (§3) |
| Schreiben/Lesen | Services (`gamified_gtd.*`) + todo-Entity-Schreibzugriff (Companion-App-kompatibel) + Events für UI | Thin-Frontend-Prinzip |
| UI | eigene Lovelace-Cards (später), alles auch ohne Cards über HA-Built-ins | |
| Automationen | Events feuern (`gamified_gtd_*`), Nutzer kann eigene Automationen bauen | |

## 2. Domänenmodell (fachlich, aus DESIGN-v2)

**Item:** `id, title, notes, status (inbox|next_action|waiting_for|on_hold|someday_maybe|reference|done),
contexts: [..], project_id?, assigned_to?, due?, due_time?, defer_until? (Tickler),
waiting_for? (whom), follow_up_on?, repeat? (Regel), depends_on?/hold_reason? (on hold),
time_estimate?, energy?, priority?, tags: [], source?, created_at, updated_at, completed_at?`

**Project:** `id, name, desired_outcome, status (active|done), due?, task_ids: [],
created_at, updated_at, completed_at?, stalled (berechnet: aktiv ohne offene next_action)`

**Review:** `id, person, started_at, completed_at?, checklist: {...}` (Checkliste aus DESIGN-v2)

**Profile (Gamification später):** je person — SPECIAL, Skills, Perks, XP/Level, Karma, Caps.

## 3. Offene technische Entscheidungen (morgen durchgehen)

1. **Entity-Mapping:** (a) geteilte `todo.gtd_*`-Entities pro Bucket (Companion-App-kompatibel,
   Better-ToDo-Stil, alter Ansatz) — GTD-Status als Attribut; (b) eine `todo.*`-Entity, Bucket
   als Attribut; (c) keine todo-Entities, nur Sensoren + Services (Companion-App außen vor).
   Hinweis: Buckets = Status des Items (entschieden) — spricht für (b)/(c); todo-Kompatibilität
   spricht für (a).
2. **Storage:** eine `Store`-JSON (Single Source of Truth, Entities als Spiegel) vs. direkt
   auf HA-Entities/Storage. Spiegel-Ansatz hält Companion-App kompatibel.
3. **Multi-User:** geteilte Listen + `assigned_to` (alter Ansatz) vs. pro Person getrennte Bereiche.
4. **Schreibpfade:** nur Services vs. Services + todo-Entity-Create/Update/Delete (Write-Through).
5. **UI-Layer:** eigene Cards (10+ Typen wie bisher) vs. so weit wie möglich HA-Built-ins
   (todo-Card, Kalender-Card) + wenige eigene Cards.

## 4. Service-Skizze (prozessnah, tech-neutral benannt)

`capture` (→ inbox, typ-los, nur Titel Pflicht) · `clarify` (decision: next_action|project|
waiting_for|someday|reference|trash|done + Felder: contexts, project, waiting_for, follow_up_on,
due, defer_until) · `set_status`/`move` (Bucket wechseln) · `complete` · `delegate`
(→ waiting_for + whom + Nachfass-Datum) · `update` (alle Felder) · `remove` ·
`create_project`/`update_project`/`remove_project`/`complete_project` (auto: stalled-Erkennung) ·
`start_review`/`complete_review` · Benachrichtigungen automatisch (due-Reminder, overdue, Zone,
Summary) · Events für UI.

## 5. Benachrichtigungs-Schicht

Eigener Scheduler (wie bisher): due-Reminder (mehrere Vorlaufzeiten), overdue_repeat,
ortsbasierte „held“-Reminder über zone/person-State, tägliche Summary (konfigurierbare Zeit),
optional persistent_notification. Alles über `notify.*` der jeweiligen Person.

## 6. UI (später im Detail)

Eigene theme-aware Lovelace-Cards: Inbox/Capture, Listen-Ansicht (nach Bucket/Kontext filterbar),
Projekt/Quest-Ansicht (Pip-Boy-Stil: Liste links, Detail rechts), Reference, Review.
Alles funktioniert auch ohne Cards über Services + todo-Entities + Sensoren.

## 7. Gamification (FNV 1:1) — Hooks (Design später)

XP beim `complete` (auch überfällig; on-time +25 %, Karma ±10 %), Quest-Rewards auto
(Schritt-XP + Bonus, Caps = XP/10), Level/Skill/Perk/SPECIAL je person, G.O.A.T. statt Tag-Skills,
Reward-Shop gegen Caps, Events. FNV-Original-Icons nie ausliefern (Drop-in-Ordner + Fallbacks).

## 8. Nächste Schritte (morgen)

1. §3-Entscheidungen treffen (Entity-Mapping, Storage, Multi-User, Schreibpfade, UI-Umfang)
2. Domänenmodell finalisieren (Felder, Status-Machine: inbox → … → done; on_hold)
3. Service-Liste finalisieren + Events
4. Dann: Branch anlegen, Skeleton, erste Services + Entities, Tests
