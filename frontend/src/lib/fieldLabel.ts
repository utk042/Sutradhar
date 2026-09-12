/**
 * The officer's name for a field, never the database's.
 *
 * "date_of_birth" is a column name; "Date of birth" is what belongs on screen.
 * A field the locale files do not know yet falls back to a readable form of its
 * own name rather than rendering blank or raw.
 */
export function fieldLabel(t: (key: string) => string, field: string): string {
  try {
    return t(`fields.${field}`);
  } catch {
    return field.replace(/_/g, ' ').replace(/^./, (c) => c.toUpperCase());
  }
}
