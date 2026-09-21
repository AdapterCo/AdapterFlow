import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { runInNewContext } from "node:vm";
import ts from "typescript";
const source = await readFile(new URL("../middleware.ts", import.meta.url), "utf8");
const compiled = ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 } }).outputText;
class Adapter extends Response {
  static next() { return new Adapter(null, {status: 200}); }
  static json(body, options) { return new Adapter(JSON.stringify(body), options); }
  static redirect(url) { const r = new Adapter(null, {status: 307, headers: {location: String(url)}}); r.cookies = {delete() {}}; return r; }
}
let failure = false;
let received;
const exports = {};
runInNewContext(compiled, {
 exports, Headers, URL, AbortSignal, process: {env: {INTERNAL_BACKEND_URL: "http://synthetic.invalid"}},
 fetch: async (_, options) => {
   received = options.headers;
   if (failure) throw new Error("offline");
   return new Response(null, {status: received.get("authorization") === "Basic valid-test" || received.get("cookie") === "adapterflow_session=verified-test" ? 200 : 401});
 },
 require: () => ({NextResponse: Adapter}),
});
async function check(path, status, headers={}, method="GET") {
 const url = new URL(path, "https://example.invalid");
 const response = await exports.middleware({method, url: url.href, nextUrl: url, headers: new Headers(headers)});
 assert.equal(response.status, status, path);
 return response;
}
await check("/api/v1/suppliers", 401);
await check("/", 307);
await check("/login", 200);
await check("/api/v1/suppliers", 401, {cookie:"adapterflow_session=forged-long-token"});
await check("/api/v1/suppliers", 401, {authorization:"Basic wrong"});
await check("/api/v1/suppliers", 200, {authorization:"Basic valid-test"});
assert.equal(received.get("authorization"), "Basic valid-test");
await check("/api/v1/suppliers", 200, {cookie:"adapterflow_session=verified-test"});
assert.equal(received.get("authorization"), null);
await check("/api/v1/suppliers", 403, {origin:"https://evil.invalid"}, "POST");
await check("/api/v1/marketplaces/mercadolivre/notifications", 200, {}, "POST");
await check("/api/v1/marketplaces/mercadolivre/notifications", 401);
failure=true;
await check("/api/v1/suppliers", 503, {authorization:"Basic valid-test"});
console.log("Middleware: forged credentials, caller forwarding, origin, webhook and unavailable backend verified.");
