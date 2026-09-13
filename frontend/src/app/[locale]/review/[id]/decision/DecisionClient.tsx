'use client';

import {useEffect, useState} from 'react';
import {useFormatter, useTranslations} from 'next-intl';
import {Link, useRouter} from '@/i18n/routing';
import Breadcrumb from '@/components/Breadcrumb';
import {getDocument, me, type CurrentUser, type DocumentDetail} from '@/lib/api';

/**
 * Confirmation.
 *
 * States plainly what was decided, by whom and when, and says the decision is in
 * the audit log. Nothing here is an action except the way back — an officer
 * arriving on this page has finished with the file.
 */
export default function DecisionClient({documentId}: {documentId: number}) {
  const t = useTranslations('decision');
  const tn = useTranslations('nav');
  const tr = useTranslations('review');
  const format = useFormatter();
  const router = useRouter();
  const [doc, setDoc] = useState<DocumentDetail | null>(null);
  const [user, setUser] = useState<CurrentUser | null>(null);

  useEffect(() => {
    let active = true;
    Promise.all([getDocument(documentId), me()]).then(([d, u]) => {
      if (!active) return;
      if (!d.ok || !u.ok) {
        router.replace('/login');
        return;
      }
      // Landing here on an undecided document means something went wrong; send
      // the officer back to the file rather than showing an empty confirmation.
      if (d.data.status !== 'approved' && d.data.status !== 'rejected') {
        router.replace(`/review/${documentId}`);
        return;
      }
      setDoc(d.data);
      setUser(u.data);
    });
    return () => {
      active = false;
    };
  }, [documentId, router]);

  if (doc === null || user === null) return null;

  const approved = doc.status === 'approved';

  return (
    <section className="sutradhar-narrow ux4g-p-l">
      <Breadcrumb
        label={tn('breadcrumb')}
        items={[
          {label: tn('desk'), href: '/'},
          {label: tr('crumb', {reference: doc.public_ref}), href: `/review/${doc.id}`},
          {label: t('crumb')}
        ]}
      />
      <div
        className={`ux4g-alert ${approved ? 'ux4g-alert-success' : 'ux4g-alert-error'} ux4g-mb-l`}
        role="status"
      >
        <span className="ux4g-heading-xs-strong">
          {approved ? t('titleApproved') : t('titleRejected')}
        </span>
      </div>

      <p className="ux4g-body-l-default ux4g-mb-l">
        {t('summary', {
          reference: doc.public_ref,
          decision: approved ? t('approvedWord') : t('rejectedWord'),
          officer: user.full_name,
          when: format.dateTime(new Date(doc.reviewed_at ?? Date.now()), {
            dateStyle: 'long',
            timeStyle: 'short'
          })
        })}
      </p>

      {doc.decision_reason && (
        <div className="ux4g-card ux4g-card-outline ux4g-mb-l">
          <div className="ux4g-card-body">
            <h2 className="ux4g-heading-xxs-strong ux4g-mb-xs">{t('reasonGiven')}</h2>
            <p className="ux4g-body-m-default">{doc.decision_reason}</p>
          </div>
        </div>
      )}

      {doc.override_note && (
        <div className="ux4g-card ux4g-card-outline ux4g-mb-l">
          <div className="ux4g-card-body">
            <h2 className="ux4g-heading-xxs-strong ux4g-mb-xs">{t('noteGiven')}</h2>
            <p className="ux4g-body-m-default">{doc.override_note}</p>
          </div>
        </div>
      )}

      <p className="ux4g-body-s-default ux4g-text-neutral-secondary ux4g-mb-xl">
        {t('auditTitle')}
      </p>

      <Link href="/" className="ux4g-btn ux4g-btn-primary ux4g-btn-lg">
        {t('backToDesk')}
      </Link>
    </section>
  );
}
