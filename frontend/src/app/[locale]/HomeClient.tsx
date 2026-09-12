'use client';

import {useCallback, useEffect, useRef, useState} from 'react';
import {useFormatter, useTranslations} from 'next-intl';
import {Link, useRouter} from '@/i18n/routing';
import StatusTag from '@/components/StatusTag';
import {
  listDocuments,
  logout,
  me,
  uploadDocument,
  type CurrentUser,
  type DocumentSummary
} from '@/lib/api';

/**
 * The officer's desk: one action, and the list of files waiting.
 *
 * The upload button is the only primary action on the screen. While any document
 * is still being checked the list refreshes on a timer, so an officer who
 * uploads and waits sees the row change state without touching anything. The
 * polling stops as soon as nothing is in flight — Phase 3 replaces it with a
 * live stream for the review screen itself.
 */
const POLL_MS = 2000;

export default function HomeClient() {
  const t = useTranslations('home');
  const tu = useTranslations('upload');
  const format = useFormatter();
  const router = useRouter();

  const [user, setUser] = useState<CurrentUser | null>(null);
  const [documents, setDocuments] = useState<DocumentSummary[]>([]);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const fileInput = useRef<HTMLInputElement>(null);

  const refresh = useCallback(async () => {
    const result = await listDocuments();
    if (result.ok) setDocuments(result.data);
  }, []);

  useEffect(() => {
    let active = true;
    me().then((result) => {
      if (!active) return;
      if (result.ok) {
        setUser(result.data);
        refresh();
      } else {
        router.replace('/login');
      }
    });
    return () => {
      active = false;
    };
  }, [router, refresh]);

  // Keep refreshing only while something is actually being checked.
  const inFlight = documents.some(
    (d) => d.status === 'uploaded' || d.status === 'processing'
  );
  useEffect(() => {
    if (!inFlight) return;
    const timer = setInterval(refresh, POLL_MS);
    return () => clearInterval(timer);
  }, [inFlight, refresh]);

  async function handleFile(event: React.ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (!file) return;
    setError(null);
    setUploading(true);
    const result = await uploadDocument(file);
    setUploading(false);
    // Let the same file be chosen again after a failure.
    if (fileInput.current) fileInput.current.value = '';

    if (result.ok) {
      refresh();
      return;
    }
    const known = [
      'upload_empty',
      'upload_too_large',
      'upload_wrong_type',
      'upload_type_mismatch',
      'upload_unreadable',
      'network'
    ];
    setError(known.includes(result.code) ? tu(`errors.${result.code}`) : tu('errors.unexpected'));
  }

  if (user === null) return null;

  return (
    <>
      <div className="ux4g-d-flex ux4g-ai-center ux4g-jc-between ux4g-gap-m ux4g-mb-l sutradhar-wrap">
        <p className="ux4g-body-m-default">{t('signedInAs', {name: user.full_name})}</p>
        <button
          type="button"
          className="ux4g-btn ux4g-btn-text-neutral ux4g-btn-lg"
          onClick={async () => {
            await logout();
            router.replace('/login');
          }}
        >
          {t('signOut')}
        </button>
      </div>

      {error !== null && (
        <div className="ux4g-alert ux4g-alert-error ux4g-mb-l" role="alert">
          <span className="ux4g-body-m-default">{error}</span>
        </div>
      )}

      <div className="ux4g-mb-xl">
        <label htmlFor="document-upload" className="ux4g-heading-xs-strong ux4g-d-block ux4g-mb-xs">
          {t('chooseFile')}
        </label>
        <p className="ux4g-body-s-default ux4g-text-neutral-secondary ux4g-mb-s">
          {t('fileHint')}
        </p>
        {/* The file input is the control; the button label is its own text, so
            there is no second control competing with it. */}
        <input
          ref={fileInput}
          id="document-upload"
          type="file"
          accept=".pdf,.png,.jpg,.jpeg,application/pdf,image/png,image/jpeg"
          onChange={handleFile}
          disabled={uploading}
          className="sutradhar-file-input"
        />
        {uploading && (
          <p className="ux4g-body-s-default ux4g-mt-s" role="status">
            {t('uploading')}
          </p>
        )}
      </div>

      <h2 className="ux4g-heading-s-strong ux4g-mb-s">{t('pendingTitle')}</h2>

      {documents.length === 0 ? (
        <div className="ux4g-empty-state">
          <div className="ux4g-empty-state-content">
            <p className="ux4g-heading-xs-strong">{t('emptyTitle')}</p>
            <p className="ux4g-body-m-default ux4g-text-neutral-secondary">{t('emptyBody')}</p>
          </div>
        </div>
      ) : (
        <div className="sutradhar-table-scroll">
          <table className="ux4g-table ux4g-table-m ux4g-table-responsive ux4g-w-100">
            <thead>
              <tr>
                <th scope="col">{t('colReference')}</th>
                <th scope="col">{t('colDocument')}</th>
                <th scope="col">{t('colStatus')}</th>
                <th scope="col">{t('colUploaded')}</th>
                <th scope="col">
                  <span className="sutradhar-sr-only">{t('review')}</span>
                </th>
              </tr>
            </thead>
            <tbody>
              {documents.map((doc) => (
                <tr key={doc.id}>
                  <td className="ux4g-table-cell-text">{doc.public_ref}</td>
                  <td className="ux4g-table-cell-text">{doc.original_filename}</td>
                  <td className="ux4g-table-cell-tags">
                    <StatusTag status={doc.status} />
                  </td>
                  <td className="ux4g-table-cell-text">
                    {format.dateTime(new Date(doc.uploaded_at), {
                      dateStyle: 'medium',
                      timeStyle: 'short'
                    })}
                  </td>
                  <td className="ux4g-table-cell-text">
                    <Link
                      href={`/review/${doc.id}`}
                      className="ux4g-btn ux4g-btn-text-primary ux4g-btn-lg"
                    >
                      {doc.status === 'pending_review' ? t('review') : t('open')}
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </>
  );
}
