'use client';

import {useId, useState} from 'react';
import {useTranslations} from 'next-intl';
import {useRouter} from '@/i18n/routing';
import {login} from '@/lib/api';

/**
 * Sign-in form. The only action on the page, per the brief.
 *
 * Accessibility and plain-language decisions:
 * - One `ux4g-btn-primary` and nothing competing with it.
 * - Errors name what happened and what to do next. The backend returns a code;
 *   the message the officer reads comes from the locale file, so Hindi needs no
 *   server change and no English is hardcoded here.
 * - Field errors use `aria-describedby` and `aria-invalid`, and the form-level
 *   error is a live region so a screen reader announces a failed sign-in.
 * - Validation messages are words, not a red border alone.
 * - `ux4g-input-lg` and `ux4g-btn-lg` clear the 44px minimum target; the md
 *   button size is 40px and would not.
 *
 * Markup note: each field needs the inner `<div class="ux4g-input">` box. That
 * div is what carries the border, background, radius, padding and
 * `:focus-within` outline; `.ux4g-input-container` is only the label/field/helper
 * stack. The package README's Input example omits it, which renders a field with
 * no visible boundary at all. Verified in the browser before and after.
 */

type FieldErrors = {mobile?: string; password?: string};

export default function LoginForm() {
  const t = useTranslations('login');
  const router = useRouter();

  const mobileId = useId();
  const mobileHelpId = useId();
  const mobileErrorId = useId();
  const passwordId = useId();
  const passwordErrorId = useId();

  const [mobile, setMobile] = useState('');
  const [password, setPassword] = useState('');
  const [fieldErrors, setFieldErrors] = useState<FieldErrors>({});
  const [formError, setFormError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  function validate(): FieldErrors {
    const errors: FieldErrors = {};
    if (!mobile.trim()) errors.mobile = t('errors.mobileRequired');
    else if (!/^[0-9]{10}$/.test(mobile.trim())) errors.mobile = t('errors.mobileFormat');
    if (!password) errors.password = t('errors.passwordRequired');
    return errors;
  }

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setFormError(null);

    const errors = validate();
    setFieldErrors(errors);
    if (Object.keys(errors).length > 0) return;

    setSubmitting(true);
    const result = await login(mobile.trim(), password);
    setSubmitting(false);

    if (result.ok) {
      router.push('/');
      return;
    }

    // Only codes the locale file knows are shown; anything else becomes the
    // generic message rather than leaking a status or an exception.
    const known = ['invalid_credentials', 'network'];
    setFormError(
      known.includes(result.code) ? t(`errors.${result.code}`) : t('errors.unexpected')
    );
  }

  return (
    <form onSubmit={handleSubmit} noValidate>
      {formError !== null && (
        <div className="ux4g-alert ux4g-alert-error ux4g-mb-l" role="alert">
          <span className="ux4g-body-m-default">{formError}</span>
        </div>
      )}

      <div
        className={`ux4g-input-container ux4g-input-lg ${
          fieldErrors.mobile ? 'ux4g-input-error' : 'ux4g-input-default'
        } ux4g-mb-l`}
      >
        <label htmlFor={mobileId}>{t('mobileLabel')}</label>
        <div className="ux4g-input">
          <input
            className="ux4g-input-input"
            id={mobileId}
            name="mobile"
            type="tel"
            inputMode="numeric"
            autoComplete="username"
            maxLength={10}
            value={mobile}
            onChange={(e) => setMobile(e.target.value)}
            aria-invalid={fieldErrors.mobile ? true : undefined}
            aria-describedby={fieldErrors.mobile ? mobileErrorId : mobileHelpId}
          />
        </div>
        {fieldErrors.mobile ? (
          <span className="ux4g-input-helper" id={mobileErrorId}>
            {fieldErrors.mobile}
          </span>
        ) : (
          <span className="ux4g-input-helper" id={mobileHelpId}>
            {t('mobileHelp')}
          </span>
        )}
      </div>

      <div
        className={`ux4g-input-container ux4g-input-lg ${
          fieldErrors.password ? 'ux4g-input-error' : 'ux4g-input-default'
        } ux4g-mb-xl`}
      >
        <label htmlFor={passwordId}>{t('passwordLabel')}</label>
        <div className="ux4g-input">
          <input
            className="ux4g-input-input"
            id={passwordId}
            name="password"
            type="password"
            autoComplete="current-password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            aria-invalid={fieldErrors.password ? true : undefined}
            aria-describedby={fieldErrors.password ? passwordErrorId : undefined}
          />
        </div>
        {fieldErrors.password && (
          <span className="ux4g-input-helper" id={passwordErrorId}>
            {fieldErrors.password}
          </span>
        )}
      </div>

      <button
        type="submit"
        className="ux4g-btn ux4g-btn-primary ux4g-btn-lg ux4g-w-100"
        disabled={submitting}
      >
        {submitting ? t('submitting') : t('submit')}
      </button>
    </form>
  );
}
