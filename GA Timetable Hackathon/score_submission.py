"""
HACKATHON SCORER — Automated Timetable Generation using GA
============================================================
Organizers run this script against EVERY team's submitted timetable CSV to
get an objective, comparable score. Teams should also run this themselves
before submitting, to self-check their output.

-------------------------------------------------------------------------
EXPECTED SUBMISSION FORMAT: timetable_output.csv
-------------------------------------------------------------------------
One row per scheduled class-session, with these exact column headers:

    Section, Day, Slot_Start, Slot_Count, Subject_Code, Subject_Name,
    Faculty_Code, Room_Code, Type

Example rows:
    SEM3,Mon,0,1,T31,Data Structures,F1,R101,Theory
    SEM3,Tue,2,3,L31,DS Lab,F1,LAB2,Lab

    - Day: one of Mon,Tue,Wed,Thu,Fri
    - Slot_Start: 0-indexed slot number within the day
    - Slot_Count: how many contiguous slots this session occupies (1 for
      theory, usually 3 for labs — must match Constraints sheet)
    - Type: Theory or Lab

-------------------------------------------------------------------------
WHAT THIS SCRIPT CHECKS
-------------------------------------------------------------------------
HARD CONSTRAINTS (any violation = timetable is NOT clash-free; heavily penalized)
    H1. No faculty member teaches two sessions at overlapping (day, slot)
    H2. No room hosts two sessions at overlapping (day, slot)
    H3. No section has two sessions at overlapping (day, slot)
    H4. Every subject in Subjects.xlsx gets exactly its required
        sessions_per_week — no subject over- or under-scheduled
    H5. Lab sessions occupy exactly Lab_Block_Length contiguous slots and
        do not run past the last slot of the day

SOFT / CUSTOM CONSTRAINTS (team-defined; scored but do not disqualify)
    Teams declare their own extension constraints in custom_constraints.csv
    (see below) — for example "faculty F6 must teach at least 3 distinct
    subjects" or "no section has more than 2 consecutive theory sessions".
    This script evaluates a few common custom-constraint TYPES out of the
    box; teams extend evaluate_custom_constraint() for anything unusual and
    must clearly document what they added.

-------------------------------------------------------------------------
CUSTOM CONSTRAINTS FORMAT: custom_constraints.csv
-------------------------------------------------------------------------
    type, param1, param2, param3, description

Supported built-in types:
    faculty_subject_pref, FACULTY_CODE, SUBJECT_CODE, , "F1 should teach T31"
        -> checks that FACULTY_CODE is indeed assigned to SUBJECT_CODE

    max_consecutive_theory, SECTION, MAX_N, , "SEM3 no more than 2 back-to-back theory"
        -> checks no section has more than MAX_N consecutive theory slots in a day

    faculty_daily_load_cap, FACULTY_CODE, MAX_SESSIONS, , "F1 max 4 sessions/day"
        -> checks a faculty member isn't scheduled more than MAX_SESSIONS
           sessions on any single day

    faculty_weekly_load_cap, FACULTY_CODE, MAX_SESSIONS, , "F1 max 16 sessions/week"
        -> checks a faculty member's TOTAL sessions across the whole week
           (all days combined) does not exceed MAX_SESSIONS

    no_gap_section, SECTION, , , "SEM5 timetable should have no idle gaps"
        -> checks a section's sessions on any given day are contiguous
           (no free slot sandwiched between two classes)

Any row with an unrecognized `type` is scored as "not evaluated — manual
review needed" and flagged in the report so judges can check it by hand.

-------------------------------------------------------------------------
SCORING (used for the leaderboard / final ranking)
-------------------------------------------------------------------------
    - Hard constraint violations: each instance = -20 points, capped at
      floor of 0 for the hard-constraint component. A timetable with ANY
      hard violation cannot be called "clash-free" regardless of soft score.
    - Soft/custom constraints: each satisfied = +10, each violated = 0
      (not negative — these are "nice to have", not disqualifying).
    - Final score = hard_component (out of 100) is reported separately
      from soft_component (out of 100 * num_custom_constraints/10, i.e.
      just total points), so judges can rank "clash-free" teams first and
      use soft score as the tiebreaker — matching the judging criteria:
      clash-free timetable first, constraint coverage second.
"""

import csv
import sys
from collections import defaultdict

DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri"]


def load_csv(path):
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


def load_subjects(path):
    """Subjects.xlsx exported as CSV, or a plain CSV with the same headers."""
    return load_csv(path)


# ==========================================================================
# HARD CONSTRAINT CHECKS
# ==========================================================================

def occupied_cells(row):
    day = row["Day"]
    start = int(row["Slot_Start"])
    count = int(row["Slot_Count"])
    return [(day, start + k) for k in range(count)]


def check_hard_constraints(schedule, subjects, slots_per_day, lab_block_length):
    violations = []

    faculty_map = defaultdict(list)
    room_map = defaultdict(list)
    section_map = defaultdict(list)

    for row in schedule:
        cells = occupied_cells(row)

        # H5: lab block length + overflow check
        if row["Type"].strip().lower() == "lab":
            if int(row["Slot_Count"]) != lab_block_length:
                violations.append(f"H5: {row['Subject_Code']} ({row['Section']}, {row['Day']}) "
                                   f"lab block length is {row['Slot_Count']}, expected {lab_block_length}")
        for (day, slot) in cells:
            if slot >= slots_per_day:
                violations.append(f"H5: {row['Subject_Code']} ({row['Section']}, {row['Day']}) "
                                   f"overflows past last slot of day (slot {slot})")

        for cell in cells:
            faculty_map[(row["Faculty_Code"], cell)].append(row)
            room_map[(row["Room_Code"], cell)].append(row)
            section_map[(row["Section"], cell)].append(row)

    for key, rows in faculty_map.items():
        if len(rows) > 1:
            desc = ", ".join(f"{r['Subject_Code']}/{r['Section']}" for r in rows)
            violations.append(f"H1: Faculty {key[0]} double-booked at {key[1]} -> {desc}")

    for key, rows in room_map.items():
        if len(rows) > 1:
            desc = ", ".join(f"{r['Subject_Code']}/{r['Section']}" for r in rows)
            violations.append(f"H2: Room {key[0]} double-booked at {key[1]} -> {desc}")

    for key, rows in section_map.items():
        if len(rows) > 1:
            desc = ", ".join(f"{r['Subject_Code']}/{r['Faculty_Code']}" for r in rows)
            violations.append(f"H3: Section {key[0]} double-booked at {key[1]} -> {desc}")

    # H4: session count per subject matches required sessions_per_week
    required = defaultdict(int)
    for s in subjects:
        required[(s["Section"], s["Subject_Code"])] = int(s["Sessions_Per_Week"])

    scheduled_count = defaultdict(int)
    for row in schedule:
        scheduled_count[(row["Section"], row["Subject_Code"])] += 1

    for key, req in required.items():
        got = scheduled_count.get(key, 0)
        if got != req:
            violations.append(f"H4: {key[1]} ({key[0]}) scheduled {got} time(s), "
                               f"required {req}")

    return violations


# ==========================================================================
# CUSTOM / SOFT CONSTRAINT CHECKS
# ==========================================================================

def evaluate_custom_constraint(row, schedule):
    """Returns (satisfied: bool, note: str) or (None, note) if unrecognized type."""
    ctype = row["type"].strip()

    if ctype == "faculty_subject_pref":
        faculty, subject = row["param1"].strip(), row["param2"].strip()
        matches = [r for r in schedule if r["Subject_Code"] == subject]
        if not matches:
            return False, f"Subject {subject} not found in schedule"
        ok = all(r["Faculty_Code"] == faculty for r in matches)
        return ok, f"{subject} taught by {set(r['Faculty_Code'] for r in matches)}"

    if ctype == "max_consecutive_theory":
        section, max_n = row["param1"].strip(), int(row["param2"])
        by_day = defaultdict(list)
        for r in schedule:
            if r["Section"] == section and r["Type"].strip().lower() == "theory":
                by_day[r["Day"]].append(int(r["Slot_Start"]))
        worst = 0
        for day, slots in by_day.items():
            slots = sorted(slots)
            run = 1
            for i in range(1, len(slots)):
                if slots[i] == slots[i - 1] + 1:
                    run += 1
                    worst = max(worst, run)
                else:
                    run = 1
            worst = max(worst, run if slots else 0)
        return worst <= max_n, f"longest consecutive theory run = {worst}"

    if ctype == "faculty_daily_load_cap":
        faculty, max_sessions = row["param1"].strip(), int(row["param2"])
        by_day = defaultdict(int)
        for r in schedule:
            if r["Faculty_Code"] == faculty:
                by_day[r["Day"]] += 1
        worst = max(by_day.values()) if by_day else 0
        return worst <= max_sessions, f"max sessions/day for {faculty} = {worst}"

    if ctype == "faculty_weekly_load_cap":
        faculty, max_sessions = row["param1"].strip(), int(row["param2"])
        total = sum(1 for r in schedule if r["Faculty_Code"] == faculty)
        return total <= max_sessions, f"total sessions/week for {faculty} = {total}"

    if ctype == "no_gap_section":
        section = row["param1"].strip()
        by_day = defaultdict(set)
        for r in schedule:
            if r["Section"] == section:
                for cell in occupied_cells(r):
                    by_day[cell[0]].add(cell[1])
        gaps_found = False
        for day, slots in by_day.items():
            if len(slots) > 1:
                span = max(slots) - min(slots) + 1
                if span > len(slots):
                    gaps_found = True
        return (not gaps_found), f"gaps found: {gaps_found}"

    return None, "Unrecognized constraint type — needs manual review"


# ==========================================================================
# MAIN
# ==========================================================================

def score_submission(schedule_path, subjects_path, custom_constraints_path=None,
                      slots_per_day=7, lab_block_length=3):
    schedule = load_csv(schedule_path)
    subjects = load_subjects(subjects_path)

    print("=" * 70)
    print("HARD CONSTRAINT CHECK")
    print("=" * 70)
    violations = check_hard_constraints(schedule, subjects, slots_per_day, lab_block_length)

    if not violations:
        print("✅ ZERO hard-constraint violations — this timetable is CLASH-FREE.")
    else:
        print(f"❌ {len(violations)} hard-constraint violation(s) found:\n")
        for v in violations:
            print("  -", v)

    hard_score = max(0, 100 - 20 * len(violations))
    print(f"\nHard-constraint score: {hard_score}/100  "
          f"({'CLASH-FREE' if not violations else 'NOT clash-free'})")

    soft_results = []
    if custom_constraints_path:
        print("\n" + "=" * 70)
        print("CUSTOM / SOFT CONSTRAINT CHECK")
        print("=" * 70)
        custom_rows = load_csv(custom_constraints_path)
        satisfied = 0
        needs_review = 0
        for row in custom_rows:
            ok, note = evaluate_custom_constraint(row, schedule)
            desc = row.get("description", "")
            if ok is None:
                needs_review += 1
                print(f"  ? [MANUAL REVIEW] {desc} -> {note}")
            elif ok:
                satisfied += 1
                print(f"  ✅ {desc} -> {note}")
            else:
                print(f"  ❌ {desc} -> {note}")
            soft_results.append((desc, ok, note))

        total_auto = len(custom_rows) - needs_review
        soft_score = round(100 * satisfied / total_auto, 1) if total_auto else None
        print(f"\nCustom-constraint score: {satisfied}/{total_auto} auto-checked "
              f"constraints satisfied" + (f" ({soft_score}%)" if soft_score is not None else ""))
        if needs_review:
            print(f"({needs_review} constraint(s) need manual judge review — unrecognized type)")

    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"Clash-free (hard constraints):  {'YES' if not violations else 'NO'}")
    print(f"Hard violations:                {len(violations)}")
    if custom_constraints_path:
        print(f"Custom constraints satisfied:   {satisfied}/{total_auto}")
    print("\nJudging note: rank CLASH-FREE submissions first (hard violations = 0),")
    print("then use custom-constraint satisfaction as the tiebreaker.")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python3 score_submission.py <timetable_output.csv> <subjects.csv> "
              "[custom_constraints.csv] [slots_per_day] [lab_block_length]")
        print("\nExample:")
        print("  python3 score_submission.py team5_timetable.csv subjects.csv "
              "team5_custom_constraints.csv 7 3")
        sys.exit(1)

    schedule_path = sys.argv[1]
    subjects_path = sys.argv[2]
    custom_path = sys.argv[3] if len(sys.argv) > 3 else None
    slots_per_day = int(sys.argv[4]) if len(sys.argv) > 4 else 7
    lab_block_length = int(sys.argv[5]) if len(sys.argv) > 5 else 3

    score_submission(schedule_path, subjects_path, custom_path, slots_per_day, lab_block_length)
