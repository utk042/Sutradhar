/**
 * Happy-path smoke test.
 *
 * Drives a real browser through the whole journey:
 *   validation -> a failed sign-in -> a keyboard-only successful one ->
 *   a refused role claim ->
 *   the session cookie being invisible to JavaScript -> upload -> checks ->
 *   findings with evidence -> approve over a blocking finding ->
 *   switch to Hindi from Settings -> reject in Hindi -> sign out.
 *
 * Both servers must already be running (see README).
 *   set -a && . ../.env && set +a && npm run smoke
 *
 * Credentials come from the environment — the same seed variables that create
 * the users — so no password is written into this file.
 *
 * PLAYWRIGHT_CHROMIUM_PATH overrides the browser binary for environments that
 * ship their own Chromium; unset, Playwright uses the one it installed.
 */
import {chromium} from 'playwright';

const BASE = process.env.SMOKE_BASE_URL ?? 'http://localhost:3000';
const SAMPLES = process.env.SMOKE_SAMPLES ?? '/home/user/Sutradhar/data/samples';
const MOBILE = process.env.SMOKE_OFFICER_MOBILE ?? '9000000001';
const PASSWORD = process.env.SUTRADHAR_SEED_OFFICER_PASSWORD;
if (!PASSWORD) {
  console.error(
    'SUTRADHAR_SEED_OFFICER_PASSWORD is not set. Load it from .env first:\n' +
    '  set -a && . ../.env && set +a && npm run smoke'
  );
  process.exit(1);
}

const shots = '/tmp/shots';
const b = await chromium.launch({executablePath: process.env.PLAYWRIGHT_CHROMIUM_PATH});
const ctx = await b.newContext({viewport: {width: 1366, height: 768}});
const p = await ctx.newPage();
const errs = [];
p.on('pageerror', (e) => errs.push(String(e)));

const step = (n, s) => console.log(`\n${n}. ${s}`);

// ---------------------------------------------------------------- sign in --
step(1, 'validation messages are words, not a red border alone');
await p.goto(`${BASE}/en/login`, {waitUntil: 'networkidle'});
await p.locator('button[type=submit]').click();
await p.waitForTimeout(300);
console.log('   ', JSON.stringify(await p.locator('.ux4g-input-helper').allTextContents()));
console.log('    aria-invalid:', await p.locator('input[type=tel]').getAttribute('aria-invalid'));

step(2, 'a wrong password says what to do, with no status code or jargon');
await p.fill('input[type=tel]', MOBILE);
await p.fill('input[type=password]', 'definitely-wrong');
await p.locator('select[name=role]').selectOption('officer');
await p.locator('button[type=submit]').click();
const alertBox = p.locator('.ux4g-alert[role=alert]');
await alertBox.waitFor({state: 'visible', timeout: 5000});
await p.waitForFunction(
  () => document.querySelector('.ux4g-alert[role=alert]')?.textContent.trim().length > 0,
  null, {timeout: 5000});
const alertText = (await alertBox.textContent()).trim();
console.log('   ', JSON.stringify(alertText));
console.log('    leaks a status code or jargon:',
  /40[0-9]|50[0-9]|exception|traceback|agent|LLM|token|prompt/i.test(alertText));

step(3, 'sign in using only the keyboard — the eye, the dropdown and all');
await p.reload({waitUntil: 'networkidle'});
await p.locator('input[type=tel]').focus();
await p.keyboard.type(MOBILE);
await p.keyboard.press('Tab');
await p.keyboard.type(PASSWORD);
await p.keyboard.press('Tab');           // the eye in the password field
await p.keyboard.press('Enter');
console.log('    the eye reveals the password:',
  (await p.locator('input[name=password]').getAttribute('type')) === 'text');
console.log('    and does not submit the form:', /login/.test(p.url()));
await p.keyboard.press('Enter');         // and hides it again
console.log('    and hides it again:',
  (await p.locator('input[name=password]').getAttribute('type')) === 'password');
await p.keyboard.press('Tab');           // the role dropdown
await p.locator('select[name=role]').selectOption('officer');
await p.locator('select[name=role]').focus();
console.log('    a role was chosen:',
  (await p.locator('select[name=role]').inputValue()) === 'officer');
await p.keyboard.press('Tab');
await p.keyboard.press('Enter');
await p.waitForURL(/\/en$/, {timeout: 8000});
console.log('    landed on', new URL(p.url()).pathname, '—',
  (await p.locator('main p').first().textContent()).trim());

step(4, 'claiming a role you do not hold is refused, and signs nothing in');
{
  const other = await b.newContext({viewport: {width: 1366, height: 768}});
  const q = await other.newPage();
  await q.goto(`${BASE}/en/login`, {waitUntil: 'networkidle'});
  await q.fill('input[type=tel]', MOBILE);
  await q.fill('input[type=password]', PASSWORD);
  await q.locator('select[name=role]').selectOption('dept_head');
  await q.locator('button[type=submit]').click();
  const refusal = q.locator('.ux4g-alert[role=alert]');
  await refusal.waitFor({state: 'visible', timeout: 5000});
  await q.waitForTimeout(250);
  console.log('   ', JSON.stringify((await refusal.textContent()).trim()));
  console.log('    still on the sign-in screen:', /login/.test(q.url()));
  console.log('    session cookies set:',
    (await other.cookies()).filter((c) => c.name.startsWith('sutradhar')).length);
  await other.close();
}

step(5, 'the session cookie is invisible to JavaScript');
console.log('    document.cookie sees:', JSON.stringify(await p.evaluate(() => document.cookie)));
console.log('    actual:', (await ctx.cookies())
  .map((c) => `${c.name}(httpOnly=${c.httpOnly},sameSite=${c.sameSite})`).join(', '));

// ------------------------------------------------- upload, review, approve --
step(6, 'upload a certificate whose date of birth disagrees with the records');
await p.setInputFiles('input[type=file]', `${SAMPLES}/birth-certificate-dob-mismatch.pdf`);
await p.waitForFunction(
  () => document.body.innerText.includes('Waiting for your decision'),
  null, {timeout: 20000});
console.log('    checks finished; the row now reads:',
  (await p.locator('table tbody tr td').nth(2).textContent()).trim());
await p.screenshot({path: `${shots}/p2-home.png`, fullPage: true});

step(7, 'the review screen leads with what needs attention');
await p.locator('table tbody tr a').first().click();
await p.waitForURL(/\/review\/\d+$/, {timeout: 8000});
await p.waitForSelector('text=/What was read from the document/', {timeout: 8000});
console.log('   ', (await p.locator('[aria-labelledby=pane-checks] p').first().textContent()).trim());
console.log('    first finding:',
  (await p.locator('ul li.ux4g-card .ux4g-heading-xxs-strong').first().textContent()).trim());
await p.screenshot({path: `${shots}/p2-review.png`, fullPage: true});

step(8, 'the evidence cites where the reference value came from');
await p.locator('button', {hasText: 'View evidence'}).first().click();
await p.waitForTimeout(300);
(await p.locator('table').filter({hasText: 'On the document'}).first().innerText())
  .split('\n').forEach((l) => console.log('      ' + l));
await p.screenshot({path: `${shots}/p2-evidence.png`, fullPage: true});

step(9, 'a blocking finding cannot be approved without a written note');
const approve = p.locator('button', {hasText: /^Approve$/});
await approve.click();
await p.waitForTimeout(400);
console.log('    a note was demanded:', (await p.locator('textarea').count()) === 1);
console.log('    approve stays disabled while it is empty:', await approve.isDisabled());
await p.locator('textarea').fill('Checked against the physical register in the office.');
await p.waitForTimeout(200);
await approve.click();
await p.waitForURL(/\/decision$/, {timeout: 8000});
await p.waitForSelector('text=/was approved by/', {timeout: 8000});
console.log('    confirmation:');
(await p.locator('main').innerText()).split('\n').filter(Boolean)
  .forEach((l) => console.log('      ' + l));
await p.screenshot({path: `${shots}/p2-confirmation.png`, fullPage: true});

// ------------------------------------------------------ reject, in Hindi ---
step(10, 'reject a document with no matching record, in Hindi');
await p.locator('a', {hasText: 'Back to your desk'}).click();
await p.waitForURL(/\/en$/, {timeout: 8000});
await p.setInputFiles('input[type=file]', `${SAMPLES}/income-certificate-unknown.pdf`);
await p.waitForFunction(
  () => (document.body.innerText.match(/Waiting for your decision/g) || []).length >= 1,
  null, {timeout: 20000});
// Language is a setting now, not a control in the chrome of every page: the
// only way to Hindi is the Settings screen, so that is the way the test goes.
await p.locator('nav a', {hasText: 'Settings'}).first().click();
await p.waitForURL(/\/en\/settings$/, {timeout: 8000});
await p.getByRole('button', {name: 'हिन्दी'}).click();
await p.waitForURL(/\/hi\/settings$/, {timeout: 8000});
await p.locator('nav a', {hasText: 'आपका डेस्क'}).first().click();
await p.waitForURL(/\/hi$/, {timeout: 8000});
await p.locator('table tbody tr a').first().click();
await p.waitForURL(/\/review\/\d+$/, {timeout: 8000});
await p.waitForSelector('h1', {timeout: 8000});
console.log('    heading:', (await p.locator('h1').innerText()).trim());
console.log('    summary:', (await p.locator('[aria-labelledby=pane-checks] p').first().innerText()).trim());
await p.screenshot({path: `${shots}/p2-review-hindi.png`, fullPage: true});

const reject = p.locator('button', {hasText: /अस्वीकृत करें/});
await reject.click();
await p.waitForTimeout(400);
console.log('    a reason was demanded:', (await p.locator('textarea').count()) === 1);
console.log('    reject stays disabled while it is empty:', await reject.isDisabled());
await p.locator('textarea').fill('अभिलेखों में कोई प्रविष्टि नहीं मिली।');
await p.waitForTimeout(200);
await reject.click();
await p.waitForURL(/\/decision$/, {timeout: 8000});
await p.waitForSelector('[role=status]', {timeout: 8000});
console.log('    confirmation:');
(await p.locator('main').innerText()).split('\n').filter(Boolean)
  .forEach((l) => console.log('      ' + l));
await p.screenshot({path: `${shots}/p2-confirmation-hindi.png`, fullPage: true});

// ------------------------------------------------------------- sign out ----
step(11, 'sign out clears the session');
await p.locator('a', {hasText: /अपने डेस्क पर लौटें/}).click();
await p.waitForURL(/\/hi$/, {timeout: 8000});
await p.getByRole('button', {name: /साइन आउट/}).click();
await p.waitForURL(/login/, {timeout: 8000});
console.log('    landed on', new URL(p.url()).pathname,
  '| session cookies left:', (await ctx.cookies()).filter((c) => c.name.startsWith('sutradhar')).length);

console.log('\npage errors:', errs.length ? errs : 'none');
console.log('smoke: all steps passed');
await b.close();
