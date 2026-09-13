'use client';

import {useId} from 'react';
import {useTranslations} from 'next-intl';

/**
 * A table that is wider than the screen it is on.
 *
 * Some tables here genuinely have more columns than a 360px phone can show —
 * the officer roster, the audit trail. The page itself must never scroll
 * sideways, so they scroll inside their own box. Two things make that box
 * usable rather than a place where columns quietly disappear:
 *
 * 1. It is a named region with `tabIndex={0}`. WCAG 2.1.1 needs a keyboard to
 *    be able to reach scrollable content; without a tab stop the only way to
 *    move a scroll container is a mouse or a finger. A screen reader announces
 *    it by name, so it is clear what is being scrolled.
 * 2. On a narrow screen it says, in words, that there is more to the side. A
 *    cut-off column with no edge shadow and no sentence is simply a column
 *    nobody knows about — which is exactly how the status and the Review
 *    button used to vanish on a phone.
 *
 * Where a table can be replaced outright by something that fits — the
 * officer's own list of waiting files — it is, and this is not used. This is
 * for the tables that really are tabular.
 */
export default function TableScroll({
  label,
  children
}: {
  /** Names the region, e.g. "Your officers". */
  label: string;
  children: React.ReactNode;
}) {
  const t = useTranslations('table');
  const hintId = useId();

  return (
    <>
      <div
        className="sutradhar-table-scroll"
        role="region"
        aria-label={label}
        aria-describedby={hintId}
        tabIndex={0}
      >
        {children}
      </div>
      <p
        id={hintId}
        className="sutradhar-only-narrow ux4g-body-s-default ux4g-text-neutral-secondary ux4g-mt-xs"
      >
        {t('scrollHint')}
      </p>
    </>
  );
}
