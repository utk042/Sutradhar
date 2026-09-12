import {setRequestLocale} from 'next-intl/server';
import DecisionClient from './DecisionClient';

export default async function DecisionPage({
  params
}: {
  params: Promise<{locale: string; id: string}>;
}) {
  const {locale, id} = await params;
  setRequestLocale(locale);
  return <DecisionClient documentId={Number(id)} />;
}
