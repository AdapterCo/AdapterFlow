import { spawn } from "node:child_process";
import { randomBytes } from "node:crypto";
import assert from "node:assert/strict";
import { createServer } from "node:http";
const port = process.env.SMOKE_PORT || "3199";
const origin = `http://127.0.0.1:${port}`;
const password = randomBytes(24).toString("hex");
const authorization = `Basic ${Buffer.from(`smoke-operator:${password}`).toString("base64")}`;
const api = createServer((req, res) => {
  res.writeHead(req.headers.authorization === authorization ? 200 : 401, { "Content-Type": "application/json" }).end("{}");
});
await new Promise(resolve => api.listen(18081, "127.0.0.1", resolve));
const child = spawn(process.execPath, ["node_modules/next/dist/bin/next", "start", "-H", "127.0.0.1", "-p", port], {
  env: { ...process.env, ADMIN_USERNAME: "smoke-operator", ADMIN_PASSWORD: password, APP_ORIGIN: origin, INTERNAL_BACKEND_URL: "http://127.0.0.1:18081" }, stdio: ["ignore", "pipe", "pipe"]
});
let logs = "";
child.stdout.on("data", data => { logs += data; });
child.stderr.on("data", data => { logs += data; });
try {
  let ready = false;
  for (let attempt = 0; attempt < 100; attempt++) {
    if (child.exitCode !== null) throw new Error(`Server exited: ${logs}`);
    try { const response = await fetch(origin + "/api/v1/suppliers"); if (response.status === 401) { ready = true; break; } } catch { /* startup */ }
    await new Promise(resolve => setTimeout(resolve, 200));
  }
  assert.ok(ready, "Unauthenticated request must return 401");
  assert.equal((await fetch(origin + "/api/v1/suppliers", { headers: { authorization: "Basic " + Buffer.from("wrong:wrong").toString("base64") } })).status, 401);
  const allowed = await fetch(origin, { headers: { authorization } });
  assert.equal(allowed.status, 200);
  assert.ok((await allowed.text()).includes("AdapterFlow"));
  const crossOrigin = await fetch(origin + "/api/v1/suppliers", { method: "POST", headers: { authorization, origin: "https://untrusted.invalid" } });
  assert.equal(crossOrigin.status, 403);
  console.log("Authentication smoke: 4 checks passed.");
} finally { child.kill(); api.closeAllConnections(); await new Promise(resolve => api.close(resolve)); }
