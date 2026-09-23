"""Adversarial fixtures verify metric semantics rather than snapshots."""
import unittest
from datetime import date, timedelta
from src.pipeline import connect, synthetic_data


def user(uid='U1', signup='2026-01-05 08:00:00', cohort='2026-01-05'):
    return dict(user_id=uid,signup_at=signup,signup_date=signup[:10],cohort_week=cohort,
                persona='explorer',onboarding_path='guided',acquisition_channel='organic',age_group='adult_18_plus')


def event(eid, when, name, uid='U1', feature=''):
    return dict(event_id=eid,user_id=uid,event_time=when,event_date=when[:10],
                session_id='S1',event_name=name,feature=feature)


class MetricsTests(unittest.TestCase):
    def test_order_and_conversion_deadline(self):
        events=[event('1','2026-01-05 09:00:00','lesson_completed'),
                event('2','2026-01-06 09:00:00','project_created'),
                event('3','2026-01-07 09:00:00','project_shared'),
                event('4','2026-01-08 09:00:00','lesson_completed'),
                event('5','2026-01-19 08:00:00','project_shared')]
        db=connect([user()],events)
        row=dict(db.execute('SELECT * FROM funnel_users').fetchone())
        self.assertEqual(row['completed_at'],'2026-01-08 09:00:00')
        self.assertIsNone(row['shared_at'])  # earlier sharing and exact 14-day boundary are excluded
        db.close()

    def test_insufficient_followup_excluded_from_funnel(self):
        db=connect([user(signup='2026-03-20 08:00:00',cohort='2026-03-16')],[])
        self.assertEqual(db.execute('SELECT COUNT(*) FROM funnel_users').fetchone()[0],0)
        db.close()

    def test_retention_distinguishes_zero_and_unobserved(self):
        db=connect([user(signup='2026-03-02 08:00:00',cohort='2026-03-02')],[])
        rows={r['week_index']:dict(r) for r in db.execute('SELECT * FROM retention')}
        self.assertEqual(rows[3]['retention_rate'],0)
        self.assertEqual(rows[3]['fully_observed'],1)
        self.assertIsNone(rows[4]['retention_rate'])
        self.assertEqual(rows[4]['fully_observed'],0)
        db.close()

    def test_deduplication_zero_days_and_rolling_boundary(self):
        calendar=[(date(2026,1,5)+timedelta(days=i)).isoformat() for i in range(31)]
        events=[event('1','2026-01-05 09:00:00','session_started'),
                event('2','2026-01-05 10:00:00','session_started')]
        db=connect([user()],events,calendar)
        rows=[dict(r) for r in db.execute('SELECT * FROM daily_activity ORDER BY date')]
        self.assertEqual(rows[0]['dau'],1)
        self.assertEqual(rows[1]['dau'],0)
        self.assertEqual(rows[29]['rolling_30d_mau'],1)
        self.assertEqual(rows[30]['rolling_30d_mau'],0)
        self.assertEqual(rows[28]['full_30d_window'],0)
        self.assertEqual(rows[29]['full_30d_window'],1)
        db.close()

    def test_calendar_mau_not_daily_sum(self):
        events=[event('1','2026-02-01 09:00:00','session_started'),
                event('2','2026-02-02 09:00:00','session_started')]
        db=connect([user()],events)
        row=db.execute("SELECT * FROM calendar_monthly_activity WHERE month='2026-02'").fetchone()
        self.assertEqual(row['calendar_mau'],1)
        self.assertEqual(row['complete_calendar_month'],1)
        self.assertEqual(db.execute("SELECT complete_calendar_month FROM calendar_monthly_activity WHERE month='2026-01'").fetchone()[0],0)
        db.close()

    def test_seeded_generation_is_repeatable(self):
        self.assertEqual(synthetic_data(),synthetic_data())


if __name__=='__main__':
    unittest.main()
