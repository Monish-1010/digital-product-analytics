# BuildFlow: an adult creative-learning product concept

**Status:** fictional portfolio case study. The personas and requirements below are hypotheses, not findings from interviews, a deployed service, or work performed for a named company.

## Vision and business problem

Help adult learners turn an idea into a small, completed creative project by making the first step clear, the next lesson relevant, and sharing optional. A digital product can attract signups while failing to help people achieve a useful outcome. This case study connects event quality and SQL measurement to a product team's prioritization decisions.

The proposed north-star metric is **weekly learners completing a lesson on an existing project**. It is a candidate outcome proxy, not proof of skill development. Supporting metrics are ordered 14-day activation, week-4 retention, and opt-in sharing. Guardrails include self-reported learning quality, task completion effort, support contacts, accessibility problems, and accidental sharing reports; these are proposed collection needs, not measured outputs here.

## Hypothesis personas

| Persona | Goal | Potential barrier | Discovery question |
|---|---|---|---|
| Explorer, an adult trying a new creative skill | Finish a small first project without committing to a long course | Too many choices and an unclear starting point | How do you decide which first task is achievable? |
| Maker, an adult with an existing project idea | Find the lesson or tool that unblocks the next step | Generic recommendations and fragmented progress | Where do you lose context when switching between learning and making? |

Research would recruit consenting adults from varied skill and accessibility backgrounds, use open-ended interviews and moderated prototype tasks, and separate observed behavior from the researcher's interpretation. No interviews were conducted for this repository.

## Stakeholders and proposed responsibilities

- Learners: understandable progression, accessible tasks, control over sharing.
- Product manager: outcome definitions, scope, prioritization, experiment decisions.
- Designer: first-project usability, accessibility, clear privacy controls.
- Data analyst: event contracts, denominator choices, quality monitoring, reporting.
- Engineer: event reliability, feature behavior, identity and consent handling.
- Support/privacy owner: problem reports, retention choices, deletion handling.

## User stories and acceptance criteria

| ID | Story | Acceptance criteria |
|---|---|---|
| US01 | As an explorer, I want a manageable starter so I can create my first project. | Starter shows expected effort; user can skip guidance; successful creation emits one idempotent project_created event. |
| US02 | As a maker, I want a next-step checklist so I can resume without losing context. | Checklist preserves completed work; keyboard navigation works; the completion event fires only after the learning task is confirmed. |
| US03 | As a learner, I want a private preview so I can decide whether to share. | Default is private; audience is explicit; cancelling emits no project_shared event; shared state is reversible. |
| US04 | As an analyst, I need consistent events so conversion and retention are trustworthy. | UTC timestamps and unique event IDs; event ordering checked; failed/duplicate events quarantined in a real implementation; metric definitions versioned. |

## Prioritization and delivery

The pipeline produces [the prioritized backlog](prioritized_backlog.csv) and [decision memo with roadmap](../docs/decision-memo.md) directly from the computed funnel. RICE = reach × impact × confidence / effort in person-weeks. Reach is the count affected over this study window for delivery ideas; the collaboration-research reach is a planning assumption. Impact and confidence are illustrative judgments. Discovery and instrumentation are dependencies even when a feature receives a high score.

The MVP would cover starter templates, a minimal project, one lesson flow, progress, and private-by-default optional sharing. Payments, child accounts, social feeds, and AI content generation are outside this case study's scope. Any future use with children would require a distinct design and governance process.

## Instrumentation plan

Minimum event envelope: event_id, user_id (pseudonymous), event_time UTC, session_id, event_name, schema_version, consent state. Project-specific events should include a pseudonymous project_id in a real system; this portfolio models a single first-project journey per user and intentionally excludes user-authored content. The local fixture omits transport and consent infrastructure. Project creation should be emitted server-side after success, and sharing only after explicit audience confirmation. Acceptance tests should exercise retries, out-of-order delivery, and deletion propagation before production use.
