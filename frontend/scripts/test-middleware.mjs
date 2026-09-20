import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { runInNewContext } from "node:vm";
import ts from "typescript";

// Execute the actual middleware with a minimal NextResponse adapter.
const source = await readFile(new URL("../middleware.ts", import.meta.url), "utf8");
const compiled = ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 } }).outputText;
class ResponseAdapter extends Response {
  static next() { return new Response(null, { status: 200, headers: { "x-middleware-next": "1" } }); }
}
const exports = {};
runInNewContext(compiled, {
  exports, process: { env: { ADMIN_USERNAME: "synthetic-user", ADMIN_PASSWORD: "synthetic-password" } },
  crypto: globalThis.crypto, TextEncoder, Uint8Array, atob,
  require: (name) => { assert.equal(name, "next/server"); return { NextResponse: ResponseAdapter }; },
});
const path = "/api/v1/marketplaces/mercadolivre/notifications";
async function check(method, pathname, expected) {
  const response = await exports.middleware({ method, nextUrl: new URL(pathname, "https://example.invalid"), headers: new Headers() });
  assert.equal(response.status, expected, `${method} ${pathname}`);
  if (expected === 200) assert.equal(response.headers.get("x-middleware-next"), "1");
}
await check("POST", path, 200);
await check("POST", path + "?delivery=1", 200);
for (const method of ["GET", "PUT", "DELETE", "PATCH", "OPTIONS", "HEAD"]) await check(method, path, 401);
for (const other of [path + "/", path + "/other", "/api/v1/marketplaces/accounts", "/api/v1/marketplaces/mercadolivre/publish", "/api/v1/suppliers"]) await check("POST", other, 401);
console.log("Middleware: public webhook POST and protected routes verified.");
