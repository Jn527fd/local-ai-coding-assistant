const relativeTimeFormatter = new Intl.RelativeTimeFormat(undefined, {
  numeric: "auto",
})

export function formatConversationTime(isoTimestamp: string): string {
  const timestamp = Date.parse(isoTimestamp)
  if (!Number.isFinite(timestamp)) return "Unknown"

  const differenceInSeconds = Math.round((timestamp - Date.now()) / 1_000)
  const absoluteSeconds = Math.abs(differenceInSeconds)

  if (absoluteSeconds < 60) return "Now"
  if (absoluteSeconds < 3_600) {
    return relativeTimeFormatter.format(
      Math.round(differenceInSeconds / 60),
      "minute",
    )
  }
  if (absoluteSeconds < 86_400) {
    return relativeTimeFormatter.format(
      Math.round(differenceInSeconds / 3_600),
      "hour",
    )
  }
  if (absoluteSeconds < 604_800) {
    return relativeTimeFormatter.format(
      Math.round(differenceInSeconds / 86_400),
      "day",
    )
  }

  return new Intl.DateTimeFormat(undefined, {
    month: "short",
    day: "numeric",
  }).format(timestamp)
}
