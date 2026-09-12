/**
 * The officer's name for a field, never the database's.
 *
 * "date_of_birth" is a column name; "Date of birth" is what belongs on screen.
 *
 * Unknown keys are asked about rather than thrown at: next-intl logs a
 * MISSING_MESSAGE error and returns a placeholder instead of raising, so a
 * try/catch would never fire and the officer would be shown the key. `t.has`
 * checks first, and anything genuinely new falls back to a readable form of its
 * own name — a check added later cannot put a raw column name on screen.
 */
type Translator = {
  (key: string): string;
  has: (key: string) => boolean;
};

export function fieldLabel(t: Translator, field: string): string {
  const key = `fields.${field}`;
  if (t.has(key)) return t(key);
  return field.replace(/_/g, ' ').replace(/^./, (c) => c.toUpperCase());
}
