'use client';

import {useTranslations} from 'next-intl';
import type {DocumentStatus} from '@/lib/api';

/**
 * A document's state, always as a word.
 *
 * UX4G tags carry colour, but the word is what conveys the state — an officer
 * reading in greyscale, or with a colour vision difference, loses nothing. That
 * is the rule throughout this interface: colour reinforces, it never informs.
 */
const VARIANT: Record<DocumentStatus, string> = {
  uploaded: 'ux4g-tag-tonal-neutral',
  processing: 'ux4g-tag-tonal-info',
  pending_review: 'ux4g-tag-tonal-warning',
  approved: 'ux4g-tag-tonal-success',
  rejected: 'ux4g-tag-tonal-error',
  failed: 'ux4g-tag-tonal-error'
};

export default function StatusTag({status}: {status: DocumentStatus}) {
  const t = useTranslations('status');
  return (
    <span className={`${VARIANT[status] ?? 'ux4g-tag-tonal-neutral'} ux4g-tag-s`}>
      {t(status)}
    </span>
  );
}
