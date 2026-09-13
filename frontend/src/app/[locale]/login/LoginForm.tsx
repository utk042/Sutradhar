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
 * A checkbox that says "Show password", not an eye in the corner of the field.
 *
 * UX4G does ship the slot for an in-field button — `ux4g-input-actions` and
 * `ux4g-input-action-btn` — but at `ux4g-input-lg` the shipped rule sizes that
 * button 1.25rem square. Twenty pixels is half the 44px this service holds
 * itself to and below even WCAG 2.2's 24px floor, and the only way to grow it
 * is to override a component internal, which §13 of the UX4G contract forbids.
 *
 * The checkbox is also simply better here. The brief says every state is
 * labelled in words and never by an icon alone, and these officers have not
 * used an app that taught them what a crossed-out eye means. A checkbox says
 * what it does, says whether it is on, has a 48px target, and is announced
 * correctly by a screen reader with no ARIA of our own.
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
 * Nothing is pre-selected. Two taps to sign in rather than one is the cost of
 * the choice being a real one, and a wrong default that quietly works for most
 * people is how the head of department ends up seeing an error every morning.
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
  const showPasswordId = useId();
  const roleLegendId = useId();
  const roleErrorId = useId();
  const roleName = useId();

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
        </div>
        {fieldErrors.password && (
          <span className="ux4g-input-helper" id={passwordErrorId}>
            {fieldErrors.password}
          </span>
        )}
      </div>

      <label
        className="ux4g-checkbox ux4g-checkbox-lg sutradhar-tap-target ux4g-mb-xl"
        htmlFor={showPasswordId}
      >
        <input
          id={showPasswordId}
          type="checkbox"
          className="ux4g-checkbox-input"
          checked={showPassword}
          onChange={(e) => setShowPassword(e.target.checked)}
        />
        <span className="ux4g-checkbox-control">
          <span className="ux4g-checkmark" />
        </span>
        <span className="ux4g-checkbox-content">
          <span className="ux4g-checkbox-header">
            <span className="ux4g-checkbox-label">{t('showPassword')}</span>
          </span>
          <span className="ux4g-checkbox-description">{t('showPasswordHint')}</span>
        </span>
      </label>

      {/* A real fieldset, so the question is read out before the options rather
          than each option arriving with no idea what it answers. */}
      <fieldset
        className="sutradhar-fieldset ux4g-mb-xl"
        aria-describedby={fieldErrors.role ? roleErrorId : undefined}
      >
        <legend id={roleLegendId} className="ux4g-heading-xxs-strong ux4g-mb-xs">
          {t('roleLabel')}
        </legend>
        <p className="ux4g-body-s-default ux4g-text-neutral-secondary ux4g-mb-s">
          {t('roleHint')}
        </p>

        <div className="sutradhar-role-options ux4g-mb-s">
          {ROLES.map((option) => (
            /* Two things are needed to make the whole row selectable, and the
               second is a workaround for a bug in the shipped UX4G runtime.

               `htmlFor`/`id` pair the label with its input, which is good
               practice regardless. It is not sufficient here, because
               `ux4g.js` installs a delegated click handler on `document`:

                 const radio = U.closest(e.target, ".ux4g-radio");
                 if (radio && !U.closest(e.target,
                     ".ux4g-radio-input, .ux4g-radio-control")) {
                   e.preventDefault();
                   return;
                 }

               Every click inside a Radio that is not on the 20px circle has
               its default action cancelled — so clicking the word "Officer"
               does nothing at all. Verified in a browser: clicking
               `.ux4g-radio-control` selects the option, clicking
               `.ux4g-radio-label` does not.

               That shrinks the real target to 20 pixels whatever padding the
               row carries, and breaks the oldest convention in forms: that the
               text beside a radio selects it. So the row sets the value itself
               on click. `preventDefault` does not stop React's own handler, and
               a radio cannot be un-selected, so a click on the circle — which
               fires both this and the input's `onChange` — sets the same value
               twice and changes nothing.

               Reported in the completion notes as UX4G contract debt rather
               than fixed silently. */
            <label
              key={option}
              htmlFor={`${roleName}-${option}`}
              className="ux4g-radio ux4g-radio-md sutradhar-tap-target"
              onClick={() => setRole(option)}
            >
              <input
                id={`${roleName}-${option}`}
                type="radio"
                className="ux4g-radio-input"
                name={roleName}
                value={option}
                checked={role === option}
                onChange={() => setRole(option)}
                aria-invalid={fieldErrors.role ? true : undefined}
              />
              <span className="ux4g-radio-control">
                <span className="ux4g-radiomark" />
              </span>
              <span className="ux4g-radio-content">
                <span className="ux4g-radio-header">
                  <span className="ux4g-radio-label">{t(`roles.${option}`)}</span>
                </span>
              </span>
            </label>
          ))}
        </div>

        {fieldErrors.role && (
          <p className="ux4g-input-helper ux4g-mt-xs" id={roleErrorId}>
            {fieldErrors.role}
          </p>
        )}
      </fieldset>

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
