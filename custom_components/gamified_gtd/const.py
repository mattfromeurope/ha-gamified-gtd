"""Constants for the Gamified GTD integration."""

from __future__ import annotations

DOMAIN = "gamified_gtd"

STORAGE_KEY = DOMAIN
STORAGE_VERSION = 1

# GTD lists
LIST_INBOX = "inbox"
LIST_NEXT_ACTIONS = "next_actions"
LIST_WAITING_FOR = "waiting_for"
LIST_SOMEDAY = "someday_maybe"

TODO_LISTS = {
    LIST_INBOX: "GTD Inbox",
    LIST_NEXT_ACTIONS: "GTD Next Actions",
    LIST_WAITING_FOR: "GTD Waiting For",
    LIST_SOMEDAY: "GTD Someday/Maybe",
}

TASK_OPEN = "open"
TASK_DONE = "done"

PROJECT_ACTIVE = "active"
PROJECT_DONE = "done"

# Config / options
CONF_PERSONS = "persons"
CONF_LEVEL_CAP = "level_cap"
CONF_DEFAULT_TIME_ESTIMATE = "default_time_estimate"
CONF_DEFAULT_ENERGY = "default_energy"
CONF_DEFAULT_XP_BASE = "default_xp_base"
CONF_CONTEXTS = "contexts"
CONF_REWARDS = "rewards"
CONF_DEFAULT_PROFILE = "default_profile"

DEFAULT_LEVEL_CAP = 50
DEFAULT_TIME_ESTIMATE = 15
DEFAULT_ENERGY = 3
DEFAULT_XP_BASE = 10
DEFAULT_CONTEXTS = ["@home", "@computer", "@phone", "@errands", "@anywhere"]

DEFAULT_REWARDS = [
    {"id": "coffee_break", "name": "Coffee break", "description": "Take a real coffee break.", "cost": 50},
    {"id": "gaming_30min", "name": "30 min gaming", "description": "Half an hour of guilt-free gaming.", "cost": 100},
    {"id": "episode", "name": "One episode", "description": "Watch one episode of your series.", "cost": 150},
]

# Task fields
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

# Services
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
SERVICE_GET_STATE = "get_state"

SERVICE_PERSON = "person"
SERVICE_SKILL = "skill"
SERVICE_POINTS = "points"
SERVICE_PERK = "perk"
SERVICE_REWARD = "reward"
SERVICE_DECISION = "decision"
SERVICE_PROJECT = "project"

# Events
EVENT_DATA_UPDATED = f"{DOMAIN}_data_updated"
EVENT_TASK_COMPLETED = f"{DOMAIN}_task_completed"
EVENT_LEVEL_UP = f"{DOMAIN}_level_up"
EVENT_PERK_AVAILABLE = f"{DOMAIN}_perk_available"
EVENT_PERK_CHOSEN = f"{DOMAIN}_perk_chosen"
EVENT_QUEST_COMPLETED = f"{DOMAIN}_quest_completed"
EVENT_REVIEW_COMPLETED = f"{DOMAIN}_review_completed"
EVENT_REWARD_REDEEMED = f"{DOMAIN}_reward_redeemed"

# Review
REVIEW_INTERVAL_DAYS = 7
REVIEW_CHECKLIST = [
    "inbox_empty",
    "next_actions_current",
    "projects_reviewed",
    "waiting_for_followed_up",
    "calendar_checked",
    "someday_reviewed",
]
