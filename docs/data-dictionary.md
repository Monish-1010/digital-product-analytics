# Dataset and metric contract

BuildFlow is a fictional creative-learning and project-planning product for adults. Every identity, session, behavior, and acquisition source is generated locally from seed `1010`. No real person, employer, university, customer, or company dataset is used. The dataset may be redistributed under this repository's MIT license.

## Scope

- Observation window: 5 January–29 March 2026 inclusive (84 days, UTC).
- 120 synthetic adult users; signups are sampled from the first 56 days.
- One session on signup day; subsequent daily session probabilities depend on a sampled user propensity, persona, and time since signup.
- Guided onboarding deliberately increases project-creation probability; makers deliberately have higher completion probability. These assumptions create analyzable patterns and cannot validate either business hypothesis.
- No purchases, advertising spend, revenue, retention intervention, or real controlled experiment is modeled.

## Tables

| Table / grain | Column | Meaning |
|---|---|---|
| `users.csv` / one user | `user_id` | Stable fictional key such as U0001 |
| | `signup_at`, `signup_date` | UTC timestamp and matching date |
| | `cohort_week` | Monday of signup calendar week |
| | `persona` | Simulation segment: explorer or maker |
| | `onboarding_path` | Guided or self_serve; a simulated category, not an experiment assignment |
| | `acquisition_channel` | Fictional organic, community, or referral category |
| | `age_group` | Constant adult_18_plus; no birth dates or real age data |
| `events.csv` / one event | `event_id` | Unique synthetic event key |
| | `user_id` | Foreign key to user |
| | `event_time`, `event_date` | UTC event timestamp and derived date |
| | `session_id` | User + day; blank for signup, which precedes the session |
| | `event_name` | signed_up, session_started, project_created, lesson_started, lesson_completed, project_shared, feature_used |
| | `feature` | For feature_used: template_library, progress_tracker, collaboration; otherwise blank |
| `dim_date.csv` / one day | `date` | Every observation date including zero-activity days |
| `dim_feature.csv` / one feature | `feature` | Fixed feature inventory, including features with zero adoption |

`data/processed/dim_user.csv` and `fact_event.csv` are validated copies of the raw synthetic tables, provided under model-friendly names. There is no claim that this event data needs industrial data cleaning.

## Definitions and denominator choices

| Output | Definition |
|---|---|
| Daily active users (DAU) | Distinct users with at least one `session_started` event that UTC date. Signup alone does not qualify. |
| Calendar MAU | Distinct active users per YYYY-MM calendar month. `complete_calendar_month` marks whether the full month is observed. January and March are partial. |
| Rolling 30-day MAU | Distinct active users from date minus 29 days through date inclusive. `full_30d_window=0` for the first 29 dates. |
| 14-day funnel | Signup → first valid later project creation → first valid later lesson completion → first valid later project share. All timestamps must be before signup + 14 days. Full follow-up is required for eligibility. |
| Funnel dropout | Previous-step users minus current-step users. Conversion from previous step and conversion from signup are both exported; they have different denominators. |
| Activation | Reaching project creation in the 14-day funnel / eligible signups. |
| Weekly retention | Active in calendar cohort week k / all signups in that cohort. W0 is the signup week, not seven days per user; it is shorter for late-week signups. |
| Censoring | A cohort week is reported only if its Sunday is on/before observation end. Future or partial weeks have blank counts/rates and fully_observed=0. |
| Aggregate week-4 retention | Sum retained users / sum cohort size over fully observed W4 cohorts. This weights by cohort size, not a simple mean of percentages. |
| Feature adoption | Distinct active users emitting feature_used for that feature / distinct active users over the full 84-day window. All three features are assumed available to every active user. Different tenure is a limitation. |
| Segmentation | Eligible users and ordered funnel outcomes by persona × onboarding_path; small cells remain visible with denominators. |

Rates are proportions in CSV (0–1). Empty retention fields mean unobserved, not zero. Stored rates are rounded to four decimals; aggregate from counts, not rounded rates. UTC date strings follow ISO 8601; timestamps use `YYYY-MM-DD HH:MM:SS` so SQLite comparisons are consistent.

## Interpretation limits

The small seeded simulation omits bots, event retries, offline delivery, identity merges, consent loss, feature entitlements, and acquisition campaigns. Raw events are already well-formed. Real implementation would need these checks, a consent-aware collection design, and contract versioning. Statistical uncertainty, causal uplift, commercial demand, and market size cannot be established from synthetic patterns. No real-world impact is claimed.
