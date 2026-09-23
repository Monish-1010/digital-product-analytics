# Power BI implementation guide

This repository includes reproducible CSV tables and SVG figures. It does **not** contain a `.pbix` file or a screenshot of a built Power BI report. The figures are generated directly from the SQL outputs; this document specifies an implementable report.

## Model

Import `data/processed/dim_user.csv` as `Users`, `dim_date.csv` as `Calendar`, and `fact_event.csv` as `Events`. Set user/event IDs to text, `Calendar[date]` and `Events[event_date]` to Date, and timestamp columns to Date/Time. Mark Calendar as the date table.

- `Users[user_id]` 1 → many `Events[user_id]`, single-direction filtering.
- `Calendar[date]` 1 → many `Events[event_date]`, single-direction filtering.
- Do not also activate a date-to-signup relationship: signup-cohort filtering should use the user attributes or a separate role-playing date table.
- Import `results/funnel.csv`, `retention.csv`, `feature_adoption.csv`, and `segmentation.csv` as independent summary tables for the static study pages. Their precomputed metrics are fixed to the observation window; they are not valid under arbitrary event-date or user slicers. Disable interactions from those slicers on summary visuals. Use `funnel_users.csv` for an optional user-level funnel model if dynamic segmentation is required.

The dimensions/facts separation and single-direction relationships follow [Microsoft's star-schema guidance](https://learn.microsoft.com/en-us/power-bi/guidance/star-schema).

## Example DAX

Use a daily axis for DAU. `[Active Users]` returns distinct users in the current filter context; at a month axis it is calendar MAU. Monthly distinct counts are not the sum of daily counts. [DISTINCTCOUNT reference](https://learn.microsoft.com/en-us/dax/distinctcount-function-dax).

```dax
Active Users =
COALESCE(
    CALCULATE(
        DISTINCTCOUNT(Events[user_id]),
        Events[event_name] = "session_started"
    ),
    0
)

Rolling 30 Day Active Users =
VAR EndDate = MAX('Calendar'[date])
RETURN
    CALCULATE(
        [Active Users],
        FILTER(
            ALL('Calendar'),
            'Calendar'[date] >= EndDate - 29 &&
            'Calendar'[date] <= EndDate
        )
    )

Observed Retention =
DIVIDE(
    CALCULATE(SUM(Retention[retained_users]), Retention[fully_observed] = 1),
    CALCULATE(SUM(Retention[cohort_size]), Retention[fully_observed] = 1)
)
```

`Observed Retention` belongs in a visual at one `week_index` per column; suppress totals across week indices because repeated cohort denominators do not describe a single retention point. Preserve blanks for censored cells. The DAX is implementation guidance and has not been executed in Power BI Desktop; SQL output CSVs are the validated numerical reference.

## Pages and interactions

| Page | Visuals | Design choices |
|---|---|---|
| Overview | DAU and rolling MAU trend; calendar MAU table; activation card | Partial month/window badges; fixed study period prominently shown |
| Activation | Ordered funnel; previous-step dropout; persona/onboarding segmentation | Display eligible users and conversion-window definition; no unsupported date slicer on precomputed funnel |
| Retention | Cohort × week heatmap; weighted week-4 card | Gray blank cells for unobserved periods; visible cohort size; no grand total over ages |
| Product decisions | Feature adoption bars; ranked RICE table; assumptions panel | Distinguish measured simulation counts from assumed impact/confidence/effort |

Palette: navy `#10243A`, teal `#087F8C`, gold `#E9B44C`, background `#F5F7FA`. Use labels and blank-state text as well as color. Every page should say “Synthetic portfolio data — fictional adult product”.

## Acceptance checks

1. Compare a chosen day's distinct users with `daily_activity.csv` and a month's with `calendar_monthly_activity.csv`.
2. Verify January and March are visibly marked partial, and rolling windows before 3 February are incomplete.
3. Match all four funnel counts to `funnel.csv`; no step can exceed the previous step.
4. Verify the newest cohort's W5 cell is blank, not 0%; W4 is fully observed for every signup cohort in this fixture.
5. Disable slicers that would imply recalculation of fixed summary CSVs.
