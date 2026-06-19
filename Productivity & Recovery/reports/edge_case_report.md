# Edge Case Report

Edge-case rows: **15**
High-risk cases protected: **100.0%**

| case                                  | chronotype   |   productivity_score | burnout_risk   |   recovery_score |   breaks | burnout_protection_ok   | input_warnings                                                            |
|:--------------------------------------|:-------------|---------------------:|:---------------|-----------------:|---------:|:------------------------|:--------------------------------------------------------------------------|
| Severe Sleep Deprivation              | Morning      |                 0    | High           |             0    |        5 | True                    | []                                                                        |
| Severe Sleep Deprivation              | Intermediate |                 0    | High           |             0    |        4 | True                    | []                                                                        |
| Severe Sleep Deprivation              | Evening      |                 0    | High           |             0    |        4 | True                    | []                                                                        |
| Extreme Stress                        | Morning      |                14.28 | High           |            28.55 |        5 | True                    | []                                                                        |
| Extreme Stress                        | Intermediate |                14.17 | High           |            28.55 |        4 | True                    | []                                                                        |
| Extreme Stress                        | Evening      |                14.17 | High           |            28.55 |        4 | True                    | []                                                                        |
| High Workload                         | Morning      |                29.53 | High           |            38.65 |        4 | True                    | []                                                                        |
| High Workload                         | Intermediate |                29.41 | High           |            38.65 |        3 | True                    | []                                                                        |
| High Workload                         | Evening      |                29.41 | High           |            38.65 |        3 | True                    | []                                                                        |
| Contradictory High Energy Poor Sleep  | Morning      |                42.15 | High           |            24.96 |        4 | True                    | ['Energy is very high despite severe sleep loss; confidence is reduced.'] |
| Contradictory High Energy Poor Sleep  | Intermediate |                42.03 | High           |            24.96 |        3 | True                    | ['Energy is very high despite severe sleep loss; confidence is reduced.'] |
| Contradictory High Energy Poor Sleep  | Evening      |                42.03 | High           |            24.96 |        3 | True                    | ['Energy is very high despite severe sleep loss; confidence is reduced.'] |
| Contradictory Low Stress High Fatigue | Morning      |                31.42 | Medium         |            60.75 |        3 | True                    | ['Fatigue is very high despite low stress; confidence is reduced.']       |
| Contradictory Low Stress High Fatigue | Intermediate |                31.31 | Medium         |            60.75 |        2 | True                    | ['Fatigue is very high despite low stress; confidence is reduced.']       |
| Contradictory Low Stress High Fatigue | Evening      |                31.31 | Medium         |            60.75 |        2 | True                    | ['Fatigue is very high despite low stress; confidence is reduced.']       |