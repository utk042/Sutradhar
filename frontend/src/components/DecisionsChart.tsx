'use client';

import {useFormatter, useTranslations} from 'next-intl';
import ChartTable from '@/components/ChartTable';
import type {DayCount} from '@/lib/api';

/**
 * Decisions, day by day.
 *
 * ## Why this shape
 *
 * The job is change over time, so columns. **One series, not two.** The obvious
 * design — approved and rejected stacked in each column — is the one thing this
 * data must not be. Green against red is the classic colour-vision collapse,
 * and measured against the skill's own validator UX4G's status greens and reds
 * separate by ΔE 6.1 under deuteranopia in the light theme and only 4.2 in
 * dark, against a floor of 6 and a target of 8. Below the floor no amount of
 * labelling rescues an adjacent pair, so the pair is not drawn adjacent: the
 * columns carry the total decided, and the approved-and-rejected split is told
 * in the tiles above where each number has its own words.
 *
 * One series, so no legend: the heading says what is plotted.
 *
 * ## The marks
 *
 * Thin columns, capped at 24px, with a rounded top and a square foot on the
 * baseline. One solid hairline baseline a step off the surface, no gridlines —
 * seven small integers do not need them, and every value is written on its own
 * cap. Nothing is dashed. Only today and the busiest day are emphasised; the
 * rest are a quiet wash of the same hue, which is what makes the emphasis mean
 * anything.
 *
 * Brand hue rather than a status colour: a count of decisions is neither good
 * nor bad, and the status palette is reserved for things that are.
 *
 * ## Reading it without seeing it
 *
 * Every value is printed on its cap, so no figure is behind a hover and there
 * is nothing for a tooltip to reveal — hover is a highlight, not a disclosure.
 * The plot is `aria-hidden`, because a screen reader would otherwise read a row
 * of bare numbers with no structure; the table underneath carries the same
 * figures with their dates attached, which is the better reading of the same
 * data.
 *
 * Plain HTML and CSS, no SVG and no library. The brief rules out a charting
 * library, and for seven columns one would be hundreds of kilobytes to avoid a
 * percentage.
 */
export default function DecisionsChart({days}: {days: DayCount[]}) {
  const t = useTranslations('charts');
  const format = useFormatter();

  const peak = Math.max(1, ...days.map((day) => day.decided));
  const total = days.reduce((sum, day) => sum + day.decided, 0);
  const todayIso = new Date().toISOString().slice(0, 10);

  return (
    <figure className="sutradhar-chart ux4g-card ux4g-card-outline">
      <div className="ux4g-card-body">
        <figcaption>
          <h3 className="ux4g-heading-xs-strong">{t('decisionsTitle')}</h3>
          <p className="ux4g-body-s-default ux4g-text-neutral-secondary ux4g-mb-m">
            {t('decisionsSubtitle', {count: total})}
          </p>
        </figcaption>

        {total === 0 ? (
          <p className="ux4g-body-m-default ux4g-text-neutral-secondary">
            {t('decisionsEmpty')}
          </p>
        ) : (
          <>
            <div className="sutradhar-columns" aria-hidden="true">
              {days.map((day) => {
                const isToday = day.day === todayIso;
                const isPeak = day.decided === peak;
                return (
                  <div className="sutradhar-column" key={day.day}>
                    <span className="sutradhar-column-cap">{day.decided}</span>
                    <div className="sutradhar-column-track">
                      <div
                        className={[
                          'sutradhar-column-bar',
                          day.decided === 0 && 'sutradhar-column-none',
                          isToday
                            ? 'sutradhar-column-today'
                            : isPeak && 'sutradhar-column-peak'
                        ]
                          .filter(Boolean)
                          .join(' ')}
                        style={{height: `${(day.decided / peak) * 100}%`}}
                      />
                    </div>
                    <span
                      className={`sutradhar-column-day${
                        isToday ? ' sutradhar-column-day-now' : ''
                      }`}
                    >
                      {format.dateTime(new Date(day.day), {weekday: 'short'})}
                    </span>
                  </div>
                );
              })}
            </div>

            <ChartTable
              label={t('showTable')}
              caption={t('decisionsTitle')}
              head={[t('colDay'), t('colDecided')]}
              rows={days.map((day) => [
                format.dateTime(new Date(day.day), {dateStyle: 'medium'}),
                String(day.decided)
              ])}
            />
          </>
        )}
      </div>
    </figure>
  );
}
