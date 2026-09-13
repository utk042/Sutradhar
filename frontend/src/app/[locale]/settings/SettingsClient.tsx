'use client';

import {useEffect, useState} from 'react';
import {useLocale, useTranslations} from 'next-intl';
import {usePathname, useRouter} from '@/i18n/routing';
import {locales, type Locale} from '@/i18n/routing';
import {
  applyThemeChoice,
  readThemeChoice,
  watchSystemTheme,
  type ThemeChoice
} from '@/lib/theme';

/**
 * How this service looks and what language it speaks.
 *
 * Both settings apply the moment they are chosen — there is no Save button,
 * because there is nothing to lose if the page closes and a confirmation step
 * for a preference is a step for nothing. Each choice is a button with
 * `aria-pressed`, so the current one is announced rather than only shaded.
 *
 * The theme is remembered in this browser; the language is part of the address,
 * so a Hindi page stays Hindi when it is bookmarked or shared.
 */
const THEME_CHOICES: ThemeChoice[] = ['light', 'dark', 'system'];

export default function SettingsClient() {
  const t = useTranslations('settings');
  const tl = useTranslations('language');
  const activeLocale = useLocale();
  const pathname = usePathname();
  const router = useRouter();

  // Read on the client only: the server cannot see localStorage, and rendering
  // a guess would flash the wrong button as selected.
  const [theme, setTheme] = useState<ThemeChoice | null>(null);

  useEffect(() => {
    setTheme(readThemeChoice());
  }, []);

  // While "match my device" is chosen, follow the device.
  useEffect(() => {
    if (theme !== 'system') return;
    return watchSystemTheme(() => applyThemeChoice('system'));
  }, [theme]);

  function choose(choice: ThemeChoice) {
    setTheme(choice);
    applyThemeChoice(choice);
  }

  return (
    <>
      <section aria-labelledby="appearance" className="ux4g-card ux4g-card-outline ux4g-mb-l">
        <div className="ux4g-card-body">
          <h2 id="appearance" className="ux4g-heading-xs-strong ux4g-mb-xs">
            {t('appearance')}
          </h2>
          <p className="ux4g-body-s-default ux4g-text-neutral-secondary ux4g-mb-m">
            {t('appearanceHint')}
          </p>

          {/* No role="group" here: the <section> above is already named
              "Appearance", and a group of the same name inside it is an echo. */}
          <div className="ux4g-d-flex ux4g-ai-center ux4g-gap-m sutradhar-wrap">
            {THEME_CHOICES.map((choice) => (
              <button
                key={choice}
                type="button"
                className={
                  theme === choice
                    ? 'ux4g-btn ux4g-btn-tonal-primary ux4g-btn-lg'
                    : 'ux4g-btn ux4g-btn-outline-neutral ux4g-btn-lg'
                }
                aria-pressed={theme === choice}
                onClick={() => choose(choice)}
              >
                {t(`theme.${choice}`)}
              </button>
            ))}
          </div>

          {theme === 'system' && (
            <p className="ux4g-body-s-default ux4g-text-neutral-tertiary ux4g-mt-s">
              {t('theme.systemHint')}
            </p>
          )}
        </div>
      </section>

      <section aria-labelledby="language" className="ux4g-card ux4g-card-outline">
        <div className="ux4g-card-body">
          <h2 id="language" className="ux4g-heading-xs-strong ux4g-mb-xs">
            {tl('label')}
          </h2>
          <p className="ux4g-body-s-default ux4g-text-neutral-secondary ux4g-mb-m">
            {t('languageHint')}
          </p>

          <div className="ux4g-d-flex ux4g-ai-center ux4g-gap-m sutradhar-wrap">
            {locales.map((locale: Locale) => (
              <button
                key={locale}
                type="button"
                className={
                  locale === activeLocale
                    ? 'ux4g-btn ux4g-btn-tonal-primary ux4g-btn-lg'
                    : 'ux4g-btn ux4g-btn-outline-neutral ux4g-btn-lg'
                }
                aria-pressed={locale === activeLocale}
                // Each language names itself in its own script, so this is
                // readable whichever one you already speak.
                lang={locale}
                onClick={() => router.replace(pathname, {locale})}
              >
                {tl(locale)}
              </button>
            ))}
          </div>
        </div>
      </section>
    </>
  );
}
