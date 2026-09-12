'use client';

import {useTranslations} from 'next-intl';
import type {ProgressState} from '@/lib/progress';

/**
 * What the system is doing, in the officer's words.
 *
 * "Matching against records", never the name of a component or a step. Each
 * check's state is a word — Running, Done — with the spinner and the tick only
 * reinforcing it.
 *
 * The list is built from what the stream reports rather than from a fixed set,
 * so enabling a fourth check in pipeline.yaml adds a line here with no change to
 * this file.
 */
export default function CheckProgressPanel({progress}: {progress: ProgressState}) {
  const t = useTranslations('review');
  const tc = useTranslations('checks');

  const heading =
    progress.phase === 'reading' || progress.phase === 'connecting'
      ? t('reading')
      : t('running');

  return (
    <div className="ux4g-card ux4g-card-solid" aria-live="polite">
      <div className="ux4g-card-body">
        <div className="ux4g-d-flex ux4g-ai-center ux4g-gap-s ux4g-mb-s">
          {/* The package README documents ux4g-spinner-{primary,inverse,danger}-
              {full,split,partial}; none of those classes exist in the shipped
              CSS, which has only the base class and the five sizes. */}
          <span className="ux4g-spinner ux4g-spinner-md sutradhar-spinner" role="presentation" />
          <div>
            <p className="ux4g-body-m-default">{heading}</p>
            <p className="ux4g-body-s-default ux4g-text-neutral-secondary">
              {t('runningHint')}
            </p>
          </div>
        </div>

        {progress.checks.length > 0 && (
          <>
            <h3 className="sutradhar-sr-only">{t('progressTitle')}</h3>
            <ul className="sutradhar-list-reset">
              {progress.checks.map((check) => (
                <li
                  key={check.name}
                  className="ux4g-d-flex ux4g-ai-center ux4g-jc-between ux4g-gap-s ux4g-mb-xs sutradhar-wrap"
                >
                  <span className="ux4g-body-m-default">{tc(check.name)}</span>
                  <span
                    className={
                      check.state === 'done'
                        ? 'ux4g-tag-tonal-success ux4g-tag-s'
                        : check.state === 'failed'
                          ? 'ux4g-tag-tonal-error ux4g-tag-s'
                          : 'ux4g-tag-tonal-info ux4g-tag-s'
                    }
                  >
                    {check.state === 'done'
                      ? t('checkDone')
                      : check.state === 'failed'
                        ? t('checkFailed')
                        : t('checkRunning')}
                  </span>
                </li>
              ))}
            </ul>
          </>
        )}
      </div>
    </div>
  );
}
