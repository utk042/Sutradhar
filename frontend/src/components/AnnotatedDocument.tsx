'use client';

import {useMemo} from 'react';
import {useTranslations} from 'next-intl';
import type {Finding} from '@/lib/api';
import {fieldLabel} from '@/lib/fieldLabel';

/**
 * The document's text with each checked value marked where it appears.
 *
 * This is the annotation layer the review screen is built around: rather than
 * reading a list of findings and then hunting for the values in the document, an
 * officer sees the document and the verdicts together. Selecting a mark opens
 * that finding's evidence.
 *
 * Every mark carries its status as a word, so it reads correctly in greyscale
 * and to a screen reader; the colour and the underline only reinforce it. Each
 * mark is a real button, so the whole annotation layer is reachable by keyboard
 * in document order.
 *
 * Values are matched literally against the text. A finding whose value cannot be
 * located is simply not marked — it still appears in the findings list, so
 * nothing is hidden by a failed match.
 */

interface Segment {
  text: string;
  finding?: Finding;
}

/** Split the text into plain runs and annotated runs, left to right. */
function annotate(text: string, findings: Finding[]): Segment[] {
  type Hit = {start: number; end: number; finding: Finding};
  const hits: Hit[] = [];

  for (const finding of findings) {
    const value = finding.document_value?.trim();
    // Long excerpts (the injection quote) and absent values are not marked:
    // the first would swallow half the document, the second has nothing to mark.
    if (!value || value.length < 2 || value.length > 80) continue;

    let from = 0;
    for (;;) {
      const at = text.indexOf(value, from);
      if (at === -1) break;
      // Skip a position already claimed by an earlier finding, so two findings
      // never produce overlapping marks.
      const clash = hits.some((h) => at < h.end && at + value.length > h.start);
      if (!clash) {
        hits.push({start: at, end: at + value.length, finding});
        break; // mark the first free occurrence only
      }
      from = at + 1;
    }
  }

  hits.sort((a, b) => a.start - b.start);

  const segments: Segment[] = [];
  let cursor = 0;
  for (const hit of hits) {
    if (hit.start > cursor) segments.push({text: text.slice(cursor, hit.start)});
    segments.push({text: text.slice(hit.start, hit.end), finding: hit.finding});
    cursor = hit.end;
  }
  if (cursor < text.length) segments.push({text: text.slice(cursor)});
  return segments;
}

export default function AnnotatedDocument({
  text,
  findings,
  selectedId,
  onSelect
}: {
  text: string;
  findings: Finding[];
  selectedId: number | null;
  onSelect: (id: number) => void;
}) {
  const t = useTranslations('review');
  const tf = useTranslations('finding');
  const segments = useMemo(() => annotate(text, findings), [text, findings]);

  return (
    <div className="sutradhar-document">
      <p className="sutradhar-sr-only">{t('annotationHint')}</p>
      <pre className="sutradhar-document-text">
        {segments.map((segment, index) =>
          segment.finding ? (
            <button
              key={index}
              type="button"
              className="sutradhar-annotation"
              data-status={segment.finding.status}
              aria-pressed={selectedId === segment.finding.id}
              aria-label={`${fieldLabel(tf as never, segment.finding.field)}: ${tf(
                segment.finding.status
              )}. ${t('viewEvidence')}`}
              onClick={() => onSelect(segment.finding!.id)}
            >
              {segment.text}
              <span className="sutradhar-annotation-label" aria-hidden="true">
                {tf(segment.finding.status)}
              </span>
            </button>
          ) : (
            <span key={index}>{segment.text}</span>
          )
        )}
      </pre>
    </div>
  );
}
