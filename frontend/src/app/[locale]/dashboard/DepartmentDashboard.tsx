'use client';

import {useCallback, useEffect, useState} from 'react';
import {useFormatter, useTranslations} from 'next-intl';
import Breadcrumb from '@/components/Breadcrumb';
import DecisionsChart from '@/components/DecisionsChart';
import FindingsChart from '@/components/FindingsChart';
import StatCard from '@/components/StatCard';
import OfficerRoster from '@/components/OfficerRoster';
import DepartmentAudit from '@/components/DepartmentAudit';
import {
  getDepartment,
  getStats,
  type Department,
  type DepartmentStats
} from '@/lib/api';

/**
 * The head of department's screen.
 *
 * Three numbers, the people, and the record. Nothing here decides anything —
 * this is oversight, and the things that change something (adding an officer,
 * suspending one, moving a file) each say plainly what they will do.
 *
 * Which of the two dashboards an officer gets is decided by DashboardClient;
 * by the time this renders, the caller is known to be a head. The server
 * refuses an officer every one of these routes regardless.
 */
export default function DepartmentDashboard() {
  const t = useTranslations('dashboard');
  const tn = useTranslations('nav');
  const format = useFormatter();

  const [department, setDepartment] = useState<Department | null>(null);
  const [stats, setStats] = useState<DepartmentStats | null>(null);

  const load = useCallback(async () => {
    const [dept, numbers] = await Promise.all([getDepartment(), getStats()]);
    if (dept.ok) setDepartment(dept.data);
    if (numbers.ok) setStats(numbers.data);
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  if (department === null) return null;

  const averageLabel =
    stats?.average_seconds == null
      ? t('noneYet')
      : stats.average_seconds < 90
        ? t('seconds', {value: Math.round(stats.average_seconds)})
        : t('minutes', {value: Math.round(stats.average_seconds / 60)});

  return (
    <section className="sutradhar-page ux4g-p-l">
      <Breadcrumb
        label={tn('breadcrumb')}
        items={[{label: tn('desk'), href: '/'}, {label: tn('dashboard')}]}
      />
      <h1 className="ux4g-heading-l-strong ux4g-mb-xs">
        {t('title', {department: department.name})}
      </h1>
      <p className="ux4g-body-m-default ux4g-text-neutral-secondary ux4g-mb-l">
        {t('subtitle')}
      </p>

      {/* The three numbers, plus what is waiting right now.
          The tone says what kind of number each is, never how big: a queue is
          the brand hue because it is neither good nor bad, finished work is
          success, and the flag count turns amber only when it is not zero. */}
      <div className="sutradhar-stat-row ux4g-mb-l">
        {[
          {
            label: t('statProcessed'),
            value: String(stats?.processed_today ?? 0),
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
            value: String(stats?.flags_raised ?? 0),
            tone: (stats?.flags_raised ?? 0) > 0 ? ('warning' as const) : ('neutral' as const),
            icon: 'flag'
          },
          {
            label: t('statPending'),
            value: String(stats?.pending_now ?? 0),
            tone: 'brand' as const,
            icon: 'pending_actions'
          }
        ].map((stat) => (
          <StatCard
            key={stat.label}
            label={stat.label}
            value={stat.value}
            tone={stat.tone}
            icon={stat.icon}
          />
        ))}
      </div>

      {/* The same two charts an officer sees, over the whole office. */}
      {stats !== null && (
        <div className="sutradhar-chart-row ux4g-mb-xl">
          <DecisionsChart days={stats.daily} />
          <FindingsChart findings={stats.findings} />
        </div>
      )}

      <OfficerRoster onChanged={load} />
      <DepartmentAudit />

      <p className="ux4g-body-s-default ux4g-text-neutral-tertiary ux4g-mt-xl">
        {format.dateTime(new Date(), {dateStyle: 'long', timeStyle: 'short'})}
      </p>
    </section>
  );
}
