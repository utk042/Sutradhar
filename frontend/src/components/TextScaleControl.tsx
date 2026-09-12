'use client';

import {useCallback, useEffect, useState} from 'react';
import {useTranslations} from 'next-intl';

/**
 * A− / A / A+ text size control.
 *
 * UX4G 2.1.0 ships no Accessibility Bar (see src/styles/app.css §2), so this is
 * built from UX4G button classes over a single root multiplier. Because 2.1.0
 * expresses component sizes in rem, changing the root font size scales the whole
 * interface rather than only body copy.
 *
 * Accessibility notes:
 * - A labelled group, so a screen reader announces what the three buttons do.
 * - Each button is a real <button>, reachable and operable by keyboard.
 * - `aria-pressed` marks the active step, so the current size is conveyed
 *   without relying on the visual fill.
 * - The change is announced through a polite live region, because a font-size
 *   change is otherwise silent to a screen reader user.
 * - `ux4g-btn-lg` is used deliberately: `ux4g-btn-md` is 2.5rem (40px), under
 *   the 44x44 minimum target Design.md §9 mandates.
 */

const STEPS = [0.875, 1, 1.125, 1.25] as const;
const DEFAULT_INDEX = 1;
const STORAGE_KEY = 'sutradhar.textScale';

function apply(index: number) {
  const root = document.documentElement;
  root.style.setProperty('--sutradhar-text-scale', String(STEPS[index]));
  root.setAttribute('data-sutradhar-text-scale', String(STEPS[index]));
}

export default function TextScaleControl() {
  const t = useTranslations('accessibility');
  const [index, setIndex] = useState(DEFAULT_INDEX);
  const [announcement, setAnnouncement] = useState('');

  // Restore the officer's last choice. Wrapped because storage access throws in
  // a locked-down browser profile, and a failure here must not break the page.
  useEffect(() => {
    try {
      const stored = window.localStorage.getItem(STORAGE_KEY);
      if (stored !== null) {
        const parsed = Number(stored);
        if (Number.isInteger(parsed) && parsed >= 0 && parsed < STEPS.length) {
          setIndex(parsed);
          apply(parsed);
        }
      }
    } catch {
      /* storage unavailable — keep the default size */
    }
  }, []);

  const change = useCallback(
    (next: number) => {
      const clamped = Math.min(Math.max(next, 0), STEPS.length - 1);
      setIndex(clamped);
      apply(clamped);
      setAnnouncement(t('currentSize', {percent: Math.round(STEPS[clamped] * 100)}));
      try {
        window.localStorage.setItem(STORAGE_KEY, String(clamped));
      } catch {
        /* storage unavailable — the change still applies for this visit */
      }
    },
    [t]
  );

  return (
    <div
      role="group"
      aria-label={t('groupLabel')}
      className="ux4g-d-flex ux4g-ai-center ux4g-gap-xs"
    >
      <button
        type="button"
        className="ux4g-btn ux4g-btn-text-neutral ux4g-btn-lg"
        onClick={() => change(index - 1)}
        disabled={index === 0}
        aria-label={t('decrease')}
      >
        {t('decreaseShort')}
      </button>
      <button
        type="button"
        className="ux4g-btn ux4g-btn-text-neutral ux4g-btn-lg"
        onClick={() => change(DEFAULT_INDEX)}
        aria-pressed={index === DEFAULT_INDEX}
        aria-label={t('reset')}
      >
        {t('resetShort')}
      </button>
      <button
        type="button"
        className="ux4g-btn ux4g-btn-text-neutral ux4g-btn-lg"
        onClick={() => change(index + 1)}
        disabled={index === STEPS.length - 1}
        aria-label={t('increase')}
      >
        {t('increaseShort')}
      </button>
      <span role="status" aria-live="polite" className="sutradhar-sr-only">
        {announcement}
      </span>
    </div>
  );
}
