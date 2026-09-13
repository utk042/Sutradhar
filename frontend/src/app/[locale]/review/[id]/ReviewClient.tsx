'use client';

import {useCallback, useEffect, useId, useState} from 'react';
import {useFormatter, useTranslations} from 'next-intl';
import {useRouter} from '@/i18n/routing';
import AnnotatedDocument from '@/components/AnnotatedDocument';
import Breadcrumb from '@/components/Breadcrumb';
import AnnotatedPage from '@/components/AnnotatedPage';
import CheckProgressPanel from '@/components/CheckProgressPanel';
import FindingCard from '@/components/FindingCard';
import {fieldLabel} from '@/lib/fieldLabel';
import {
  INITIAL_PROGRESS,
  reduceProgress,
  watchProgress,
  type ProgressState
} from '@/lib/progress';
import StatusTag from '@/components/StatusTag';
import TableScroll from '@/components/TableScroll';
import {
  decide,
  documentFileUrl,
  getDocument,
  type DocumentDetail
} from '@/lib/api';

/**
 * The review screen.
 *
 * Split: the document on the left, what the checks found on the right. The
 * decision sits below, disabled until the checks have finished — an officer
 * cannot approve a file the system has not looked at yet.
 *
 * The language is the officer's. "Checking against records…", never the name of
 * a component or a step. The technical trace is behind a disclosure for
 * demonstrations and questions, which is the only place jargon is allowed.
 *
 * Nothing on this screen decides anything. The two buttons at the bottom are the
 * only thing in the system that does.
 *
 * Progress arrives over Server-Sent Events rather than polling. The stream is
 * the fast path, not the source of truth: when it closes — finished, dropped, or
 * never opened — the document is fetched and rendered from that. So a proxy that
 * kills the connection costs a moment, not correctness.
 */

export default function ReviewClient({documentId}: {documentId: number}) {
  const t = useTranslations('review');
  const tf = useTranslations('finding');
  const tn = useTranslations('nav');
  const format = useFormatter();
  const router = useRouter();

  const [doc, setDoc] = useState<DocumentDetail | null>(null);
  const [progress, setProgress] = useState<ProgressState>(INITIAL_PROGRESS);
  //: Which finding's evidence is open. Shared between the document's marks and
  //: the findings list, so selecting either reveals the same thing.
  const [selectedFinding, setSelectedFinding] = useState<number | null>(null);

  // Selecting a mark on the document opens that finding's evidence and brings
  // it into view, so the two halves of the screen stay in step.
  const selectFinding = useCallback((id: number) => {
    setSelectedFinding((current) => (current === id ? null : id));
    document.getElementById(`finding-${id}`)?.scrollIntoView({
      behavior: 'smooth',
      block: 'center'
    });
  }, []);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState<null | 'approved' | 'rejected'>(null);
  const [mode, setMode] = useState<null | 'reject' | 'override'>(null);
  const [reason, setReason] = useState('');
  const reasonId = useId();

  const load = useCallback(async () => {
    const result = await getDocument(documentId);
    if (result.ok) setDoc(result.data);
    else if (result.code === 'not_authenticated') router.replace('/login');
  }, [documentId, router]);

  useEffect(() => {
    load();
  }, [load]);

  // Follow the run live. The broker replays what has already happened, so
  // connecting after the checks have finished still shows what they did.
  const running = doc?.status === 'uploaded' || doc?.status === 'processing';
  useEffect(() => {
    if (!running) return;
    const close = watchProgress(
      documentId,
      (payload) => setProgress((current) => reduceProgress(current, payload)),
      () => {
        load();
      }
    );
    return close;
  }, [running, documentId, load]);

  if (doc === null) return null;

  const decided = doc.status === 'approved' || doc.status === 'rejected';
  const canDecide = doc.status === 'pending_review' && submitting === null;
  const flagged = doc.findings.filter((f) => f.status !== 'verified');

  // Most serious first. An officer scanning the panel should meet what needs
  // their attention before a list of things that were fine.
  const RANK = {blocking: 0, warning: 1, info: 2} as const;
  const ordered = [...doc.findings].sort((a, b) => RANK[a.severity] - RANK[b.severity]);

  async function submit(decision: 'approved' | 'rejected') {
    setError(null);
    setSubmitting(decision);
    const result = await decide(documentId, decision, {
      reason: decision === 'rejected' ? reason : undefined,
      override_note: decision === 'approved' && mode === 'override' ? reason : undefined
    });
    setSubmitting(null);

    if (result.ok) {
      router.push(`/review/${documentId}/decision`);
      return;
    }
    const known = [
      'reason_required',
      'override_note_required',
      'document_not_awaiting_review',
      'document_not_found',
      'network'
    ];
    setError(known.includes(result.code) ? t(`errors.${result.code}`) : t('errors.unexpected'));
  }

  function onApprove() {
    // A blocking finding needs a written note before approval is possible.
    if (doc!.has_blocking && mode !== 'override') {
      setMode('override');
      setReason('');
      return;
    }
    submit('approved');
  }

  function onReject() {
    if (mode !== 'reject') {
      setMode('reject');
      setReason('');
      return;
    }
    submit('rejected');
  }

  return (
    <section className="sutradhar-page ux4g-p-l">
      <Breadcrumb
        label={tn('breadcrumb')}
        items={[
          {label: tn('desk'), href: '/'},
          {label: t('crumb', {reference: doc.public_ref})}
        ]}
      />
      <div className="ux4g-d-flex ux4g-ai-center ux4g-gap-s ux4g-mb-l sutradhar-wrap">
        <h1 className="ux4g-heading-l-strong">{t('title', {reference: doc.public_ref})}</h1>
        <StatusTag status={doc.status} />
      </div>

      {error !== null && (
        <div className="ux4g-alert ux4g-alert-error ux4g-mb-l" role="alert">
          <span className="ux4g-body-m-default">{error}</span>
        </div>
      )}

      <div className="sutradhar-review-split ux4g-mb-xl">
        {/* Left: the document itself. */}
        <section aria-labelledby="pane-document">
          <h2 id="pane-document" className="ux4g-heading-s-strong ux4g-mb-s">
            {t('documentPane')}
          </h2>
          <div className="ux4g-card ux4g-card-outline ux4g-mb-s">
            <div className="ux4g-card-body">
              <p className="ux4g-body-m-default ux4g-mb-xs">{doc.original_filename}</p>
              <a
                className="ux4g-btn ux4g-btn-outline-primary ux4g-btn-lg"
                href={documentFileUrl(doc.id)}
                target="_blank"
                rel="noreferrer"
              >
                {t('readDocument')}
              </a>
            </div>
          </div>

          {/* The document itself where it can be rendered; the text it was read
              from where it cannot — a scan with no text layer, or anything that
              is not a PDF. The fallback says so rather than looking like a
              choice. */}
          {doc.page_count > 0 && doc.findings.length > 0 ? (
            <div className="ux4g-card ux4g-card-outline ux4g-mb-s">
              <div className="ux4g-card-body">
                <h3 className="ux4g-heading-xs-strong ux4g-mb-xs">{t('documentPage')}</h3>
                <AnnotatedPage
                  documentId={doc.id}
                  pageCount={doc.page_count}
                  findings={doc.findings}
                  selectedId={selectedFinding}
                  onSelect={selectFinding}
                />
              </div>
            </div>
          ) : (
            doc.extracted_text &&
            doc.findings.length > 0 && (
              <div className="ux4g-card ux4g-card-outline ux4g-mb-s">
                <div className="ux4g-card-body">
                  <h3 className="ux4g-heading-xs-strong ux4g-mb-xs">{t('documentText')}</h3>
                  <p className="ux4g-body-s-default ux4g-text-neutral-secondary ux4g-mb-s">
                    {t('textFallback')}
                  </p>
                  <AnnotatedDocument
                    text={doc.extracted_text}
                    findings={doc.findings}
                    selectedId={selectedFinding}
                    onSelect={selectFinding}
                  />
                </div>
              </div>
            )
          )}

          {Object.keys(doc.extracted).length > 0 && (
            <>
              <h3 className="ux4g-heading-xs-strong ux4g-mb-xs">{t('extractedTitle')}</h3>
              <TableScroll label={t('extractedTitle')}>
                <table className="ux4g-table ux4g-table-s ux4g-w-100">
                  <tbody>
                    {Object.entries(doc.extracted).map(([field, value]) => (
                      <tr key={field}>
                        <th scope="row" className="ux4g-table-cell-text">
                          {fieldLabel(tf as never, field)}
                        </th>
                        <td className="ux4g-table-cell-text">{value}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </TableScroll>
            </>
          )}
        </section>

        {/* Right: progress while running, findings when done. */}
        <section aria-labelledby="pane-checks">
          <h2 id="pane-checks" className="ux4g-heading-s-strong ux4g-mb-s">
            {t('checksPane')}
          </h2>

          {running ? (
            <CheckProgressPanel progress={progress} />
          ) : (
            <>
              <p className="ux4g-body-m-default ux4g-mb-s" aria-live="polite">
                {t('complete', {count: flagged.length})}
              </p>
              <h3 className="sutradhar-sr-only">{t('findingsTitle')}</h3>
              <ul className="sutradhar-list-reset">
                {ordered.map((finding) => (
                  <FindingCard
                    key={finding.id}
                    finding={finding}
                    expanded={selectedFinding === finding.id}
                    onToggle={(id) =>
                      setSelectedFinding((current) => (current === id ? null : id))
                    }
                  />
                ))}
              </ul>
            </>
          )}

          {doc.checks.length > 0 && (
            <details className="ux4g-mt-m">
              <summary className="ux4g-body-s-default">{t('technicalDetails')}</summary>
              <TableScroll label={t('technicalDetails')}>
                <table className="ux4g-table ux4g-table-s ux4g-w-100">
                  <thead>
                    <tr>
                      <th scope="col">{t('checkName')}</th>
                      <th scope="col">{t('checkStatus')}</th>
                      <th scope="col">{t('checkDuration')}</th>
                    </tr>
                  </thead>
                  <tbody>
                    {doc.checks.map((check) => (
                      <tr key={check.agent_name}>
                        <td className="ux4g-table-cell-text">{check.agent_name}</td>
                        <td className="ux4g-table-cell-text">{check.status}</td>
                        <td className="ux4g-table-cell-text">
                          {t('milliseconds', {ms: check.duration_ms ?? 0})}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </TableScroll>
            </details>
          )}
        </section>
      </div>

      {/* The gate. */}
      {!decided && (
        <section aria-labelledby="decision" className="ux4g-card ux4g-card-solid">
          <div className="ux4g-card-body">
            <h2 id="decision" className="ux4g-heading-s-strong ux4g-mb-xs">
              {t('decisionTitle')}
            </h2>
            <p className="ux4g-body-s-default ux4g-text-neutral-secondary ux4g-mb-m">
              {t('decisionHint')}
            </p>

            {running && (
              <p className="ux4g-body-m-default ux4g-mb-m">{t('waitForChecks')}</p>
            )}

            {mode !== null && (
              <div
                className={`ux4g-input-container ux4g-input-lg ux4g-input-default ux4g-mb-m`}
              >
                <label htmlFor={reasonId}>
                  {mode === 'reject' ? t('reasonLabel') : t('overrideLabel')}
                </label>
                <div className="ux4g-textarea">
                  <textarea
                    id={reasonId}
                    className="ux4g-textarea-input"
                    rows={3}
                    value={reason}
                    onChange={(e) => setReason(e.target.value)}
                  />
                </div>
                <span className="ux4g-input-helper">
                  {mode === 'reject' ? t('reasonHint') : t('overrideHint')}
                </span>
              </div>
            )}

            <div className="ux4g-d-flex ux4g-ai-center ux4g-gap-m sutradhar-wrap sutradhar-stack-narrow">
              <button
                type="button"
                className="ux4g-btn ux4g-btn-primary ux4g-btn-lg"
                disabled={!canDecide || (mode === 'override' && reason.trim() === '')}
                aria-disabled={!canDecide}
                onClick={onApprove}
              >
                {submitting === 'approved' ? t('approving') : t('approve')}
              </button>
              <button
                type="button"
                className="ux4g-btn ux4g-btn-outline-danger ux4g-btn-lg"
                disabled={!canDecide || (mode === 'reject' && reason.trim() === '')}
                aria-disabled={!canDecide}
                onClick={onReject}
              >
                {submitting === 'rejected' ? t('rejecting') : t('reject')}
              </button>
              {mode !== null && (
                <button
                  type="button"
                  className="ux4g-btn ux4g-btn-text-neutral ux4g-btn-lg"
                  onClick={() => {
                    setMode(null);
                    setReason('');
                  }}
                >
                  {t('cancel')}
                </button>
              )}
            </div>
          </div>
        </section>
      )}

      {decided && (
        <p className="ux4g-body-m-default">
          {format.dateTime(new Date(doc.reviewed_at ?? doc.uploaded_at), {
            dateStyle: 'medium',
            timeStyle: 'short'
          })}
        </p>
      )}
    </section>
  );
}
