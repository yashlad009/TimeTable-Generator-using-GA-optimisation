"""
GA-based Timetable Scheduler — KIT's CSE-AIML & CSE-DS Dept
Semesters: 3 (SY), 5 (TY), 7 (BTech) | A.Y. 2026-27 Odd Sem

Subjects, faculty initials, and rooms below are pulled from the department's
master timetable PDF (Updated 08-08-2026). Session-per-week counts are
ESTIMATES read off the grid (merged/rotating lab cells make an exact count
hard to automate) — verify these against the PDF before treating this as the
final published timetable.

-------------------------------------------------------------------------------
PROBLEM ENCODING
-------------------------------------------------------------------------------
- A "class session" = one lecture/lab slot that needs to be scheduled.
- DAYS = Tue-Sat (5 working days per the PDF), SLOTS_PER_DAY = 7
    slot 0: 9-10   slot 1: 10-11   [11-11.15 break, not modeled as a slot]
    slot 2: 11.15-12.15  slot 3: 12.15-1.15  [1.15-2 lunch, not modeled]
    slot 4: 2-3   slot 5: 3-4   slot 6: 4-5
- CHROMOSOME = one full timetable = a list, one gene per class-session-to-be-scheduled.
  Each gene = (day, slot, room)   [faculty & subject & section are fixed per session]
- FIXED SLOTS: multi-disciplinary electives (MDM), open/program electives (OE/PE),
  LeetCode sessions and Project Phase-I are already pinned to specific
  day/slot/room combinations in the master timetable (they're shared across
  sections/rooms, e.g. "CSAMCR 02/03/04"), so they are NOT re-optimized by the
  GA — they're loaded as pre-occupied cells that the GA must schedule around.

FITNESS FUNCTION (penalty-based; lower penalty = higher fitness)
  Hard constraints (heavily penalized):
    - Same faculty teaching two sessions at the same (day, slot)
    - Same room used by two sessions at the same (day, slot)
    - Same section having two sessions at the same (day, slot)
    - Lab session not fitting within allowed contiguous lab slots
    - Any GA-placed session colliding with a FIXED slot (faculty/room/section clash)
  Soft constraints (lightly penalized):
    - Idle gaps in a section's day
    - Uneven load across the week

  fitness = 1 / (1 + total_penalty)
"""

import random
import copy

random.seed(42)  # remove/change this once you start experimenting



DAYS = ["Tue", "Wed", "Thu", "Fri", "Sat"]
SLOTS_PER_DAY = 7          
LAB_BLOCK_SLOTS = 2        # a lab occupies 2 contiguous slots

ROOMS_THEORY = ["CSAMCR01", "CSAMCR02", "CSAMCR03", "CSAMCR04", "CSAMCR05", "CSAMCR06", "CSDSCR01"]
ROOMS_LAB = ["LAB1", "LAB2", "LAB3", "LAB4", "LAB5", "LAB6"]


HOME_ROOM = {
    "SEM3-A": "CSAMCR06", "SEM3-B": "CSAMCR02", "SEM3-C": "CSDSCR01",
    "SEM5-A": "CSAMCR03", "SEM5-B": "CSAMCR04", "SEM5-C": "CSAMCR05",
    "SEM7-A": "CSAMCR01", "SEM7-B": "CSAMCR01", "SEM7-D": "CSAMCR01",  
}

 
SECTIONS = {
    # ---------------- SEM 3 (SY AIML) ----------------
    "SEM3-A": {
        "theory": [
            {"code": "ADS",  "name": "Advanced Data Structures", "faculty": "SS",  "sessions_per_week": 3},
            {"code": "DMGT", "name": "Discrete Mathematics",     "faculty": "SGB", "sessions_per_week": 3},
            {"code": "LA",   "name": "Linear Algebra",           "faculty": "SHD", "sessions_per_week": 3},
            {"code": "DBMS", "name": "DBMS",                     "faculty": "SSS", "sessions_per_week": 4},
            {"code": "PAIML","name": "Principles of AI/ML",      "faculty": "SM",  "sessions_per_week": 3},
            {"code": "CI",   "name": "Comm. & Interpersonal Skills", "faculty": "MeghaThombare", "sessions_per_week": 2},
            {"code": "SST",  "name": "Statistics for ML",        "faculty": "NS",  "sessions_per_week": 1},
        ],
        "lab": [
            {"code": "ADSL", "name": "ADS Lab",  "faculty": "SS",  "sessions_per_week": 2},
            {"code": "DBMSL","name": "DBMS Lab", "faculty": "SSS", "sessions_per_week": 2},
            {"code": "MPI",  "name": "Mini Project-I", "faculty": "NB", "sessions_per_week": 2},
            {"code": "SSTL", "name": "SST Lab",  "faculty": "NS",  "sessions_per_week": 1},
            {"code": "CEE",  "name": "Comm. Eng. Essentials Lab", "faculty": "SK", "sessions_per_week": 1},
        ],
    },
    "SEM3-B": {
        "theory": [
            {"code": "ADS",  "name": "Advanced Data Structures", "faculty": "SS",  "sessions_per_week": 3},
            {"code": "DMGT", "name": "Discrete Mathematics","faculty": "SC",  "sessions_per_week": 3},
            {"code": "LA",   "name": "Linear Algebra","faculty": "MUM", "sessions_per_week": 3},
            {"code": "DBMS", "name": "DBMS","faculty": "PSK", "sessions_per_week": 4},
            {"code": "PAIML","name": "Principles of AI/ML","faculty": "Vajreshwari", "sessions_per_week": 2},
            {"code": "CI",   "name": "Comm. & Interpersonal Skills", "faculty": "MeghaThombare", "sessions_per_week": 2},
            {"code": "SST",  "name": "Statistics for ML","faculty": "SL",  "sessions_per_week": 1},
        ],
        "lab": [
            {"code": "ADSL", "name": "ADS Lab",  "faculty": "SS",  "sessions_per_week": 2},
            {"code": "DBMSL","name": "DBMS Lab", "faculty": "PSK", "sessions_per_week": 2},
            {"code": "MPI",  "name": "Mini Project-I", "faculty": "DDK", "sessions_per_week": 2},
            {"code": "SSTL", "name": "SST Lab",  "faculty": "SL",  "sessions_per_week": 1},
            {"code": "CEE",  "name": "Comm. Eng. Essentials Lab", "faculty": "TG", "sessions_per_week": 1},
        ],
    },
    "SEM3-C": {
        "theory": [
            {"code": "ADS",  "name": "Advanced Data Structures", "faculty": "KVJ", "sessions_per_week": 3},
            {"code": "DMGT", "name": "Discrete Mathematics",     "faculty": "SGB", "sessions_per_week": 3},
            {"code": "LA",   "name": "Linear Algebra",           "faculty": "JJB", "sessions_per_week": 3},
            {"code": "DBMS", "name": "DBMS",                     "faculty": "AK",  "sessions_per_week": 4},
            {"code": "PAIML","name": "Principles of AI/ML",      "faculty": "Vajreshwari", "sessions_per_week": 2},
            {"code": "CI",   "name": "Comm. & Interpersonal Skills", "faculty": "MeghaThombare", "sessions_per_week": 2},
            {"code": "SST",  "name": "Statistics for ML",        "faculty": "Kajesh", "sessions_per_week": 1},
        ],
        "lab": [
            {"code": "ADSL", "name": "ADS Lab",  "faculty": "KVJ", "sessions_per_week": 2},
            {"code": "DBMSL","name": "DBMS Lab", "faculty": "AK",  "sessions_per_week": 2},
            {"code": "MPI",  "name": "Mini Project-I", "faculty": "SGupta", "sessions_per_week": 2},
            {"code": "SSTL", "name": "SST Lab",  "faculty": "Kajesh", "sessions_per_week": 1},
            {"code": "CEE",  "name": "Comm. Eng. Essentials Lab", "faculty": "RohitD", "sessions_per_week": 1},
        ],
    },

    # ---------------- SEM 5 (TY AIML) ----------------
    "SEM5-A": {
        "theory": [
            {"code": "EDA",  "name": "Exploratory Data Analysis", "faculty": "SM",  "sessions_per_week": 4},
            {"code": "ML",   "name": "Machine Learning",          "faculty": "VSP", "sessions_per_week": 4},
            {"code": "COOS", "name": "Computer Organisation and OS",    "faculty": "AC",  "sessions_per_week": 2},
        ],
        "lab": [
            {"code": "EDAL", "name": "EDA Lab",   "faculty": "SM",  "sessions_per_week": 2},
            {"code": "MLL",  "name": "ML Lab",    "faculty": "VSP", "sessions_per_week": 2},
            {"code": "APL",  "name": "Advance java programming", "faculty": "NM", "sessions_per_week": 2},
            {"code": "BCVS", "name": "bussiness communication and value science ", "faculty": "SK/TG", "sessions_per_week": 1},
            {"code": "MPIII","name": "Mini Project-III", "faculty": "KVJ/SGB", "sessions_per_week": 2},
        ],
    },
    "SEM5-B": {
        "theory": [
            {"code": "EDA",  "name": "Exploratory Data Analysis", "faculty": "SSS", "sessions_per_week": 4},
            {"code": "ML",   "name": "Machine Learning",          "faculty": "RK/PSK", "sessions_per_week": 4},
            {"code": "COOS", "name": "Computer Organisation and OS",    "faculty": "AC",  "sessions_per_week": 2},
        ],
        "lab": [
            {"code": "EDAL", "name": "EDA Lab",   "faculty": "SSS", "sessions_per_week": 2},
            {"code": "MLL",  "name": "ML Lab",    "faculty": "RK",  "sessions_per_week": 2},
            {"code": "APL",  "name": "Advance java programming lab", "faculty": "NM", "sessions_per_week": 2},
            {"code": "BCVS", "name": "bussiness communication and value science ", "faculty": "SK/TG", "sessions_per_week": 1},
            {"code": "MPIII","name": "Mini Project-III", "faculty": "RK/Kajesh/SM", "sessions_per_week": 2},
        ],
    },
    "SEM5-C": {
        "theory": [
            {"code": "EDA",  "name": "Exploratory Data Analysis", "faculty": "APB", "sessions_per_week": 4},
            {"code": "ML",   "name": "Machine Learning",          "faculty": "VAP", "sessions_per_week": 4},
            {"code": "COOS", "name": "Computer Organisation and OS",    "faculty": "AC",  "sessions_per_week": 2},
        ],
        "lab": [
            {"code": "EDAL", "name": "EDA Lab",   "faculty": "APB", "sessions_per_week": 2},
            {"code": "MLL",  "name": "ML Lab",    "faculty": "VAP", "sessions_per_week": 2},
            {"code": "APL",  "name": "Advance java programming lab", "faculty": "NM", "sessions_per_week": 2},
            {"code": "BCVS", "name": "bussiness communication and value science ", "faculty": "SK/TG", "sessions_per_week": 1},
            {"code": "MPIII","name": "Mini Project-III", "faculty": "NS/SL", "sessions_per_week": 2},
        ],
    },

    # ---------------- SEM 7 (BTech AIML / DS) ----------------
    "SEM7-A": {
        "theory": [
            {"code": "CBCS", "name": "Choice-Based Credit Subject", "faculty": "AK",  "sessions_per_week": 2},
        ],
        "lab": [
            {"code": "GenAI", "name": "Generative AI Lab", "faculty": "UPG", "sessions_per_week": 3},
            {"code": "MLDO",  "name": "ML DevOps Lab",     "faculty": "VSP", "sessions_per_week": 3},
        ],
    },
    "SEM7-B": {
        "theory": [
            {"code": "CBCS", "name": "Choice-Based Credit Subject", "faculty": "AK",  "sessions_per_week": 2},
        ],
        "lab": [
            {"code": "GenAI", "name": "Generative AI Lab", "faculty": "RK",  "sessions_per_week": 3},
            {"code": "MLDO",  "name": "ML DevOps Lab",     "faculty": "SDJ", "sessions_per_week": 3},
        ],
    },
    "SEM7-D": {  # BTech DS
        "theory": [
            {"code": "CBCS", "name": "Choice-Based Credit Subject", "faculty": "APB", "sessions_per_week": 2},
        ],
        "lab": [
            {"code": "GenAI", "name": "Generative AI Lab", "faculty": "VAP", "sessions_per_week": 3},
            {"code": "MLDO",  "name": "ML DevOps Lab",     "faculty": "SDJ", "sessions_per_week": 3},
        ],
    },
}

# ------------------------------------------------------------------------------
# FIXED SLOTS: already pinned in the master timetable (shared electives, project
# time, LeetCode). The GA does NOT move these; it only avoids clashing with them.
# Each entry: (section, day_idx, slot_idx, span, label, faculty, room)
# ------------------------------------------------------------------------------
def d(day_name):
    return DAYS.index(day_name)

# ------------------------------------------------------------------------------
# FIXED EVENTS
#
# These events are already fixed in the master timetable.
# The GA does NOT move them.
#
# Structure is intentionally kept the same:
#
# {
#     "sections": [...],
#     "day": d("Tue"),
#     "slot": 0,
#     "span": 1,
#     "label": "...",
#     "faculties": [...],
#     "rooms": [...],
#     "blocks_section": True,
#     "blocks_faculty": True/False,
#     "blocks_room": True/False
# }
#
# IMPORTANT:
# When the same logical event occurs at different times, it is represented
# by separate dictionaries. No new "occurrences" field is introduced.
#
# LeetCode is intentionally NOT included because it is optional.
# ------------------------------------------------------------------------------

def d(day_name):
    return DAYS.index(day_name)


FIXED_EVENTS = [

    # ==========================================================================
    # SEM 3
    # ==========================================================================

    # ---------------- MDM-I ----------------
    # Tue 9:00-10:00
    # Wed 9:00-10:00
    #
    # Shared by SEM3-A, SEM3-B, SEM3-C.
    # Faculties: NB, DDK, Gupta
    # Rooms: CSAMCR06, CSDSCR01, CSAMCR02
    #
    # Verified from timetable pages 1, 2 and 3.
    # ==========================================================================

    {
        "sections": ["SEM3-A", "SEM3-B", "SEM3-C"],
        "day": d("Tue"),
        "slot": 0,
        "span": 1,
        "label": "MDM-I",
        "faculties": ["NB", "DDK", "Gupta"],
        "rooms": ["CSAMCR06", "CSDSCR01", "CSAMCR02"],
        "blocks_section": True,
        "blocks_faculty": True,
        "blocks_room": True
    },

    {
        "sections": ["SEM3-A", "SEM3-B", "SEM3-C"],
        "day": d("Wed"),
        "slot": 0,
        "span": 1,
        "label": "MDM-I",
        "faculties": ["NB", "DDK", "Gupta"],
        "rooms": ["CSAMCR06", "CSDSCR01", "CSAMCR02"],
        "blocks_section": True,
        "blocks_faculty": True,
        "blocks_room": True
    },


    # ---------------- T & P ----------------
    # SEM3-A : Thu 9:00-11:00
    # SEM3-B : Thu 11:15-1:15
    # SEM3-C : Thu 2:00-4:00
    #
    # Verified from pages 1, 2 and 3.
    # ==========================================================================

    {
        "sections": ["SEM3-A"],
        "day": d("Thu"),
        "slot": 0,
        "span": 2,
        "label": "T&P",
        "faculties": [],
        "rooms": ["CSAMCR06"],
        "blocks_section": True,
        "blocks_faculty": False,
        "blocks_room": True
    },

    {
        "sections": ["SEM3-B"],
        "day": d("Thu"),
        "slot": 2,
        "span": 2,
        "label": "T&P",
        "faculties": [],
        "rooms": ["CSAMCR02"],
        "blocks_section": True,
        "blocks_faculty": False,
        "blocks_room": True
    },

    {
        "sections": ["SEM3-C"],
        "day": d("Thu"),
        "slot": 4,
        "span": 2,
        "label": "T&P",
        "faculties": [],
        "rooms": ["CSDSCR01"],
        "blocks_section": True,
        "blocks_faculty": False,
        "blocks_room": True
    },


    # ==========================================================================
    # SEM 5
    # ==========================================================================

    # ---------------- MDM-3 ----------------
    # Thu 9:00-10:00
    # Fri 9:00-10:00
    # Fri 12:15-1:15
    #
    # Shared by SEM5-A, SEM5-B, SEM5-C.
    #
    # Faculties: SL, KVJ, SC
    # Rooms: CSAMCR02, CSAMCR03, CSAMCR04
    #
    # IMPORTANT:
    # The third occurrence is FRIDAY SLOT 3, not slot 0.
    #
    # Verified from pages 4, 5 and 6.
    # ==========================================================================

    {
        "sections": ["SEM5-A", "SEM5-B", "SEM5-C"],
        "day": d("Thu"),
        "slot": 0,
        "span": 1,
        "label": "MDM-3",
        "faculties": ["SL", "KVJ", "SC"],
        "rooms": ["CSAMCR02", "CSAMCR03", "CSAMCR04"],
        "blocks_section": True,
        "blocks_faculty": True,
        "blocks_room": True
    },

    {
        "sections": ["SEM5-A", "SEM5-B", "SEM5-C"],
        "day": d("Fri"),
        "slot": 0,
        "span": 1,
        "label": "MDM-3",
        "faculties": ["SL", "KVJ", "SC"],
        "rooms": ["CSAMCR02", "CSAMCR03", "CSAMCR04"],
        "blocks_section": True,
        "blocks_faculty": True,
        "blocks_room": True
    },

    {
        "sections": ["SEM5-A", "SEM5-B", "SEM5-C"],
        "day": d("Fri"),
        "slot": 3,
        "span": 1,
        "label": "MDM-3",
        "faculties": ["SL", "KVJ", "SC"],
        "rooms": ["CSAMCR02", "CSAMCR03", "CSAMCR04"],
        "blocks_section": True,
        "blocks_faculty": True,
        "blocks_room": True
    },


    # ---------------- OE-I ----------------
    # Online common lecture for SEM5-A/B/C.
    #
    # Tue 11:15-12:15
    # Wed 11:15-12:15
    # Fri 11:15-12:15
    #
    # No physical room.
    # No physical faculty resource is consumed by this scheduler.
    #
    # Verified from pages 4, 5 and 6.
    # ==========================================================================

    {
        "sections": ["SEM5-A", "SEM5-B", "SEM5-C"],
        "day": d("Tue"),
        "slot": 2,
        "span": 1,
        "label": "OE-I",
        "faculties": [],
        "rooms": [],
        "blocks_section": True,
        "blocks_faculty": False,
        "blocks_room": False
    },

    {
        "sections": ["SEM5-A", "SEM5-B", "SEM5-C"],
        "day": d("Wed"),
        "slot": 2,
        "span": 1,
        "label": "OE-I",
        "faculties": [],
        "rooms": [],
        "blocks_section": True,
        "blocks_faculty": False,
        "blocks_room": False
    },

    {
        "sections": ["SEM5-A", "SEM5-B", "SEM5-C"],
        "day": d("Fri"),
        "slot": 2,
        "span": 1,
        "label": "OE-I",
        "faculties": [],
        "rooms": [],
        "blocks_section": True,
        "blocks_faculty": False,
        "blocks_room": False
    },


    # ---------------- PE1 ----------------
    # Tue 4:00-5:00
    # Wed 4:00-5:00
    # Fri 2:00-3:00
    #
    # Shared by SEM5-A/B/C.
    #
    # Faculties: NS, NB, DDK
    # Rooms: CSAMCR02, CSAMCR03, CSAMCR04
    #
    # Verified from pages 4, 5 and 6.
    # ==========================================================================

    {
        "sections": ["SEM5-A", "SEM5-B", "SEM5-C"],
        "day": d("Tue"),
        "slot": 6,
        "span": 1,
        "label": "PE1",
        "faculties": ["NS", "NB", "DDK"],
        "rooms": ["CSAMCR02", "CSAMCR03", "CSAMCR04"],
        "blocks_section": True,
        "blocks_faculty": True,
        "blocks_room": True
    },

    {
        "sections": ["SEM5-A", "SEM5-B", "SEM5-C"],
        "day": d("Wed"),
        "slot": 6,
        "span": 1,
        "label": "PE1",
        "faculties": ["NS", "NB", "DDK"],
        "rooms": ["CSAMCR02", "CSAMCR03", "CSAMCR04"],
        "blocks_section": True,
        "blocks_faculty": True,
        "blocks_room": True
    },

    {
        "sections": ["SEM5-A", "SEM5-B", "SEM5-C"],
        "day": d("Fri"),
        "slot": 4,
        "span": 1,
        "label": "PE1",
        "faculties": ["NS", "NB", "DDK"],
        "rooms": ["CSAMCR02", "CSAMCR03", "CSAMCR04"],
        "blocks_section": True,
        "blocks_faculty": True,
        "blocks_room": True
    },


    # ---------------- T & P ----------------
    # SEM5-A : Sat 9:00-11:00
    # SEM5-B : Sat 11:15-1:15
    # SEM5-C : Sat 2:00-4:00
    #
    # Verified from pages 4, 5 and 6.
    # ==========================================================================

    {
        "sections": ["SEM5-A"],
        "day": d("Sat"),
        "slot": 0,
        "span": 2,
        "label": "T&P",
        "faculties": [],
        "rooms": ["CSAMCR03"],
        "blocks_section": True,
        "blocks_faculty": False,
        "blocks_room": True
    },

    {
        "sections": ["SEM5-B"],
        "day": d("Sat"),
        "slot": 2,
        "span": 2,
        "label": "T&P",
        "faculties": [],
        "rooms": ["CSAMCR04"],
        "blocks_section": True,
        "blocks_faculty": False,
        "blocks_room": True
    },

    {
        "sections": ["SEM5-C"],
        "day": d("Sat"),
        "slot": 4,
        "span": 2,
        "label": "T&P",
        "faculties": [],
        "rooms": ["CSAMCR05"],
        "blocks_section": True,
        "blocks_faculty": False,
        "blocks_room": True
    },


    # ==========================================================================
    # SEM 7
    # ==========================================================================

    # ---------------- MDM-5 ----------------
    # Tue 9:00-10:00
    # Wed 11:15-12:15
    # Fri 3:00-4:00
    #
    # Shared by SEM7-A/B/D.
    #
    # Faculty:
    #   SGB / Kajesh
    #
    # IMPORTANT:
    # The timetable shows DIFFERENT room pairs at different occurrences.
    #
    # Tue -> CSAMCR01 / CSAMCR03
    # Wed -> CSAMCR01 / CSAMCR06
    # Fri -> CSAMCR01 / CSDSCR01
    #
    # The PDF shows TWO rooms for MDM-5 at each occurrence.
    # Therefore I am NOT inventing a third room.
    #
    # Verified visually from pages 7, 8 and 9.
    # ==========================================================================

    {
        "sections": ["SEM7-A", "SEM7-B", "SEM7-D"],
        "day": d("Tue"),
        "slot": 0,
        "span": 1,
        "label": "MDM-5",
        "faculties": ["SGB", "Kajesh"],
        "rooms": ["CSAMCR01", "CSAMCR03"],
        "blocks_section": True,
        "blocks_faculty": True,
        "blocks_room": True
    },

    {
        "sections": ["SEM7-A", "SEM7-B", "SEM7-D"],
        "day": d("Wed"),
        "slot": 2,
        "span": 1,
        "label": "MDM-5",
        "faculties": ["SGB", "Kajesh"],
        "rooms": ["CSAMCR01", "CSAMCR06"],
        "blocks_section": True,
        "blocks_faculty": True,
        "blocks_room": True
    },

    {
        "sections": ["SEM7-A", "SEM7-B", "SEM7-D"],
        "day": d("Fri"),
        "slot": 5,
        "span": 1,
        "label": "MDM-5",
        "faculties": ["SGB", "Kajesh"],
        "rooms": ["CSAMCR01", "CSDSCR01"],
        "blocks_section": True,
        "blocks_faculty": True,
        "blocks_room": True
    },


    # ---------------- OE-III ----------------
    # Online common lecture for SEM7-A/B/D.
    #
    # Tue 11:15-12:15
    # Wed 11:15-12:15
    #
    # No physical room/faculty resource.
    #
    # Verified from pages 7, 8 and 9.
    # ==========================================================================

    {
        "sections": ["SEM7-A", "SEM7-B", "SEM7-D"],
        "day": d("Tue"),
        "slot": 2,
        "span": 1,
        "label": "OE-III",
        "faculties": [],
        "rooms": [],
        "blocks_section": True,
        "blocks_faculty": False,
        "blocks_room": False
    },

    {
        "sections": ["SEM7-A", "SEM7-B", "SEM7-D"],
        "day": d("Wed"),
        "slot": 2,
        "span": 1,
        "label": "OE-III",
        "faculties": [],
        "rooms": [],
        "blocks_section": True,
        "blocks_faculty": False,
        "blocks_room": False
    },


    # ---------------- PE III ----------------
    # Tue 2:00-3:00
    # Wed 2:00-3:00
    # Thu 2:00-3:00
    #
    # Shared by SEM7-A/B/D.
    #
    # Faculty:
    # Vajreshwari / Shamkumar Gupta / DDK
    #
    # Rooms:
    # Tue/Wed -> CSAMCR01/04/05
    # Thu     -> CSAMCR01/03/04
    #
    # Verified from pages 7, 8 and 9.
    # ==========================================================================

    {
        "sections": ["SEM7-A", "SEM7-B", "SEM7-D"],
        "day": d("Tue"),
        "slot": 4,
        "span": 1,
        "label": "PE III",
        "faculties": [
            "Vajreshwari",
            "Shamkumar Gupta",
            "DDK"
        ],
        "rooms": [
            "CSAMCR01",
            "CSAMCR04",
            "CSAMCR05"
        ],
        "blocks_section": True,
        "blocks_faculty": True,
        "blocks_room": True
    },

    {
        "sections": ["SEM7-A", "SEM7-B", "SEM7-D"],
        "day": d("Wed"),
        "slot": 4,
        "span": 1,
        "label": "PE III",
        "faculties": [
            "Vajreshwari",
            "Shamkumar Gupta",
            "DDK"
        ],
        "rooms": [
            "CSAMCR01",
            "CSAMCR04",
            "CSAMCR05"
        ],
        "blocks_section": True,
        "blocks_faculty": True,
        "blocks_room": True
    },

    {
        "sections": ["SEM7-A", "SEM7-B", "SEM7-D"],
        "day": d("Thu"),
        "slot": 4,
        "span": 1,
        "label": "PE III",
        "faculties": [
            "Vajreshwari",
            "Shamkumar Gupta",
            "DDK"
        ],
        "rooms": [
            "CSAMCR01",
            "CSAMCR03",
            "CSAMCR04"
        ],
        "blocks_section": True,
        "blocks_faculty": True,
        "blocks_room": True
    },


    # ---------------- Project Phase-I ----------------
    #
    # Saturday:
    #
    # 9:00-11:00
    # 11:15-1:15
    # 2:00-4:00
    #
    # These MUST be separate events because slot 1 is separated by the
    # 11:00-11:15 break and slot 3 is separated by lunch.
    #
    # No room/faculty is specified in the timetable.
    #
    # Verified visually from pages 7, 8 and 9.
    # ==========================================================================

    {
        "sections": ["SEM7-A"],
        "day": d("Sat"),
        "slot": 0,
        "span": 2,
        "label": "Project Phase-I",
        "faculties": [],
        "rooms": [],
        "blocks_section": True,
        "blocks_faculty": False,
        "blocks_room": False
    },

    {
        "sections": ["SEM7-A"],
        "day": d("Sat"),
        "slot": 2,
        "span": 2,
        "label": "Project Phase-I",
        "faculties": [],
        "rooms": [],
        "blocks_section": True,
        "blocks_faculty": False,
        "blocks_room": False
    },

    {
        "sections": ["SEM7-A"],
        "day": d("Sat"),
        "slot": 4,
        "span": 2,
        "label": "Project Phase-I",
        "faculties": [],
        "rooms": [],
        "blocks_section": True,
        "blocks_faculty": False,
        "blocks_room": False
    },

    {
        "sections": ["SEM7-B"],
        "day": d("Sat"),
        "slot": 0,
        "span": 2,
        "label": "Project Phase-I",
        "faculties": [],
        "rooms": [],
        "blocks_section": True,
        "blocks_faculty": False,
        "blocks_room": False
    },

    {
        "sections": ["SEM7-B"],
        "day": d("Sat"),
        "slot": 2,
        "span": 2,
        "label": "Project Phase-I",
        "faculties": [],
        "rooms": [],
        "blocks_section": True,
        "blocks_faculty": False,
        "blocks_room": False
    },

    {
        "sections": ["SEM7-B"],
        "day": d("Sat"),
        "slot": 4,
        "span": 2,
        "label": "Project Phase-I",
        "faculties": [],
        "rooms": [],
        "blocks_section": True,
        "blocks_faculty": False,
        "blocks_room": False
    },

    {
        "sections": ["SEM7-D"],
        "day": d("Sat"),
        "slot": 0,
        "span": 2,
        "label": "Project Phase-I",
        "faculties": [],
        "rooms": [],
        "blocks_section": True,
        "blocks_faculty": False,
        "blocks_room": False
    },

    {
        "sections": ["SEM7-D"],
        "day": d("Sat"),
        "slot": 2,
        "span": 2,
        "label": "Project Phase-I",
        "faculties": [],
        "rooms": [],
        "blocks_section": True,
        "blocks_faculty": False,
        "blocks_room": False
    },

    {
        "sections": ["SEM7-D"],
        "day": d("Sat"),
        "slot": 4,
        "span": 2,
        "label": "Project Phase-I",
        "faculties": [],
        "rooms": [],
        "blocks_section": True,
        "blocks_faculty": False,
        "blocks_room": False
    },

]

# ==============================================================================
# 2. BUILD THE LIST OF SESSIONS TO SCHEDULE (this becomes the chromosome length)
# ==============================================================================

def build_sessions():
    sessions = []
    for section, data in SECTIONS.items():
        for subj in data["theory"]:
            for i in range(subj["sessions_per_week"]):
                sessions.append({
                    "section": section, "code": subj["code"], "name": subj["name"],
                    "faculty": subj["faculty"], "type": "theory", "occurrence": i,
                })
        for subj in data["lab"]:
            for i in range(subj["sessions_per_week"]):
                sessions.append({
                    "section": section, "code": subj["code"], "name": subj["name"],
                    "faculty": subj["faculty"], "type": "lab", "occurrence": i,
                })
    return sessions

SESSIONS = build_sessions()
N_GENES = len(SESSIONS)

# Pre-index fixed-event occupancy for fast clash lookup during fitness evaluation.
FIXED_CELLS_BY_SECTION = {}   # section -> set of (day, slot)
FIXED_FACULTY_CELLS = {}      # (day, slot) -> set of faculty tokens
FIXED_ROOM_CELLS = {}         # (day, slot) -> set of room tokens

for event in FIXED_EVENTS:
    for section in event["sections"]:
        for k in range(event["span"]):
            cell = (event["day"], event["slot"] + k)
            if event["blocks_section"]:
                FIXED_CELLS_BY_SECTION.setdefault(section, set()).add(cell)

            if event["blocks_faculty"]:
                for faculty in event["faculties"]:
                    FIXED_FACULTY_CELLS.setdefault(cell, set()).add(faculty)

            if event["blocks_room"]:
                for room in event["rooms"]:
                    FIXED_ROOM_CELLS.setdefault(cell, set()).add(room)


def random_gene(session):
    day = random.randrange(len(DAYS))
    if session["type"] == "lab":
        start_slot = random.randrange(SLOTS_PER_DAY - LAB_BLOCK_SLOTS + 1)
        room = random.choice(ROOMS_LAB)
    else:
        start_slot = random.randrange(SLOTS_PER_DAY)
        room = HOME_ROOM.get(session["section"], random.choice(ROOMS_THEORY))
    return {"day": day, "slot": start_slot, "room": room}


def random_chromosome():
    return [random_gene(s) for s in SESSIONS]


def init_population(pop_size):
    return [random_chromosome() for _ in range(pop_size)]


# ==============================================================================
# 4. FITNESS FUNCTION
# ==============================================================================

def occupied_slots(gene, session):
    n = LAB_BLOCK_SLOTS if session["type"] == "lab" else 1
    return {(gene["day"], gene["slot"] + k) for k in range(n)}


def faculty_tokens(faculty):
    """Return faculty codes as separate tokens when data contains '/'."""
    return {token.strip() for token in str(faculty).split("/") if token.strip() and token.strip() != "-"}


def compute_penalty(chromosome):
    penalty = 0
    HARD = 10
    SOFT = 1

    faculty_usage = {}
    room_usage = {}
    section_usage = {}

    for gene, session in zip(chromosome, SESSIONS):
        if session["type"] == "lab" and gene["slot"] + LAB_BLOCK_SLOTS > SLOTS_PER_DAY:
            penalty += HARD
            continue

        cells = occupied_slots(gene, session)
        session_faculty = faculty_tokens(session["faculty"])

        # Clash against fixed events.
        for cell in cells:
            # The section cannot have another class at the same time.
            if cell in FIXED_CELLS_BY_SECTION.get(session["section"], set()):
                penalty += HARD

            # Only fixed events that actually consume faculty block faculty.
            fixed_faculty = FIXED_FACULTY_CELLS.get(cell, set())
            if session_faculty & fixed_faculty:
                penalty += HARD

            # OE has no rooms, so it does not appear in FIXED_ROOM_CELLS.
            if gene["room"] in FIXED_ROOM_CELLS.get(cell, set()):
                penalty += HARD

        # Record GA-created resource usage.
        for cell in cells:
            for faculty in session_faculty:
                faculty_usage.setdefault(cell, []).append(faculty)
            room_usage.setdefault(cell, []).append(gene["room"])
            section_usage.setdefault(cell, []).append(session["section"])

    # GA-vs-GA conflicts.
    for cell, flist in faculty_usage.items():
        if len(flist) > len(set(flist)):
            penalty += HARD * (len(flist) - len(set(flist)))

    for cell, rlist in room_usage.items():
        if len(rlist) > len(set(rlist)):
            penalty += HARD * (len(rlist) - len(set(rlist)))

    for cell, slist in section_usage.items():
        if len(slist) > len(set(slist)):
            penalty += HARD * (len(slist) - len(set(slist)))

    # Soft: minimize idle gaps per section per day.
    # Fixed MDM/OE/Project/T&P events count as occupied; LeetCode does not exist
    # here because it is optional and must not constrain the GA.
    section_day_slots = {}

    for gene, session in zip(chromosome, SESSIONS):
        key = (session["section"], gene["day"])
        for cell in occupied_slots(gene, session):
            section_day_slots.setdefault(key, set()).add(cell[1])

    for section, cells in FIXED_CELLS_BY_SECTION.items():
        for day, slot in cells:
            section_day_slots.setdefault((section, day), set()).add(slot)

    for key, slots in section_day_slots.items():
        if len(slots) > 1:
            span = max(slots) - min(slots) + 1
            gaps = span - len(slots)
            penalty += SOFT * gaps

    return penalty


def fitness(chromosome):
    return 1.0 / (1.0 + compute_penalty(chromosome))


# ==============================================================================
# 5. GA OPERATORS
# ==============================================================================

def tournament_selection(pop, fits, k=3):
    contenders = random.sample(range(len(pop)), k)
    best = max(contenders, key=lambda i: fits[i])
    return pop[best]


def crossover(parent1, parent2, rate=0.8):
    if random.random() > rate:
        return copy.deepcopy(parent1), copy.deepcopy(parent2)
    point = random.randrange(1, N_GENES)
    child1 = parent1[:point] + parent2[point:]
    child2 = parent2[:point] + parent1[point:]
    return child1, child2


def mutate(chromosome, rate=0.05):
    for i in range(N_GENES):
        if random.random() < rate:
            chromosome[i] = random_gene(SESSIONS[i])
    return chromosome


# ==============================================================================
# 6. MAIN GA LOOP
# ==============================================================================

def run_ga(pop_size=300, generations=2000, elitism=8, patience=200, verbose=True):
    population = init_population(pop_size)
    best_ever = None
    best_ever_fit = -1
    no_improve = 0
    history = []

    for gen in range(generations):
        fits = [fitness(c) for c in population]

        gen_best_idx = max(range(pop_size), key=lambda i: fits[i])
        gen_best_fit = fits[gen_best_idx]
        history.append(gen_best_fit)

        if gen_best_fit > best_ever_fit:
            best_ever_fit = gen_best_fit
            best_ever = copy.deepcopy(population[gen_best_idx])
            no_improve = 0
        else:
            no_improve += 1

        if verbose and gen % 20 == 0:
            print(f"Gen {gen:4d} | best fitness = {gen_best_fit:.4f} | "
                  f"penalty = {compute_penalty(population[gen_best_idx])}")

        if compute_penalty(best_ever) == 0:
            print(f"\n✅ Zero-conflict timetable found at generation {gen}.")
            break
        if no_improve >= patience:
            print(f"\n⏹ No improvement for {patience} generations — stopping early at gen {gen}.")
            break

        ranked = sorted(range(pop_size), key=lambda i: fits[i], reverse=True)
        next_pop = [copy.deepcopy(population[i]) for i in ranked[:elitism]]

        while len(next_pop) < pop_size:
            p1 = tournament_selection(population, fits)
            p2 = tournament_selection(population, fits)
            c1, c2 = crossover(p1, p2)
            mutate(c1)
            mutate(c2)
            next_pop.append(c1)
            if len(next_pop) < pop_size:
                next_pop.append(c2)

        population = next_pop

    return best_ever, best_ever_fit, history


def print_timetable(chromosome, section_filter=None):
    grid = {}

    # Print fixed events first.
    for event in FIXED_EVENTS:
        for section in event["sections"]:
            if section_filter and section != section_filter:
                continue
            for k in range(event["span"]):
                grid[(event["day"], event["slot"] + k)] = f"*{event['label']}*"

    # Print GA-generated sessions.
    for gene, session in zip(chromosome, SESSIONS):
        if section_filter and session["section"] != section_filter:
            continue
        n = LAB_BLOCK_SLOTS if session["type"] == "lab" else 1
        label = f"{session['code']}({session['faculty']},{gene['room']})"
        for k in range(n):
            grid[(gene["day"], gene["slot"] + k)] = label

    print(f"\n--- Timetable: {section_filter or 'ALL SECTIONS'} ---")
    header = "Slot".ljust(6) + "".join(day.ljust(24) for day in DAYS)
    print(header)
    for slot in range(SLOTS_PER_DAY):
        row = str(slot).ljust(6)
        for day in range(len(DAYS)):
            row += grid.get((day, slot), "-").ljust(24)
        print(row)


if __name__ == "__main__":
    import time
    print(f"Total sessions to schedule (chromosome length): {N_GENES}")
    print("Running GA...\n")

    t0 = time.time()
    best, best_fit, history = run_ga(pop_size=300, generations=2000, elitism=8, patience=200)
    t1 = time.time()

    print(f"\nRuntime: {t1 - t0:.2f} seconds")
    print(f"Best fitness: {best_fit:.4f}  |  Remaining penalty: {compute_penalty(best)}")

    for section in SECTIONS:
        print_timetable(best, section)

    # export to CSV
    import csv as _csv
    with open("timetable_output.csv", "w", newline="") as f:
        writer = _csv.writer(f)
        writer.writerow(["Section", "Day", "Slot_Start", "Slot_Count", "Subject_Code",
                          "Subject_Name", "Faculty_Code", "Room_Code", "Type"])
        for event in FIXED_EVENTS:
            for section in event["sections"]:
                rooms = "/".join(event["rooms"]) if event["rooms"] else "ONLINE/NONE"
                faculties = "/".join(event["faculties"]) if event["faculties"] else "-"
                writer.writerow([section, DAYS[event["day"]], event["slot"], event["span"],
                                 event["label"], event["label"], faculties, rooms, "Fixed"])
        for gene, session in zip(best, SESSIONS):
            n = LAB_BLOCK_SLOTS if session["type"] == "lab" else 1
            writer.writerow([session["section"], DAYS[gene["day"]], gene["slot"], n,
                              session["code"], session["name"], session["faculty"],
                              gene["room"], session["type"].capitalize()])

    with open("subjects_export.csv", "w", newline="") as f:
        writer = _csv.writer(f)
        writer.writerow(["Section", "Subject_Code", "Subject_Name", "Type", "Faculty_Code", "Sessions_Per_Week"])
        for section, data in SECTIONS.items():
            for subj in data["theory"] + data["lab"]:
                t = "Theory" if subj in data["theory"] else "Lab"
                writer.writerow([section, subj["code"], subj["name"], t, subj["faculty"], subj["sessions_per_week"]])

    print("\nExported timetable_output.csv and subjects_export.csv.")

