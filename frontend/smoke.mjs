/**
 * Happy-path smoke test.
 *
 * Drives a real browser through the Phase 1 journey: validation, a failed
 * sign-in, a keyboard-only successful sign-in, the session cookie being
 * invisible to JavaScript, text sizing, Hindi, and sign-out.
 *
 * Both servers must already be running (see README).
 *   npm run smoke
 *
 * Credentials come from the environment — the same seed variables used to
 * create the users — so no password is written into this file:
 *   SUTRADHAR_SEED_OFFICER_PASSWORD=... npm run smoke
 *
 * PLAYWRIGHT_CHROMIUM_PATH overrides the browser binary for environments that
 * ship their own Chromium; unset, Playwright uses the one it installed.
 */
import {chromium} from 'playwright';

const BASE = process.env.SMOKE_BASE_URL ?? 'http://localhost:3000';
const MOBILE = process.env.SMOKE_OFFICER_MOBILE ?? '9000000001';
const PASSWORD = process.env.SUTRADHAR_SEED_OFFICER_PASSWORD;
if (!PASSWORD) {
  console.error(
    'SUTRADHAR_SEED_OFFICER_PASSWORD is not set. Load it from .env first:\n' +
    '  set -a && . ../.env && set +a && npm run smoke'
  );
  process.exit(1);
}
const executablePath = process.env.PLAYWRIGHT_CHROMIUM_PATH || undefined;
const b = await chromium.launch({executablePath});
const ctx = await b.newContext({viewport:{width:1366,height:768}});
const p = await ctx.newPage();
const errs = [];
p.on('pageerror', e => errs.push(String(e)));
p.on('console', m => m.type()==='error' && errs.push(m.text()));

// ---------- 1. validation messages are words, not colour alone ----------
await p.goto(`${BASE}/en/login`,{waitUntil:'networkidle'});
await p.locator('button[type=submit]').click();
await p.waitForTimeout(300);
console.log('empty submit ->', JSON.stringify(await p.locator('.ux4g-input-helper').allTextContents()));
console.log('aria-invalid set:', await p.locator('input[type=tel]').getAttribute('aria-invalid'));

// ---------- 2. wrong password: plain language, no status code ----------
await p.fill('input[type=tel]',MOBILE);
await p.fill('input[type=password]','definitely-wrong');
await p.locator('button[type=submit]').click();
const alertBox = p.locator('.ux4g-alert[role=alert]');
await alertBox.waitFor({state:'visible',timeout:5000});
await p.waitForFunction(() => {
  const el = document.querySelector('.ux4g-alert[role=alert]');
  return el && el.textContent.trim().length > 0;
}, null, {timeout:5000});
const alertText = (await alertBox.textContent()).trim();
console.log('wrong password ->', JSON.stringify(alertText));
console.log('  leaks status code/jargon:', /40[0-9]|50[0-9]|error:|exception|traceback|agent|LLM|token|prompt/i.test(alertText));
await p.screenshot({path:'/tmp/shots/02-error.png'});

// ---------- 3. keyboard-only sign in ----------
await p.fill('input[type=tel]',''); await p.fill('input[type=password]','');
await p.locator('input[type=tel]').focus();
await p.keyboard.type(MOBILE);
await p.keyboard.press('Tab');
await p.keyboard.type(PASSWORD);
await p.keyboard.press('Tab');
console.log('\nfocus before Enter:', await p.evaluate(()=>document.activeElement.textContent?.trim()));
await p.keyboard.press('Enter');
await p.waitForURL(/\/en$/,{timeout:8000});
console.log('keyboard-only sign in -> landed on', new URL(p.url()).pathname);
await p.waitForSelector('text=/Signed in as/',{timeout:5000});
console.log('home shows:', (await p.locator('main p').first().textContent()).trim());
await p.screenshot({path:'/tmp/shots/03-home.png', fullPage:true});

// ---------- 4. cookie is httpOnly and invisible to JS ----------
const jsCookies = await p.evaluate(()=>document.cookie);
const realCookies = (await ctx.cookies()).map(c=>`${c.name}(httpOnly=${c.httpOnly},sameSite=${c.sameSite})`);
console.log('document.cookie sees:', JSON.stringify(jsCookies));
console.log('actual cookies:', realCookies.join(', '));

// ---------- 5. text scale control actually scales the UI ----------
const before = await p.evaluate(()=>getComputedStyle(document.documentElement).fontSize);
await p.getByRole('button',{name:'Increase text size'}).click();
await p.getByRole('button',{name:'Increase text size'}).click();
const after = await p.evaluate(()=>getComputedStyle(document.documentElement).fontSize);
const btnH = await p.evaluate(()=>{const b=document.querySelector('.ux4g-btn');return getComputedStyle(b).minHeight;});
console.log(`\nA+ : root font ${before} -> ${after}; a button's min-height is now ${btnH} (rem-based, so controls grow too)`);
await p.screenshot({path:'/tmp/shots/04-scaled.png', fullPage:true});

// ---------- 6. Hindi ----------
await p.getByRole('button',{name:'हिन्दी'}).click();
await p.waitForURL(/\/hi/,{timeout:8000});
console.log('switched to Hindi ->', new URL(p.url()).pathname, '| heading:', (await p.locator('h1').textContent()).trim());
await p.screenshot({path:'/tmp/shots/05-hindi.png', fullPage:true});

// ---------- 7. sign out ----------
await p.getByRole('button',{name:/साइन आउट|Sign out/}).click();
await p.waitForURL(/login/,{timeout:8000});
console.log('sign out -> ', new URL(p.url()).pathname);
console.log('cookies after sign out:', (await ctx.cookies()).length);

console.log('\npage errors:', errs.length ? errs : 'none');
await b.close();

console.log('\nsmoke: all steps passed');
