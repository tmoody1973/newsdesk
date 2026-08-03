import { chromium } from "playwright";
import fs from "fs";

// Second-escalation retake: trim F3 and F5 as well (the refusal keeps naming
// the stat-dense blocks at 36-40 words against the 23-27 window).
const OUT = "demo-clips";
fs.mkdirSync(OUT, { recursive: true });
const CODE = process.env.CODE;
const PP = "https://www.propublica.org/article/machine-bias-risk-assessments-in-criminal-sentencing";
const APP = "https://newsdesk-rosy.vercel.app";
const TITLE = "The algorithm that labeled her high risk";

const TRIMS = [
  [0, "Brisha Borden was rated high risk after taking a child's bicycle and scooter, and she has not been charged with any new crimes since."],
  [1, "ProPublica analyzed risk scores for more than 7,000 people arrested in Broward County, Florida, in 2013 and 2014."],
  [2, "Black defendants were 77 percent more likely than white defendants to be labeled at higher risk of committing a future violent crime."],
  [4, "In 2014, U.S. Attorney General Eric Holder warned that risk assessment scores might be injecting bias into the courts."],
];

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
mark("S2 trim-facts");
const factBoxes = p.getByPlaceholder("One verified statement, as you would say it out loud.");
for (const [idx, text] of TRIMS) {
  await factBoxes.nth(idx).scrollIntoViewIfNeeded();
  await factBoxes.nth(idx).click();
  await factBoxes.nth(idx).fill("");
  await factBoxes.nth(idx).pressSequentially(text, { delay: 10 });
  await pause(p, 700);
}
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
for (let round = 1; round <= 12; round++) {
  const outcome = await Promise.race([
    p.getByText("This is the script").first().waitFor({ timeout: 660000 }).then(() => "script"),
    p.getByText("stage script failed").first().waitFor({ timeout: 660000 }).then(() => "refusal"),
  ]).catch(() => "timeout");
  mark(`S2 round${round} ${outcome}`);
  if (outcome === "script") break;
  if (outcome === "refusal") {
    await pause(p, 6000);
    if (round === 12) break;
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
fs.renameSync(await p.video().path(), `${OUT}/s2-wizard-retake3.webm`);

await ctx.close();
await browser.close();
console.log("DONE scene 2 retake3");
