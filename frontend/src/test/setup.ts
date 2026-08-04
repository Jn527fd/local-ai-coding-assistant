import "@testing-library/jest-dom/vitest"
import { afterEach } from "vitest"
import { cleanup } from "@testing-library/react"

afterEach(() => cleanup())

Object.defineProperty(window, "requestAnimationFrame", {
  configurable: true,
  writable: true,
  value: (callback: FrameRequestCallback) => window.setTimeout(callback, 0),
})
Object.defineProperty(window, "cancelAnimationFrame", {
  configurable: true,
  writable: true,
  value: (handle: number) => window.clearTimeout(handle),
})
Object.defineProperty(window, "scrollTo", {
  configurable: true,
  writable: true,
  value: () => undefined,
})
