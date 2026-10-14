// Own the generation from request start through decode; only the latest photo
// may change the canvas/name/status. Always release stale decoded bitmaps.
export function createLatestPhotoLoader({ decode, apply, onError }) {
  let sequence = 0;
  return async (source, name) => {
    const ticket = ++sequence;
    let bitmap;
    try {
      const resolved = await source;
      if (ticket !== sequence) return false;
      bitmap = await decode(resolved);
      if (ticket !== sequence) return false;
      apply(bitmap, name);
      return true;
    } catch (error) {
      if (ticket === sequence) onError(error);
      return false;
    } finally { bitmap?.close(); }
  };
}
