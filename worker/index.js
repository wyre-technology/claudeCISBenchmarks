/**
 * Cloudflare Worker — CIS Benchmarks MCP edge proxy
 *
 * Responsibilities:
 *   1. API key authentication (Bearer token)
 *   2. CORS preflight handling
 *   3. Streaming-safe forwarding to the DO App Platform origin
 *
 * Secrets (set via `wrangler secret put`):
 *   MCP_API_KEY     — Bearer token clients must send
 *
 * Vars (set in wrangler.toml or dashboard):
 *   DO_ORIGIN_URL   — e.g. https://cis-benchmarks-mcp.ondigitalocean.app
 *   ALLOWED_ORIGIN  — CORS allowed origin (default: *)
 */

const CORS_HEADERS = (env) => ({
  "Access-Control-Allow-Origin": env.ALLOWED_ORIGIN ?? "*",
  "Access-Control-Allow-Methods": "GET, POST, DELETE, OPTIONS",
  // mcp-session-id is used by stateful MCP clients
  "Access-Control-Allow-Headers": "Content-Type, Authorization, mcp-session-id",
  "Access-Control-Expose-Headers": "mcp-session-id",
  "Access-Control-Max-Age": "86400",
});

function corsResponse(env, status = 204) {
  return new Response(null, { status, headers: CORS_HEADERS(env) });
}

function errorResponse(env, status, message) {
  return new Response(JSON.stringify({ error: message }), {
    status,
    headers: { "Content-Type": "application/json", ...CORS_HEADERS(env) },
  });
}

export default {
  async fetch(request, env) {
    // ── CORS preflight ─────────────────────────────────────────
    if (request.method === "OPTIONS") {
      return corsResponse(env);
    }

    // ── Authentication ─────────────────────────────────────────
    // Skip auth for the health endpoint so DO health checks pass
    const url = new URL(request.url);
    const isHealth = url.pathname === "/health";

    if (!isHealth && env.MCP_API_KEY) {
      const auth = request.headers.get("Authorization") ?? "";
      if (auth !== `Bearer ${env.MCP_API_KEY}`) {
        return errorResponse(env, 401, "Unauthorized");
      }
    }

    // ── Forward to origin ──────────────────────────────────────
    if (!env.DO_ORIGIN_URL) {
      return errorResponse(env, 500, "DO_ORIGIN_URL not configured");
    }

    const originUrl = `${env.DO_ORIGIN_URL.replace(/\/$/, "")}${url.pathname}${url.search}`;

    // Build forwarded headers — strip Cloudflare-specific headers
    const forwardedHeaders = new Headers();
    for (const [key, value] of request.headers.entries()) {
      if (/^(cf-|x-forwarded-|cdn-loop)/i.test(key)) continue;
      forwardedHeaders.set(key, value);
    }
    // Don't forward the client's auth to the origin
    forwardedHeaders.delete("authorization");

    let originResponse;
    try {
      originResponse = await fetch(originUrl, {
        method: request.method,
        headers: forwardedHeaders,
        body: request.body,
        // Required for streaming MCP responses (SSE / chunked)
        duplex: "half",
      });
    } catch (err) {
      return errorResponse(env, 502, `Origin unreachable: ${err.message}`);
    }

    // Pass the response body through as a stream — don't buffer it.
    // This is essential for MCP's streamable-http transport.
    const responseHeaders = new Headers(originResponse.headers);
    Object.entries(CORS_HEADERS(env)).forEach(([k, v]) => responseHeaders.set(k, v));

    return new Response(originResponse.body, {
      status: originResponse.status,
      headers: responseHeaders,
    });
  },
};
