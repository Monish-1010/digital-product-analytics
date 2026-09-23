# Product decision memo

All figures below describe the seeded fictional BuildFlow simulation. They are not market evidence, user research, or achieved business results.

## What the pipeline reports

- **Activation:** 78/120 (65.0%) create a project in the ordered 14-day funnel.
- **Sharing:** 15/120 (12.5%) reach the final ordered step.
- **Week-4 retention:** 45/120 (37.5%) across fully observed cohorts, weighted by cohort size.
- **Onboarding comparison:** guided 48/69 (69.6%); self-serve 30/51 (58.8%) activate. The generator deliberately embeds different probabilities. This is an association in synthetic data, not a measured treatment effect.
- Calendar MAU counts distinct active users within each month. January and March are partial months; compare coverage before interpreting a trend. The rolling-30-day series has a different window and must not be labelled calendar MAU.

## Decision and uncertainty

The illustrative RICE calculation puts **Lesson next-step checklist** first at **23.25**. See [the backlog](../product/prioritized_backlog.csv) for exact inputs. Reach for the first three items is the observed count dropping at that step across this 84-day study; impact, confidence, effort, and the research-item reach are explicit planning assumptions. Scores prioritize discussion, not spending approval. These are not quarterly forecasts. The first two scores are almost tied, so small changes in assumed effort or confidence would reverse their order; discovery should cover both before a commitment.

Validate the problem with adult participants before building. If the need is supported, randomize the proposed experience for eligible new adult users with stable assignment. For the top-ranked idea, pre-register **14-day ordered lesson completion rate** as the primary outcome, plus exposure checks, a sample-size calculation using a real baseline, and completion-quality/support guardrails. Keep downstream sharing and retention as secondary outcomes. Wait until every enrolled user has 14 days of follow-up; avoid repeated significance checks. Do not infer that a synthetic segment difference predicts a live experiment's uplift.

## Proposed roadmap (relative to a hypothetical kickoff)

| Stage | Scope | Evidence gate |
|---|---|---|
| Weeks 1–2 | Instrumentation audit, adult-user discovery, validate event contracts | Correct event ordering and a supported unmet need |
| Weeks 3–4 | Prototype lesson next-step checklist and run moderated tasks | Users understand the next step; privacy defaults remain clear |
| Weeks 5–8 | Run a measured experiment if traffic supports it | Full 14-day follow-up and predeclared decision criteria |
| Weeks 9–12 | Evaluate remaining starter/checklist and private share ideas in re-scored order | Re-score with real reach, research, effort, and outcome evidence |

Dates are planning windows, not delivery promises. Collaboration remains a discovery topic until research distinguishes usability friction from lack of demand.
