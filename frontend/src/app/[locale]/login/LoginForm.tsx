'use client';

import {useId, useState} from 'react';
import {useTranslations} from 'next-intl';
import {useRouter} from '@/i18n/routing';
import {login, type DeclaredRole} from '@/lib/api';

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
 *
 * ## Showing the password
 *
 * An eye button inside the field, in UX4G's own `ux4g-input-actions` slot.
 *
 * One accessibility fix goes with it. The shipped rule
 * `.ux4g-input-lg .ux4g-input-action-btn { height: 1.25rem; width: 1.25rem }`
 * makes that button a 20px target — under half the 44px this service holds
 * itself to, and below even WCAG 2.2's 24px floor. `sutradhar-reveal` changes
 * nothing about the button: it adds a transparent pseudo-element that extends
 * the *hit area* to 44x44, which is what WCAG measures. The field still looks
 * exactly as UX4G drew it. See `app.css` for the arithmetic.
 *
 * The icon is never the only signal. The button's accessible name is a verb —
 * "Show password" or "Hide password" — and it changes with the state, so a
 * screen reader announces the new name the moment it is pressed. The field
 * showing plain text is the visible confirmation.
 *
 * ## Choosing a role
 *
 * The officer says which role they are signing in as, and the server refuses
 * the sign-in if that disagrees with the account. It is a declaration, not a
 * request: picking "head of department" cannot make anyone one. The role in
 * force is read from the database on every request and nothing on this page
 * touches it — see `app/api/auth.py`, where the check deliberately sits *below*
 * the password check so that it can never answer "which role is this number?"
 * to someone who has not proved they own the account.
 *
 * A native `<select>` in UX4G's Input shell, not UX4G's own Dropdown. Two
 * reasons, and the first is decisive:
 *
 * 1. UX4G's Dropdown is driven by the global runtime, which writes
 *    `valueNode.textContent` and toggles classes on the element directly.
 *    React owns that subtree and will overwrite both on its next render. The
 *    two cannot both be in charge of the same DOM.
 * 2. A native select is the better control for these users anyway: on a phone
 *    it opens the operating system's own picker, which is large, familiar and
 *    needs no learning.
 *
 * The shipped package has no Select — `.ux4g-select-*` are `user-select`
 * utilities — so the field is composed from the Input classes with the chevron
 * and the native appearance reset in `app.css`.
 *
 * Nothing is pre-selected. Two steps to sign in rather than one is the cost of
 * the choice being a real one, and a default that quietly works for most people
 * is how the head of department ends up seeing an error every morning.
 */

type FieldErrors = {mobile?: string; password?: string; role?: string};

const ROLES: DeclaredRole[] = ['officer', 'dept_head'];

export default function LoginForm() {
  const t = useTranslations('login');
  const router = useRouter();

  const mobileId = useId();
  const mobileHelpId = useId();
  const mobileErrorId = useId();
  const passwordId = useId();
  const passwordErrorId = useId();
  const roleId = useId();
  const roleHintId = useId();
  const roleErrorId = useId();

  const [mobile, setMobile] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [role, setRole] = useState<DeclaredRole | null>(null);
  const [fieldErrors, setFieldErrors] = useState<FieldErrors>({});
  const [formError, setFormError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  function validate(): FieldErrors {
    const errors: FieldErrors = {};
    if (!mobile.trim()) errors.mobile = t('errors.mobileRequired');
    else if (!/^[0-9]{10}$/.test(mobile.trim())) errors.mobile = t('errors.mobileFormat');
    if (!password) errors.password = t('errors.passwordRequired');
    if (role === null) errors.role = t('errors.roleRequired');
    return errors;
  }

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setFormError(null);

    const errors = validate();
    setFieldErrors(errors);
    if (Object.keys(errors).length > 0) return;

    setSubmitting(true);
    const result = await login(mobile.trim(), password, role!);
    setSubmitting(false);

    if (result.ok) {
      // The password is not left visible on a screen the next person will use.
      setShowPassword(false);
      router.push('/');
      return;
    }

    // Only codes the locale file knows are shown; anything else becomes the
    // generic message rather than leaking a status or an exception.
    const known = ['invalid_credentials', 'role_mismatch', 'network'];
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
        } ux4g-mb-s`}
      >
        <label htmlFor={passwordId}>{t('passwordLabel')}</label>
        <div className="ux4g-input">
          {/* Only the `type` changes when the box is ticked. The element is the
              same one either way, so focus and the caret stay where they were
              and a password manager does not see the field replaced. */}
          <input
            className="ux4g-input-input"
            id={passwordId}
            name="password"
            type={showPassword ? 'text' : 'password'}
            autoComplete="current-password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            aria-invalid={fieldErrors.password ? true : undefined}
            aria-describedby={fieldErrors.password ? passwordErrorId : undefined}
          />
          <div className="ux4g-input-actions">
            <button
              type="button"
              className="ux4g-input-action-btn sutradhar-reveal"
              /* The name is a verb and it changes with the state, so pressing
                 it announces what it now does. `aria-pressed` on top of a
                 changing name would have a screen reader say both, which
                 contradicts itself. */
              aria-label={showPassword ? t('hidePassword') : t('showPassword')}
              aria-controls={passwordId}
              onClick={() => setShowPassword((shown) => !shown)}
            >
              <span className="ux4g-icon-outlined" aria-hidden="true">
                {showPassword ? 'visibility_off' : 'visibility'}
              </span>
            </button>
          </div>
        </div>
        {fieldErrors.password && (
          <span className="ux4g-input-helper" id={passwordErrorId}>
            {fieldErrors.password}
          </span>
        )}
      </div>

      <div
        className={`ux4g-input-container ux4g-input-lg ${
          fieldErrors.role ? 'ux4g-input-error' : 'ux4g-input-default'
        } ux4g-mb-xl`}
      >
        <label htmlFor={roleId}>{t('roleLabel')}</label>
        <div className="ux4g-input">
          <select
            id={roleId}
            name="role"
            className="ux4g-input-input sutradhar-select"
            value={role ?? ''}
            onChange={(e) => setRole((e.target.value || null) as DeclaredRole | null)}
            aria-invalid={fieldErrors.role ? true : undefined}
            aria-describedby={fieldErrors.role ? roleErrorId : roleHintId}
          >
            {/* Empty and disabled, so nothing is chosen until the officer
                chooses it. Kept in the list rather than hidden: on a phone the
                native picker opens on the current value, and an option the
                wheel can land on but not select is worse than one that simply
                reads as the question. */}
            <option value="" disabled>
              {t('rolePlaceholder')}
            </option>
            {ROLES.map((option) => (
              <option key={option} value={option}>
                {t(`roles.${option}`)}
              </option>
            ))}
          </select>
          {/* Decorative: the control is already announced as a combo box. */}
          <span className="ux4g-input-actions" aria-hidden="true">
            <span className="ux4g-icon-outlined">expand_more</span>
          </span>
        </div>
        {fieldErrors.role ? (
          <span className="ux4g-input-helper" id={roleErrorId}>
            {fieldErrors.role}
          </span>
        ) : (
          <span className="ux4g-input-helper" id={roleHintId}>
            {t('roleHint')}
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
