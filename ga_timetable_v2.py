"""
Sem 3 (SY), Sem 5 (TY), Sem 7 (BTech)

Information about time table
Week      : Tue..Sat, 7 one-hour slots/day
            0: 9-10   1: 10-11   [break]   2: 11.15-12.15   3: 12.15-1.15   [lunch]
            4: 2-3    5: 3-4     6: 4-5
Batches   : every division has 2 batch GROUPS (e.g. A1,A2 and A3,A4).
Theory    : 1 hour, whole division (both groups). Home classroom.
Lab block : 2 hours. Two groups run in PARALLEL with different subjects/labs
            (e.g. A1,A2 -> SST in LAB2 while A3,A4 -> ADS in LAB3).
            A 2-hour block can only start at slot 0, 2, 4 or 5, because it must
            not straddle the 11-11.15 break or the 1.15-2 lunch.
1-hr batch: CEE / MP-I(Vajreshwari) type sessions (1 hour, one or two groups).
Fixed     : MDM, PE, OE, T&P, Project Phase-I are already combined across
            divisions in the PDF, so they are FIXED. The GA only schedules
            around them (their faculty / rooms / divisions are blocked).
            OE is online -> blocks the division and nothing else.

HARD constraints (must be 0):
  * a batch group has two things at the same time
  * a faculty member has two things at the same time
  * a classroom is used twice at the same time (home rooms, fixed rooms)
  * more than 6 labs needed at once
  * more sem-7 'pool' classes than free classrooms at once
SOFT constraints (minimised): idle gaps, same theory subject twice a day,
  theory in the last hour.
"""
import random, csv, sys, time
from collections import defaultdict

# 0. BASIC CONSTANTS

DAYS = ["Tue", "Wed", "Thu", "Fri", "Sat"]
N_DAYS, N_SLOTS = 5, 7
SLOT_LABELS = ["9.00-10.00", "10.00-11.00", "11.15-12.15", "12.15-1.15",
               "2.00-3.00", "3.00-4.00", "4.00-5.00"]
LAB_STARTS = (0, 2, 4, 5)            # legal start slots of a 2-hour block
LABS = [f"LAB{i}" for i in range(1, 7)]
CLASSROOMS = ["CSAMCR01", "CSAMCR02", "CSAMCR03", "CSAMCR04",
              "CSAMCR05", "CSAMCR06", "CSDSCR01"]
LAB_CAP = len(LABS)

HARD_W = 1000
W_GAP, W_SAME_DAY, W_LAST_HOUR = 2, 3, 1      # soft weights (tune freely)


# 1. DATA  

# home = fixed classroom for theory. for sem 7 B and ds there was no home so they take whichever classroom is free ("pool").
DIV = {
    "SEM3-A": dict(home="CSAMCR06", groups=("A1,A2", "A3,A4")),
    "SEM3-B": dict(home="CSAMCR02", groups=("B1,B2", "B3,B4")),
    "SEM3-C": dict(home="CSDSCR01", groups=("C1,C2", "C3,C4")),
    "SEM5-A": dict(home="CSAMCR03", groups=("A1,A2", "A3,A4")),
    "SEM5-B": dict(home="CSAMCR04", groups=("B1,B2", "B3,B4")),
    "SEM5-C": dict(home="CSAMCR05", groups=("C1,C2", "C3,C4")),
    "SEM7-A": dict(home="CSAMCR01", groups=("A1,A2", "A3,A4")),
    "SEM7-B": dict(home=None,       groups=("B1,B2", "B3,B4")),
    "SEM7-DS": dict(home=None,      groups=("D1,D2", "D3,D4")),
}

EVENTS = []   # things the GA must place


def _f(x):
    return [t for t in x.split("/")] if isinstance(x, str) else list(x)


def theory(div, code, fac, n):
    room = "home" if DIV[div]["home"] else "pool"
    for _ in range(n):
        EVENTS.append(dict(div=div, dur=1, kind="theory", parts=[
            dict(groups=(0, 1), code=code, fac=_f(fac), room=room)]))


def lab_block(div, g1, g2):
    """2-hour block, two groups in parallel. g = (code, faculty)."""
    EVENTS.append(dict(div=div, dur=2, kind="lab", parts=[
        dict(groups=(0,), code=g1[0], fac=_f(g1[1]), room="lab"),
        dict(groups=(1,), code=g2[0], fac=_f(g2[1]), room="lab")]))


def short_block(div, g1, g2, room="lab"):
    """1-hour block, two groups in parallel (CEE / EE)."""
    EVENTS.append(dict(div=div, dur=1, kind="lab", parts=[
        dict(groups=(0,), code=g1[0], fac=_f(g1[1]), room=room),
        dict(groups=(1,), code=g2[0], fac=_f(g2[1]), room=room)]))


def single(div, grp, code, fac, room="home"):
    """1-hour session for ONE batch group."""
    EVENTS.append(dict(div=div, dur=1, kind="batch", parts=[
        dict(groups=(grp,), code=code, fac=_f(fac), room=room)]))


# ---------------------------- SEM 3 (SY) -------------------------------------
# G1 = x1,x2   G2 = x3,x4      
d = "SEM3-A"
for c, f, n in [("ADS", "SS", 3), ("DMGT", "SGB", 3), ("LA", "SHD", 4),
                ("DBMS", "SSS", 4), ("PAIML", "SM", 3), ("CI", "MeghaThombare", 2)]:
    theory(d, c, f, n)
lab_block(d, ("SST", "NS"),  ("ADS", "SS"))
lab_block(d, ("ADS", "SS"),  ("SST", "NS"))
lab_block(d, ("DBMS", "SSS"), ("MP-I", "NB"))
lab_block(d, ("MP-I", "AC"), ("DBMS", "SSS"))
lab_block(d, ("MP-I", "AC"), ("MP-I", "NB"))
short_block(d, ("CEE", "SK"), ("EE", "RohitD"))

d = "SEM3-B"
for c, f, n in [("ADS", "SS", 3), ("DMGT", "SC", 4), ("LA", "MUM", 4),
                ("DBMS", "PSK", 4), ("PAIML", "Vajreshwari", 2), ("CI", "MeghaThombare", 2)]:
    theory(d, c, f, n)
lab_block(d, ("ADS", "SS"),   ("SST", "SL"))
lab_block(d, ("SST", "SL"),   ("MP-I", "SC"))
lab_block(d, ("MP-I", "DDK"), ("DBMS", "PSK"))
lab_block(d, ("DBMS", "PSK"), ("ADS", "SS"))
lab_block(d, ("MP-I", "DDK"), ("MP-I", "SC"))
short_block(d, ("CEE", "TG"), ("EE", "RohitD"))

d = "SEM3-C"
for c, f, n in [("ADS", "KVJ", 3), ("DMGT", "SGB", 3), ("LA", "JJB", 4),
                ("DBMS", "AK", 3), ("PAIML", "Vajreshwari", 2), ("CI", "MeghaThombare", 2)]:
    theory(d, c, f, n)
lab_block(d, ("ADS", "KVJ"),   ("DBMS", "AK"))
lab_block(d, ("DBMS", "AK"),   ("ADS", "KVJ"))
lab_block(d, ("SST", "Kajesh"), ("MP-I", "SGupta"))
lab_block(d, ("MP-I", "SGupta"), ("SST", "Kajesh"))
for g in (0, 1):                       # same faculty for both groups -> separate hours
    single(d, g, "CEE", "RohitD", room="home")        # PDF: in CSDSCR01
    single(d, g, "MP-I", "Vajreshwari", room="home")  # PDF: in CSDSCR01

# ---------------------------- SEM 5 (TY) -------------------------------------
# OE-I online, PE-1 / MDM-3 combined -> all FIXED below.
d = "SEM5-A"
for c, f, n in [("EDA", "SM", 3), ("ML", "VSP", 3), ("COOS", "AC", 2)]:
    theory(d, c, f, n)
lab_block(d, ("EDA", "SM"),  ("ML", "VSP"))
lab_block(d, ("ML", "VSP"),  ("APL", "NM"))
lab_block(d, ("APL", "NM"),  ("BCVS", "SK/TG"))
lab_block(d, ("BCVS", "SK/TG"), ("EDA", "SM"))
lab_block(d, ("MP-III", "KVJ"), ("MP-III", "SGB"))
lab_block(d, ("MP-III", "KVJ"), ("MP-III", "SGB"))

d = "SEM5-B"
for c, f, n in [("EDA", "SSS", 3), ("ML", "PSK", 3), ("COOS", "AC", 2)]:
    theory(d, c, f, n)
lab_block(d, ("ML", "RK"),   ("BCVS", "SK/TG"))
lab_block(d, ("EDA", "SSS"), ("APL", "NM"))
lab_block(d, ("BCVS", "SK/TG"), ("EDA", "SSS"))
lab_block(d, ("APL", "NM"),  ("ML", "RK"))
lab_block(d, ("MP-III", "RK"), ("MP-III", "Kajesh"))
lab_block(d, ("MP-III", "RK"), ("MP-III", "SM"))

d = "SEM5-C"
for c, f, n in [("EDA", "APB", 3), ("ML", "VAP", 3), ("COOS", "AC", 2)]:
    theory(d, c, f, n)
lab_block(d, ("MP-III", "NS"), ("APL", "NM"))
lab_block(d, ("BCVS", "SK/TG"), ("MP-III", "SL"))
lab_block(d, ("APL", "NM"),  ("ML", "VAP"))
lab_block(d, ("EDA", "APB"), ("BCVS", "SK/TG"))
lab_block(d, ("ML", "VAP"),  ("EDA", "APB"))
lab_block(d, ("MP-III", "NS"), ("MP-III", "SL"))     # PDF: CSAMCR05 (see notes)

# ---------------------------- SEM 7 (BTech) ----------------------------------
for d, cbcs, gen, mld in [("SEM7-A", "AK", "UPG", "VSP"),
                          ("SEM7-B", "AK", "RK", "SDJ"),
                          ("SEM7-DS", "APB", "VAP", "SDJ")]:
    theory(d, "CBCS", cbcs, 3)
    theory(d, "GenAI", gen, 3)
    theory(d, "MLDEVOPS", mld, 3)
    lab_block(d, ("GenAI", gen), ("MLDEVOPS", mld))
    lab_block(d, ("MLDEVOPS", mld), ("GenAI", gen))

# ------------------------------ FIXED EVENTS ---------------------------------
FIXED = []


def fixed(divs, day, start, dur, label, fac=(), rooms=()):
    FIXED.append(dict(divs=list(divs), day=DAYS.index(day), start=start, dur=dur,
                      label=label, fac=list(fac), rooms=list(rooms)))


SY = ["SEM3-A", "SEM3-B", "SEM3-C"]
TY = ["SEM5-A", "SEM5-B", "SEM5-C"]
BT = ["SEM7-A", "SEM7-B", "SEM7-DS"]

# Sem 3: MDM-I = 3 subjects -> 3 rooms
for dy in ("Tue", "Wed"):
    fixed(SY, dy, 0, 1, "MDM-I", ["NB", "DDK", "SGupta"],
          ["CSAMCR06", "CSDSCR01", "CSAMCR02"])
# Sem 3: T&P (2 h) - one day (Thu), separate time per division, home room
fixed(["SEM3-A"], "Thu", 0, 2, "T&P", [], ["CSAMCR06"])
fixed(["SEM3-B"], "Thu", 2, 2, "T&P", [], ["CSAMCR02"])
fixed(["SEM3-C"], "Thu", 4, 2, "T&P", [], ["CSDSCR01"])

# Sem 5: MDM-3 (3 subjects, 3 rooms), PE-1 (3 subjects, 3 rooms), OE-I (online)
for dy, s in (("Wed", 0), ("Thu", 0), ("Fri", 3)):
    fixed(TY, dy, s, 1, "MDM-3", ["SL", "KVJ", "SC"], ["CSAMCR02", "CSAMCR03", "CSAMCR04"])
for dy, s in (("Tue", 6), ("Wed", 6), ("Fri", 4)):
    fixed(TY, dy, s, 1, "PE-1", ["NS", "NB", "DDK"], ["CSAMCR02", "CSAMCR03", "CSAMCR04"])
for dy, s in (("Tue", 2), ("Wed", 2), ("Fri", 2)):
    fixed(TY, dy, s, 1, "OE-I (online)")
# Sem 5: T&P (2 h) - one day (Sat)
fixed(["SEM5-A"], "Sat", 0, 2, "T&P", [], ["CSAMCR03"])
fixed(["SEM5-B"], "Sat", 2, 2, "T&P", [], ["CSAMCR04"])
fixed(["SEM5-C"], "Sat", 4, 2, "T&P", [], ["CSAMCR05"])

# Sem 7: MDM-V (2 subjects, 2 rooms - rooms differ per slot in the PDF)
fixed(BT, "Tue", 0, 1, "MDM-V", ["SGB", "Kajesh"], ["CSAMCR01", "CSAMCR03"])
fixed(BT, "Thu", 2, 1, "MDM-V", ["SGB", "Kajesh"], ["CSAMCR01", "CSAMCR06"])
fixed(BT, "Wed", 5, 1, "MDM-V", ["SGB", "Kajesh"], ["CSAMCR01", "CSDSCR01"])
# Sem 7: PE-III (3 subjects, 3 rooms)
fixed(BT, "Tue", 4, 1, "PE-III", ["Vajreshwari", "SGupta", "DDK"], ["CSAMCR01", "CSAMCR04", "CSAMCR05"])
fixed(BT, "Wed", 4, 1, "PE-III", ["Vajreshwari", "SGupta", "DDK"], ["CSAMCR01", "CSAMCR04", "CSAMCR05"])
fixed(BT, "Thu", 4, 1, "PE-III", ["Vajreshwari", "SGupta", "DDK"], ["CSAMCR01", "CSAMCR03", "CSAMCR04"])
# Sem 7: OE-III (online)
for dy in ("Tue", "Wed"):
    fixed(BT, dy, 2, 1, "OE-III (online)")
# Sem 7: Project Phase-I (no room / faculty given in PDF)
fixed(["SEM7-A"], "Thu", 5, 2, "Project Phase-I")
fixed(["SEM7-B"], "Fri", 5, 2, "Project Phase-I")
fixed(["SEM7-DS"], "Wed", 0, 2, "Project Phase-I")
fixed(BT, "Sat", 0, 6, "Project Phase-I")          # Sat 9.00 - 4.00


# 2. PRE-PROCESSING

def cell(day, slot):
    return day * N_SLOTS + slot


N = len(EVENTS)
for i, ev in enumerate(EVENTS):
    ev["id"] = i
    home = DIV[ev["div"]]["home"]
    ev["gkeys"] = [(ev["div"], g) for p in ev["parts"] for g in p["groups"]]
    ev["facs"] = [f for p in ev["parts"] for f in p["fac"]]
    ev["spec_rooms"] = [home for p in ev["parts"] if p["room"] == "home"]
    ev["n_lab"] = sum(1 for p in ev["parts"] if p["room"] == "lab")
    ev["n_pool"] = sum(1 for p in ev["parts"] if p["room"] == "pool")
    starts = LAB_STARTS if ev["dur"] == 2 else range(N_SLOTS)
    ev["valid"] = [(dy, s) for dy in range(N_DAYS) for s in starts]

EVENTS_OF = defaultdict(list)
for ev in EVENTS:
    EVENTS_OF[ev["div"]].append(ev["id"])

FIXED_SLOTS = defaultdict(set)         # (div, day) -> slots busy because of fixed events
for fx in FIXED:
    for dv in fx["divs"]:
        for k in range(fx["dur"]):
            FIXED_SLOTS[(dv, fx["day"])].add(fx["start"] + k)

POOL_N = len(CLASSROOMS)
POOLSET = set(CLASSROOMS)


# 3. STATE : incremental hard-conflict counter

class State:
    def __init__(self):
        self.g = defaultdict(int)
        self.f = defaultdict(int)
        self.r = defaultdict(int)
        self.lab = defaultdict(int)
        self.pool = defaultdict(int)
        self.poolspec = defaultdict(int)
        self.H = 0
        for fx in FIXED:                       # preload fixed events
            for k in range(fx["dur"]):
                c = cell(fx["day"], fx["start"] + k)
                for dv in fx["divs"]:
                    for g in (0, 1):
                        self._bump(self.g, ((dv, g), c), 1)
                for f in fx["fac"]:
                    self._bump(self.f, (f, c), 1)
                for r in fx["rooms"]:
                    self._room(r, c, 1)
        self.base_H = self.H                   

    @staticmethod
    def _bump(dct, key, sign):
        c = dct[key]
        dct[key] = c + sign
        if sign > 0:
            return 1 if c >= 1 else 0
        return -1 if c >= 2 else 0

    def _pe(self, c):
        return max(0, self.pool[c] - (POOL_N - self.poolspec[c]))

    def _room(self, room, c, sign):
        old = self._pe(c)
        h = self._bump(self.r, (room, c), sign)
        if room in POOLSET:
            n = self.r[(room, c)]
            if sign > 0 and n == 1:
                self.poolspec[c] += 1
            elif sign < 0 and n == 0:
                self.poolspec[c] -= 1
        self.H += h + (self._pe(c) - old)

    def apply(self, ev, day, start, sign):
        for k in range(ev["dur"]):
            c = cell(day, start + k)
            for gk in ev["gkeys"]:
                self.H += self._bump(self.g, (gk, c), sign)
            for f in ev["facs"]:
                self.H += self._bump(self.f, (f, c), sign)
            for r in ev["spec_rooms"]:
                self._room(r, c, sign)
            if ev["n_lab"]:
                d0 = self.lab[c]
                self.lab[c] = d0 + sign * ev["n_lab"]
                self.H += max(0, self.lab[c] - LAB_CAP) - max(0, d0 - LAB_CAP)
            if ev["n_pool"]:
                old = self._pe(c)
                self.pool[c] += sign * ev["n_pool"]
                self.H += self._pe(c) - old

    def conflicted(self, ev, day, start):
        for k in range(ev["dur"]):
            c = cell(day, start + k)
            for gk in ev["gkeys"]:
                if self.g[(gk, c)] > 1:
                    return True
            for f in ev["facs"]:
                if self.f[(f, c)] > 1:
                    return True
            for r in ev["spec_rooms"]:
                if self.r[(r, c)] > 1:
                    return True
            if ev["n_lab"] and self.lab[c] > LAB_CAP:
                return True
            if ev["n_pool"] and self._pe(c) > 0:
                return True
        return False


def build_state(pos):
    st = State()
    for ev, (dy, s) in zip(EVENTS, pos):
        st.apply(ev, dy, s, 1)
    return st


# 4. SOFT COST

def soft_division(div, pos):
    cost = 0
    occ = {(g, dy): set(FIXED_SLOTS.get((div, dy), ())) for g in (0, 1) for dy in range(N_DAYS)}
    seen = defaultdict(int)
    for i in EVENTS_OF[div]:
        ev = EVENTS[i]
        dy, s = pos[i]
        for p in ev["parts"]:
            for g in p["groups"]:
                for k in range(ev["dur"]):
                    occ[(g, dy)].add(s + k)
        if ev["kind"] == "theory":
            seen[(ev["parts"][0]["code"], dy)] += 1
            if s == N_SLOTS - 1:
                cost += W_LAST_HOUR
    for n in seen.values():
        if n > 1:
            cost += W_SAME_DAY * (n - 1)
    for sl in occ.values():
        if len(sl) > 1:
            cost += W_GAP * ((max(sl) - min(sl) + 1) - len(sl))
    return cost


def soft_total(pos):
    return sum(soft_division(dv, pos) for dv in DIV)


def total_penalty(pos, st=None):
    st = st or build_state(pos)
    return (st.H - st.base_H) * HARD_W + soft_total(pos), st


# 5. LOCAL SEARCH (min-conflicts) + GA

def local_search(st, pos, rng, iters=300, noise=0.08):
    for _ in range(iters):
        conf = [i for i in range(N) if st.conflicted(EVENTS[i], *pos[i])]
        if not conf:
            return
        i = rng.choice(conf)
        ev = EVENTS[i]
        st.apply(ev, *pos[i], -1)
        if rng.random() < noise:
            choice = rng.choice(ev["valid"])
        else:
            best, cands = None, []
            for p in ev["valid"]:
                st.apply(ev, *p, 1)
                h = st.H
                st.apply(ev, *p, -1)
                if best is None or h < best:
                    best, cands = h, [p]
                elif h == best:
                    cands.append(p)
            choice = rng.choice(cands)
        st.apply(ev, *choice, 1)
        pos[i] = choice


def polish(st, pos, rng, tries=4000):
    """Lower the soft cost without ever adding a hard conflict."""
    cur_soft = {dv: soft_division(dv, pos) for dv in DIV}
    for _ in range(tries):
        i = rng.randrange(N)
        ev = EVENTS[i]
        old = pos[i]
        new = rng.choice(ev["valid"])
        if new == old:
            continue
        h0 = st.H
        st.apply(ev, *old, -1)
        st.apply(ev, *new, 1)
        pos[i] = new
        s_new = soft_division(ev["div"], pos)
        if st.H <= h0 and s_new <= cur_soft[ev["div"]]:
            cur_soft[ev["div"]] = s_new
        else:
            st.apply(ev, *new, -1)
            st.apply(ev, *old, 1)
            pos[i] = old


def random_individual(rng):
    pos = [rng.choice(ev["valid"]) for ev in EVENTS]
    st = build_state(pos)
    local_search(st, pos, rng, iters=400)
    return pos


def crossover(p1, p2, rng):
    child = list(p1)
    for dv in DIV:                      # inherit whole divisions -> keeps packing intact
        if rng.random() < 0.5:
            for i in EVENTS_OF[dv]:
                child[i] = p2[i]
    return child


def mutate(pos, rng, rate=0.02):
    for i in range(N):
        if rng.random() < rate:
            pos[i] = rng.choice(EVENTS[i]["valid"])


def run_ga(seed=42, pop_size=20, generations=60, elitism=2, verbose=True):
    rng = random.Random(seed)
    pop = [random_individual(rng) for _ in range(pop_size)]
    best, best_pen = None, None
    for gen in range(generations):
        scored = []
        for ind in pop:
            pen, st = total_penalty(ind)
            scored.append((pen, ind, st))
        scored.sort(key=lambda t: t[0])
        if best_pen is None or scored[0][0] < best_pen:
            best_pen, best = scored[0][0], list(scored[0][1])
        hard = best_pen // HARD_W
        if verbose and gen % 5 == 0:
            print(f"gen {gen:3d} | best penalty {best_pen:6d}  (hard {hard}, soft {best_pen % HARD_W})")
        if hard == 0 and gen >= 8:      # a clash-free table exists; a few more gens tidy soft cost
            break
        nxt = [list(s[1]) for s in scored[:elitism]]
        while len(nxt) < pop_size:
            a = min(rng.sample(scored, 3), key=lambda t: t[0])[1]
            b = min(rng.sample(scored, 3), key=lambda t: t[0])[1]
            child = crossover(a, b, rng)
            mutate(child, rng)
            st = build_state(child)
            local_search(st, child, rng, iters=150)
            nxt.append(child)
        pop = nxt

    # final: repair + polish the best individual
    st = build_state(best)
    local_search(st, best, rng, iters=2000)
    if st.H - st.base_H == 0:
        polish(st, best, rng, tries=20000)
    pen, _ = total_penalty(best)
    return best, pen


# 6. ROOM DECODING (labs + pool classrooms) + INDEPENDENT VALIDATOR

def decode(pos):
    """Return {(event_id, part_idx): room}. Interval-colouring for labs."""
    rooms = {}
    used_spec = defaultdict(set)           # cell -> rooms taken by fixed/home use
    for fx in FIXED:
        for k in range(fx["dur"]):
            used_spec[cell(fx["day"], fx["start"] + k)].update(fx["rooms"])
    for ev, (dy, s) in zip(EVENTS, pos):
        for pi, p in enumerate(ev["parts"]):
            if p["room"] == "home":
                rooms[(ev["id"], pi)] = DIV[ev["div"]]["home"]
                for k in range(ev["dur"]):
                    used_spec[cell(dy, s + k)].add(DIV[ev["div"]]["home"])
    lab_busy = {l: set() for l in LABS}
    lab_parts = sorted(((pos[ev["id"]], ev["id"], pi, ev["dur"])
                        for ev in EVENTS for pi, p in enumerate(ev["parts"]) if p["room"] == "lab"),
                       key=lambda t: (t[0][0], t[0][1]))
    for (dy, s), i, pi, dur in lab_parts:
        cs = {cell(dy, s + k) for k in range(dur)}
        for l in LABS:
            if not (lab_busy[l] & cs):
                lab_busy[l] |= cs
                rooms[(i, pi)] = l
                break
        else:
            rooms[(i, pi)] = "NO-LAB"
    taken = defaultdict(set)
    for ev, (dy, s) in zip(EVENTS, pos):
        for pi, p in enumerate(ev["parts"]):
            if p["room"] == "pool":
                c = cell(dy, s)
                for r in CLASSROOMS:
                    if r not in used_spec[c] and r not in taken[c]:
                        taken[c].add(r)
                        rooms[(ev["id"], pi)] = r
                        break
                else:
                    rooms[(ev["id"], pi)] = "NO-ROOM"
    return rooms


def validate(pos, rooms):
    """Independent re-check on the final decoded timetable. Returns list of clashes."""
    use = defaultdict(list)       # (kind, key, cell) -> [labels]
    for fx in FIXED:
        for k in range(fx["dur"]):
            c = cell(fx["day"], fx["start"] + k)
            for dv in fx["divs"]:
                for g in (0, 1):
                    use[("group", (dv, g), c)].append("FIXED " + fx["label"])
            for f in fx["fac"]:
                use[("faculty", f, c)].append("FIXED " + fx["label"] + f" [{','.join(fx['divs'])}]")
            for r in fx["rooms"]:
                use[("room", r, c)].append("FIXED " + fx["label"])
    for ev, (dy, s) in zip(EVENTS, pos):
        for pi, p in enumerate(ev["parts"]):
            for k in range(ev["dur"]):
                c = cell(dy, s + k)
                for g in p["groups"]:
                    use[("group", (ev["div"], g), c)].append(f"{ev['div']} {p['code']}")
                for f in p["fac"]:
                    use[("faculty", f, c)].append(f"{ev['div']} {p['code']}")
                r = rooms.get((ev["id"], pi))
                if r:
                    use[("room", r, c)].append(f"{ev['div']} {p['code']}")
    return [(k, v) for k, v in use.items() if len(v) > 1]


def describe(c):
    return f"{DAYS[c // N_SLOTS]} {SLOT_LABELS[c % N_SLOTS]}"


# 7. OUTPUT

def build_grid(pos, rooms):
    """grid[div][(day, slot)] -> list of text lines"""
    grid = {dv: defaultdict(list) for dv in DIV}
    for fx in FIXED:
        for dv in fx["divs"]:
            for k in range(fx["dur"]):
                rm = "/".join(fx["rooms"]) if fx["rooms"] else ""
                txt = fx["label"] + (f" ({rm})" if rm else "")
                if fx["fac"]:
                    txt += " [" + "/".join(fx["fac"]) + "]"
                grid[dv][(fx["day"], fx["start"] + k)].append(("fixed", txt if k == 0 else "↳ " + fx["label"]))
    for ev, (dy, s) in zip(EVENTS, pos):
        for k in range(ev["dur"]):
            for pi, p in enumerate(ev["parts"]):
                r = rooms[(ev["id"], pi)]
                grp = "" if p["groups"] == (0, 1) else DIV[ev["div"]]["groups"][p["groups"][0]] + ": "
                txt = f"{grp}{p['code']} ({'/'.join(p['fac'])}) {r}"
                grid[ev["div"]][(dy, s + k)].append((ev["kind"], txt if k == 0 else "↳ " + grp + p["code"]))
    return grid


def print_division(dv, grid):
    print(f"\n=== {dv}  (home: {DIV[dv]['home'] or 'pool'}) ===")
    for sl in range(N_SLOTS):
        print(f"{SLOT_LABELS[sl]:<12}", end="")
        for dy in range(N_DAYS):
            items = [t for _, t in grid[dv].get((dy, sl), [])]
            print(f"{DAYS[dy]}: " + (" | ".join(items) if items else "-"), end="   ")
        print()


def export_csv(pos, rooms, fn="timetable_output.csv"):
    with open(fn, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["Division", "Day", "Start_Slot", "Time", "Hours", "Type", "Group", "Subject", "Faculty", "Room"])
        for fx in FIXED:
            for dv in fx["divs"]:
                w.writerow([dv, DAYS[fx["day"]], fx["start"], SLOT_LABELS[fx["start"]].split("-")[0], fx["dur"],
                            "Fixed", "ALL", fx["label"], "/".join(fx["fac"]), "/".join(fx["rooms"]) or "-"])
        for ev, (dy, s) in zip(EVENTS, pos):
            for pi, p in enumerate(ev["parts"]):
                grp = "ALL" if p["groups"] == (0, 1) else DIV[ev["div"]]["groups"][p["groups"][0]]
                w.writerow([ev["div"], DAYS[dy], s, SLOT_LABELS[s].split("-")[0], ev["dur"], ev["kind"],
                            grp, p["code"], "/".join(p["fac"]), rooms[(ev["id"], pi)]])


def export_html(grid, fn="timetable_output.html"):
    css = ("body{font-family:Segoe UI,Arial,sans-serif;margin:20px;background:#f6f7f9}"
           "h2{margin:28px 0 6px}table{border-collapse:collapse;background:#fff;width:100%;font-size:12px}"
           "th,td{border:1px solid #ccd;padding:5px;vertical-align:top}th{background:#2b3a55;color:#fff}"
           ".t{width:92px;font-weight:600;background:#eef}.brk td{background:#ddd;text-align:center;font-weight:600}"
           ".theory{background:#e8f4ff}.lab{background:#e9f9ea}.batch{background:#fff7dc}"
           ".fixed{background:#fde8e8}.cell div{margin:1px 0}")
    out = [f"<html><head><meta charset='utf-8'><style>{css}</style><title>Timetable</title></head><body>"
           "<h1>KIT CSE-AIML &amp; DS - A.Y. 2026-27 Odd Sem (GA generated)</h1>"
           "<p>Blue=theory, Green=lab, Yellow=1-hr batch session, Red=fixed (MDM/PE/OE/T&amp;P/Project). "
           "LeetCode not scheduled.</p>"]
    for dv in DIV:
        out.append(f"<h2>{dv} &mdash; {DIV[dv]['home'] or 'classroom from pool'}</h2><table><tr><th></th>"
                   + "".join(f"<th>{d_}</th>" for d_ in DAYS) + "</tr>")
        for sl in range(N_SLOTS):
            if sl == 2:
                out.append("<tr class='brk'><td colspan='6'>Break 11.00-11.15</td></tr>")
            if sl == 4:
                out.append("<tr class='brk'><td colspan='6'>Lunch 1.15-2.00</td></tr>")
            out.append(f"<tr><td class='t'>{SLOT_LABELS[sl]}</td>")
            for dy in range(N_DAYS):
                items = grid[dv].get((dy, sl), [])
                if not items:
                    out.append("<td class='cell'></td>")
                else:
                    cls = items[0][0]
                    out.append(f"<td class='cell {cls}'>" + "".join(f"<div>{t}</div>" for _, t in items) + "</td>")
            out.append("</tr>")
        out.append("</table>")
    out.append("</body></html>")
    with open(fn, "w", encoding="utf-8") as fh:
        fh.write("\n".join(out))


# 8. MAIN

if __name__ == "__main__":
    seed = int(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1].lstrip("-").isdigit() else 42
    show = [a for a in sys.argv[1:] if a in DIV]
    print(f"Events to schedule: {N}   Fixed events: {len(FIXED)}   seed={seed}")
    base = State().base_H
    if base:
        print(f"NOTE: the PDF's own fixed blocks already clash {base} time(s) - see report below.")
    t0 = time.time()
    best, pen = run_ga(seed=seed)
    print(f"\nGA finished in {time.time() - t0:.1f}s | hard clashes: {pen // HARD_W} | soft cost: {pen % HARD_W}")

    rooms = decode(best)
    clashes = validate(best, rooms)
    # clashes that exist only between FIXED blocks are data issues from the PDF
    data_issues = [c for c in clashes if all(x.startswith("FIXED") for x in c[1])]
    real = [c for c in clashes if c not in data_issues]
    print(f"Independent validation: {len(real)} real clash(es) in generated sessions")
    for (kind, key, c), who in real:
        print("  CLASH", kind, key, describe(c), who)
    if data_issues:
        print(f"\nPDF data issues (fixed blocks clash with each other - GA cannot change these):")
        for (kind, key, c), who in data_issues:
            print(f"  {kind} {key} at {describe(c)}: {who}")

    grid = build_grid(best, rooms)
    for dv in (show or []):
        print_division(dv, grid)
    export_csv(best, rooms)
    export_html(grid)
    print("\nWrote timetable_output.csv and timetable_output.html")
