// Calls to the local server (127.0.0.1 only). The per-launch token comes from the URL hash.

const hashToken = new URLSearchParams(location.hash.slice(1)).get("token");
if (hashToken) {
  try { sessionStorage.setItem("bn-token", hashToken); } catch { /* storage may be unavailable */ }
  history.replaceState(null, "", location.pathname);
}
let TOKEN = hashToken;
try { TOKEN = TOKEN || sessionStorage.getItem("bn-token"); } catch { /* ignore */ }

export class ApiError extends Error {
  constructor(message, status) { super(message); this.status = status; }
}

async function request(method, path, body, { raw = false, headers = {} } = {}) {
  const opts = { method, headers: { "X-App-Token": TOKEN || "", ...headers } };
  if (body instanceof ArrayBuffer || body instanceof Blob) {
    opts.body = body;
  } else if (body !== undefined) {
    opts.headers["Content-Type"] = "application/json";
    opts.body = JSON.stringify(body);
  }
  let res;
  try {
    res = await fetch(path, opts);
  } catch (e) {
    throw new ApiError("The app's local engine isn't responding. Try restarting Bible Narrator.", 0);
  }
  if (!res.ok) {
    let msg = `${res.status} ${res.statusText}`;
    try { const j = await res.json(); msg = j.detail || msg; } catch { /* not json */ }
    if (res.status === 401) msg = "This window lost its connection to the app. Please restart Bible Narrator.";
    throw new ApiError(msg, res.status);
  }
  return raw ? res : res.json();
}

export const api = {
  get: (p) => request("GET", p),
  post: (p, b) => request("POST", p, b ?? {}),
  put: (p, b) => request("PUT", p, b),
  patch: (p, b) => request("PATCH", p, b),
  del: (p) => request("DELETE", p),
  raw: (method, p, body, headers) => request(method, p, body, { raw: true, headers }),
  qs: (o) => new URLSearchParams(Object.entries(o).filter(([, v]) => v !== undefined && v !== null && v !== "")).toString(),
};

// Native file picker when running inside the desktop window (pywebview), else null.
export async function nativePick(kind) {
  if (window.pywebview && window.pywebview.api && window.pywebview.api.choose_file) {
    try { return await window.pywebview.api.choose_file(kind); } catch { return null; }
  }
  return undefined; // not available: caller shows a path field instead
}
