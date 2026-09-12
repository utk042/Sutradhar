import {defineRouting} from 'next-intl/routing';
import {createNavigation} from 'next-intl/navigation';

export const locales = ['en', 'hi'] as const;
export type Locale = (typeof locales)[number];

export const routing = defineRouting({
  locales,
  defaultLocale: 'en',
  // Always prefix, so an officer can see and share which language a screen is
  // in, and so /hi/... is a stable bookmarkable URL rather than cookie state.
  localePrefix: 'always'
});

export const {Link, redirect, usePathname, useRouter, getPathname} =
  createNavigation(routing);
