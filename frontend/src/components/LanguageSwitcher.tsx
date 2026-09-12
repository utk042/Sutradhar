'use client';

import {useLocale, useTranslations} from 'next-intl';
import {usePathname, useRouter} from '@/i18n/routing';
import {locales, type Locale} from '@/i18n/routing';

/**
 * Language switch between English and Hindi.
 *
 * Rendered as two buttons rather than a dropdown: with only two options a
 * dropdown adds a click and hides the alternative, and "nothing more than two
 * clicks" applies to changing language too. `aria-pressed` conveys the current
 * language without relying on the visual fill.
 */
export default function LanguageSwitcher() {
  const t = useTranslations('language');
  const active = useLocale();
  const pathname = usePathname();
  const router = useRouter();

  return (
    <div role="group" aria-label={t('label')} className="ux4g-d-flex ux4g-ai-center ux4g-gap-xs">
      {locales.map((locale: Locale) => (
        <button
          key={locale}
          type="button"
          className={
            locale === active
              ? 'ux4g-btn ux4g-btn-tonal-primary ux4g-btn-lg'
              : 'ux4g-btn ux4g-btn-text-neutral ux4g-btn-lg'
          }
          aria-pressed={locale === active}
          onClick={() => router.replace(pathname, {locale})}
        >
          {t(locale)}
        </button>
      ))}
    </div>
  );
}
