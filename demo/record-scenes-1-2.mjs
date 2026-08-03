import { chromium } from "playwright";
import fs from "fs";

const OUT = "demo-clips";
fs.mkdirSync(OUT, { recursive: true });
const CODE = process.env.CODE;
const PP = "https://www.propublica.org/article/machine-bias-risk-assessments-in-criminal-sentencing";
const APP = "https://newsdesk-rosy.vercel.app";
const TITLE = "The algorithm that labeled her high risk";

const browser = await chromium.launch();
const ctx = await browser.newContext({
  viewport: { width: 1920, height: 1080 },
  recordVideo: { dir: OUT, size: { width: 1920, height: 1080 } },
});

const mark = (s) => console.log(`MARK ${Date.now()} ${s}`);
const pause = (p, ms) => p.waitForTimeout(ms);

// ---------- Scene 1: the problem — the real story, then the front page ------
let p = await ctx.newPage();
mark("S1 propublica");
await p.goto(PP, { waitUntil: "domcontentloaded", timeout: 45000 }).catch(() => {});
await pause(p, 4000);
for (let i = 0; i < 6; i++) { await p.mouse.wheel(0, 520); await pause(p, 2600); }
mark("S1 frontpage");
await p.goto(APP + "/", { waitUntil: "domcontentloaded" });
await pause(p, 4500);
await p.mouse.wheel(0, 500); await pause(p, 2500);
await p.mouse.wheel(0, -500); await pause(p, 1500);
await p.close();
fs.renameSync((await p.video().path()), `${OUT}/s1-problem.webm`);

// ---------- Scene 2: the whole wizard, one take --------------------------
p = await ctx.newPage();
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
await p.getByText("Proposed facts").waitFor({ timeout: 90000 });
await pause(p, 2500);
await p.mouse.wheel(0, 350); await pause(p, 3000);
mark("S2 add-facts");
for (let i = 0; i < 5; i++) {
  const btn = p.getByRole("button", { name: "Add fact" }).first();
  await btn.scrollIntoViewIfNeeded();
  await btn.click();
  await pause(p, 1300);
}
await p.mouse.wheel(0, 800); await pause(p, 2500);
mark("S2 check-sources");
await p.getByRole("button", { name: "Check sources" }).click();
await p.getByRole("heading", { name: /Through-line object/ }).waitFor({ timeout: 15000 });
await pause(p, 2500);
mark("S2 art-direction");
// show the kit toggle deliberately: hover diorama, then stay on house
await p.getByRole("button", { name: "Paper diorama" }).hover(); await pause(p, 1600);
await p.getByRole("button", { name: "Paper diorama" }).click(); await pause(p, 2200);
await p.getByRole("button", { name: "House — mixed media" }).click(); await pause(p, 1600);
await p.getByRole("button", { name: "Record", exact: true }).click().catch(() => {});
await pause(p, 1200);
const ac2 = p.getByRole("textbox", { name: /Access code/ });
if (await ac2.count()) await ac2.fill(CODE);
mark("S2 write-script");
await p.getByRole("button", { name: "Write script" }).click();
// wait for either script review blocks or a refusal paragraph; retry up to 3x
for (let round = 1; round <= 4; round++) {
  const outcome = await Promise.race([
    p.getByText("This is the script").first().waitFor({ timeout: 660000 }).then(() => "script"),
    p.getByText("stage script failed").first().waitFor({ timeout: 660000 }).then(() => "refusal"),
  ]).catch(() => "timeout");
  mark(`S2 round${round} ${outcome}`);
  if (outcome === "script") break;
  if (outcome === "refusal") {
    await pause(p, 6000); // let the refusal be READ on camera
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
fs.renameSync((await p.video().path()), `${OUT}/s2-wizard.webm`);

await ctx.close(); await browser.close();
console.log("DONE scene 1-2");
