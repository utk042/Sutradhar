import {defineRouting} from 'next-intl/routing';
import {createNavigation} from 'next-intl/navigation';

export const locales = ['en', 'hi'] as const;
export type Locale = (typeof locales)[number];

export const routing = defineRouting({
  locales,
  defaultLocale: 'en',
  // Always prefix, so an officer can see and share which language a screen is
  // in, and so /hi/... is a stable bookmarkable URL rather than cookie state.
  localePrefix: 'always',
  /**
   * English unless the officer asks for Hindi, on the Settings screen.
   *
   * next-intl otherwise sniffs `Accept-Language` and redirects, so an office
   * machine configured for Hindi would open in Hindi and nobody would know why
   * — the officer never chose it and the screen that owns the choice would show
   * a language they had not set. Language is a setting here, not a guess.
   */
  localeDetection: false
});

export const {Link, redirect, usePathname, useRouter, getPathname} =
  createNavigation(routing);
