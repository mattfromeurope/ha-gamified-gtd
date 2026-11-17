# ha-gamified-gtd

A gamified attempt on GTD in Home Assistant.

Combines David Allen's **Getting Things Done** method with gamification taken **1:1 from
Fallout: New Vegas**: S.P.E.C.I.A.L. attributes, 13 derived skills, XP and levels (engine XP
curve, level cap 50), a selectable perk every 2 levels, karma and caps — with GTD projects as
quests and the weekly review as a recurring quest.

The full, agreed design lives in [DESIGN.md](DESIGN.md).

## Status

Backend (config flow, storage, `todo` entities, sensors, services, events) and the ten
custom cards are in place.

## Custom cards

Auto-registered by the integration (hard-refresh the browser once after an update).
The cards are **theme-aware**: all colors come from the selected HA theme (card
background, text, dividers, primary color), so they match the built-in cards; the FNV
content (labels, drop-in icons) stays. The profile cards follow the Pip-Boy 3000 layout
from the game (display only, no Add/Edit/Delete buttons); the interactive character
screen is the Level-Up card:

| Card type | Config |
|---|---|
| `custom:gamified-gtd-stats` | `person` (+ `title`) — Pip-Boy **top bar**: HP, LEVEL + XP bar, CAPS, plus the karma row |
| `custom:gamified-gtd-special` | `person` — the 7 S.P.E.C.I.A.L. attributes with bars, like the STATS page |
| `custom:gamified-gtd-skills` | `person` — the 13 skills with bars; Tag! skills carry a `TAG!` badge |
| `custom:gamified-gtd-perks` | `person` — **only the owned perks**, with name + description |
| `custom:gamified-gtd-levelup` | `person` — allocate skill points / choose the pending perk (the level-up dialogs) |
| `custom:gamified-gtd-goat` | `person` — the **G.O.A.T.** (Vault 101 aptitude test): 10 questions with slide images, result sets the 3 Tag! skills — see below |
| `custom:gamified-gtd-quests` | `title` — quest log with progress, new/complete quest |
| `custom:gamified-gtd-tasks` | `list` (`inbox`/`next_actions`/`waiting_for`/`someday_maybe`/`all`), `assigned` (`all`/`me`/person), `show_completed` — full task form (title, notes, list, project, assigned, due date+time, priority, time estimate, energy, context, tags, reminders, overdue repeat, location condition), per-row **move-to-list** select, Clarify dialog for the inbox |
| `custom:gamified-gtd-review` | `person` — auto-checked weekly review checklist |
| `custom:gamified-gtd-rewards` | `person` — caps reward shop |

### Character creation: SPECIAL + G.O.A.T.

- In the options flow (**Configure → S.P.E.C.I.A.L.**) each attribute starts at **5** and
  you freely distribute **5 more points** (raise or lower, 1–10 each; the total must be
  exactly 40) — like character creation in FNV.
- Instead of picking Tag! skills manually, take the **G.O.A.T.**: add the
  `custom:gamified-gtd-goat` card to a dashboard once at setup, answer the 10 questions
  and the result (3 Tag! skills + the vault "job") is applied via
  `gamified_gtd.submit_goat` and stored on the profile (`sensor.<name>_level` attribute
  `goat`). The slide images from Fallout 3 are **not shipped** (copyright) — drop them
  into `www/gamified_gtd_icons/goat/slide_<n>.png` (links are in the questionnaire, see
  DESIGN.md); without images the card shows a text fallback.
- Tasks can be moved between the four GTD lists at any time (`gamified_gtd.move_task`)
  and assigned to a quest in the task form (`project_id`) or via `add_to_project`.

All card actions only call the `gamified_gtd.*` services / read sensors — everything works
without the cards via HA built-ins (todo card, developer tools, automations).

### Cards not loading? ("Custom element not found")

The integration serves `www/` under `/gamified_gtd_static/` and adds
`/gamified_gtd_static/gamified-gtd-cards.js?v=<version>` to the frontend's extra module
URLs, which HA's `index.html` imports on every page load. If a card shows
"Custom element not found":

1. Update to the current version, **restart Home Assistant**, then **hard-refresh the
   browser tab** (Ctrl/Cmd+Shift+R). The extra-module list is baked into the served
   index page, and the JS itself is cached for a month (the `?v=` parameter changes with
   every release, so updates are picked up automatically).
2. In the browser DevTools, check the console for `Failed to load extra module ...` and
   the Network tab for `/gamified_gtd_static/gamified-gtd-cards.js` — it must return 200
   with a JavaScript content type. A 404 means the static path was not registered (check
   the HA log for `Could not register static path for card assets`).
3. No CDN or extra Lovelace resource is needed: the card module loads `lit` via a dynamic
   import, falling back to the vendored `gamified-gtd-lit.js` bundle, so it works on HA
   versions both with and without a `"lit"` import map.

### Icons

The original FNV icons are copyrighted and **not shipped**. Drop your own files into
`custom_components/gamified_gtd/www/gamified_gtd_icons/<kind>/<id>.png` (`special`, `skill`,
`perk`, `quest`, `goat`) — see the README in that folder. The cards fall back to text glyphs.

## Installation

1. Install via HACS (or copy `custom_components/gamified_gtd/` into your `config/custom_components/`).
2. Restart Home Assistant.
3. Add the integration: *Settings → Devices & Services → Add Integration → Gamified GTD*.
4. Select the persons and configure SPECIAL / Tag! skills per person in the options.

## Entities

- `todo.gtd_inbox`, `todo.gtd_next_actions`, `todo.gtd_waiting_for`, `todo.gtd_someday_maybe`
  (shared lists; assignment via the `assigned_to` attribute)
- Per person: `sensor.<name>_level`, `sensor.<name>_hp`, `sensor.<name>_karma`,
  `sensor.<name>_caps`, `sensor.<name>_special`, `sensor.<name>_skills`, `sensor.<name>_perks`
- `sensor.gtd_quest_log`

## Services

`gamified_gtd.add_to_inbox`, `clarify`, `complete_task`, `update_task`, `move_task`,
`skip_task`, `remove_task`, `create_project`, `add_to_project`, `complete_project`,
`allocate_skill_points`, `choose_perk`, `start_review`, `complete_review`, `redeem_reward`,
`submit_goat`, `get_state` — see `custom_components/gamified_gtd/services.yaml`.
`update_task` also accepts `list` (move) and `project_id` (assign to quest).

## Notifications

Configured in the integration options (per person: notify service, e.g. `notify.mobile_app_*`):

- **Per-task reminders** (`reminders: [60, 1440]` = 1 h / 1 day before due; tasks with only a
  date use 09:00 as reference time) — fields `reminders`, `due_time`, `location`,
  `overdue_repeat` on `add_to_inbox` / `update_task`
- **Location-based reminders** (`location: {zone: zone.home, mode: inside}`): delivered
  immediately if the condition matches, otherwise **held** until the person enters/leaves
  the zone; dropped when the task is completed or the due changes. Persons without location
  tracking count as matching, so nothing is swallowed
- **Repeat while overdue** (`overdue_repeat: 15` = every 15 min until completed)
- **Daily summary** per person at a configurable time (due/overdue always included, plus
  tasks due within 7 days; no message when empty); optionally also in the HA notification
  center (`persistent_notification`)

Events: `gamified_gtd_reminder_sent`, `gamified_gtd_summary_sent` — build your own
automations on top if you prefer.

## Voice assistants / LLM agents

The integration registers a tool set for conversation agents (Assist → *Control Home
Assistant* → tick **Gamified GTD** next to your agent). Tools: `list_tasks` (filters +
ready-to-read `speech` lines), `add_task`, `complete_task`, `clarify_task`, `get_state`,
`allocate_skill_points`, `choose_perk`, `create_project`, `complete_project`, `review`,
`redeem_reward` — all calling the same logic as the services/cards.

## Events

`gamified_gtd_task_completed`, `gamified_gtd_level_up`, `gamified_gtd_perk_available`,
`gamified_gtd_perk_chosen`, `gamified_gtd_quest_completed`, `gamified_gtd_review_completed`,
`gamified_gtd_reward_redeemed`, `gamified_gtd_goat_completed`.
