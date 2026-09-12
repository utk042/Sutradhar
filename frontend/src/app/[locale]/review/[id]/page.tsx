import {setRequestLocale} from 'next-intl/server';
import ReviewClient from './ReviewClient';

export default async function ReviewPage({
  params
}: {
  params: Promise<{locale: string; id: string}>;
}) {
  const {locale, id} = await params;
  setRequestLocale(locale);
  return <ReviewClient documentId={Number(id)} />;
}
