'use client';

import {useTranslations} from 'next-intl';
import ChartTable from '@/components/ChartTable';
import type {FindingTally} from '@/lib/api';

/**
 * How the checks came out.
 *
 * ## Why this shape
 *
 * Three states, and the reader's job is to compare their magnitudes — so bars,
 * horizontal, because the labels are phrases rather than words and horizontal
 * bars give a phrase room to be read.
 *
 * **Separate rows, never a stack.** The three states mean good, bad and
 * uncertain, so they wear UX4G's reserved status colours rather than a
 * categorical palette. But green and red do not separate under colour blindness
 * — ΔE 6.1 deuteranopia in light, 4.2 in dark, against a floor of 6 — so they
 * are never drawn touching. Each state gets its own row, its own written label
 * and its own count, and the colour is the third thing saying what the row
 * already says twice. That is the mitigation the status palette is supposed to
 * ship with: an icon and a label, never colour alone.
 *
 * The order is fixed and meaningful — settled, then the two that need a person
 * — so it never re-sorts by value. A bar that moves when the numbers change is
 * a bar nobody can learn.
 *
 * ## The marks
 *
 * Each bar sits in a track one step off the surface, so a zero is still a
 * visible row rather than a missing one. Bars are thin with a rounded end, and
 * the count is written at the tip, outside the fill, where it can never be
 * clipped by a short bar.
 *
 * Contrast against the card, measured: success 9.4:1 light and 11.6:1 dark,
 * error 9.4 and 11.6, warning 5.4 and 13.1. All well past the 3:1 a mark needs.
 * These are UX4G's `--ux4g-text-status-*` steps rather than the `bg-*-strong`
 * ones, which would have put the warning bar at 2.4:1 on a white card.
 */

type Row = {
  key: 'verified' | 'mismatch' | 'unverifiable';
  tone: 'success' | 'danger' | 'warning';
  icon: string;
};

//: Fixed order: what is settled, then what needs a person. Never sorted by value.
const ROWS: Row[] = [
  {key: 'verified', tone: 'success', icon: 'check_circle'},
  {key: 'mismatch', tone: 'danger', icon: 'cancel'},
  {key: 'unverifiable', tone: 'warning', icon: 'help'}
];

export default function FindingsChart({findings}: {findings: FindingTally}) {
  const t = useTranslations('charts');
  const tf = useTranslations('finding');

  const total = findings.verified + findings.mismatch + findings.unverifiable;
  const peak = Math.max(1, findings.verified, findings.mismatch, findings.unverifiable);

  return (
    <figure className="sutradhar-chart ux4g-card ux4g-card-outline">
      <div className="ux4g-card-body">
        <figcaption>
          <h3 className="ux4g-heading-xs-strong">{t('findingsTitle')}</h3>
          <p className="ux4g-body-s-default ux4g-text-neutral-secondary ux4g-mb-m">
            {t('findingsSubtitle', {count: total})}
          </p>
        </figcaption>

        {total === 0 ? (
          <p className="ux4g-body-m-default ux4g-text-neutral-secondary">
            {t('findingsEmpty')}
          </p>
        ) : (
          <>
            <ul className="sutradhar-list-reset sutradhar-bars">
              {ROWS.map((row) => {
                const count = findings[row.key];
                return (
                  <li key={row.key} className={`sutradhar-bar-row sutradhar-tone-${row.tone}`}>
                    <span className="sutradhar-bar-label">
                      <span className="ux4g-icon-outlined sutradhar-bar-icon" aria-hidden="true">
                        {row.icon}
                      </span>
                      {tf(row.key)}
                    </span>
                    <span className="sutradhar-bar-track">
                      <span
                        className="sutradhar-bar-fill"
                        style={{width: `${(count / peak) * 100}%`}}
                      />
                    </span>
                    <span className="sutradhar-bar-count sutradhar-figures">{count}</span>
                  </li>
                );
              })}
            </ul>

            <ChartTable
              label={t('showTable')}
              caption={t('findingsTitle')}
              head={[t('colResult'), t('colCount')]}
              rows={ROWS.map((row) => [tf(row.key), String(findings[row.key])])}
            />
          </>
        )}
      </div>
    </figure>
  );
}
