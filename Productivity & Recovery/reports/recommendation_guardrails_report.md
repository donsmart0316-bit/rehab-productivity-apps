# Recommendation Guardrails & Realism Audit

| case                           |   quality_score | passed   | issues   | recovery_priority_mode   |   deferred_tasks |
|:-------------------------------|----------------:|:---------|:---------|:-------------------------|-----------------:|
| Unusual human tasks            |             100 | True     |          | False                    |                0 |
| High burnout recovery priority |             100 | True     |          | True                     |                1 |

## Classification Checks
### Unusual human tasks
|                        | 0         |
|:-----------------------|:----------|
| Write Research Paper   | Deep Work |
| Doctor Appointment     | Health    |
| Gym Workout            | Exercise  |
| Rest                   | Rest      |
| Prayer                 | Spiritual |
| Travel to Airport      | Travel    |
| Going Out With Friends | Social    |

### High burnout recovery priority
|                 | 0         |
|:----------------|:----------|
| Nap             | Rest      |
| Emergency Work  | Deep Work |
| Therapy Session | Health    |

## Schedule Checks
### Unusual human tasks
- 07:00-08:55 | Write Research Paper | Category: Deep Work | Because your recovery is strong and your chronotype favors this morning period, this is the best time for demanding focus work.
- 08:55-09:05 | Recovery Break | Category: break | After a 115-minute work block, this break helps restore attention and prevents fatigue from accumulating.
- 10:50-11:00 | Posture and Eye Reset | Category: break | A short posture reset and 20-20-20 eye break keeps screen work from becoming physical strain.
- 11:00-11:45 | Doctor Appointment | Category: Health | Health-related time is protected as a priority appointment because wellbeing takes precedence over productivity optimization.
- 14:00-15:00 | Gym Workout | Category: Exercise | Exercise is scheduled away from the deepest cognitive window so it supports physical health and recovery without displacing priority focus work.
- 15:00-15:45 | Rest | Category: Rest | Rest is treated as recovery time, not as a work block, so the schedule protects it without adding another recovery break afterward.
- 16:00-16:30 | Prayer | Category: Spiritual | Prayer is scheduled in a calm afternoon period to support grounding and reflection without requiring high cognitive load.
- 17:00-18:00 | Travel to Airport | Category: Travel | Travel is scheduled with lower cognitive expectations because transitions and movement create practical load.
- 18:00-19:30 | Going Out With Friends | Category: Social | Social time is placed outside peak cognitive-demand periods so connection does not compete with deep work.

### High burnout recovery priority
- 08:00-08:45 | Nap | Category: Rest | Rest is treated as recovery time, not as a work block, so the schedule protects it without adding another recovery break afterward.
- 09:00-09:45 | Emergency Work | Category: Deep Work | This demanding task is placed in your strongest morning window, but the block is kept short because burnout risk is high and recovery needs protection.
- 09:45-10:15 | Recovery Break | Category: break | After a 45-minute work block, this break helps restore attention and prevents fatigue from accumulating.
- 10:50-11:00 | Posture and Eye Reset | Category: break | A short posture reset and 20-20-20 eye break keeps screen work from becoming physical strain.
- 12:30-13:00 | Protected Recovery Window | Category: break | High burnout risk requires a non-negotiable recovery buffer before more cognitive demand.
- 13:00-14:00 | Therapy Session | Category: Health | Health-related time is protected as a priority appointment because wellbeing takes precedence over productivity optimization.
- 15:00-15:10 | Standing / Walking Break | Category: break | A brief movement break supports circulation, alertness, and recovery even on a good day.
