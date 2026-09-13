'use client';

import {useCallback, useEffect, useState} from 'react';
import {useFormatter, useTranslations} from 'next-intl';
import {useRouter} from '@/i18n/routing';
import OfficerRoster from '@/components/OfficerRoster';
import DepartmentAudit from '@/components/DepartmentAudit';
import {
  getDepartment,
  getStats,
  me,
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
 * An officer who reaches this URL is sent back to their desk rather than shown
 * an error: the server refuses them anyway, and being told off for opening a
 * page you cannot use is not useful.
 */
export default function DashboardClient() {
  const t = useTranslations('dashboard');
  const format = useFormatter();
  const router = useRouter();

  const [department, setDepartment] = useState<Department | null>(null);
  const [stats, setStats] = useState<DepartmentStats | null>(null);

  const load = useCallback(async () => {
    const [dept, numbers] = await Promise.all([getDepartment(), getStats()]);
    if (dept.ok) setDepartment(dept.data);
    if (numbers.ok) setStats(numbers.data);
  }, []);

  useEffect(() => {
    let active = true;
    me().then((who) => {
      if (!active) return;
      if (!who.ok) {
        router.replace('/login');
      } else if (who.data.role !== 'dept_head') {
        router.replace('/');
      } else {
        load();
      }
    });
    return () => {
      active = false;
    };
  }, [router, load]);

  if (department === null) return null;

  const averageLabel =
    stats?.average_seconds == null
      ? t('noneYet')
      : stats.average_seconds < 90
        ? t('seconds', {value: Math.round(stats.average_seconds)})
        : t('minutes', {value: Math.round(stats.average_seconds / 60)});

  return (
    <section className="sutradhar-page ux4g-p-l">
      <h1 className="ux4g-heading-l-strong ux4g-mb-xs">
        {t('title', {department: department.name})}
      </h1>
      <p className="ux4g-body-m-default ux4g-text-neutral-secondary ux4g-mb-l">
        {t('subtitle')}
      </p>

      {/* The three numbers, plus what is waiting right now. */}
      <div className="sutradhar-stat-row ux4g-mb-xl">
        {[
          {label: t('statProcessed'), value: String(stats?.processed_today ?? 0)},
          {label: t('statAverage'), value: averageLabel},
          {label: t('statFlags'), value: String(stats?.flags_raised ?? 0)},
          {label: t('statPending'), value: String(stats?.pending_now ?? 0)}
        ].map((stat) => (
          <div key={stat.label} className="ux4g-card ux4g-card-solid">
            <div className="ux4g-card-body">
              <p className="ux4g-body-s-default ux4g-text-neutral-secondary ux4g-mb-xs">
                {stat.label}
              </p>
              <p className="ux4g-heading-l-strong">{stat.value}</p>
            </div>
          </div>
        ))}
      </div>

      <OfficerRoster onChanged={load} />
      <DepartmentAudit />

      <p className="ux4g-body-s-default ux4g-text-neutral-tertiary ux4g-mt-xl">
        {format.dateTime(new Date(), {dateStyle: 'long', timeStyle: 'short'})}
      </p>
    </section>
  );
}
