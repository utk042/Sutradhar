'use client';

import {useCallback, useEffect, useId, useState} from 'react';
import {useTranslations} from 'next-intl';
import TableScroll from '@/components/TableScroll';
import {
  createOfficer,
  listOfficers,
  setOfficerActive,
  setProvider,
  getProvider,
  type Officer
} from '@/lib/api';

/**
 * The people in this office, and the controls over them.
 *
 * Suspending someone is written as "Suspend" rather than "Delete", because that
 * is what it does: their access stops, and everything they decided stays,
 * attributed to them. Nothing here removes a person's work.
 *
 * Adding an officer sets a password the head then tells them. There is no email
 * in this system and no reset flow, so the alternative would be an account
 * nobody can sign in to.
 */
export default function OfficerRoster({onChanged}: {onChanged: () => void}) {
  const t = useTranslations('dashboard');
  const [officers, setOfficers] = useState<Officer[]>([]);
  const [adding, setAdding] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [provider, setProviderState] = useState<string | null>(null);
  const [providerSaved, setProviderSaved] = useState(false);

  const [name, setName] = useState('');
  const [mobile, setMobile] = useState('');
  const [password, setPassword] = useState('');
  const nameId = useId();
  const mobileId = useId();
  const passwordId = useId();

  const load = useCallback(async () => {
    const [roster, current] = await Promise.all([listOfficers(), getProvider()]);
    if (roster.ok) setOfficers(roster.data);
    if (current.ok) setProviderState(current.data.provider);
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  function describe(code: string) {
    const known = [
      'mobile_already_registered',
      'user_not_found',
      'officer_not_active',
      'document_already_decided',
      'network'
    ];
    return known.includes(code) ? t(`errors.${code}`) : t('errors.unexpected');
  }

  async function submitNewOfficer(event: React.FormEvent) {
    event.preventDefault();
    setError(null);
    setBusy(true);
    const result = await createOfficer({
      full_name: name.trim(),
      mobile_number: mobile.trim(),
      password
    });
    setBusy(false);

    if (!result.ok) {
      setError(describe(result.code));
      return;
    }
    setAdding(false);
    setName('');
    setMobile('');
    setPassword('');
    load();
    onChanged();
  }

  async function toggleAccess(officer: Officer) {
    setError(null);
    const result = await setOfficerActive(officer.id, !officer.is_active);
    if (!result.ok) {
      setError(describe(result.code));
      return;
    }
    load();
    onChanged();
  }

  return (
    <section aria-labelledby="roster" className="ux4g-mb-xl">
      <div className="ux4g-d-flex ux4g-ai-center ux4g-jc-between ux4g-gap-m ux4g-mb-s sutradhar-wrap">
        <h2 id="roster" className="ux4g-heading-s-strong">
          {t('officersTitle')}
        </h2>
        {!adding && (
          <button
            type="button"
            className="ux4g-btn ux4g-btn-primary ux4g-btn-lg"
            onClick={() => setAdding(true)}
          >
            {t('addOfficer')}
          </button>
        )}
      </div>

      {error !== null && (
        <div className="ux4g-alert ux4g-alert-error ux4g-mb-m" role="alert">
          <span className="ux4g-body-m-default">{error}</span>
        </div>
      )}

      {adding && (
        <form
          onSubmit={submitNewOfficer}
          className="ux4g-card ux4g-card-outline ux4g-mb-m"
          noValidate
        >
          <div className="ux4g-card-body">
            <h3 className="ux4g-heading-xs-strong ux4g-mb-xs">{t('addOfficerTitle')}</h3>
            <p className="ux4g-body-s-default ux4g-text-neutral-secondary ux4g-mb-m">
              {t('addOfficerHint')}
            </p>

            <div className="ux4g-input-container ux4g-input-lg ux4g-input-default ux4g-mb-m">
              <label htmlFor={nameId}>{t('nameLabel')}</label>
              <div className="ux4g-input">
                <input
                  id={nameId}
                  className="ux4g-input-input"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  autoComplete="off"
                />
              </div>
            </div>

            <div className="ux4g-input-container ux4g-input-lg ux4g-input-default ux4g-mb-m">
              <label htmlFor={mobileId}>{t('mobileLabel')}</label>
              <div className="ux4g-input">
                <input
                  id={mobileId}
                  className="ux4g-input-input"
                  type="tel"
                  inputMode="numeric"
                  maxLength={10}
                  value={mobile}
                  onChange={(e) => setMobile(e.target.value)}
                  autoComplete="off"
                />
              </div>
            </div>

            <div className="ux4g-input-container ux4g-input-lg ux4g-input-default ux4g-mb-l">
              <label htmlFor={passwordId}>{t('passwordLabel')}</label>
              <div className="ux4g-input">
                <input
                  id={passwordId}
                  className="ux4g-input-input"
                  type="text"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  autoComplete="off"
                />
              </div>
              <span className="ux4g-input-helper">{t('passwordHint')}</span>
            </div>

            <div className="ux4g-d-flex ux4g-ai-center ux4g-gap-m sutradhar-wrap">
              <button
                type="submit"
                className="ux4g-btn ux4g-btn-primary ux4g-btn-lg"
                disabled={busy || name.trim() === '' || password.length < 12}
              >
                {busy ? t('creating') : t('create')}
              </button>
              <button
                type="button"
                className="ux4g-btn ux4g-btn-text-neutral ux4g-btn-lg"
                onClick={() => {
                  setAdding(false);
                  setError(null);
                }}
              >
                {t('cancel')}
              </button>
            </div>
          </div>
        </form>
      )}

      {officers.length === 0 ? (
        <div className="ux4g-empty-state">
          <div className="ux4g-empty-state-content">
            <p className="ux4g-body-m-default">{t('noOfficers')}</p>
          </div>
        </div>
      ) : (
        <TableScroll label={t('officersTitle')}>
          <table className="ux4g-table ux4g-table-m ux4g-w-100">
            <thead>
              <tr>
                <th scope="col">{t('colName')}</th>
                <th scope="col">{t('colMobile')}</th>
                <th scope="col">{t('colRole')}</th>
                <th scope="col">{t('colPending')}</th>
                <th scope="col">{t('colDecided')}</th>
                <th scope="col">{t('colAccess')}</th>
                <th scope="col">
                  <span className="sutradhar-sr-only">{t('colAccess')}</span>
                </th>
              </tr>
            </thead>
            <tbody>
              {officers.map((officer) => (
                <tr key={officer.id}>
                  <td className="ux4g-table-cell-text">{officer.full_name}</td>
                  <td className="ux4g-table-cell-text">{officer.mobile_number}</td>
                  <td className="ux4g-table-cell-text">
                    {officer.role === 'dept_head' ? t('roleHead') : t('roleOfficer')}
                  </td>
                  <td className="ux4g-table-cell-text">{officer.pending}</td>
                  <td className="ux4g-table-cell-text">{officer.decided}</td>
                  <td className="ux4g-table-cell-tags">
                    <span
                      className={
                        officer.is_active
                          ? 'ux4g-tag-tonal-success ux4g-tag-s'
                          : 'ux4g-tag-tonal-error ux4g-tag-s'
                      }
                    >
                      {officer.is_active ? t('active') : t('suspended')}
                    </span>
                  </td>
                  <td className="ux4g-table-cell-text">
                    {officer.role !== 'dept_head' && (
                      <button
                        type="button"
                        className={
                          officer.is_active
                            ? 'ux4g-btn ux4g-btn-outline-danger ux4g-btn-lg'
                            : 'ux4g-btn ux4g-btn-outline-neutral ux4g-btn-lg'
                        }
                        onClick={() => toggleAccess(officer)}
                      >
                        {officer.is_active ? t('suspend') : t('restore')}
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </TableScroll>
      )}

      {/* Where documents are read. The wording is about where the data goes,
          not about which vendor: that is the part an officer's department
          actually has to answer for. */}
      <div className="ux4g-card ux4g-card-outline ux4g-mt-l">
        <div className="ux4g-card-body">
          <h3 className="ux4g-heading-xs-strong ux4g-mb-xs">{t('providerTitle')}</h3>
          <p className="ux4g-body-s-default ux4g-text-neutral-secondary ux4g-mb-m">
            {t('providerHint')}
          </p>
          <div className="ux4g-d-flex ux4g-ai-center ux4g-gap-m sutradhar-wrap">
            {[
              {value: 'local', label: t('providerLocal')},
              {value: 'gemini', label: t('providerGemini')}
            ].map((choice) => (
              <button
                key={choice.value}
                type="button"
                className={
                  provider === choice.value
                    ? 'ux4g-btn ux4g-btn-tonal-primary ux4g-btn-lg'
                    : 'ux4g-btn ux4g-btn-outline-neutral ux4g-btn-lg'
                }
                aria-pressed={provider === choice.value}
                onClick={async () => {
                  const result = await setProvider(choice.value);
                  if (result.ok) {
                    setProviderState(result.data.provider);
                    setProviderSaved(true);
                  }
                }}
              >
                {choice.label}
              </button>
            ))}
            {providerSaved && (
              <span className="ux4g-body-s-default ux4g-text-success-default" role="status">
                {t('providerSaved')}
              </span>
            )}
          </div>
        </div>
      </div>
    </section>
  );
}
