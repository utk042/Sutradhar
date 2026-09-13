'use client';

import {useEffect, useState} from 'react';
import {useFormatter, useTranslations} from 'next-intl';
import {Link} from '@/i18n/routing';
import Breadcrumb from '@/components/Breadcrumb';
import DecisionsChart from '@/components/DecisionsChart';
import FindingsChart from '@/components/FindingsChart';
import StatCard from '@/components/StatCard';
import StatusTag from '@/components/StatusTag';
import {getMyWork, type WorkSummary} from '@/lib/api';

/**
 * An officer's own screen: what is waiting, and what they have done.
 *
 * Deliberately *not* on the desk. The desk has one action on it — upload — and
 * the list of files waiting, and it stays that way: a row of numbers above the
 * only button on the screen competes with it, and the officers this is for are
 * the ones least helped by two things asking for attention at once. This is one
 * click away, from the same navigation bar on every page.
 *
 * It is the same shape as the head of department's screen one level up — four
 * numbers and a list — so that moving between the two teaches nothing new. What
 * differs is the scope: every number here is this officer's own desk, and the
 * server enforces that, not this component.
 *
 * The numbers are the ones an officer can act on. "Flagged on files waiting for
 * you" counts only what is still undecided: a lifetime total of everything the
 * checks ever raised is a number nobody can do anything about this morning.
 *
 * Every number is also a sentence — "Waiting for your decision: 3" reads the
 * same to a screen reader as it does on the page, because the label sits in the
 * same card as the figure and neither is an icon.
 */
export default function OfficerWork() {
  const t = useTranslations('work');
  const td = useTranslations('dashboard');
  const tn = useTranslations('nav');
  const format = useFormatter();

  const [work, setWork] = useState<WorkSummary | null>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    let active = true;
    getMyWork().then((result) => {
      if (!active) return;
      if (result.ok) setWork(result.data);
      // A screen that renders nothing when the request fails leaves the officer
      // looking at a blank page with no idea whether it is loading, broken, or
      // simply empty. Say which, in a sentence, with no status code in it.
      else setFailed(true);
    });
    return () => {
      active = false;
    };
  }, []);

  if (failed) {
    return (
      <section className="sutradhar-page ux4g-p-l">
        <Breadcrumb
          label={tn('breadcrumb')}
          items={[{label: tn('desk'), href: '/'}, {label: t('title')}]}
        />
        <h1 className="ux4g-heading-l-strong ux4g-mb-l">{t('title')}</h1>
        <div className="ux4g-alert ux4g-alert-error" role="alert">
          <span className="ux4g-body-m-default">{t('loadFailed')}</span>
        </div>
      </section>
    );
  }

  if (work === null) return null;

  const averageLabel =
    work.average_seconds == null
      ? td('noneYet')
      : work.average_seconds < 90
        ? td('seconds', {value: Math.round(work.average_seconds)})
        : td('minutes', {value: Math.round(work.average_seconds / 60)});

  /**
   * Four tiles, four tones.
   *
   * The tone says what kind of number it is, not how big it is: work waiting is
   * the brand hue because a queue is neither good nor bad, work finished is
   * success, and a flag is amber only when there is one — a zero wearing a
   * warning colour would be shouting about nothing.
   */
  const numbers = [
    {
      label: t('statPending'),
      value: String(work.pending_now),
      tone: 'brand' as const,
      icon: 'pending_actions'
    },
    {
      label: t('statDecidedToday'),
      value: String(work.decided_today),
      tone: 'success' as const,
      icon: 'task_alt'
    },
    {
      label: t('statAverage'),
      value: averageLabel,
      tone: 'neutral' as const,
      icon: 'schedule'
    },
    {
      label: t('statFlags'),
      value: String(work.flags_waiting),
      tone: work.flags_waiting > 0 ? ('warning' as const) : ('neutral' as const),
      icon: 'flag'
    }
  ];

  return (
    <section className="sutradhar-page ux4g-p-l">
      <Breadcrumb
        label={tn('breadcrumb')}
        items={[{label: tn('desk'), href: '/'}, {label: t('title')}]}
      />
      <h1 className="ux4g-heading-l-strong ux4g-mb-xs">{t('title')}</h1>
      <p className="ux4g-body-m-default ux4g-text-neutral-secondary ux4g-mb-l">
        {t('subtitle')}
      </p>

      <div className="sutradhar-stat-row ux4g-mb-l">
        {numbers.map((number) => (
          <StatCard
            key={number.label}
            label={number.label}
            value={number.value}
            tone={number.tone}
            icon={number.icon}
          />
        ))}
      </div>

      <div className="sutradhar-chart-row ux4g-mb-xl">
        <DecisionsChart days={work.daily} />
        <FindingsChart findings={work.findings} />
      </div>

      {/* The one thing on this screen that leads anywhere: back to the files
          that are actually waiting. A screen of numbers with no way to act on
          them is a screen an officer visits once. */}
      {work.pending_now > 0 && (
        <p className="ux4g-mb-xl">
          <Link href="/" className="ux4g-btn ux4g-btn-primary ux4g-btn-lg">
            {t('goToWaiting', {count: work.pending_now})}
          </Link>
        </p>
      )}

      <h2 className="ux4g-heading-s-strong ux4g-mb-s">{t('recentTitle')}</h2>

      {work.recent.length === 0 ? (
        <div className="ux4g-empty-state">
          <div className="ux4g-empty-state-content">
            <p className="ux4g-heading-xs-strong">{t('recentEmptyTitle')}</p>
            <p className="ux4g-body-m-default ux4g-text-neutral-secondary">
              {t('recentEmptyBody')}
            </p>
          </div>
        </div>
      ) : (
        <ul className="sutradhar-list-reset sutradhar-decision-list">
          {work.recent.map((decided) => (
            <li key={decided.id} className="ux4g-card ux4g-card-outline">
              <div className="ux4g-card-body sutradhar-decision-row">
                <div>
                  <p className="ux4g-heading-xxs-strong ux4g-mb-xs">{decided.public_ref}</p>
                  <p className="ux4g-mb-xs">
                    <StatusTag status={decided.status} />
                  </p>
                  <p className="ux4g-body-s-default ux4g-text-neutral-secondary">
                    {decided.reviewed_at === null
                      ? td('noneYet')
                      : format.dateTime(new Date(decided.reviewed_at), {
                          dateStyle: 'medium',
                          timeStyle: 'short'
                        })}
                  </p>
                </div>
                <Link
                  href={`/review/${decided.id}/decision`}
                  className="ux4g-btn ux4g-btn-text-primary ux4g-btn-lg"
                >
                  {t('openDecision')}
                </Link>
              </div>
            </li>
          ))}
        </ul>
      )}

      <p className="ux4g-body-s-default ux4g-text-neutral-tertiary ux4g-mt-xl">
        {t('decidedTotal', {count: work.decided_total})}
      </p>
    </section>
  );
}
