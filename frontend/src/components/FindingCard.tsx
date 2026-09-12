'use client';

import {useId, useState} from 'react';
import {useTranslations} from 'next-intl';
import type {Finding} from '@/lib/api';
import {fieldLabel} from '@/lib/fieldLabel';

/**
 * One check result, with its evidence one click away.
 *
 * Every state is named in words — "Verified", "Does not match", "Needs your
 * check" — and the tag colour only reinforces the word. The evidence panel puts
 * the document's value beside the record's value and cites where the record
 * came from, because a finding an officer cannot check is just an assertion.
 */
const STATUS_TAG: Record<Finding['status'], string> = {
  verified: 'ux4g-tag-tonal-success',
  mismatch: 'ux4g-tag-tonal-error',
  unverifiable: 'ux4g-tag-tonal-warning'
};

const SEVERITY_TAG: Record<Finding['severity'], string> = {
  blocking: 'ux4g-tag-outline-error',
  warning: 'ux4g-tag-outline-warning',
  info: 'ux4g-tag-outline-neutral'
};

export default function FindingCard({
  finding,
  expanded,
  onToggle
}: {
  finding: Finding;
  /** Controlled by the parent when an annotation in the document selects it. */
  expanded?: boolean;
  onToggle?: (id: number) => void;
}) {
  const t = useTranslations('review');
  const tf = useTranslations('finding');
  const tc = useTranslations('checks');
  const [openLocally, setOpenLocally] = useState(false);
  const panelId = useId();

  // Controlled when the parent passes `expanded`, self-managed otherwise, so the
  // card works on its own and as part of the annotation layer.
  const open = expanded ?? openLocally;

  const severityLabel =
    finding.severity === 'blocking'
      ? tf('severityBlocking')
      : finding.severity === 'warning'
        ? tf('severityWarning')
        : tf('severityInfo');

  return (
    <li className="ux4g-card ux4g-card-outline ux4g-mb-s" id={`finding-${finding.id}`}>
      <div className="ux4g-card-body">
        <div className="ux4g-d-flex ux4g-ai-center ux4g-gap-s ux4g-mb-xs sutradhar-wrap">
          <span className={`${STATUS_TAG[finding.status]} ux4g-tag-s`}>
            {tf(finding.status)}
          </span>
          <span className="ux4g-heading-xxs-strong">{fieldLabel(tf as never, finding.field)}</span>
          {finding.severity !== 'info' && (
            <span className={`${SEVERITY_TAG[finding.severity]} ux4g-tag-s`}>
              {severityLabel}
            </span>
          )}
        </div>

        <p className="ux4g-body-m-default ux4g-mb-xs">{finding.explanation_en}</p>
        {/* Which check said this. Two checks can look at the same field — the
            records match and the rule about it — and without this they render as
            two identical cards. The officer's wording, never the agent name. */}
        <p className="ux4g-body-s-default ux4g-text-neutral-tertiary ux4g-mb-s">
          {t('fromCheck', {check: tc.has(finding.agent) ? tc(finding.agent) : finding.agent})}
        </p>

        <button
          type="button"
          className="ux4g-btn ux4g-btn-text-primary ux4g-btn-lg"
          aria-expanded={open}
          aria-controls={panelId}
          onClick={() => (onToggle ? onToggle(finding.id) : setOpenLocally((v) => !v))}
        >
          {open ? t('closeEvidence') : t('viewEvidence')}
        </button>

        <div id={panelId} hidden={!open} className="ux4g-mt-s">
          <table className="ux4g-table ux4g-table-s ux4g-w-100">
            <caption className="sutradhar-sr-only">{t('evidenceTitle')}</caption>
            <tbody>
              <tr>
                <th scope="row" className="ux4g-table-cell-text">{t('onDocument')}</th>
                <td className="ux4g-table-cell-text">
                  {finding.document_value ?? t('notRecorded')}
                </td>
              </tr>
              <tr>
                <th scope="row" className="ux4g-table-cell-text">{t('inRecords')}</th>
                <td className="ux4g-table-cell-text">
                  {finding.reference_value ?? t('notRecorded')}
                </td>
              </tr>
              <tr>
                <th scope="row" className="ux4g-table-cell-text">{t('source')}</th>
                <td className="ux4g-table-cell-text">{finding.reference_source}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </li>
  );
}
