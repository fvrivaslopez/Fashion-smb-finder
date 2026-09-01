#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BONUS & GOAL ALLOCATOR
=======================
A personal tool to split one big company milestone (e.g. "365 new
customers this year") into per-person sub-goals and compute the bonus
each team member has earned, based on a rule you set once per person.

Usage:  python3 bonus_goal_allocator.py

No external dependencies (standard library only).
Everything is stored locally in bonus_data.json. Nothing is sent anywhere.
"""

import os
import sys
import json
import uuid
from datetime import datetime

DATA_FILE = "bonus_data.json"

DATA_DEFAULT = {
    "company_goal": {
        "name": "",
        "target": 0,
        "unit": "",
        "period": "",
        "pool_amount": 0.0,
    },
    "members": {},   # id -> member dict
    "history": [],   # list of snapshot dicts
}

BONUS_TYPES = {
    "1": ("per_unit", "Per unit  (rate x units achieved by this person)"),
    "2": ("milestone", "Milestone (flat amount once their sub-goal is hit, prorated below 100%)"),
    "3": ("pool_share", "Pool share (a % of the shared bonus pool set on the company goal)"),
}


# ─────────────────────────────────────────────
#  STORAGE
# ─────────────────────────────────────────────

def load_data() -> dict:
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, encoding="utf-8") as f:
            data = json.load(f)
        for k, v in DATA_DEFAULT.items():
            data.setdefault(k, v)
        return data
    return json.loads(json.dumps(DATA_DEFAULT))


def save_data(data: dict):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


DATA = load_data()


# ─────────────────────────────────────────────
#  TERMINAL UTILITIES
# ─────────────────────────────────────────────

def clear():
    os.system("cls" if os.name == "nt" else "clear")


def separator(title: str = ""):
    width = 60
    if title:
        padding = max(width - len(title) - 7, 1)
        print(f"\n{'─'*5} {title.upper()} {'─'*padding}")
    else:
        print("─" * 60)


def pause():
    input("\n  [Press ENTER to continue]")


def input_option(minimum: int, maximum: int, message: str = "  -> Option: ") -> int:
    while True:
        try:
            v = int(input(message).strip())
            if minimum <= v <= maximum:
                return v
            print(f"  [x] Enter a number between {minimum} and {maximum}")
        except ValueError:
            print("  [x] Enter a valid number")


def input_text(message: str, required: bool = False, default: str = "") -> str:
    suffix = f" [{default}]" if default else ""
    while True:
        v = input(f"{message}{suffix}: ").strip()
        if not v:
            v = default
        if v or not required:
            return v
        print("  [x] This field cannot be empty")


def input_float(message: str, default: float = 0.0) -> float:
    suffix = f" [{default}]" if default else ""
    while True:
        raw = input(f"{message}{suffix}: ").strip()
        if not raw:
            return default
        try:
            return float(raw.replace(",", "."))
        except ValueError:
            print("  [x] Enter a valid number")


# ─────────────────────────────────────────────
#  COMPANY GOAL
# ─────────────────────────────────────────────

def edit_company_goal():
    separator("Company goal")
    goal = DATA["company_goal"]
    print("  Leave a field blank to keep its current value.\n")

    goal["name"] = input_text("  Goal name (e.g. 'Year 1 growth target')", default=goal["name"])
    goal["target"] = input_float("  Target amount (e.g. 365)", default=goal["target"])
    goal["unit"] = input_text("  Unit (e.g. 'new customers')", default=goal["unit"])
    goal["period"] = input_text("  Period (e.g. '2027' or 'Q1 2027')", default=goal["period"])
    goal["pool_amount"] = input_float(
        "  Shared bonus pool available for 'pool share' members (0 if none)",
        default=goal["pool_amount"],
    )
    save_data(DATA)
    print("\n  [OK] Company goal saved.")
    pause()


# ─────────────────────────────────────────────
#  TEAM MEMBERS
# ─────────────────────────────────────────────

def pick_bonus_type() -> str:
    print()
    for key, (_, label) in BONUS_TYPES.items():
        print(f"    {key}) {label}")
    choice = input_option(1, len(BONUS_TYPES), "  -> Bonus type: ")
    return BONUS_TYPES[str(choice)][0]


def add_member():
    separator("Add team member")
    name = input_text("  Name", required=True)
    role = input_text("  Role (e.g. 'Sales', 'Software Engineer')", required=True)
    sub_goal = input_text("  Their goal in plain words (e.g. 'raise conversion rate from 0.8% to 1.2%')")
    sub_goal_target = input_float("  Numeric target for that goal, if any (0 if purely descriptive)")

    bonus_type = pick_bonus_type()
    if bonus_type == "per_unit":
        bonus_value = input_float("  Amount paid per unit achieved (e.g. 129)")
    elif bonus_type == "milestone":
        bonus_value = input_float("  Flat bonus paid once their target is fully reached")
    else:
        bonus_value = input_float("  Their share of the shared pool, as a percent (e.g. 10 for 10%)")

    member_id = uuid.uuid4().hex[:8]
    DATA["members"][member_id] = {
        "name": name,
        "role": role,
        "sub_goal": sub_goal,
        "sub_goal_target": sub_goal_target,
        "bonus_type": bonus_type,
        "bonus_value": bonus_value,
        "achieved": 0.0,
        "notes": "",
    }
    save_data(DATA)
    print(f"\n  [OK] {name} added (id: {member_id}).")
    pause()


def list_members(interactive: bool = False):
    separator("Team members")
    members = DATA["members"]
    if not members:
        print("  No team members yet. Use option 2 from the main menu to add one.")
        pause()
        return None

    ids = list(members.keys())
    for i, mid in enumerate(ids, start=1):
        m = members[mid]
        print(f"  {i}) {m['name']}  -  {m['role']}  (id: {mid})")

    if not interactive:
        pause()
        return None

    idx = input_option(1, len(ids), "  -> Select a member number: ")
    return ids[idx - 1]


def edit_or_remove_member():
    mid = list_members(interactive=True)
    if mid is None:
        return
    m = DATA["members"][mid]

    separator(f"Editing {m['name']}")
    print("  1) Edit details")
    print("  2) Remove this member")
    print("  0) Back")
    choice = input_option(0, 2)

    if choice == 1:
        m["name"] = input_text("  Name", default=m["name"])
        m["role"] = input_text("  Role", default=m["role"])
        m["sub_goal"] = input_text("  Their goal in plain words", default=m["sub_goal"])
        m["sub_goal_target"] = input_float("  Numeric target for that goal", default=m["sub_goal_target"])
        m["bonus_type"] = pick_bonus_type()
        label = {"per_unit": "rate per unit", "milestone": "flat bonus", "pool_share": "pool share %"}[m["bonus_type"]]
        m["bonus_value"] = input_float(f"  New {label}", default=m["bonus_value"])
        save_data(DATA)
        print("\n  [OK] Updated.")
    elif choice == 2:
        confirm = input_text(f"  Type the name '{m['name']}' again to confirm removal", required=True)
        if confirm == m["name"]:
            del DATA["members"][mid]
            save_data(DATA)
            print("\n  [OK] Removed.")
        else:
            print("\n  [x] Name did not match. Nothing removed.")
    pause()


def record_progress():
    mid = list_members(interactive=True)
    if mid is None:
        return
    m = DATA["members"][mid]
    separator(f"Record progress for {m['name']}")
    print(f"  Current achieved value: {m['achieved']}")
    m["achieved"] = input_float("  New achieved value (total to date, not a delta)", default=m["achieved"])
    save_data(DATA)
    print("\n  [OK] Progress updated.")
    pause()


# ─────────────────────────────────────────────
#  BONUS CALCULATION
# ─────────────────────────────────────────────

def compute_bonus(member: dict) -> float:
    bonus_type = member["bonus_type"]
    achieved = member["achieved"]
    value = member["bonus_value"]
    target = member["sub_goal_target"]

    if bonus_type == "per_unit":
        return achieved * value

    if bonus_type == "milestone":
        if target <= 0:
            return 0.0
        progress = min(achieved / target, 1.0)
        return value * progress

    if bonus_type == "pool_share":
        pool = DATA["company_goal"].get("pool_amount", 0.0)
        return pool * (value / 100.0)

    return 0.0


def format_money(amount: float) -> str:
    return f"{amount:,.2f}"


def build_report_lines() -> list:
    goal = DATA["company_goal"]
    lines = []
    lines.append("=" * 60)
    lines.append("BONUS & GOAL REPORT")
    lines.append("=" * 60)
    lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    lines.append("")

    if goal["name"] or goal["target"]:
        lines.append(f"Company goal : {goal['name'] or '(unnamed)'}")
        lines.append(f"Target       : {goal['target']} {goal['unit']}".strip())
        lines.append(f"Period       : {goal['period']}")
        if goal["pool_amount"]:
            lines.append(f"Shared pool  : {format_money(goal['pool_amount'])}")
        lines.append("")
    else:
        lines.append("(No company goal configured yet — set one from the main menu.)")
        lines.append("")

    members = DATA["members"]
    if not members:
        lines.append("(No team members yet.)")
        return lines

    total_bonus = 0.0
    for m in members.values():
        bonus = compute_bonus(m)
        total_bonus += bonus

        lines.append("-" * 60)
        lines.append(f"{m['name']}  ({m['role']})")
        if m["sub_goal"]:
            lines.append(f"  Goal        : {m['sub_goal']}")
        if m["sub_goal_target"]:
            pct = (m["achieved"] / m["sub_goal_target"] * 100) if m["sub_goal_target"] else 0
            lines.append(f"  Progress    : {m['achieved']} / {m['sub_goal_target']}  ({pct:.0f}%)")
        else:
            lines.append(f"  Achieved    : {m['achieved']}")
        rule = {
            "per_unit": f"{format_money(m['bonus_value'])} per unit",
            "milestone": f"{format_money(m['bonus_value'])} flat on completion",
            "pool_share": f"{m['bonus_value']}% of shared pool",
        }[m["bonus_type"]]
        lines.append(f"  Bonus rule  : {rule}")
        lines.append(f"  Bonus earned: {format_money(bonus)}")

    lines.append("-" * 60)
    lines.append(f"TOTAL BONUS PAYOUT: {format_money(total_bonus)}")
    lines.append("=" * 60)
    return lines


def show_report():
    lines = build_report_lines()
    clear()
    print("\n".join(lines))
    pause()


def save_snapshot():
    lines = build_report_lines()
    DATA["history"].append({
        "date": datetime.now().isoformat(timespec="seconds"),
        "report": "\n".join(lines),
    })
    save_data(DATA)
    print("\n  [OK] Snapshot saved to history.")
    pause()


def view_history():
    separator("History")
    history = DATA["history"]
    if not history:
        print("  No snapshots saved yet.")
        pause()
        return
    for i, snap in enumerate(history, start=1):
        print(f"  {i}) {snap['date']}")
    choice = input_option(0, len(history), "  -> Select a snapshot to view (0 to cancel): ")
    if choice == 0:
        return
    clear()
    print(history[choice - 1]["report"])
    pause()


# ─────────────────────────────────────────────
#  MAIN MENU
# ─────────────────────────────────────────────

def main_menu():
    while True:
        clear()
        separator("Bonus & Goal Allocator")
        goal = DATA["company_goal"]
        if goal["name"]:
            print(f"  Current goal: {goal['name']}  -  {goal['target']} {goal['unit']} ({goal['period']})")
        else:
            print("  No company goal set yet.")
        print(f"  Team members: {len(DATA['members'])}")
        print()
        print("  1) Set / edit company goal")
        print("  2) Add team member")
        print("  3) Edit or remove a team member")
        print("  4) Record progress for a member")
        print("  5) View team members")
        print("  6) Generate bonus report")
        print("  7) Save current report to history")
        print("  8) View saved history")
        print("  0) Exit")
        choice = input_option(0, 8)

        if choice == 1:
            edit_company_goal()
        elif choice == 2:
            add_member()
        elif choice == 3:
            edit_or_remove_member()
        elif choice == 4:
            record_progress()
        elif choice == 5:
            list_members()
        elif choice == 6:
            show_report()
        elif choice == 7:
            save_snapshot()
        elif choice == 8:
            view_history()
        elif choice == 0:
            print("\n  Bye.")
            sys.exit(0)


if __name__ == "__main__":
    try:
        main_menu()
    except KeyboardInterrupt:
        print("\n\n  Interrupted. Nothing was lost — your data is saved as you go.")
        sys.exit(0)
