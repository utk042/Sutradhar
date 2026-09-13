"use client";

import { useCallback, useEffect, useState } from "react";
import { useFormatter, useTranslations } from "next-intl";
import { Link, useRouter } from "@/i18n/routing";
import DocumentPicker, { type PickerState } from "@/components/DocumentPicker";
import StatusTag from "@/components/StatusTag";
import TableScroll from "@/components/TableScroll";
import {
  listDocuments,
  me,
  uploadDocument,
  type DocumentSummary,
} from "@/lib/api";

/**
 * The officer's desk: one action, and the list of files waiting.
 *
 * The upload panel is the only primary action on the screen. Signing out and
 * moving between screens live in the navigation bar, where they are reachable
 * from every page rather than from this one — which is also what keeps this
 * screen down to the single action the brief asks for.
 *
 * While any document is still being checked the list refreshes on a timer, so
 * an officer who uploads and waits sees the row change state without touching
 * anything. The polling stops as soon as nothing is in flight.
 */
const POLL_MS = 2000;

/** Codes the locale file has a sentence for. Anything else is `unexpected`. */
const KNOWN_UPLOAD_ERRORS = [
  "upload_empty",
  "upload_too_large",
  "upload_wrong_type",
  "upload_type_mismatch",
  "upload_unreadable",
  "network",
];

export default function HomeClient() {
  const t = useTranslations("home");
  const tu = useTranslations("upload");
  const format = useFormatter();
  const router = useRouter();

  const [ready, setReady] = useState(false);
  const [documents, setDocuments] = useState<DocumentSummary[]>([]);
  const [picker, setPicker] = useState<PickerState>("idle");
  const [chosen, setChosen] = useState<{ name: string; size: number } | null>(
    null,
  );
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    const result = await listDocuments();
    if (result.ok) setDocuments(result.data);
  }, []);

  useEffect(() => {
    let active = true;
    me().then((result) => {
      if (!active) return;
      if (result.ok) {
        setReady(true);
        refresh();
      } else {
        router.replace("/login");
      }
    });
    return () => {
      active = false;
    };
  }, [router, refresh]);

  // Keep refreshing only while something is actually being checked.
  const inFlight = documents.some(
    (d) => d.status === "uploaded" || d.status === "processing",
  );
  useEffect(() => {
    if (!inFlight) return;
    const timer = setInterval(refresh, POLL_MS);
    return () => clearInterval(timer);
  }, [inFlight, refresh]);

  async function handleFile(file: File) {
    setError(null);
    setChosen({ name: file.name, size: file.size });
    setPicker("uploading");

    const result = await uploadDocument(file);

    if (result.ok) {
      setPicker("done");
      refresh();
      return;
    }

    setPicker("error");
    setError(
      KNOWN_UPLOAD_ERRORS.includes(result.code)
        ? tu(`errors.${result.code}`)
        : tu("errors.unexpected"),
    );
  }

  function uploadedAt(doc: DocumentSummary) {
    return format.dateTime(new Date(doc.uploaded_at), {
      dateStyle: "medium",
      timeStyle: "short",
    });
  }

  if (!ready) return null;

  return (
    <>
      <div className="ux4g-mb-xl sutradhar-picker">
        <DocumentPicker
          state={picker}
          fileName={chosen?.name ?? null}
          fileSize={chosen?.size ?? null}
          error={error}
          onChoose={handleFile}
        />
      </div>

      <h2 className="ux4g-heading-s-strong ux4g-mb-s">{t("pendingTitle")}</h2>

      {documents.length === 0 ? (
        <div className="ux4g-empty-state">
          <div className="ux4g-empty-state-content">
            <p className="ux4g-heading-xs-strong">{t("emptyTitle")}</p>
            <p className="ux4g-body-m-default ux4g-text-neutral-secondary">
              {t("emptyBody")}
            </p>
          </div>
        </div>
      ) : (
        <>
          {/* The same list, told twice, because a five-column table cannot be
              read on a 360px screen and UX4G's `ux4g-table-responsive` is only
              `overflow-x: auto` — the status and the Review button end up off
              the side of a container with nothing to say it scrolls.

              Only one of the two is ever rendered: the other is `display:none`,
              which removes it from the accessibility tree as well as from
              sight, so nothing is announced twice. Breaking the table's own
              markup with `display:block` would have kept one copy but thrown
              away the row-and-column relationships a screen reader depends on,
              which is not a trade worth making in a government service. */}
          <div className="sutradhar-only-wide">
            <TableScroll label={t("pendingTitle")}>
              <table className="ux4g-table ux4g-table-m ux4g-table-responsive ux4g-w-100">
                <thead>
                  <tr>
                    <th scope="col">{t("colReference")}</th>
                    <th scope="col">{t("colDocument")}</th>
                    <th scope="col">{t("colStatus")}</th>
                    <th scope="col">{t("colUploaded")}</th>
                    <th scope="col">
                      <span className="sutradhar-sr-only">{t("review")}</span>
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {documents.map((doc) => (
                    <tr key={doc.id}>
                      <td className="ux4g-table-cell-text">{doc.public_ref}</td>
                      <td className="ux4g-table-cell-text sutradhar-break-word">
                        {doc.original_filename}
                      </td>
                      <td className="ux4g-table-cell-tags">
                        <StatusTag status={doc.status} />
                      </td>
                      <td className="ux4g-table-cell-text">
                        {uploadedAt(doc)}
                      </td>
                      <td className="ux4g-table-cell-text">
                        <Link
                          href={`/review/${doc.id}`}
                          className="ux4g-btn ux4g-btn-text-primary ux4g-btn-lg"
                        >
                          {doc.status === "pending_review"
                            ? t("review")
                            : t("open")}
                        </Link>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </TableScroll>
          </div>

          <ul className="sutradhar-only-narrow sutradhar-list-reset sutradhar-doc-cards">
            {documents.map((doc) => (
              <li key={doc.id} className="ux4g-card ux4g-card-outline">
                <div className="ux4g-card-body">
                  <p className="ux4g-heading-xxs-strong ux4g-mb-xs sutradhar-break-word">
                    {doc.original_filename}
                  </p>
                  <p className="ux4g-body-s-default ux4g-text-neutral-secondary ux4g-mb-xs">
                    {t("colReference")}: {doc.public_ref}
                  </p>
                  <p className="ux4g-mb-xs">
                    <StatusTag status={doc.status} />
                  </p>
                  <p className="ux4g-body-s-default ux4g-text-neutral-secondary ux4g-mb-s">
                    {t("colUploaded")}: {uploadedAt(doc)}
                  </p>
                  <Link
                    href={`/review/${doc.id}`}
                    className="ux4g-btn ux4g-btn-outline-primary ux4g-btn-lg ux4g-w-100"
                  >
                    {doc.status === "pending_review" ? t("review") : t("open")}
                  </Link>
                </div>
              </li>
            ))}
          </ul>
        </>
      )}
    </>
  );
}
