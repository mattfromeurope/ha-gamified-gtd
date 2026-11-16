# ha-gamified-gtd

A gamified attempt on GTD in Home Assistant.

Combines David Allen's **Getting Things Done** method with gamification taken **1:1 from
Fallout: New Vegas**: S.P.E.C.I.A.L. attributes, 13 derived skills, XP and levels (engine XP
curve, level cap 50), a selectable perk every 2 levels, karma and caps — with GTD projects as
quests and the weekly review as a recurring quest.

The full, agreed design lives in [DESIGN.md](DESIGN.md).

## Status

Backend (config flow, storage, `todo` entities, sensors, services, events) and the five
Pip-Boy-style custom cards are in place.

## Custom cards

Auto-registered by the integration (hard-refresh the browser once after an update):

| Card type | Config |
|---|---|
| `custom:gamified-gtd-stats` | `person: person.alex` (+ `title`) — level/XP bar, HP, karma, caps, SPECIAL, skills, perks; dialogs for skill points and perk choice |
| `custom:gamified-gtd-quests` | `title` — quest log with progress, new/complete quest |
| `custom:gamified-gtd-tasks` | `list` (`inbox`/`next_actions`/`waiting_for`/`someday_maybe`/`all`), `assigned` (`all`/`me`/person), `show_completed` — incl. Clarify dialog for the inbox |
| `custom:gamified-gtd-review` | `person` — auto-checked weekly review checklist |
| `custom:gamified-gtd-rewards` | `person` — caps reward shop |

All card actions only call the `gamified_gtd.*` services / read sensors — everything works
without the cards via HA built-ins (todo card, developer tools, automations).

### Icons

The original FNV icons are copyrighted and **not shipped**. Drop your own files into
`custom_components/gamified_gtd/www/gamified_gtd_icons/<kind>/<id>.png` (`special`, `skill`,
`perk`, `quest`) — see the README in that folder. The cards fall back to text glyphs.

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

`gamified_gtd.add_to_inbox`, `clarify`, `complete_task`, `update_task`, `skip_task`,
`remove_task`, `create_project`, `add_to_project`, `complete_project`,
`allocate_skill_points`, `choose_perk`, `start_review`, `complete_review`, `redeem_reward`,
`get_state` — see `custom_components/gamified_gtd/services.yaml`.

## Events

`gamified_gtd_task_completed`, `gamified_gtd_level_up`, `gamified_gtd_perk_available`,
`gamified_gtd_perk_chosen`, `gamified_gtd_quest_completed`, `gamified_gtd_review_completed`,
`gamified_gtd_reward_redeemed`.
