import { chromium } from "playwright";
import fs from "fs";

// Re-film S5 + S5b after the caption stage completed (the first pass crashed
// waiting for a captions section that had not been written yet).
const OUT = "demo-clips";
fs.mkdirSync(OUT, { recursive: true });
const APP = "https://newsdesk-rosy.vercel.app";
const RUN = "the-algorithm-that-labeled-her-high-risk";
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

let p = await ctx.newPage();
mark("S5 published-board");
await p.goto(`${APP}/runs/${RUN}`, { waitUntil: "domcontentloaded" });
await pause(p, 6000);
mark("S5 run-log");
await p.getByRole("heading", { name: "Run log" }).scrollIntoViewIfNeeded();
await pause(p, 1000);
for (let i = 0; i < 4; i++) { await p.mouse.wheel(0, 260); await pause(p, 2000); }
mark("S5 receipt");
await p.goto(`${APP}/runs/${RUN}/receipt`, { waitUntil: "domcontentloaded" });
await pause(p, 3000);
for (let i = 0; i < 8; i++) { await p.mouse.wheel(0, 420); await pause(p, 1500); }
mark("S5 human-run-1");
await p.goto(`${APP}/runs/why-one-in-four-babies-in-this-karachi`, { waitUntil: "domcontentloaded" });
await pause(p, 8000);
mark("S5 human-run-2");
await p.goto(`${APP}/runs/why-did-openai-s-and-anthropic-s-ai`, { waitUntil: "domcontentloaded" });
await pause(p, 6000);
// The demo run has no captions (GMI balance hit 402 during the caption
// stage); the captions beat films on this human-approved run instead.
mark("S5 captions");
await p.getByRole("heading", { name: "Social captions" }).scrollIntoViewIfNeeded();
await pause(p, 2500);
const copy = p.getByRole("button", { name: "Copy", exact: true }).first();
if (await copy.count()) { await copy.click(); await pause(p, 2500); }
mark("S5 end");
await save(p, "s5-published.webm");

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
console.log("DONE scene 5 refilm");
