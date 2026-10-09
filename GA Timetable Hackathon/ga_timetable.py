"""
GA-based Timetable Scheduler — Reference Implementation
Dept: CSE (AIML) | Semesters: 3, 5, 7 (Odd Sem)

This is a STARTER / REFERENCE implementation. Students should:
  1. Replace the DUMMY DATA below with actual department data (from master timetable)
  2. Understand and be ready to explain every part of encoding / fitness / operators
  3. Extend it (see "Extension Ideas" at the bottom) rather than submit this as-is

-------------------------------------------------------------------------------
PROBLEM ENCODING
-------------------------------------------------------------------------------
- A "class session" = one lecture/lab slot that needs to be scheduled.
  Each theory subject needs N sessions/week, each lab needs M (usually 1 block of 2-3 hrs).
- DAYS = 5 (Mon-Fri), SLOTS_PER_DAY = 7  -> 35 slots/week per room/section.
- CHROMOSOME = one full timetable = a list, one gene per class-session-to-be-scheduled.
  Each gene = (day, slot, room)   [faculty & subject & section are fixed per session]
- POPULATION = a list of chromosomes (candidate timetables).

FITNESS FUNCTION (penalty-based; lower penalty = higher fitness)
  Hard constraints (heavily penalized):
    - Same faculty teaching two sessions at the same (day, slot)
    - Same room used by two sessions at the same (day, slot)
    - Same section (semester/section) having two sessions at the same (day, slot)
    - Lab session not fitting within allowed contiguous lab slots
  Soft constraints (lightly penalized):
    - Faculty teaching more than 1 subject back-to-back with no gap across sections (optional)
    - Idle gaps in a section's day
    - Uneven load across the week

  fitness = 1 / (1 + total_penalty)
"""

import random
import copy

random.seed(42)  # remove/change this once students start experimenting

# ==============================================================================
# 1. DUMMY DEPARTMENT DATA  (STUDENTS: replace with real data from master timetable)
# ==============================================================================

DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri"]
SLOTS_PER_DAY = 7          # e.g. 9-10,10-11,11-12,12-1(lunch skip),1-2,2-3,3-4,4-5
LAB_BLOCK_SLOTS = 3        # a lab occupies 3 contiguous slots

ROOMS_THEORY = ["R101", "R102", "R103"]
ROOMS_LAB = ["LAB1", "LAB2"]

# Each semester/section has its own subjects, each subject has a faculty and
# a weekly session count. THIS IS DUMMY DATA — replace with your dept's actual list.
SECTIONS = {
    "SEM3": {
        "theory": [
            {"code": "T31", "name": "Data Structures",          "faculty": "F1",  "sessions_per_week": 4},
            {"code": "T32", "name": "Discrete Mathematics",     "faculty": "F2",  "sessions_per_week": 3},
            {"code": "T33", "name": "Digital Logic Design",     "faculty": "F3",  "sessions_per_week": 3},
            {"code": "T34", "name": "OOP with Java",            "faculty": "F4",  "sessions_per_week": 3},
            {"code": "T35", "name": "Probability & Statistics", "faculty": "F5",  "sessions_per_week": 3},
        ],
        "lab": [
            {"code": "L31", "name": "DS Lab",   "faculty": "F1",  "sessions_per_week": 1},
            {"code": "L32", "name": "OOP Lab",  "faculty": "F4",  "sessions_per_week": 1},
            {"code": "L33", "name": "DLD Lab",  "faculty": "F3",  "sessions_per_week": 1},
        ],
    },
    "SEM5": {
        "theory": [
            {"code": "T51", "name": "Machine Learning",         "faculty": "F6",  "sessions_per_week": 4},
            {"code": "T52", "name": "Computer Networks",        "faculty": "F7",  "sessions_per_week": 3},
            {"code": "T53", "name": "DBMS",                     "faculty": "F8",  "sessions_per_week": 3},
            {"code": "T54", "name": "Operating Systems",        "faculty": "F9",  "sessions_per_week": 3},
            {"code": "T55", "name": "Automata Theory",          "faculty": "F10", "sessions_per_week": 3},
        ],
        "lab": [
            {"code": "L51", "name": "ML Lab",    "faculty": "F6",  "sessions_per_week": 1},
            {"code": "L52", "name": "DBMS Lab",  "faculty": "F8",  "sessions_per_week": 1},
            {"code": "L53", "name": "CN Lab",    "faculty": "F7",  "sessions_per_week": 1},
        ],
    },
    "SEM7": {
        "theory": [
            {"code": "T71", "name": "Deep Learning",            "faculty": "F11", "sessions_per_week": 4},
            {"code": "T72", "name": "NLP",                      "faculty": "F12", "sessions_per_week": 3},
            {"code": "T73", "name": "Big Data Analytics",       "faculty": "F13", "sessions_per_week": 3},
            {"code": "T74", "name": "Cloud Computing",          "faculty": "F14", "sessions_per_week": 3},
            {"code": "T75", "name": "Elective-III",             "faculty": "F15", "sessions_per_week": 3},
        ],
        "lab": [
            {"code": "L71", "name": "DL Lab",   "faculty": "F11", "sessions_per_week": 1},
            {"code": "L72", "name": "NLP Lab",  "faculty": "F12", "sessions_per_week": 1},
            {"code": "L73", "name": "BDA Lab",  "faculty": "F13", "sessions_per_week": 1},
        ],
    },
}

# ==============================================================================
# 2. BUILD THE LIST OF SESSIONS TO SCHEDULE (this becomes the chromosome length)
# ==============================================================================

def build_sessions():
    """Flatten SECTIONS into a list of individual class-sessions that need a
    (day, slot, room) assigned. This list defines chromosome length & gene meaning."""
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


# ==============================================================================
# 3. CHROMOSOME / POPULATION
# ==============================================================================

def random_gene(session):
    """A gene = (day_idx, start_slot_idx, room). Lab needs LAB_BLOCK_SLOTS contiguous slots."""
    day = random.randrange(len(DAYS))
    if session["type"] == "lab":
        start_slot = random.randrange(SLOTS_PER_DAY - LAB_BLOCK_SLOTS + 1)
        room = random.choice(ROOMS_LAB)
    else:
        start_slot = random.randrange(SLOTS_PER_DAY)
        room = random.choice(ROOMS_THEORY)
    return {"day": day, "slot": start_slot, "room": room}


def random_chromosome():
    return [random_gene(s) for s in SESSIONS]


def init_population(pop_size):
    return [random_chromosome() for _ in range(pop_size)]


# ==============================================================================
# 4. FITNESS FUNCTION
# ==============================================================================

def occupied_slots(gene, session):
    """Returns the set of (day, slot) cells this gene occupies."""
    n = LAB_BLOCK_SLOTS if session["type"] == "lab" else 1
    return {(gene["day"], gene["slot"] + k) for k in range(n)}


def compute_penalty(chromosome):
    penalty = 0
    HARD = 10
    SOFT = 1

    faculty_usage = {}   # (day,slot) -> list of faculty
    room_usage = {}       # (day,slot) -> list of rooms
    section_usage = {}    # (day,slot) -> list of sections

    for gene, session in zip(chromosome, SESSIONS):
        # lab overflow check (hard)
        if session["type"] == "lab" and gene["slot"] + LAB_BLOCK_SLOTS > SLOTS_PER_DAY:
            penalty += HARD
            continue

        cells = occupied_slots(gene, session)
        for cell in cells:
            faculty_usage.setdefault(cell, []).append(session["faculty"])
            room_usage.setdefault(cell, []).append(gene["room"])
            section_usage.setdefault(cell, []).append(session["section"])

    for cell, flist in faculty_usage.items():
        if len(flist) > len(set(flist)):
            penalty += HARD * (len(flist) - len(set(flist)))
    for cell, rlist in room_usage.items():
        if len(rlist) > len(set(rlist)):
            penalty += HARD * (len(rlist) - len(set(rlist)))
    for cell, slist in section_usage.items():
        if len(slist) > len(set(slist)):
            penalty += HARD * (len(slist) - len(set(slist)))

    # --- soft constraint example: minimize idle gaps per section per day ---
    section_day_slots = {}
    for gene, session in zip(chromosome, SESSIONS):
        key = (session["section"], gene["day"])
        for cell in occupied_slots(gene, session):
            section_day_slots.setdefault(key, set()).add(cell[1])

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

def run_ga(pop_size=150, generations=300, elitism=4, patience=40, verbose=True):
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

        # --- build next generation ---
        ranked = sorted(range(pop_size), key=lambda i: fits[i], reverse=True)
        next_pop = [copy.deepcopy(population[i]) for i in ranked[:elitism]]  # elitism

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
    for gene, session in zip(chromosome, SESSIONS):
        if section_filter and session["section"] != section_filter:
            continue
        n = LAB_BLOCK_SLOTS if session["type"] == "lab" else 1
        label = f"{session['code']}({session['faculty']},{gene['room']})"
        for k in range(n):
            grid[(gene["day"], gene["slot"] + k)] = label

    print(f"\n--- Timetable: {section_filter or 'ALL SECTIONS'} ---")
    header = "Slot".ljust(6) + "".join(d.ljust(22) for d in DAYS)
    print(header)
    for slot in range(SLOTS_PER_DAY):
        row = str(slot).ljust(6)
        for day in range(len(DAYS)):
            row += grid.get((day, slot), "-").ljust(22)
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

    print_timetable(best, "SEM3")
    print_timetable(best, "SEM5")
    print_timetable(best, "SEM7")

    # export to CSV in the hackathon submission format, for scorer testing
    import csv as _csv
    with open("timetable_output.csv", "w", newline="") as f:
        writer = _csv.writer(f)
        writer.writerow(["Section", "Day", "Slot_Start", "Slot_Count", "Subject_Code",
                          "Subject_Name", "Faculty_Code", "Room_Code", "Type"])
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

    print("\nExported timetable_output.csv and subjects_export.csv for scorer testing.")

# ==============================================================================
# EXTENSION IDEAS FOR STUDENTS (pick 2-3, don't just submit the base version)
# ==============================================================================
# 1. Add faculty unavailability (e.g., F3 not available Fri afternoon) as a hard constraint.
# 2. Add room capacity vs section strength as a constraint.
# 3. Add "no more than 2 consecutive theory sessions" as a soft constraint.
# 4. Compare crossover strategies: single-point vs uniform vs order crossover.
# 5. Compare selection strategies: tournament vs roulette wheel vs rank selection.
# 6. Plot fitness-vs-generation curve (convergence graph) using matplotlib.
# 7. Run 10 trials with different random seeds, report mean/std of generations-to-converge.
# 8. Add multi-objective handling: separate hard-violation count vs soft-penalty score,
#    and only compare soft penalty when hard violations are tied (lexicographic fitness).
# 9. Export best timetable to Excel/CSV per section.
