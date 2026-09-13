'use client';

import {useId, useRef, useState} from 'react';
import {useFormatter, useTranslations} from 'next-intl';

/**
 * Choosing a document to send for checking.
 *
 * **What this replaces.** The screen used to render a bare
 * `<input type="file">`. A native file input is a grey 1990s control whose
 * label is written by the browser, in the browser's language — so a Hindi
 * screen still said "No file chosen" in English, the target was far under
 * 44px, and it looked nothing like the rest of the service. UX4G ships a File
 * Upload component for exactly this and the contract says to use it.
 *
 * The native input is still the thing doing the work; it is only moved out of
 * sight. Every path still goes through it, so the file dialogue, the browser's
 * own permissions and the accept filter all behave normally — nothing here
 * reimplements a file picker, it only dresses the one the browser already has.
 *
 * Accessibility:
 * - One tab stop. The panel is a drop target for a mouse, not a second
 *   control; the button is what a keyboard reaches, and dragging a file is
 *   never the only way to do anything.
 * - The state is written in words inside the panel — "Uploading…",
 *   "Received" — not carried by the border colour UX4G changes per state.
 * - Progress and errors are live regions, so an officer who cannot see the
 *   panel is still told what happened.
 * - `ux4g-btn-lg` is 48px, clear of the 44px minimum. The `md` size is 40px
 *   and would not be.
 */

export type PickerState = 'idle' | 'uploading' | 'error' | 'done';

const UPLOAD_ACCEPT = '.pdf,.png,.jpg,.jpeg,application/pdf,image/png,image/jpeg';

export default function DocumentPicker({
  state,
  fileName,
  fileSize,
  error,
  onChoose
}: {
  state: PickerState;
  fileName: string | null;
  fileSize: number | null;
  /** Already translated: this component never looks up an error code. */
  error: string | null;
  onChoose: (file: File) => void;
}) {
  const t = useTranslations('upload');
  const format = useFormatter();

  const inputRef = useRef<HTMLInputElement>(null);
  const headingId = useId();
  const hintId = useId();

  const [dragging, setDragging] = useState(false);

  // UX4G's own state classes. `scanning` is the one that reads as "working on
  // it" — it is what the design system uses while a file is being processed,
  // and it hides the choose button so the officer cannot start a second upload
  // over the top of the first.
  const stateClass = {
    idle: 'ux4g-upload-state-default',
    uploading: 'ux4g-upload-state-scanning',
    error: 'ux4g-upload-state-error',
    done: 'ux4g-upload-state-uploaded'
  }[state];

  function take(file: File | undefined | null) {
    if (!file) return;
    onChoose(file);
    // Let the same file be chosen again after a failure. Without this the
    // input holds the old value and picking it a second time fires no event.
    if (inputRef.current) inputRef.current.value = '';
  }

  function onDrop(event: React.DragEvent) {
    event.preventDefault();
    setDragging(false);
    if (state === 'uploading') return;
    take(event.dataTransfer.files?.[0]);
  }

  const sizeLabel =
    fileSize === null
      ? null
      : t('fileSize', {
          size: format.number(fileSize / 1048576, {maximumFractionDigits: 1})
        });

  return (
    <div className={`ux4g-upload ${stateClass}`}>
      <div
        className={`ux4g-upload-panel${dragging ? ' sutradhar-upload-dragging' : ''}`}
        onDragOver={(event) => {
          event.preventDefault();
          setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={onDrop}
      >
        <div className="ux4g-upload-content">
          <div className="ux4g-upload-option">
            <span className="ux4g-upload-icon-wrap">
              {state === 'uploading' ? (
                <span
                  className="ux4g-spinner ux4g-spinner-md sutradhar-spinner ux4g-upload-spinner"
                  aria-hidden="true"
                />
              ) : (
                <span className="ux4g-icon-outlined ux4g-upload-icon" aria-hidden="true">
                  {state === 'error' ? 'error' : 'upload_file'}
                </span>
              )}
            </span>

            <div className="ux4g-upload-titleblock">
              <p id={headingId} className="ux4g-upload-heading ux4g-heading-xs-strong">
                {state === 'uploading'
                  ? t('uploading')
                  : state === 'done'
                    ? t('received')
                    : t('heading')}
              </p>
              <p
                id={hintId}
                className="ux4g-upload-hint ux4g-body-s-default ux4g-text-neutral-secondary"
              >
                {state === 'uploading' ? t('uploadingHint') : t('hint')}
              </p>
            </div>

            <div className="ux4g-upload-divider" aria-hidden="true">
              <span className="ux4g-upload-divider-line" />
              <span className="ux4g-body-s-default ux4g-text-neutral-tertiary">
                {t('or')}
              </span>
              <span className="ux4g-upload-divider-line" />
            </div>

            {/* `ux4g-jc-center` rather than a rule of our own: the shipped
                `.ux4g-upload-actions` left-aligns its button while everything
                above it in the panel is centred, which reads as a mistake. A
                UX4G utility on the element is the contract's own answer to
                that — no descendant override of a component internal. */}
            <div className="ux4g-upload-actions ux4g-jc-center">
              <button
                type="button"
                className="ux4g-btn ux4g-btn-primary ux4g-btn-lg ux4g-upload-btn"
                aria-describedby={hintId}
                disabled={state === 'uploading'}
                onClick={() => inputRef.current?.click()}
              >
                {state === 'done' ? t('chooseAnother') : t('choose')}
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* The control that actually opens the file browser. Hidden from sight,
          not from the accessibility tree's point of view — it is never reached
          by tab because the button above stands in for it, and it carries a
          label so anything that does reach it is not an unnamed control. */}
      <input
        ref={inputRef}
        type="file"
        className="sutradhar-sr-only"
        tabIndex={-1}
        aria-label={t('choose')}
        accept={UPLOAD_ACCEPT}
        onChange={(event) => take(event.target.files?.[0])}
      />

      {/* What was chosen. Announced, so the choice is confirmed whether or not
          the officer can see the panel. */}
      <div aria-live="polite">
        {fileName !== null && state !== 'uploading' && (
          <ul className="ux4g-upload-file-list sutradhar-list-reset">
            <li
              className={`ux4g-upload-file-item${
                state === 'error' ? ' ux4g-upload-file-item-error' : ''
              }`}
            >
              <div className="ux4g-upload-file-row">
                <span className="ux4g-upload-file-leading">
                  <span
                    className="ux4g-icon-outlined ux4g-upload-file-icon"
                    aria-hidden="true"
                  >
                    description
                  </span>
                </span>
                <span className="ux4g-upload-file-copy">
                  <span className="ux4g-upload-file-name ux4g-body-s-strong">
                    {fileName}
                  </span>
                  <span className="ux4g-upload-file-description">
                    {state === 'error' ? t('notSent') : (sizeLabel ?? t('received'))}
                  </span>
                </span>
              </div>
            </li>
          </ul>
        )}
      </div>

      {error !== null && (
        <p className="ux4g-upload-error-msg ux4g-body-s-default" role="alert">
          {error}
        </p>
      )}
    </div>
  );
}
