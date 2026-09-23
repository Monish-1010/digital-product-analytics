-- SQLite. Dates are UTC. Calendar dimension includes days with zero events.
CREATE VIEW active_events AS
SELECT * FROM events WHERE event_name = 'session_started';

CREATE VIEW daily_activity AS
SELECT c.date, COUNT(DISTINCT a.user_id) AS dau,
  (SELECT COUNT(DISTINCT r.user_id) FROM active_events r
   WHERE r.event_date BETWEEN date(c.date, '-29 days') AND c.date) AS rolling_30d_mau,
  CASE WHEN c.date >= date((SELECT MIN(date) FROM calendar), '+29 days')
       THEN 1 ELSE 0 END AS full_30d_window
FROM calendar c LEFT JOIN active_events a ON a.event_date = c.date
GROUP BY c.date;

CREATE VIEW calendar_monthly_activity AS
SELECT substr(c.date, 1, 7) AS month, COUNT(DISTINCT a.user_id) AS calendar_mau,
  MIN(c.date) AS observed_from, MAX(c.date) AS observed_to,
  CASE WHEN MIN(c.date) = date(MIN(c.date), 'start of month')
        AND MAX(c.date) = date(MAX(c.date), 'start of month', '+1 month', '-1 day')
       THEN 1 ELSE 0 END AS complete_calendar_month
FROM calendar c LEFT JOIN active_events a ON a.event_date = c.date
GROUP BY substr(c.date, 1, 7);

-- One row per signup: strictly ordered steps within [signup, signup + 14 days).
-- Chained MIN searches allow a valid later completion even if an invalid early
-- event exists. All users must have the full 14-day opportunity to convert.
CREATE VIEW funnel_users AS
WITH eligible AS (
 SELECT * FROM users
 WHERE datetime(signup_at, '+14 days') <= datetime((SELECT MAX(date) FROM calendar), '+1 day')
), created AS (
 SELECT u.*, (SELECT MIN(event_time) FROM events e
   WHERE e.user_id=u.user_id AND e.event_name='project_created'
   AND e.event_time > u.signup_at AND e.event_time < datetime(u.signup_at, '+14 days')) AS created_at
 FROM eligible u
), completed AS (
 SELECT c.*, (SELECT MIN(event_time) FROM events e
   WHERE e.user_id=c.user_id AND e.event_name='lesson_completed'
   AND e.event_time > c.created_at AND e.event_time < datetime(c.signup_at, '+14 days')) AS completed_at
 FROM created c
)
SELECT c.*, (SELECT MIN(event_time) FROM events e
 WHERE e.user_id=c.user_id AND e.event_name='project_shared'
 AND e.event_time > c.completed_at AND e.event_time < datetime(c.signup_at, '+14 days')) AS shared_at
FROM completed c;

CREATE VIEW funnel AS
SELECT 1 AS step_order, 'Signed up' AS step, COUNT(*) AS users FROM funnel_users
UNION ALL SELECT 2, 'Created project', COUNT(created_at) FROM funnel_users
UNION ALL SELECT 3, 'Completed lesson', COUNT(completed_at) FROM funnel_users
UNION ALL SELECT 4, 'Shared project', COUNT(shared_at) FROM funnel_users;

-- Weekly cohorts start Monday; week 0 is the calendar signup week.
-- Unobserved full weeks remain NULL, never zero-filled.
CREATE VIEW retention AS
WITH RECURSIVE ages(week_index) AS (SELECT 0 UNION ALL SELECT week_index+1 FROM ages WHERE week_index<11),
cohorts AS (SELECT cohort_week, COUNT(*) AS cohort_size FROM users GROUP BY cohort_week),
active AS (
 SELECT u.cohort_week, CAST((julianday(e.event_date)-julianday(u.cohort_week))/7 AS INTEGER) AS week_index,
 COUNT(DISTINCT e.user_id) AS retained_users
 FROM users u JOIN active_events e ON u.user_id=e.user_id GROUP BY 1,2
)
SELECT c.cohort_week, a.week_index, c.cohort_size,
 CASE WHEN date(c.cohort_week, '+' || (a.week_index*7+6) || ' days') <= (SELECT MAX(date) FROM calendar)
      THEN COALESCE(r.retained_users,0) END AS retained_users,
 CASE WHEN date(c.cohort_week, '+' || (a.week_index*7+6) || ' days') <= (SELECT MAX(date) FROM calendar)
      THEN ROUND(1.0*COALESCE(r.retained_users,0)/c.cohort_size,4) END AS retention_rate,
 CASE WHEN date(c.cohort_week, '+' || (a.week_index*7+6) || ' days') <= (SELECT MAX(date) FROM calendar)
      THEN 1 ELSE 0 END AS fully_observed
FROM cohorts c CROSS JOIN ages a LEFT JOIN active r USING(cohort_week,week_index);

CREATE VIEW feature_adoption AS
SELECT f.feature, COUNT(DISTINCT e.user_id) AS adopted_users,
 (SELECT COUNT(DISTINCT user_id) FROM active_events) AS eligible_active_users,
 ROUND(1.0*COUNT(DISTINCT e.user_id)/(SELECT COUNT(DISTINCT user_id) FROM active_events),4) AS adoption_rate
FROM features f LEFT JOIN events e ON e.feature=f.feature AND e.event_name='feature_used'
GROUP BY f.feature;

CREATE VIEW segmentation AS
SELECT persona, onboarding_path, COUNT(*) AS eligible_users,
 COUNT(created_at) AS activated_users,
 ROUND(1.0*COUNT(created_at)/COUNT(*),4) AS activation_rate,
 COUNT(completed_at) AS lesson_completers,
 COUNT(shared_at) AS sharers
FROM funnel_users GROUP BY persona,onboarding_path;
