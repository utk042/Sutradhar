import {getRequestConfig} from 'next-intl/server';
import {routing, type Locale} from './routing';

export default getRequestConfig(async ({requestLocale}) => {
  const requested = await requestLocale;

  // The [locale] segment acts as a catch-all, so an unknown value must fall
  // back rather than 404 with a missing-messages error.
  const locale: Locale = routing.locales.includes(requested as Locale)
    ? (requested as Locale)
    : routing.defaultLocale;

  return {
    locale,
    messages: (await import(`../../messages/${locale}.json`)).default
  };
});
