import { chromium } from "playwright";
import fs from "fs";

// Contingency retake of scene 2 only (HANDOFF-demo-video.md: if all 4 rounds
// refuse, trim the two longest facts to one spoken sentence each and re-run
// scene 2 from the wizard — the run resumes by title).
const OUT = "demo-clips";
fs.mkdirSync(OUT, { recursive: true });
const CODE = process.env.CODE;
const PP = "https://www.propublica.org/article/machine-bias-risk-assessments-in-criminal-sentencing";
const APP = "https://newsdesk-rosy.vercel.app";
const TITLE = "The algorithm that labeled her high risk";

const F1_TRIM =
  "Brisha Borden was rated high risk after taking a child's bicycle and scooter, and she has not been charged with any new crimes since.";
const F2_TRIM =
  "ProPublica analyzed risk scores for more than 7,000 people arrested in Broward County, Florida, in 2013 and 2014.";

const browser = await chromium.launch();
const ctx = await browser.newContext({
  viewport: { width: 1920, height: 1080 },
  recordVideo: { dir: OUT, size: { width: 1920, height: 1080 } },
});

const mark = (s) => console.log(`MARK ${Date.now()} ${s}`);
const pause = (p, ms) => p.waitForTimeout(ms);

const p = await ctx.newPage();
mark("S2 wizard-open");
await p.goto(APP + "/new", { waitUntil: "domcontentloaded" });
await pause(p, 2500);
await p.getByRole("textbox", { name: /What is this story about/ }).click();
await p.getByRole("textbox", { name: /What is this story about/ }).pressSequentially(TITLE, { delay: 28 });
await pause(p, 900);
mark("S2 paste-url");
await p.getByRole("textbox", { name: /Paste a link/ }).click();
await p.getByRole("textbox", { name: /Paste a link/ }).pressSequentially(PP, { delay: 6 });
await p.getByRole("textbox", { name: /Access code/ }).fill(CODE);
await pause(p, 700);
mark("S2 pull");
await p.getByRole("button", { name: "Pull facts" }).click();
await p.getByText("Proposed facts").first().waitFor({ timeout: 90000 });
await pause(p, 2500);
await p.mouse.wheel(0, 350); await pause(p, 3000);
mark("S2 add-facts");
for (let i = 0; i < 5; i++) {
  const btn = p.getByRole("button", { name: "Add fact" }).first();
  await btn.scrollIntoViewIfNeeded();
  await btn.click();
  await pause(p, 1300);
}
// Trim the two longest facts to one spoken sentence each. The refusal rounds
// kept failing POL-5 (23-27 words per line) on the number-dense blocks.
mark("S2 trim-facts");
const factBoxes = p.getByPlaceholder("One verified statement, as you would say it out loud.");
await factBoxes.nth(0).scrollIntoViewIfNeeded();
await factBoxes.nth(0).click();
await factBoxes.nth(0).fill("");
await factBoxes.nth(0).pressSequentially(F1_TRIM, { delay: 12 });
await pause(p, 900);
await factBoxes.nth(1).scrollIntoViewIfNeeded();
await factBoxes.nth(1).click();
await factBoxes.nth(1).fill("");
await factBoxes.nth(1).pressSequentially(F2_TRIM, { delay: 12 });
await pause(p, 900);
await p.mouse.wheel(0, 600); await pause(p, 2000);
mark("S2 check-sources");
await p.getByRole("button", { name: "Check sources" }).click();
await p.getByRole("heading", { name: /Through-line object/ }).waitFor({ timeout: 15000 });
await pause(p, 2500);
mark("S2 art-direction");
await p.getByRole("button", { name: "Paper diorama" }).hover(); await pause(p, 1600);
await p.getByRole("button", { name: "Paper diorama" }).click(); await pause(p, 2200);
await p.getByRole("button", { name: "House — mixed media" }).click(); await pause(p, 1600);
await p.getByRole("button", { name: "Record", exact: true }).click().catch(() => {});
await pause(p, 1200);
const ac2 = p.getByRole("textbox", { name: /Access code/ });
if (await ac2.count()) await ac2.fill(CODE);
mark("S2 write-script");
await p.getByRole("button", { name: "Write script" }).click();
for (let round = 1; round <= 4; round++) {
  const outcome = await Promise.race([
    p.getByText("This is the script").first().waitFor({ timeout: 660000 }).then(() => "script"),
    p.getByText("stage script failed").first().waitFor({ timeout: 660000 }).then(() => "refusal"),
  ]).catch(() => "timeout");
  mark(`S2 round${round} ${outcome}`);
  if (outcome === "script") break;
  if (outcome === "refusal") {
    await pause(p, 6000);
    if (round === 4) break;
    const ac = p.getByRole("textbox", { name: /Access code/ });
    if (await ac.count()) await ac.fill(CODE);
    await p.getByRole("button", { name: "Write script" }).click();
  } else break;
}
await pause(p, 2500);
await p.mouse.wheel(0, 500); await pause(p, 3000);
await p.mouse.wheel(0, 600); await pause(p, 3000);
mark("S2 send-to-generation");
const send = p.getByRole("button", { name: "Send to generation" });
if (await send.count()) {
  await send.scrollIntoViewIfNeeded();
  await send.click();
  await p.waitForURL(/\/runs\//, { timeout: 30000 }).catch(() => {});
  await pause(p, 5000);
}
mark("S2 end");
await p.close();
fs.renameSync(await p.video().path(), `${OUT}/s2-wizard-retake.webm`);

await ctx.close();
await browser.close();
console.log("DONE scene 2 retake");
