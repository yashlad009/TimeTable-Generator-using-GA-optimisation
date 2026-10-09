# TimeTable Generator using GA Optimisation

Automatic timetable generation for CSE-AIML & DS divisions (Sem 3, Sem 5, Sem 7) using a **Genetic Algorithm + min-conflicts local search**.

## Features
- Schedules theory lectures, 2-hour labs and 1-hour batch sessions
- Works around fixed events (MDM, PE, OE, T&P, Project Phase-I)
- Handles batch groups, faculty, classrooms and lab capacity
- Independent validator re-checks the final timetable
- Exports to CSV and HTML

## Constraints

**Hard (must be 0)**
- A batch group has two sessions at the same time
- A faculty member has two sessions at the same time
- A classroom is used twice at the same time
- More than 6 labs needed at once
- More pool classes than free classrooms

**Soft (minimised)**
- Idle gaps in a day
- Same theory subject twice in a day
- Theory in the last hour

## How it works
1. Each timetable is a list: one `(day, slot)` per event
2. Start with a random population, repaired by local search
3. Tournament selection, division-wise crossover, mutation
4. Repair clashes, keep the best (elitism)
5. Polish soft cost, then assign labs and classrooms
6. Validate and export

`Penalty = hard clashes × 1000 + soft cost`

## Run
```bash
python ga_timetable_v2.py            # default seed 42
python ga_timetable_v2.py 7          # custom seed
python ga_timetable_v2.py 7 SEM3-A   # print a division's timetable
```

## Output
- `timetable_output.csv` - all sessions (division, day, time, subject, faculty, room)
- `timetable_output.html` - colour-coded timetable per division

## Files
| File | Description |
|---|---|
| `ga_timetable_v2.py` | Version 2 |
| `ga_timetable_v3.py` | Version 3 |
| `backup.py` | Backup copy |
| `timetable_output.csv` | Generated output |
| `timetable_output.html` | Generated output |

## Tech
Python 3 (standard library only)
