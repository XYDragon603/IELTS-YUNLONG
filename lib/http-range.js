// A single byte range is enough for browser media seeking. Unsupported syntax
// is ignored (full response); valid but unsatisfiable ranges receive 416.
export function byteRange(header, size) {
  const match = /^bytes=(\d*)-(\d*)$/.exec(header || '');
  if (!match || (!match[1] && !match[2])) return null;
  let start, end;
  if (!match[1]) {
    const suffix = Number(match[2]);
    start = Math.max(0, size - suffix); end = size - 1;
    if (!suffix) return false;
  } else {
    start = Number(match[1]); end = match[2] ? Number(match[2]) : size - 1;
  }
  if (!Number.isSafeInteger(start) || !Number.isSafeInteger(end) || start >= size || end < start || !size) return false;
  return { start, end: Math.min(end, size - 1) };
}
