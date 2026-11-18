# Gamified GTD — Design Document

A Home Assistant integration that combines David Allen's **Getting Things Done (GTD)** method
with gamification mechanics taken **1:1 from Fallout: New Vegas** (S.P.E.C.I.A.L., Skills,
Perks every 2 levels, XP/level curve, Karma, Caps).

Inspired by the existing integration [Better ToDo](https://github.com/Timmes123/ha-better-todo)
(shared `todo` entities with an `assigned_to` attribute, own storage as single source of truth,
services + events, custom Lovelace card shipped with the integration — the card comes later here).

## Decisions (agreed)

- **Language/branding:** English UI, FNV elements used directly (Pip-Boy style planned for the card).
- **Gamification scope:** full FNV system — S.P.E.C.I.A.L., derived Skills, Perks, XP/Levels, Karma, Caps.
- **Build order:** backend + entities first, custom Lovelace card later.
- **Multi-user:** yes, from the start, via HA `person` entities; one profile per person.

---

## 1. GTD core

### Lists

| List | Purpose |
|---|---|
| `inbox` | Capture everything without thinking |
| `next_actions` | Concrete next actions, optionally with a **context** (`@home`, `@computer`, `@phone`, `@errands`, `@anywhere`, freely extendable) |
| `waiting_for` | Delegated items / waiting on others (not counted as open quest steps) |
| `someday_maybe` | Someday/maybe |
| `reference` | Reference material (not actionable, kept for later) |

`todo` entities (one per list, shared across users) mirror the own storage; assignment happens
via the `assigned_to` attribute (Better ToDo approach). The integration's own storage is the
single source of truth.

### Task fields

`id, title, notes, list, status, context, project_id, priority (1–5, 1 = highest),
due (date, optional), time_estimate (minutes, optional), energy (1–5, optional),
assigned_to (person entity id or null), tags, created_at, completed_at`

`time_estimate` and `energy` are set per action by the user; if not given, a **global default**
from the options applies (once, not per task).

### Clarify

`clarify` processes an inbox item into: next action (with context) / project (with desired outcome) /
waiting-for (with `waiting_for` whom) / someday / reference (not actionable, keep) / trash (delete) —
or marks it done directly (2-minute rule). Tasks also carry `defer_until` (GTD tickler date, separate
from `due`) and `updated_at`, which drives the computed weekly-review checklist.

### Projects = Quests

A GTD project (an outcome needing more than one action step) is a **quest**:

- `projects[]`: `id, name, desired_outcome, task_ids, status, due (optional), created_at, completed_at`
- Tasks carry a `project_id`; progress = done steps / all steps (`x/y` in the quest log)
- A quest inherits the **earliest due date** of its open steps; an optional quest deadline grants
  **+25 % quest XP** when finished in time
- **Rewards are calculated automatically, never configured per quest:**
  quest XP = sum of the XP of its steps + `25 XP × number of steps`; quest Caps derive from the
  quest XP via the global 1 Cap / 10 XP rule
- Quests can be reopened (new step with the same `project_id`) or completed manually without steps
- Completing a quest fires `quest_completed`

### Weekly Review

- Recurring quest; interval configurable (default 7 days); `days_since_review` attribute
- The **checklist is checked automatically** (e.g. "inbox empty" = no open inbox tasks;
  "next actions current" = no untouched next action older than 7 days, …)
- `start_review` / `complete_review`; completion pays an **automatically calculated bonus**
  (100 XP base + streak multiplier for consecutive on-time reviews) and fires `review_completed`
- Review overdue by more than 7 days: **Karma −1 per week**

---

## 2. FNV gamification system (1:1)

### S.P.E.C.I.A.L.

7 attributes (Strength, Perception, Endurance, Charisma, Intelligence, Agility, Luck), each 1–10.
Set **once per profile at setup** in the options flow, like FNV character creation: every attribute
starts at **5**, **5 points are freely distributed** (values may be raised AND lowered, 1–10 each,
total must be exactly **40** — enforced by the config-flow validator). Afterwards only +1 via perks
(e.g. *Intense Training*, up to 10×). Tasks never raise SPECIAL directly — they only grant XP.

**Tag! skills via the G.O.A.T.:** instead of picking the 3 Tag! skills manually, the user takes the
*Generalized Occupational Aptitude Test* (Fallout 3, Vault 101) once at setup via the
`custom:gamified-gtd-goat` card: 10 questions (slide image per question), each answer scores 1 point
per skill label (question 6 answer 2 scores two skills; question 10 — all answers "The Overseer." —
scores nothing). The **top 3 skills become the Tag! skills** (ties alphabetical, per the wiki), the
top skill determines the vault "job" shown as flavor text. Submitted via `gamified_gtd.submit_goat`
(answers = 10 indices), stored on the profile (`goat` key, exposed as `goat` attribute on
`sensor.<name>_level`), event `gamified_gtd_goat_completed`. Full questionnaire + slide image links
(Fallout Wiki `FO3_GOAT_slide_<n>.jpg`, drop-in folder `gamified_gtd_icons/goat/`) in
`custom_components/gamified_gtd/goat_data.py`.

### Skills (13, exactly as in FNV)

Barter, Energy Weapons, Explosives, Guns, Lockpick, Medicine, Melee Weapons, Repair, Science,
Sneak, Speech, Survival, Unarmed.

- Formula 1:1: `skill = 2 + 2 × governing SPECIAL + ceil(Luck / 2) + allocated skill points
  (+15 per Tag! skill)`, max 100
- Governing attributes: STR→Melee Weapons; PER→Energy Weapons, Explosives, Lockpick;
  END→Survival, Unarmed; CHA→Barter, Speech; INT→Medicine, Repair, Science; AGI→Guns, Sneak;
  LCK→+ceil(L/2) on all skills
- 3 **Tag!** skills at profile creation: +15 each
- Skills only increase via **skill points at level-up** — leveling is independent of the actual
  tasks (except for the XP they grant)

### XP and levels

- XP to reach level *n* (GECK/FNV engine formula, cumulative):
  `XP(n) = (n − 1) × ((n − 2)/2 × 150 + 200)` — level 2 = 200, level 3 = 550, level 4 = 1050,
  level 50 = 186,200 XP total
- **Level cap 50** (30 configurable, "base game")
- Derived stat for flavor: `HP = 95 + 20 × END + 5 × level`

### Level-up

- **Skill points per level-up = 10 + 0.5 × INT** (odd INT alternates, remainder is carried over)
- **Every 2nd level (from level 2): one perk selectable**, with FNV requirements
  (minimum level, SPECIAL min/max, skill, perk prerequisite, any-of conditions).
  All **88 regular FNV perks** are ported in `perks_data.py` (levels 2–28, ranks incl.
  10× Intense Training / 3× Swift Learner / 3× Demolition Expert / 2× others);
  requirements are enforced by `choose_perk`. Effects are translated into integration
  mechanics where they map (XP multiplier, caps multiplier, skill points per level,
  +1 SPECIAL, HP bonus, instant level, extra Tag! skill); combat/dialogue perks stay
  selectable 1:1 as flavor entries
- Level-up fires `level_up`; an available perk choice fires `perk_available`

### XP from tasks

`XP = base (10) × priority factor × effort factor`, rounded:

- Priority factor: P1 ×3, P2 ×2, P3 ×1.5, P4 ×1, P5 ×0.5
- Effort factor, time: ≤ 2 min ×0.5 (2-minute rule), ≤ 15 min ×1, ≤ 60 min ×1.5, > 60 min ×2
- Effort factor, energy: 1 ×0.8, 2 ×0.9, 3 ×1, 4 ×1.2, 5 ×1.5
- **On-time bonus: +25 % XP** when completed before the due date
- **Karma modifier: ±10 % on XP**, applied automatically (`1 + karma/100 × 0.1`)
- Perk effects (e.g. *Swift Learner* +10 % XP) stack multiplicatively
- Exact numbers are tuned later; the mechanism is fixed

### Caps

- **1 Cap per 10 XP**, but **only when the task is not overdue** — every completed action grants
  XP, overdue actions just don't yield Caps from it
- Quest and review rewards pay Caps via the same rule

### Karma

- Range **−100 … +100**; karma titles inspired by FNV (in the game they are level- and
  karma-dependent; here they are scaled to the −100…+100 range: Saint … Fiend)
- +1 when completed before due; −1 when completed > 7 days overdue; −1 per overdue review week
- Effect: automatic ±10 % XP modifier (see above); title + events for automations

### Rewards shop (Caps)

- Configurable reward list (name, description, cap cost) in the options
- A **small set of default rewards** ships predefined but can be edited/deleted; custom rewards
  can be added
- `redeem_reward` checks the balance, deducts caps, fires `reward_redeemed`; the actual
  "payout" (notification, automation, …) is wired by the user via the event

---

## 3. Multi-user

- One profile per configured HA `person` entity (config flow: person selection; per-person
  SPECIAL allocation + 3 Tag! skills)
- Task assigned → XP goes to the assigned person
- Task unassigned → XP goes to the person triggering the completion (user context of the service
  call); if not determinable, to a configured default profile

## 4. Entities

**Todo lists:** `todo.gtd_inbox`, `todo.gtd_next_actions`, `todo.gtd_waiting_for`,
`todo.gtd_someday_maybe` (standard `todo`, Companion-App compatible; rich fields as attributes).

**Per person** (`<name>` = person name):

| Entity | State | Key attributes |
|---|---|---|
| `sensor.<name>_level` | level | `xp`, `xp_to_next`, `skill_points_available`, `perk_choice_pending`, `days_since_review` |
| `sensor.<name>_hp` | HP | — |
| `sensor.<name>_karma` | karma title | `karma` value |
| `sensor.<name>_caps` | caps | — |
| `sensor.<name>_special` | — | 7 SPECIAL values |
| `sensor.<name>_skills` | — | 13 skills |
| `sensor.<name>_perks` | count | chosen perks |
| `sensor.gtd_quest_log` | — | active/completed quests with `x/y` progress |

## 5. Services (`gamified_gtd.*`)

| Service | Purpose |
|---|---|
| `add_to_inbox` | quick capture (title + optional fields incl. `time_estimate`/`energy`) |
| `clarify` | process inbox item → next action (with context) / project / waiting-for / someday / done |
| `complete_task` | XP (always), Caps (only if not overdue), Karma, level-up check, events |
| `update_task` / `move_task` / `skip_task` / `remove_task` | editing; `move_task` moves a task between the GTD lists (keeps project + metadata), `update_task` also accepts `list` and `project_id` (assign to quest, keeps `project.task_ids` in sync) |
| `create_project` / `add_to_project` / `complete_project` | quest management |
| `allocate_skill_points` | distribute skill points from level-ups (person + skill + points) |
| `choose_perk` | pick a perk every 2 levels; requirements (level/SPECIAL/skill) enforced |
| `start_review` / `complete_review` | weekly review |
| `redeem_reward` | spend caps on a reward |
| `add_reward` / `update_reward` / `remove_reward` | manage the shop (custom rewards editable/deletable; id generated on add) |
| `update_project` / `remove_project` | rename quest / change outcome+deadline / delete quest (tasks are kept and detached) |
| `submit_goat` | G.O.A.T. answers (10 indices) → sets the 3 Tag! skills; returns tags + job |
| `reset_profile` | reset ONLY the FNV character of a person (level/XP/SPECIAL/skills/perks/caps/GOAT) so character creation can be redone — tasks, quests, reviews, rewards, karma untouched; fires `profile_reset`, re-arms the pending hint |
| `get_state` | full profile as response (automations, voice, LLM) |

Character creation is "pending" for a profile until it has a G.O.A.T. result or Tag! skills
(`character_creation_pending` attribute on the level sensor). Pending profiles get a one-time
persistent notification once at HA start, and reset_profile sends it immediately to the
triggering user (resolved via the service-call context user_id → person entity; persistent
notifications are global in HA, so the message text names the user). The notification links to
`/config/integrations/integration/gamified_gtd`; its options flow runs S.P.E.C.I.A.L. first and
the G.O.A.T. directly after (one question per form: question text + slide image in the
markdown description, 4 answers as radio buttons via SelectSelectorMode.LIST), then a
result step (Tag! skills + vault job) that optionally continues to the manual Tag! picker —
HA has
no login event and no URL that starts a flow directly, so
"next login" is approximated by the HA-start notification and "click" by one click on
"Configure" on the integration page.

## 6. Events

`task_completed`, `level_up`, `perk_available`, `perk_chosen`, `quest_completed`,
`review_completed`, `reward_redeemed`, `goat_completed`, `profile_reset` — each with the
relevant data.

## 7. Storage & options

- Own versioned JSON via HA's Store API (`.storage/gamified_gtd`), included in HA backups
- Contains: profiles (SPECIAL, skills, perks, XP, level, karma, caps, tags), tasks, projects/quests,
  reviews, rewards, options
- Options: persons, level cap (30/50), default `time_estimate` / `energy`, default contexts,
  reward list, XP base

## 8. Frontend: custom cards (later stage)

**Principle:** cards are thin frontends. They read sensors/store and only call the existing
services — no own state, no parallel logic. Everything a card can do is also possible with
HA built-ins (todo list card, developer tools, automations); the card is just the convenient
variant. Services themselves cannot open dialogs/popups in HA — dialogs are opened by the card
(or via browser_mod in automations).

Ten separate card types (auto-registered by the integration, YAML-configurable). **Styling is
theme-aware**: all colors use HA theme variables (`--primary-text-color`, `--divider-color`,
`--primary-color`, card background), so the cards match the built-in cards and follow the active
theme — the Pip-Boy look is only in the layout/content (top bar, STATS-page rows, drop-in icons).
The profile cards mirror the Pip-Boy 3000 pages and are **display-only** (no Add/Edit/Delete
buttons); interactivity (skill points, perk choice) lives in the dedicated Level-Up card.

| Card type | Shows / does | YAML options | Built-in equivalent |
|---|---|---|---|
| `gamified-gtd-stats` | Pip-Boy **top bar**: HP bar, LEVEL + XP bar, CAPS; karma row below | `person`, `title` | `sensor.<name>_level/hp/karma/caps` |
| `gamified-gtd-special` | The 7 S.P.E.C.I.A.L. attributes (icon, bar, value) like the STATS page | `person`, `title` | `sensor.<name>_special` |
| `gamified-gtd-skills` | The 13 skills with bars; Tag! skills get a `TAG!` badge | `person`, `title` | `sensor.<name>_skills` (+ `tagged_skills` attribute) |
| `gamified-gtd-perks` | **Only owned perks**, name + description each | `person`, `title` | `sensor.<name>_perks` (`perk_details` attribute) |
| `gamified-gtd-levelup` | Skill points available + **allocate** dialog; pending perk choice + **choose** dialog (with requirement display, Intense Training/Tag! selectors) | `person`, `title` | `allocate_skill_points` / `choose_perk` / `get_state` |
| `gamified-gtd-goat` | The **G.O.A.T.**: intro → 10 questions (slide image `goat/slide_<n>.png` if dropped in, else text fallback) → result (vault job + 3 Tag! skills) → `submit_goat`; shows stored result + retake | `person`, `title` | `submit_goat` service + `goat` attribute on the level sensor + `goat_completed` event |
| `gamified-gtd-quests` | Active quests with `x/y` progress, desired outcome, deadline; completed quests | `title` | `sensor.gtd_quest_log` + project services + `quest_completed` event |
| `gamified-gtd-tasks` | One GTD list or all; **full task form** (title, notes, list, project, assigned, due date+time, priority, time estimate, energy, context, tags, reminders, overdue repeat, location zone+mode — the Better ToDo option set plus GTD/gamification fields); per-row **move-to-list** select; complete checkbox; **inbox mode with Clarify dialog** | `list`, `assigned` (`all` / `me` / person), `show_completed`, `title` | HA todo list card on `todo.gtd_*` (completing there awards XP/Caps/Karma via the entity) + `gamified_gtd.*` services incl. `move_task` |
| `gamified-gtd-review` | Review due?, auto-checked checklist, start/complete buttons, streak | `person` | `start_review` / `complete_review`, `days_since_review` attribute, `review_completed` event |
| `gamified-gtd-rewards` | Reward shop with cap costs, balance, redeem button | `person` | `sensor.<name>_caps` + `redeem_reward` + `reward_redeemed` event |

Note: HA does **not** expose todo items in a todo entity's state attributes (the built-in
frontend uses websocket for that) — the integration therefore adds `todo_items` explicitly to
the `todo.gtd_*` attributes, which is what the tasks card reads.

### Clarify dialog (inside `gamified-gtd-tasks`, inbox mode)

Task title/notes on top, decision as segmented control — *Next Action* (context chips below) /
*Project* (pick existing or create new with desired outcome) / *Waiting for* / *Someday* /
*Done now (2-minute rule)* — plus optional priority, due, time estimate, energy, person.
One click calls `gamified_gtd.clarify` and closes the dialog.

Example YAML:

```yaml
type: custom:gamified-gtd-stats
person: person.alex
```
```yaml
type: custom:gamified-gtd-tasks
list: next_actions
assigned: me
```

## 9. Roadmap

1. Backend + entities + services + events (this stage)
2. Full 88-perk data set port
3. Custom Pip-Boy-style Lovelace card (auto-registered)
4. Reminders/notifications (done — `notify.py`: due reminders, location-held reminders, repeat-while-overdue, daily summary, HA notification center); LLM/voice tools (done — `llm_api.py`: list_tasks/add_task/complete_task/clarify_task/get_state/allocate_skill_points/choose_perk/create_project/complete_project/review/redeem_reward via `homeassistant.helpers.llm`)
