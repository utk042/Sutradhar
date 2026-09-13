'use client';

import {useEffect, useState} from 'react';
import {useFormatter, useTranslations} from 'next-intl';
import {getAudit, type AuditPage} from '@/lib/api';

/**
 * The department's record of what happened.
 *
 * Two things matter here and they are both stated in words rather than implied.
 * First, whether the chain still verifies: a log that cannot say whether it has
 * been altered is not worth reading, so the answer is at the top either way.
 * Second, what each row means — "A document was approved", not the action code
 * the database stores.
 *
 * The rows carry no personal data. `audit.record` refuses to write a name, a
 * date of birth or a document number, so this can be read over a shoulder and
 * exported without becoming a leak.
 */
const PAGE_SIZE = 25;

export default function DepartmentAudit() {
  const t = useTranslations('dashboard');
  const ta = useTranslations('actions');
  const format = useFormatter();
  const [page, setPage] = useState<AuditPage | null>(null);
  const [offset, setOffset] = useState(0);

  useEffect(() => {
    getAudit(PAGE_SIZE, offset).then((result) => {
      if (result.ok) setPage(result.data);
    });
  }, [offset]);

  if (page === null) return null;

  return (
    <section aria-labelledby="audit">
      <h2 id="audit" className="ux4g-heading-s-strong ux4g-mb-s">
        {t('auditTitle')}
      </h2>

      <div
        className={`ux4g-alert ${
          page.chain_intact ? 'ux4g-alert-success' : 'ux4g-alert-error'
        } ux4g-mb-m`}
        role="status"
      >
        <span className="ux4g-body-m-default">
          {page.chain_intact ? t('auditIntact') : t('auditBroken')}
        </span>
      </div>

      {page.rows.length === 0 ? (
        <div className="ux4g-empty-state">
          <div className="ux4g-empty-state-content">
            <p className="ux4g-body-m-default">{t('noActivity')}</p>
          </div>
        </div>
      ) : (
        <>
          <div className="sutradhar-table-scroll">
            <table className="ux4g-table ux4g-table-m ux4g-table-zebra-rows ux4g-w-100">
              <thead>
                <tr>
                  <th scope="col">{t('colWhen')}</th>
                  <th scope="col">{t('colWhat')}</th>
                  <th scope="col">{t('colWho')}</th>
                  <th scope="col">{t('colFile')}</th>
                </tr>
              </thead>
              <tbody>
                {page.rows.map((row) => (
                  <tr key={row.sequence}>
                    <td className="ux4g-table-cell-text">
                      {format.dateTime(new Date(row.created_at), {
                        dateStyle: 'medium',
                        timeStyle: 'short'
                      })}
                    </td>
                    <td className="ux4g-table-cell-text">
                      {ta.has(row.action) ? ta(row.action) : row.action}
                    </td>
                    <td className="ux4g-table-cell-text">
                      {row.actor_role
                        ? row.actor_role === 'dept_head'
                          ? t('roleHead')
                          : t('roleOfficer')
                        : '—'}
                    </td>
                    <td className="ux4g-table-cell-text">
                      {row.document_id !== null ? `#${row.document_id}` : '—'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {page.total > PAGE_SIZE && (
            <nav className="ux4g-d-flex ux4g-ai-center ux4g-gap-m ux4g-mt-s sutradhar-wrap">
              <button
                type="button"
                className="ux4g-btn ux4g-btn-outline-neutral ux4g-btn-lg"
                disabled={offset === 0}
                onClick={() => setOffset((o) => Math.max(0, o - PAGE_SIZE))}
              >
                {t('newer')}
              </button>
              <span className="ux4g-body-s-default" aria-live="polite">
                {t('showing', {
                  from: offset + 1,
                  to: Math.min(offset + PAGE_SIZE, page.total),
                  total: page.total
                })}
              </span>
              <button
                type="button"
                className="ux4g-btn ux4g-btn-outline-neutral ux4g-btn-lg"
                disabled={offset + PAGE_SIZE >= page.total}
                onClick={() => setOffset((o) => o + PAGE_SIZE)}
              >
                {t('older')}
              </button>
            </nav>
          )}
        </>
      )}
    </section>
  );
}
