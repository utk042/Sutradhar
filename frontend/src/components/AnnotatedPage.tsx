'use client';

import {useMemo, useState} from 'react';
import {useTranslations} from 'next-intl';
import type {Finding} from '@/lib/api';
import {documentPageUrl} from '@/lib/api';
import {fieldLabel} from '@/lib/fieldLabel';

/**
 * The document itself, with the checks marked on the page.
 *
 * The page is rendered server-side and shown as an image; the marks are
 * positioned over it as percentages, so they stay in place at any width without
 * the browser needing to know anything about PDFs.
 *
 * Two checks can examine the same value — the records match and the rule about
 * it — and they arrive with identical boxes. Drawn naively that is two marks
 * stacked exactly on top of each other, and a click on an ambiguous target.
 * Marks are grouped by position: one mark per place on the page, showing the
 * most serious verdict there, and selecting it opens that finding.
 *
 * Each mark is a button with a written label, so the page is navigable by
 * keyboard and readable without colour.
 *
 * The zoom exists because it has to. A4 rendered into half of a 1366px screen
 * puts certificate text at roughly eight points — visible, but not readable by
 * the officers this is built for. Zooming scales the frame; the marks are
 * positioned in percentages and follow it without any arithmetic.
 */

//: Multiples of the pane width. "Fit" is the whole page in view; the rest
//: trade that for legibility, and the frame scrolls.
const ZOOMS = [1, 1.5, 2, 3] as const;

const SEVERITY_RANK = {blocking: 0, warning: 1, info: 2} as const;
const STATUS_RANK = {mismatch: 0, unverifiable: 1, verified: 2} as const;

interface Mark {
  key: string;
  left: number;
  top: number;
  width: number;
  height: number;
  finding: Finding;
  alsoCount: number;
}

function marksFor(findings: Finding[], page: number): Mark[] {
  const byPosition = new Map<string, Finding[]>();

  for (const finding of findings) {
    if (
      finding.page_number !== page ||
      finding.box_left === null ||
      finding.box_top === null ||
      finding.box_width === null ||
      finding.box_height === null
    ) {
      continue;
    }
    // Rounded, so two boxes that differ by a rounding error still group.
    const key = [finding.box_left, finding.box_top, finding.box_width, finding.box_height]
      .map((n) => (n as number).toFixed(4))
      .join(':');
    byPosition.set(key, [...(byPosition.get(key) ?? []), finding]);
  }

  return [...byPosition.entries()].map(([key, group]) => {
    const leading = [...group].sort(
      (a, b) =>
        SEVERITY_RANK[a.severity] - SEVERITY_RANK[b.severity] ||
        STATUS_RANK[a.status] - STATUS_RANK[b.status]
    )[0];
    return {
      key,
      left: leading.box_left as number,
      top: leading.box_top as number,
      width: leading.box_width as number,
      height: leading.box_height as number,
      finding: leading,
      alsoCount: group.length - 1
    };
  });
}

export default function AnnotatedPage({
  documentId,
  pageCount,
  findings,
  selectedId,
  onSelect
}: {
  documentId: number;
  pageCount: number;
  findings: Finding[];
  selectedId: number | null;
  onSelect: (id: number) => void;
}) {
  const t = useTranslations('review');
  const tf = useTranslations('finding');
  const [page, setPage] = useState(1);
  const [zoomIndex, setZoomIndex] = useState(0);
  const marks = useMemo(() => marksFor(findings, page), [findings, page]);
  const zoom = ZOOMS[zoomIndex];

  return (
    <div>
      <p className="sutradhar-sr-only">{t('annotationHint')}</p>

      <div className="ux4g-d-flex ux4g-ai-center ux4g-gap-s ux4g-mb-xs sutradhar-wrap">
        <span className="ux4g-body-s-default ux4g-text-neutral-secondary">
          {t('zoom')}
        </span>
        <button
          type="button"
          className="ux4g-btn ux4g-btn-outline-neutral ux4g-btn-lg"
          disabled={zoomIndex === 0}
          onClick={() => setZoomIndex((z) => Math.max(0, z - 1))}
        >
          {t('zoomOut')}
        </button>
        <span className="ux4g-body-s-default" aria-live="polite">
          {zoomIndex === 0 ? t('zoomFit') : t('zoomLevel', {percent: Math.round(zoom * 100)})}
        </span>
        <button
          type="button"
          className="ux4g-btn ux4g-btn-outline-neutral ux4g-btn-lg"
          disabled={zoomIndex === ZOOMS.length - 1}
          onClick={() => setZoomIndex((z) => Math.min(ZOOMS.length - 1, z + 1))}
        >
          {t('zoomIn')}
        </button>
      </div>

      <div className="sutradhar-page-scroll">
        <div className="sutradhar-page-frame" style={{width: `${zoom * 100}%`}}>
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            className="sutradhar-page-image"
            src={documentPageUrl(documentId, page)}
            alt={t('pageAlt', {page, total: pageCount})}
          />
          {marks.map((mark) => (
            <button
            key={mark.key}
            type="button"
            className="sutradhar-page-mark"
            data-status={mark.finding.status}
            aria-pressed={selectedId === mark.finding.id}
            aria-label={`${fieldLabel(tf as never, mark.finding.field)}: ${tf(
              mark.finding.status
            )}. ${t('viewEvidence')}`}
            style={{
              left: `${mark.left * 100}%`,
              top: `${mark.top * 100}%`,
              width: `${mark.width * 100}%`,
              height: `${mark.height * 100}%`
            }}
            onClick={() => onSelect(mark.finding.id)}
          >
            <span className="sutradhar-page-mark-label" aria-hidden="true">
              {tf(mark.finding.status)}
            </span>
          </button>
          ))}
        </div>
      </div>

      {pageCount > 1 && (
        <nav
          className="ux4g-d-flex ux4g-ai-center ux4g-gap-s ux4g-mt-s"
          aria-label={t('pageNav')}
        >
          <button
            type="button"
            className="ux4g-btn ux4g-btn-outline-neutral ux4g-btn-lg"
            disabled={page <= 1}
            onClick={() => setPage((p) => Math.max(1, p - 1))}
          >
            {t('previousPage')}
          </button>
          <span className="ux4g-body-m-default" aria-live="polite">
            {t('pageOf', {page, total: pageCount})}
          </span>
          <button
            type="button"
            className="ux4g-btn ux4g-btn-outline-neutral ux4g-btn-lg"
            disabled={page >= pageCount}
            onClick={() => setPage((p) => Math.min(pageCount, p + 1))}
          >
            {t('nextPage')}
          </button>
        </nav>
      )}
    </div>
  );
}
