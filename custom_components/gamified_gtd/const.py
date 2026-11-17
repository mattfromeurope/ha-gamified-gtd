"""Constants for the Gamified GTD integration.

Groups: storage, GTD lists, config/option keys + defaults, task fields, service names,
event names, notification options, review settings.
"""

from __future__ import annotations

# Integration domain — also used as service domain and storage key prefix.
DOMAIN = "gamified_gtd"

# Storage: one versioned JSON file in .storage (single source of truth, HA-backed-up).
STORAGE_KEY = DOMAIN
STORAGE_VERSION = 1
# Debounce for the debounced store write (seconds) — see GTDManager._save. The UI
# refresh event is NOT delayed by this; only the disk write is.
STORAGE_WRITE_DELAY = 1.0

# ---------------------------------------------------------------------------
# GTD lists
# ---------------------------------------------------------------------------
# The four GTD lists; each maps to one shared todo entity (todo.gtd_<list>).
LIST_INBOX = "inbox"
LIST_NEXT_ACTIONS = "next_actions"
LIST_WAITING_FOR = "waiting_for"
LIST_SOMEDAY = "someday_maybe"

# list key -> card/entity display name.
TODO_LISTS = {
    LIST_INBOX: "GTD Inbox",
    LIST_NEXT_ACTIONS: "GTD Next Actions",
    LIST_WAITING_FOR: "GTD Waiting For",
    LIST_SOMEDAY: "GTD Someday/Maybe",
}

# Task lifecycle states (kept separate from HA's TodoItemStatus on purpose).
TASK_OPEN = "open"
TASK_DONE = "done"

# Project (quest) states.
PROJECT_ACTIVE = "active"
PROJECT_DONE = "done"

# ---------------------------------------------------------------------------
# Config / options keys
# ---------------------------------------------------------------------------
CONF_PERSONS = "persons"  # list of person.* entity ids, one profile each
CONF_LEVEL_CAP = "level_cap"  # 30 = "base game", 50 = all DLCs (FNV)
CONF_DEFAULT_TIME_ESTIMATE = "default_time_estimate"  # fallback minutes per action
CONF_DEFAULT_ENERGY = "default_energy"  # fallback energy 1-5 per action
CONF_DEFAULT_XP_BASE = "default_xp_base"  # XP base value for the task formula
CONF_CONTEXTS = "contexts"  # default @contexts for filtering
CONF_REWARDS = "rewards"  # caps reward shop (None = use stored defaults)
CONF_DEFAULT_PROFILE = "default_profile"  # fallback person for unassigned tasks

DEFAULT_LEVEL_CAP = 50
DEFAULT_TIME_ESTIMATE = 15
DEFAULT_ENERGY = 3
DEFAULT_XP_BASE = 10
DEFAULT_CONTEXTS = ["@home", "@computer", "@phone", "@errands", "@anywhere"]

# Predefined rewards; editable/deletable in the options, custom ones can be added.
DEFAULT_REWARDS = [
    {"id": "coffee_break", "name": "Coffee break", "description": "Take a real coffee break.", "cost": 50},
    {"id": "gaming_30min", "name": "30 min gaming", "description": "Half an hour of guilt-free gaming.", "cost": 100},
    {"id": "episode", "name": "One episode", "description": "Watch one episode of your series.", "cost": 150},
]

# ---------------------------------------------------------------------------
# Task fields (service payload keys)
# ---------------------------------------------------------------------------
ATTR_TASK_ID = "task_id"
ATTR_TITLE = "title"
ATTR_NOTES = "notes"
ATTR_LIST = "list"
ATTR_CONTEXT = "context"
ATTR_PROJECT_ID = "project_id"
ATTR_PRIORITY = "priority"
ATTR_DUE = "due"
ATTR_TIME_ESTIMATE = "time_estimate"
ATTR_ENERGY = "energy"
ATTR_ASSIGNED_TO = "assigned_to"
ATTR_TAGS = "tags"

# ---------------------------------------------------------------------------
# Services (domain is always DOMAIN)
# ---------------------------------------------------------------------------
SERVICE_ADD_TO_INBOX = "add_to_inbox"
SERVICE_CLARIFY = "clarify"
SERVICE_COMPLETE_TASK = "complete_task"
SERVICE_UPDATE_TASK = "update_task"
SERVICE_SKIP_TASK = "skip_task"
SERVICE_REMOVE_TASK = "remove_task"
SERVICE_CREATE_PROJECT = "create_project"
SERVICE_ADD_TO_PROJECT = "add_to_project"
SERVICE_COMPLETE_PROJECT = "complete_project"
SERVICE_ALLOCATE_SKILL_POINTS = "allocate_skill_points"
SERVICE_CHOOSE_PERK = "choose_perk"
SERVICE_START_REVIEW = "start_review"
SERVICE_COMPLETE_REVIEW = "complete_review"
SERVICE_REDEEM_REWARD = "redeem_reward"
SERVICE_ADD_REWARD = "add_reward"
SERVICE_UPDATE_REWARD = "update_reward"
SERVICE_REMOVE_REWARD = "remove_reward"
SERVICE_GET_STATE = "get_state"
SERVICE_MOVE_TASK = "move_task"
SERVICE_SUBMIT_GOAT = "submit_goat"
SERVICE_RESET_PROFILE = "reset_profile"

# Shared payload keys
SERVICE_PERSON = "person"
SERVICE_SKILL = "skill"
SERVICE_POINTS = "points"
SERVICE_PERK = "perk"
SERVICE_REWARD = "reward"
SERVICE_DECISION = "decision"
SERVICE_PROJECT = "project"

# ---------------------------------------------------------------------------
# Events
# ---------------------------------------------------------------------------
# Internal: fired after every save so entities/scheduler refresh.
EVENT_DATA_UPDATED = f"{DOMAIN}_data_updated"
# Public events for automations.
EVENT_TASK_COMPLETED = f"{DOMAIN}_task_completed"
EVENT_LEVEL_UP = f"{DOMAIN}_level_up"
EVENT_PERK_AVAILABLE = f"{DOMAIN}_perk_available"
EVENT_PERK_CHOSEN = f"{DOMAIN}_perk_chosen"
EVENT_QUEST_COMPLETED = f"{DOMAIN}_quest_completed"
EVENT_REVIEW_COMPLETED = f"{DOMAIN}_review_completed"
EVENT_REWARD_REDEEMED = f"{DOMAIN}_reward_redeemed"
EVENT_REMINDER_SENT = f"{DOMAIN}_reminder_sent"
EVENT_SUMMARY_SENT = f"{DOMAIN}_summary_sent"
EVENT_GOAT_COMPLETED = f"{DOMAIN}_goat_completed"
EVENT_PROFILE_RESET = f"{DOMAIN}_profile_reset"

# ---------------------------------------------------------------------------
# Notification options
# ---------------------------------------------------------------------------
CONF_NOTIFY_SERVICES = "notify_services"  # {person_entity_id: notify service, "" = none}
CONF_SUMMARY_ENABLED = "summary_enabled"  # daily summary on/off
CONF_SUMMARY_TIME = "summary_time"  # HH:MM
CONF_HA_NOTIFICATION = "ha_notification"  # also post to persistent_notification
CONF_UNASSIGNED_TO_ALL = "unassigned_to_all"  # unassigned tasks go to all configured persons
DEFAULT_SUMMARY_TIME = "08:00"
SUMMARY_HORIZON_DAYS = 7  # summary includes tasks due within this many days
DEFAULT_DUE_TIME = "09:00"  # reference time for due dates without a time

# ---------------------------------------------------------------------------
# Karma rules
# ---------------------------------------------------------------------------
OVERDUE_KARMA_DAYS = 7  # completing > 7 days overdue costs karma
REVIEW_OVERDUE_KARMA_PER_WEEK = -1  # karma per overdue review week

# ---------------------------------------------------------------------------
# Weekly review
# ---------------------------------------------------------------------------
REVIEW_INTERVAL_DAYS = 7
# Checklist items; the state is computed automatically in the manager.
REVIEW_CHECKLIST = [
    "inbox_empty",
    "next_actions_current",
    "projects_reviewed",
    "waiting_for_followed_up",
    "calendar_checked",
    "someday_reviewed",
]

# ---------------------------------------------------------------------------
# FNV character creation (SPECIAL allocator) and the G.O.A.T.
# ---------------------------------------------------------------------------
# SPECIAL allocation like in Fallout: New Vegas character creation: every attribute
# starts at SPECIAL_BASE (5) and SPECIAL_FREE_POINTS (5) points are distributed
# freely — values may be raised AND lowered, but must stay within SPECIAL_MIN..MAX.
# The total is therefore always SPECIAL_BASE * 7 + SPECIAL_FREE_POINTS = 40.
SPECIAL_BASE = 5
SPECIAL_FREE_POINTS = 5
SPECIAL_MIN = 1
SPECIAL_MAX = 10
SPECIAL_TOTAL_POINTS = SPECIAL_BASE * 7 + SPECIAL_FREE_POINTS  # 40

# The G.O.A.T. (Fallout 3) determines the Tag! skills at setup — see goat_data.py.
# Slide images are user drop-ins: www/gamified_gtd_icons/goat/slide_<n>.png
GOAT_SLIDE_COUNT = 10  # 10 slides (questions), slide 10 is the joke question
