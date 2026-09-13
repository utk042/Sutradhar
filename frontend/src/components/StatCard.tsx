import type {ReactNode} from 'react';

/**
 * One number, and what it means.
 *
 * A single current value is a stat tile, not a one-bar chart — the number *is*
 * the chart. What the tile adds over a bare figure is a tone: a coloured rule
 * down its edge and a matching icon, so a row of them has a shape the eye can
 * read before any of it is understood.
 *
 * The tone is never the only thing carrying the meaning. Every tile's label is
 * a sentence, and the figure is the figure — the colour and the icon are
 * reinforcement, which is what the brief asks and what makes the row survive
 * greyscale, colour blindness and a bad office monitor.
 *
 * Tones are UX4G's reserved status colours plus the brand hue, used only where
 * they mean what they say: `danger` is for something that needs resolving,
 * `warning` for something to look at, `success` for work completed, `brand` for
 * a plain count that is neither good nor bad. They are never used to tell two
 * arbitrary series apart — that would spend a reserved channel on identity.
 *
 * Figures use the font's proportional digits. `tabular-nums` gives every digit
 * the width of a zero, which makes a number like 121 look loose at this size;
 * it belongs in columns that must align, not on a tile.
 */

export type Tone = 'brand' | 'success' | 'warning' | 'danger' | 'neutral';

export default function StatCard({
  label,
  value,
  tone = 'brand',
  icon,
  footnote
}: {
  label: string;
  value: string;
  tone?: Tone;
  /** A Material icon ligature, e.g. "pending_actions". Decorative. */
  icon?: string;
  footnote?: ReactNode;
}) {
  return (
    <div className={`ux4g-card ux4g-card-solid sutradhar-stat sutradhar-tone-${tone}`}>
      <div className="ux4g-card-body">
        <div className="sutradhar-stat-head">
          <p className="ux4g-body-s-default ux4g-text-neutral-secondary">{label}</p>
          {icon && (
            /* `sutradhar-stat-icon` also carries `ux4g-icon-outlined`, which a
               stray topbar rule in the shipped CSS colours
               `--ux4g-text-neutral-inverse` — near-white on a white card. The
               paired class wins on specificity and hands it back the tone. */
            <span
              className="ux4g-icon-outlined sutradhar-stat-icon"
              aria-hidden="true"
            >
              {icon}
            </span>
          )}
        </div>
        <p className="sutradhar-stat-value">{value}</p>
        {footnote && (
          <p className="ux4g-body-s-default ux4g-text-neutral-tertiary">{footnote}</p>
        )}
      </div>
    </div>
  );
}
