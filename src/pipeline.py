"""Reproducible, standard-library-only analytics for a fictional adult product."""
from __future__ import annotations

import csv
from datetime import date, datetime, timedelta
from html import escape
from pathlib import Path
import random
import sqlite3

ROOT = Path(__file__).resolve().parents[1]
START = date(2026, 1, 5)
END = date(2026, 3, 29)
SEED = 1010
FEATURES = ['template_library', 'progress_tracker', 'collaboration']
NAVY, TEAL, GOLD, BG = '#10243A', '#087F8C', '#E9B44C', '#F5F7FA'


def write_csv(path, rows, fields=None):
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = fields or list(rows[0])
    with path.open('w', newline='', encoding='utf-8') as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def synthetic_data():
    rng = random.Random(SEED)
    users, events = [], []

    def emit(user_id, when, session, name, feature=''):
        events.append(dict(event_id=f'E{len(events)+1:06d}', user_id=user_id,
                           event_time=when.strftime('%Y-%m-%d %H:%M:%S'),
                           event_date=when.date().isoformat(), session_id=session,
                           event_name=name, feature=feature))

    for i in range(120):
        uid = f'U{i+1:04d}'
        joined = START + timedelta(days=rng.randrange(56))
        signup = datetime.combine(joined, datetime.min.time()).replace(hour=8)
        persona = rng.choice(['explorer', 'maker'])
        onboarding = rng.choice(['self_serve', 'guided'])
        users.append(dict(user_id=uid, signup_at=signup.strftime('%Y-%m-%d %H:%M:%S'),
                          signup_date=joined.isoformat(),
                          cohort_week=(joined-timedelta(days=joined.weekday())).isoformat(),
                          persona=persona, onboarding_path=onboarding,
                          acquisition_channel=rng.choice(['organic', 'community', 'referral']),
                          age_group='adult_18_plus'))
        emit(uid, signup, '', 'signed_up')
        created, completed, shared = False, False, False
        # Deliberate simulation assumptions, not estimated behavioral parameters.
        propensity = rng.uniform(0.045, 0.15) + (0.045 if persona == 'maker' else 0)
        for day in range((END-joined).days+1):
            chance = propensity * (1 if day < 14 else 0.64)
            if day != 0 and rng.random() > chance:
                continue
            stamp = signup + timedelta(days=day, hours=1, minutes=rng.randrange(60))
            session = f'{uid}-{day:03d}'
            emit(uid, stamp, session, 'session_started')
            if not created and rng.random() < (0.53 if onboarding == 'guided' else 0.26):
                created = True
                emit(uid, stamp+timedelta(minutes=2), session, 'project_created')
            emit(uid, stamp+timedelta(minutes=3), session, 'lesson_started')
            if created and rng.random() < (0.48 if persona == 'maker' else 0.30):
                completed = True
                emit(uid, stamp+timedelta(minutes=8), session, 'lesson_completed')
            if completed and not shared and rng.random() < 0.20:
                shared = True
                emit(uid, stamp+timedelta(minutes=12), session, 'project_shared')
            for feature, probability in zip(FEATURES, [0.44, 0.30, 0.07]):
                if rng.random() < probability:
                    emit(uid, stamp+timedelta(minutes=15+FEATURES.index(feature)), session,
                         'feature_used', feature)
    events.sort(key=lambda e: (e['event_time'], e['event_id']))
    return users, events


def connect(users, events, calendar=None):
    """Create an in-memory model; small fixtures may inject their calendar."""
    db = sqlite3.connect(':memory:')
    db.row_factory = sqlite3.Row
    db.executescript('''
      CREATE TABLE users(user_id TEXT PRIMARY KEY, signup_at TEXT, signup_date TEXT,
        cohort_week TEXT, persona TEXT, onboarding_path TEXT, acquisition_channel TEXT, age_group TEXT);
      CREATE TABLE events(event_id TEXT PRIMARY KEY, user_id TEXT, event_time TEXT,
        event_date TEXT, session_id TEXT, event_name TEXT, feature TEXT);
      CREATE TABLE calendar(date TEXT PRIMARY KEY);
      CREATE TABLE features(feature TEXT PRIMARY KEY);
    ''')
    for table, rows in [('users', users), ('events', events)]:
        if rows:
            fields = list(rows[0])
            db.executemany(f"INSERT INTO {table} ({','.join(fields)}) VALUES ({','.join('?' for _ in fields)})",
                           [[row[k] for k in fields] for row in rows])
    calendar = calendar if calendar is not None else [
        (START+timedelta(days=d)).isoformat() for d in range((END-START).days+1)]
    db.executemany('INSERT INTO calendar VALUES (?)', [(d,) for d in calendar])
    db.executemany('INSERT INTO features VALUES (?)', [(f,) for f in FEATURES])
    db.execute('CREATE INDEX ix_events_user_time ON events(user_id,event_name,event_time)')
    db.execute('CREATE INDEX ix_events_date ON events(event_date,event_name)')
    db.executescript((ROOT/'sql/metrics.sql').read_text(encoding='utf-8'))
    return db


def query(db, view):
    ordering = {'daily_activity': 'date', 'calendar_monthly_activity': 'month',
                'funnel': 'step_order', 'funnel_users': 'user_id',
                'retention': 'cohort_week,week_index', 'feature_adoption': 'feature',
                'segmentation': 'persona,onboarding_path'}
    return [dict(row) for row in db.execute(f'SELECT * FROM {view} ORDER BY {ordering[view]}')]


def validate(users, events, outputs):
    """Enforce referential integrity and metric invariants before writing results."""
    ids = {u['user_id'] for u in users}
    assert len(ids) == len(users)
    assert len({e['event_id'] for e in events}) == len(events)
    assert all(e['user_id'] in ids and START.isoformat() <= e['event_date'] <= END.isoformat() for e in events)
    assert all(r['dau'] <= r['rolling_30d_mau'] <= len(users) for r in outputs['daily_activity'])
    counts = [r['users'] for r in outputs['funnel']]
    assert counts == sorted(counts, reverse=True)
    for row in outputs['retention']:
        if row['fully_observed']:
            assert 0 <= row['retention_rate'] <= 1
        else:
            assert row['retained_users'] is None and row['retention_rate'] is None
    return [dict(check='unique_user_and_event_ids', status='PASS'),
            dict(check='event_foreign_keys_and_observation_window', status='PASS'),
            dict(check='daily_distinct_count_bounds', status='PASS'),
            dict(check='ordered_funnel_monotonicity', status='PASS'),
            dict(check='retention_bounds_and_censoring', status='PASS')]


def svg_frame(title, subtitle, content, height=460):
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="1000" height="{height}" viewBox="0 0 1000 {height}">
<title>{escape(title)}</title><desc>{escape(subtitle)}</desc>
<rect width="1000" height="{height}" fill="{BG}"/>
<style>text{{font-family:Arial,Helvetica,sans-serif;fill:{NAVY}}}.title{{font-size:26px;font-weight:700}}.sub{{font-size:14px}}.label{{font-size:15px}}.note{{font-size:12px}}</style>
<text x="40" y="46" class="title">{escape(title)}</text>
<text x="40" y="73" class="sub">{escape(subtitle)}</text>
{content}
<text x="40" y="{height-22}" class="note">BUILD FLOW  /  MONISH  /  SYNTHETIC PORTFOLIO DATA · NOT A LIVE PRODUCT</text>
</svg>'''


def figures(outputs):
    funnel = outputs['funnel']
    body = ''
    for i, row in enumerate(funnel):
        y = 117+i*68
        width = 580*row['users']/funnel[0]['users']
        body += f'<text x="40" y="{y+25}" class="label">{escape(row["step"])}</text>'
        body += f'<rect x="230" y="{y}" width="{width:.1f}" height="40" rx="5" fill="{TEAL if i<3 else GOLD}"/>'
        body += f'<text x="{245+width:.1f}" y="{y+26}" class="label">{row["users"]} ({row["conversion_from_signup"]:.1%})</text>'
    (ROOT/'images/funnel.svg').write_text(svg_frame('From sign-up to shared project',
        'Strictly ordered steps within 14 days · all signup cohorts have a full conversion window',body),encoding='utf-8')

    daily = outputs['daily_activity']
    ceiling = max(r['rolling_30d_mau'] for r in daily)+10
    body = ''
    for v in range(0, int(ceiling)+1, 20):
        y=365-v/ceiling*240
        body += f'<line x1="70" x2="935" y1="{y:.1f}" y2="{y:.1f}" stroke="#D9E1E8"/><text x="32" y="{y+5:.1f}" class="note">{v}</text>'
    for key, color in [('rolling_30d_mau',TEAL), ('dau',GOLD)]:
        points = ' '.join(f'{70+i/(len(daily)-1)*865:.1f},{365-r[key]/ceiling*240:.1f}' for i,r in enumerate(daily))
        body += f'<polyline points="{points}" fill="none" stroke="{color}" stroke-width="3"/>'
    body += f'<text x="70" y="396" class="note">{START.isoformat()}</text><text x="850" y="396" class="note">{END.isoformat()}</text>'
    body += f'<rect x="590" y="93" width="18" height="5" fill="{TEAL}"/><text x="617" y="101" class="label">Rolling 30-day MAU</text><rect x="810" y="93" width="18" height="5" fill="{GOLD}"/><text x="837" y="101" class="label">DAU</text>'
    (ROOT/'images/activity.svg').write_text(svg_frame('A growing audience is not daily engagement',
        'Active = session started · first 29 rolling windows are partial · distinct users, not event totals',body),encoding='utf-8')

    rows = outputs['retention']
    cohorts = sorted({r['cohort_week'] for r in rows})
    body = '<text x="40" y="112" class="label">Signup week</text>'
    for age in range(12):
        body += f'<text x="{202+age*62}" y="112" class="note">W{age}</text>'
    for r in rows:
        i=cohorts.index(r['cohort_week']); x=190+r['week_index']*62; y=130+i*37
        rate=r['retention_rate']
        opacity=0.12+(rate or 0)*0.8
        fill=TEAL if r['fully_observed'] else '#D9E1E8'
        if r['week_index']==0:
            body += f'<text x="40" y="{y+23}" class="note">{r["cohort_week"]} · n={r["cohort_size"]}</text>'
        body += f'<rect x="{x}" y="{y}" width="57" height="31" rx="3" fill="{fill}" fill-opacity="{opacity if r["fully_observed"] else 1:.2f}"/>'
        label=f'{rate:.0%}' if rate is not None else '—'
        body += f'<text x="{x+12}" y="{y+21}" class="note">{label}</text>'
    body += '<text x="40" y="453" class="note">W0 is the signup calendar week. Gray dashes are weeks not fully observed; zero is an observed no-return week.</text>'
    (ROOT/'images/retention.svg').write_text(svg_frame('Retention with honest observation windows',
        'Monday cohorts · active at least once during each calendar cohort week · denominator = cohort signups',body,510),encoding='utf-8')


def product_outputs(outputs):
    f=outputs['funnel']; seg=outputs['segmentation']
    by_path={}
    for path in ['guided','self_serve']:
        subset=[r for r in seg if r['onboarding_path']==path]
        total=sum(r['eligible_users'] for r in subset)
        activated=sum(r['activated_users'] for r in subset)
        by_path[path]=(activated,total,activated/total)
    candidates=[
        dict(id='P01',initiative='First-project guided starter',reach=f[0]['users']-f[1]['users'],impact=2.0,confidence=0.55,effort_person_weeks=2.0,
             evidence='14-day signup-to-create gap',hypothesis='A smaller first step improves activation',success_metric='14-day ordered project creation rate',guardrail='Support contacts per new signup'),
        dict(id='P02',initiative='Lesson next-step checklist',reach=f[1]['users']-f[2]['users'],impact=1.5,confidence=0.50,effort_person_weeks=1.0,
             evidence='14-day create-to-complete gap',hypothesis='An explicit next step improves learning completion',success_metric='14-day ordered lesson completion rate',guardrail='User-reported completion quality'),
        dict(id='P03',initiative='Private share preview',reach=f[2]['users']-f[3]['users'],impact=1.0,confidence=0.45,effort_person_weeks=1.5,
             evidence='14-day complete-to-share gap',hypothesis='A privacy-first preview reduces sharing uncertainty',success_metric='14-day ordered share rate',guardrail='Accidental public-share reports'),
        dict(id='P04',initiative='Collaboration discovery interviews',reach=20,impact=0.5,confidence=0.30,effort_person_weeks=1.0,
             evidence='Low full-period collaboration adoption; need validation',hypothesis='Discover whether low adoption reflects low demand or poor discoverability',success_metric='Decision supported by adult-user research',guardrail='No implementation before problem validation')]
    for r in candidates:
        r['rice_score']=round(r['reach']*r['impact']*r['confidence']/r['effort_person_weeks'],2)
    candidates.sort(key=lambda r:r['rice_score'],reverse=True)
    for i,r in enumerate(candidates): r['priority_rank']=i+1
    write_csv(ROOT/'product/prioritized_backlog.csv',candidates)
    week4=[r for r in outputs['retention'] if r['week_index']==4 and r['fully_observed']]
    retained=sum(r['retained_users'] for r in week4); denominator=sum(r['cohort_size'] for r in week4)
    summary=[dict(metric='synthetic_users',value=f[0]['users'],unit='users'),
             dict(metric='14_day_activation',value=round(f[1]['users']/f[0]['users'],4),unit='proportion'),
             dict(metric='14_day_ordered_share',value=round(f[3]['users']/f[0]['users'],4),unit='proportion'),
             dict(metric='observed_week_4_retention',value=round(retained/denominator,4),unit='proportion'),
             dict(metric='observed_week_4_denominator',value=denominator,unit='users')]
    write_csv(ROOT/'results/summary.csv',summary)
    notes=f'''# Product decision memo

All figures below describe the seeded fictional BuildFlow simulation. They are not market evidence, user research, or achieved business results.

## What the pipeline reports

- **Activation:** {f[1]['users']}/{f[0]['users']} ({f[1]['users']/f[0]['users']:.1%}) create a project in the ordered 14-day funnel.
- **Sharing:** {f[3]['users']}/{f[0]['users']} ({f[3]['users']/f[0]['users']:.1%}) reach the final ordered step.
- **Week-4 retention:** {retained}/{denominator} ({retained/denominator:.1%}) across fully observed cohorts, weighted by cohort size.
- **Onboarding comparison:** guided {by_path['guided'][0]}/{by_path['guided'][1]} ({by_path['guided'][2]:.1%}); self-serve {by_path['self_serve'][0]}/{by_path['self_serve'][1]} ({by_path['self_serve'][2]:.1%}) activate. The generator deliberately embeds different probabilities. This is an association in synthetic data, not a measured treatment effect.
- Calendar MAU counts distinct active users within each month. January and March are partial months; compare coverage before interpreting a trend. The rolling-30-day series has a different window and must not be labelled calendar MAU.

## Decision and uncertainty

The illustrative RICE calculation puts **{candidates[0]['initiative']}** first at **{candidates[0]['rice_score']:.2f}**. See [the backlog](../product/prioritized_backlog.csv) for exact inputs. Reach for the first three items is the observed count dropping at that step across this 84-day study; impact, confidence, effort, and the research-item reach are explicit planning assumptions. Scores prioritize discussion, not spending approval. These are not quarterly forecasts. The first two scores are almost tied, so small changes in assumed effort or confidence would reverse their order; discovery should cover both before a commitment.

Validate the problem with adult participants before building. If the need is supported, randomize the proposed experience for eligible new adult users with stable assignment. For the top-ranked idea, pre-register **{candidates[0]['success_metric']}** as the primary outcome, plus exposure checks, a sample-size calculation using a real baseline, and completion-quality/support guardrails. Keep downstream sharing and retention as secondary outcomes. Wait until every enrolled user has 14 days of follow-up; avoid repeated significance checks. Do not infer that a synthetic segment difference predicts a live experiment's uplift.

## Proposed roadmap (relative to a hypothetical kickoff)

| Stage | Scope | Evidence gate |
|---|---|---|
| Weeks 1–2 | Instrumentation audit, adult-user discovery, validate event contracts | Correct event ordering and a supported unmet need |
| Weeks 3–4 | Prototype {candidates[0]['initiative'].lower()} and run moderated tasks | Users understand the next step; privacy defaults remain clear |
| Weeks 5–8 | Run a measured experiment if traffic supports it | Full 14-day follow-up and predeclared decision criteria |
| Weeks 9–12 | Evaluate remaining starter/checklist and private share ideas in re-scored order | Re-score with real reach, research, effort, and outcome evidence |

Dates are planning windows, not delivery promises. Collaboration remains a discovery topic until research distinguishes usability friction from lack of demand.
'''
    (ROOT/'docs/decision-memo.md').write_text(notes,encoding='utf-8')


def main():
    users,events=synthetic_data()
    write_csv(ROOT/'data/raw/users.csv',users)
    write_csv(ROOT/'data/raw/events.csv',events)
    db=connect(users,events)
    views=['daily_activity','calendar_monthly_activity','funnel','funnel_users','retention','feature_adoption','segmentation']
    outputs={name:query(db,name) for name in views}
    for i,row in enumerate(outputs['funnel']):
        previous=outputs['funnel'][i-1]['users'] if i else row['users']
        row['dropoff_from_previous']=previous-row['users']
        row['conversion_from_previous']=round(row['users']/previous,4) if previous else None
        row['conversion_from_signup']=round(row['users']/len(outputs['funnel_users']),4)
    checks=validate(users,events,outputs)
    for name,rows in outputs.items():
        write_csv(ROOT/'results'/f'{name}.csv',rows)
    write_csv(ROOT/'results/quality_checks.csv',checks)
    write_csv(ROOT/'data/processed/dim_date.csv',[dict(date=r[0]) for r in db.execute('SELECT date FROM calendar ORDER BY date')])
    write_csv(ROOT/'data/processed/dim_user.csv',users)
    write_csv(ROOT/'data/processed/fact_event.csv',events)
    write_csv(ROOT/'data/processed/dim_feature.csv',[dict(feature=f) for f in FEATURES])
    figures(outputs)
    product_outputs(outputs)
    db.close()
    print(f'Rebuilt {len(users)} synthetic adult users, {len(events)} events, 84 daily observations.')
    print('CSV outputs, SVG figures, product backlog, and decision memo generated successfully.')


if __name__=='__main__':
    main()
