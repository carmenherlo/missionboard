// The only module that talks to the backend.

import { t } from "./texts.js";

// Parent code typed in this session; sent with every request while set.
export const session = { parentCode: null };

export class ApiError extends Error {
  constructor(status, detail) {
    super(detail || `HTTP ${status}`);
    this.status = status;
  }
}

async function request(method, path, { json, body, contentType } = {}) {
  const headers = {};
  if (session.parentCode) headers["X-Parent-Code"] = session.parentCode;
  if (json !== undefined) {
    headers["Content-Type"] = "application/json";
    body = JSON.stringify(json);
  } else if (contentType) {
    headers["Content-Type"] = contentType;
  }
  const res = await fetch(path, { method, headers, body });
  if (!res.ok) {
    const payload = await res.json().catch(() => ({}));
    throw new ApiError(res.status, typeof payload.detail === "string" ? payload.detail : null);
  }
  return res;
}

export async function api(method, path, options) {
  const res = await request(method, path, options);
  return res.status === 204 ? null : res.json();
}

// A file to download, with the name the server gives it. Fetched here (not
// with a plain link) so the parent code goes along.
export async function apiFile(path) {
  const res = await request("GET", path);
  const filename = res.headers.get("Content-Disposition")?.match(/filename="([^"]+)"/)?.[1];
  return { blob: await res.blob(), filename };
}

export function errorMessage(err) {
  if (!(err instanceof ApiError)) return t.errors.offline;
  if (err.status === 401) return t.errors.badParentCode;
  if (err.status === 409) return t.errors.presetTaken;
  if (err.status === 413) return t.errors.photoTooLarge;
  if (err.status === 415 || err.status === 422) return t.errors.invalidData;
  return t.errors.generic;
}
