// Real Next middleware/rewrite transport, with a local synthetic API only.
import assert from "node:assert/strict";
import { createServer } from "node:http";
import { createHash, randomBytes } from "node:crypto";
import { spawn } from "node:child_process";
import { readFile } from "node:fs/promises";
import { createReadStream } from "node:fs";
import { Readable } from "node:stream";

const manifest = JSON.parse(await readFile(".next/routes-manifest.json", "utf8"));
const rules = Array.isArray(manifest.rewrites) ? manifest.rewrites : Object.values(manifest.rewrites).flat();
const destination = new URL(rules.find(rule => rule.source === "/api/:path*").destination);
assert.ok(["localhost", "127.0.0.1"].includes(destination.hostname), "Build with INTERNAL_BACKEND_URL=http://127.0.0.1:18080 for this local test");
const state = randomBytes(32).toString("hex");
const cookie = randomBytes(32).toString("hex");
const user = "synthetic-operator", password = randomBytes(24).toString("hex");
const authorization = "Basic " + Buffer.from(`${user}:${password}`).toString("base64");
const api = createServer(async (req, res) => {
  res.setHeader("Content-Type", "application/json");
  if (req.headers.authorization !== authorization) { res.writeHead(401).end("{}"); return; }
  if (req.url === "/api/v1/ready") { res.end(JSON.stringify({ status: "ready" })); return; }
  if (req.url === "/api/v1/marketplaces/mercadolivre/auth-url") {
    res.setHeader("Set-Cookie", `ml_oauth=${cookie}; Path=/api/v1/marketplaces/mercadolivre; HttpOnly; SameSite=Lax`);
    res.end(JSON.stringify({ auth_url: `https://provider.invalid/authorize?state=${state}` })); return;
  }
  if (req.url === "/api/v1/marketplaces/mercadolivre/oauth/callback") {
    let body = ""; for await (const chunk of req) body += chunk;
    const payload = JSON.parse(body);
    const valid = req.headers.cookie === `ml_oauth=${cookie}` && payload.state === state && payload.code === "synthetic-code";
    res.writeHead(valid ? 200 : 400).end(JSON.stringify({ received: valid })); return;
  }
  if (req.url === "/api/v1/imports/upload") {
    let bytes = 0; const hash = createHash("sha256");
    for await (const chunk of req) { bytes += chunk.length; hash.update(chunk); }
    res.end(JSON.stringify({ bytes, sha256: hash.digest("hex") })); return;
  }
  res.writeHead(404).end("{}");
});
await new Promise((resolve, reject) => { api.once("error", reject); api.listen(Number(destination.port), destination.hostname, resolve); });
const port = "3299", origin = `http://127.0.0.1:${port}`;
const child = spawn(process.execPath, ["node_modules/next/dist/bin/next", "start", "-H", "127.0.0.1", "-p", port], {
  env: { ...process.env, ADMIN_USERNAME: user, ADMIN_PASSWORD: password, APP_ORIGIN: origin }, stdio: ["ignore", "pipe", "pipe"],
});
let logs = "";
child.stdout.on("data", data => { logs += data; }); child.stderr.on("data", data => { logs += data; });
try {
  let ready = false;
  for (let attempt = 0; attempt < 100; attempt++) {
    if (child.exitCode !== null) throw new Error(logs);
    try { if ((await fetch(origin)).status === 401) { ready = true; break; } } catch { /* startup */ }
    await new Promise(resolve => setTimeout(resolve, 200));
  }
  assert.ok(ready);
  const health = spawn(process.execPath, ["scripts/healthcheck.mjs"], { env: { ...process.env, PORT: port, ADMIN_USERNAME: user, ADMIN_PASSWORD: password }, stdio: "ignore" });
  assert.equal(await new Promise((resolve, reject) => { health.once("error", reject); health.once("exit", resolve); }), 0, "Healthcheck must exercise the real authenticated proxy");
  const auth = await fetch(origin + "/api/v1/marketplaces/mercadolivre/auth-url", { headers: { authorization } });
  assert.equal(auth.status, 200);
  assert.ok(auth.headers.get("set-cookie").includes("HttpOnly"));
  const authURL = new URL((await auth.json()).auth_url);
  assert.equal(authURL.searchParams.get("state"), state);
  const callback = await fetch(origin + "/api/v1/marketplaces/mercadolivre/oauth/callback", { method: "POST", headers: { authorization, cookie: `ml_oauth=${cookie}`, "content-type": "application/json", origin }, body: JSON.stringify({ code: "synthetic-code", state }) });
  assert.equal(callback.status, 200);
  assert.equal((await callback.json()).received, true);

  // A multipart body beyond the previous 10 MiB truncation, or the user's full local PDF.
  const boundary = "adapterflow-smoke-" + randomBytes(12).toString("hex");
  const expected = createHash("sha256"); let bytes = 0;
  async function* multipart() {
    const prefix = Buffer.from(`--${boundary}\r\nContent-Disposition: form-data; name="file"; filename="catalog.pdf"\r\nContent-Type: application/pdf\r\n\r\n`);
    expected.update(prefix); bytes += prefix.length; yield prefix;
    const data = process.env.PDF_SMOKE_FILE ? createReadStream(process.env.PDF_SMOKE_FILE) : Readable.from((function* () { for (let i = 0; i < 24; i++) yield Buffer.alloc(1024 * 1024, i); })());
    for await (const chunk of data) { expected.update(chunk); bytes += chunk.length; yield chunk; }
    const suffix = Buffer.from(`\r\n--${boundary}--\r\n`); expected.update(suffix); bytes += suffix.length; yield suffix;
  }
  const upload = await fetch(origin + "/api/v1/imports/upload", { method: "POST", headers: { authorization, origin, "content-type": `multipart/form-data; boundary=${boundary}` }, body: Readable.from(multipart()), duplex: "half", signal: AbortSignal.timeout(120000) });
  assert.equal(upload.status, 200);
  assert.deepEqual(await upload.json(), { bytes, sha256: expected.digest("hex") });
  assert.ok(!logs.includes("Request body exceeded"));
  console.log(`Proxy verified: OAuth state/cookie/auth forwarded; ${bytes} upload bytes preserved (SHA-256).`);
} finally {
  child.kill(); api.closeAllConnections(); await new Promise(resolve => api.close(resolve));
}
