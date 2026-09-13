/**
 * The picture beside the sign-in form.
 *
 * It is not decoration for its own sake. It draws what the product does, in the
 * order it happens: a document arrives, three checks run against it side by
 * side, and everything they find converges on one person, who decides. That is
 * the whole claim of the system, and an officer signing in for the first time
 * reads it here before they read any copy.
 *
 * Drawn in `currentColor` and UX4G tokens rather than as a bitmap:
 *
 * - It is sharp at any size and costs about two kilobytes, which matters on the
 *   connections this service actually runs on.
 * - It re-colours itself in dark mode from one asset. A PNG would need two, and
 *   whichever one shipped would be wrong half the time.
 *
 * `aria-hidden`, and it carries no information that is not also written in
 * words beside it — a screen reader user loses nothing by skipping it.
 */
export default function AuthArtwork() {
  return (
    <svg
      className="sutradhar-auth-art"
      viewBox="0 0 320 260"
      role="presentation"
      aria-hidden="true"
      focusable="false"
    >
      {/* The uploaded document. */}
      <g className="sutradhar-auth-art-paper">
        <rect x="16" y="30" width="104" height="140" rx="8" />
        <g className="sutradhar-auth-art-rule">
          <rect x="32" y="52" width="60" height="7" rx="3.5" />
          <rect x="32" y="72" width="72" height="6" rx="3" />
          <rect x="32" y="88" width="52" height="6" rx="3" />
          <rect x="32" y="116" width="72" height="6" rx="3" />
          <rect x="32" y="132" width="44" height="6" rx="3" />
        </g>
      </g>

      {/* The three checks, running side by side rather than one after another. */}
      <g className="sutradhar-auth-art-line">
        <path d="M120 100 C 150 100, 150 52, 182 52" />
        <path d="M120 100 H 182" />
        <path d="M120 100 C 150 100, 150 148, 182 148" />
      </g>

      <g className="sutradhar-auth-art-check">
        <g>
          <rect x="182" y="34" width="36" height="36" rx="10" />
          <path className="sutradhar-auth-art-tick" d="M191 52 l6 6 l12 -13" />
        </g>
        <g>
          <rect x="182" y="82" width="36" height="36" rx="10" />
          <path className="sutradhar-auth-art-tick" d="M191 100 l6 6 l12 -13" />
        </g>
        <g>
          <rect x="182" y="130" width="36" height="36" rx="10" />
          <path className="sutradhar-auth-art-tick" d="M191 148 l6 6 l12 -13" />
        </g>
      </g>

      {/* Everything they found converges on one person. */}
      <g className="sutradhar-auth-art-line">
        <path d="M218 52 C 248 52, 248 100, 268 100" />
        <path d="M218 100 H 268" />
        <path d="M218 148 C 248 148, 248 100, 268 100" />
      </g>

      <g className="sutradhar-auth-art-person">
        <circle cx="272" cy="100" r="34" />
        <circle className="sutradhar-auth-art-person-head" cx="272" cy="90" r="11" />
        <path
          className="sutradhar-auth-art-person-head"
          d="M254 122 a18 18 0 0 1 36 0"
        />
      </g>

      {/* The decision the person makes, and nothing before it. */}
      <g className="sutradhar-auth-art-line">
        <path d="M272 134 V 196" />
      </g>
      <g className="sutradhar-auth-art-paper">
        <rect x="200" y="196" width="104" height="44" rx="8" />
        <g className="sutradhar-auth-art-rule">
          <rect x="216" y="212" width="48" height="6" rx="3" />
          <rect x="216" y="226" width="32" height="6" rx="3" />
        </g>
      </g>
    </svg>
  );
}
