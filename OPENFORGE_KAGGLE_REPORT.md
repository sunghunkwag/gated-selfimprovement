# OPENFORGE LONG RUN -- Kaggle report

wall: 7.50 h of 7.8 h budget
## OPEN_1
```
{
 "arm": "OPEN",
 "diagnosis": [
  "NO_ADMIT_15",
  "WALL_CLOCK"
 ],
 "elapsed": 25.3,
 "gen": 4444,
 "novel_behaviours": 189,
 "seed": 1,
 "solved_total": 226,
 "target": 100000,
 "vocab": 37
}
```
## CLOSED_1
```
{
 "arm": "CLOSED",
 "diagnosis": [
  "NO_SOLVE_10",
  "NOVELTY_STALL_15"
 ],
 "elapsed": 19.4,
 "gen": 4444,
 "novel_behaviours": 0,
 "seed": 1,
 "solved_total": 1297,
 "target": 4444,
 "vocab": 0
}
```
## OPEN_2
```
{
 "arm": "OPEN",
 "diagnosis": [
  "NO_SOLVE_10",
  "NO_ADMIT_15",
  "NOVELTY_STALL_15",
  "WALL_CLOCK"
 ],
 "elapsed": 25.9,
 "gen": 2609,
 "novel_behaviours": 80,
 "seed": 2,
 "solved_total": 59,
 "target": 100000,
 "vocab": 37
}
```
### CLOSED seed 1 trajectory
  gen      1: vocab   0 solved     1 novel     0
  gen     10: vocab   0 solved    10 novel     0
  gen     50: vocab   0 solved    39 novel     0
  gen    100: vocab   0 solved    63 novel     0
  gen    250: vocab   0 solved   121 novel     0
  gen    500: vocab   0 solved   188 novel     0
  gen   1000: vocab   0 solved   295 novel     0
  gen   2000: vocab   0 solved   494 novel     0
  gen   4000: vocab   0 solved  1155 novel     0
  gen   4444: vocab   0 solved  1297 novel     0
### OPEN seed 1 trajectory
  gen      1: vocab   1 solved     1 novel     0
  gen     10: vocab   6 solved    13 novel     7
  gen     50: vocab   8 solved    29 novel    36
  gen    100: vocab  12 solved    46 novel    48
  gen    250: vocab  15 solved    55 novel    52
  gen    500: vocab  19 solved    60 novel    56
  gen   1000: vocab  24 solved    94 novel    81
  gen   2000: vocab  28 solved   134 novel   109
  gen   4000: vocab  35 solved   201 novel   168
  gen   4444: vocab  37 solved   226 novel   189
### OPEN seed 2 trajectory
  gen      1: vocab   1 solved     0 novel     0
  gen     10: vocab   8 solved     6 novel     6
  gen     50: vocab  17 solved    14 novel    38
  gen    100: vocab  19 solved    28 novel    52
  gen    250: vocab  29 solved    36 novel    59
  gen    500: vocab  30 solved    56 novel    78
  gen   1000: vocab  32 solved    56 novel    78
  gen   2000: vocab  36 solved    56 novel    78
  gen   2609: vocab  37 solved    59 novel    80
