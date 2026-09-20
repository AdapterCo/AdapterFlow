try {
  const authorization = "Basic " + Buffer.from(`${process.env.ADMIN_USERNAME}:${process.env.ADMIN_PASSWORD}`).toString("base64");
  // Exercise the same middleware and compiled rewrite used by the browser.
  const response = await fetch(`http://127.0.0.1:${process.env.PORT || "3099"}/api/v1/ready`, {
    headers: { authorization }, signal: AbortSignal.timeout(5000),
  });
  if (!response.ok || (await response.json()).status !== "ready") process.exit(1);
} catch { process.exit(1); }
