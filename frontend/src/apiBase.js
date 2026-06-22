const DEFAULT_BACKEND_PORT = "8000";
const LOOPBACK_HOSTS = new Set(["localhost", "127.0.0.1", "::1"]);

function trimTrailingSlash(value) {
  return value.replace(/\/+$/, "");
}

function isLoopbackHost(hostname) {
  return LOOPBACK_HOSTS.has(hostname);
}

function browserLocation(locationLike) {
  if (!locationLike || !locationLike.hostname || !locationLike.protocol) {
    return null;
  }

  return locationLike;
}

function sameHostBackendUrl(locationLike, port = DEFAULT_BACKEND_PORT) {
  const location = browserLocation(locationLike);
  if (!location) {
    return `http://localhost:${port}`;
  }

  return `${location.protocol}//${location.hostname}:${port}`;
}

export function resolveApiBaseUrl(configuredValue = "", locationLike) {
  const configured = String(configuredValue || "").trim();
  const location = browserLocation(locationLike);

  if (!configured || configured === "auto") {
    return sameHostBackendUrl(location, DEFAULT_BACKEND_PORT);
  }

  let configuredUrl;
  try {
    configuredUrl = new URL(configured);
  } catch {
    return trimTrailingSlash(configured);
  }

  if (
    location &&
    isLoopbackHost(configuredUrl.hostname) &&
    !isLoopbackHost(location.hostname)
  ) {
    configuredUrl.hostname = location.hostname;
  }

  return trimTrailingSlash(configuredUrl.toString());
}
