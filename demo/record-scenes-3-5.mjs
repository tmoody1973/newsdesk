import { chromium } from "playwright";
import fs from "fs";

const OUT = "demo-clips";
fs.mkdirSync(OUT, { recursive: true });
const CODE = process.env.CODE;
const APP = "https://newsdesk-rosy.vercel.app";
const RUN = "the-algorithm-that-labeled-her-high-risk";
const APPROVER = "Claude (agent) — UNREVIEWED, pending Tarik Moody";
const B2 = `https://s3.us-east-005.backblazeb2.com/newsdesk-assets/${RUN}/${RUN}.mp4`;

const browser = await chromium.launch();
const ctx = await browser.newContext({
  viewport: { width: 1920, height: 1080 },
  recordVideo: { dir: OUT, size: { width: 1920, height: 1080 } },
});

const mark = (s) => console.log(`MARK ${Date.now()} ${s}`);
const pause = (p, ms) => p.waitForTimeout(ms);
const save = async (p, name) => {
  await p.close();
  fs.renameSync(await p.video().path(), `${OUT}/${name}`);
};

// ---------- Scene 2b b-roll: the brand kit page (for SEG 2b's middle) ------
let p = await ctx.newPage();
mark("S2b kit-open");
await p.goto(`${APP}/brand-kit`, { waitUntil: "domcontentloaded" });
await pause(p, 4000);
for (let i = 0; i < 6; i++) { await p.mouse.wheel(0, 380); await pause(p, 2400); }
mark("S2b kit-end");
await save(p, "s2b-kit.webm");

// ---------- Scene 3: the run board, live, while blocks render --------------
p = await ctx.newPage();
mark("S3 board-open");
await p.goto(`${APP}/runs/${RUN}`, { waitUntil: "domcontentloaded" });
await pause(p, 3000);
// film the board polling until every block is ready (Send to editor appears)
// or the run is already approved from a previous pass
const deadline = Date.now() + 12 * 60 * 1000;
let readyPath = null;
while (Date.now() < deadline) {
  if (await p.getByRole("link", { name: "Send to editor" }).count()) { readyPath = "review"; break; }
  if (await p.getByText("Approved", { exact: true }).first().count()) { readyPath = "approved"; break; }
  await pause(p, 4000);
}
mark(`S3 blocks-ready ${readyPath ?? "TIMEOUT"}`);
await pause(p, 4000);
await p.mouse.wheel(0, 500); await pause(p, 2500);
await p.mouse.wheel(0, -500); await pause(p, 1500);
await save(p, "s3-board.webm");
if (!readyPath) { await browser.close(); throw new Error("blocks never became ready"); }

// ---------- Scene 4: editor review, the stamp, assembly --------------------
p = await ctx.newPage();
mark("S4 review-open");
await p.goto(`${APP}/runs/${RUN}/review`, { waitUntil: "domcontentloaded" });
await pause(p, 3500);
// approve each block, deliberately, scrolling as we go
while (true) {
  const btn = p.getByRole("button", { name: "Approve", exact: true }).first();
  if (!(await btn.count())) break;
  await btn.scrollIntoViewIfNeeded();
  await pause(p, 900);
  await btn.click();
  await pause(p, 1100);
}
mark("S4 all-approved");
const nameBox = p.getByLabel("Your name");
await nameBox.scrollIntoViewIfNeeded();
await nameBox.click();
await nameBox.pressSequentially(APPROVER, { delay: 30 });
await pause(p, 800);
await p.getByLabel("Access code").fill(CODE);
await pause(p, 1200);
mark("S4 stamp");
await p.getByRole("button", { name: "Stamp: Approved" }).click();
await pause(p, 3000);
// back on the board: film AWAITING -> assembly -> published
await p.goto(`${APP}/runs/${RUN}`, { waitUntil: "domcontentloaded" }).catch(() => {});
mark("S4 assembly-wait");
const pubDeadline = Date.now() + 8 * 60 * 1000;
while (Date.now() < pubDeadline) {
  if (await p.getByRole("heading", { name: "The film" }).count()) break;
  await pause(p, 4000);
}
mark("S4 published");
await pause(p, 5000);
await save(p, "s4-approve.webm");

// ---------- Scene 5: the stamp, the log, captions, receipt, human runs -----
p = await ctx.newPage();
mark("S5 published-board");
await p.goto(`${APP}/runs/${RUN}`, { waitUntil: "domcontentloaded" });
await pause(p, 6000); // the stamp and the cost line
mark("S5 run-log");
await p.getByRole("heading", { name: "Run log" }).scrollIntoViewIfNeeded();
await pause(p, 1000);
for (let i = 0; i < 4; i++) { await p.mouse.wheel(0, 260); await pause(p, 2000); } // ~8s deliberate
mark("S5 captions");
await p.getByRole("heading", { name: "Social captions" }).scrollIntoViewIfNeeded();
await pause(p, 2500);
const copy = p.getByRole("button", { name: "Copy", exact: true }).first();
if (await copy.count()) { await copy.click(); await pause(p, 2500); } // "Copied ✓" on film
mark("S5 receipt");
await p.goto(`${APP}/runs/${RUN}/receipt`, { waitUntil: "domcontentloaded" });
await pause(p, 3000);
for (let i = 0; i < 8; i++) { await p.mouse.wheel(0, 420); await pause(p, 1500); } // ~12s scroll
mark("S5 human-run-1");
await p.goto(`${APP}/runs/why-one-in-four-babies-in-this-karachi`, { waitUntil: "domcontentloaded" });
await pause(p, 8000);
mark("S5 human-run-2");
await p.goto(`${APP}/runs/why-did-openai-s-and-anthropic-s-ai`, { waitUntil: "domcontentloaded" });
await pause(p, 8000);
mark("S5 end");
await save(p, "s5-published.webm");

// ---------- Scene 5b: the published film plays inside the demo -------------
p = await ctx.newPage();
mark("S5b film-open");
await p.goto(B2, { waitUntil: "domcontentloaded" }).catch(() => {});
await pause(p, 1500);
await p.evaluate(() => {
  const v = document.querySelector("video");
  if (v) { v.muted = true; v.play(); }
}).catch(() => {});
mark("S5b playing");
await pause(p, 13000);
mark("S5b end");
await save(p, "s5b-film.webm");

await ctx.close();
await browser.close();
console.log("DONE scenes 3-5");
