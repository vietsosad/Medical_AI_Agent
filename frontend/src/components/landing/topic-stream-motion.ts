export function positiveModulo(value: number, modulus: number): number {
  if (!Number.isFinite(value) || !Number.isFinite(modulus) || modulus <= 0) return 0;
  return ((value % modulus) + modulus) % modulus;
}

export function advanceCircularPhase(
  phase: number,
  elapsedMilliseconds: number,
  speedPixelsPerSecond: number,
  loopLength: number,
): number {
  if (elapsedMilliseconds <= 0 || speedPixelsPerSecond <= 0) {
    return positiveModulo(phase, loopLength);
  }

  return positiveModulo(
    phase + speedPixelsPerSecond * (elapsedMilliseconds / 1_000),
    loopLength,
  );
}

/**
 * Projects one item from a circular track onto the visible horizontal axis.
 * The item wraps only after its trailing edge has left the viewport, avoiding
 * a jump or a duplicated DOM node at the seam.
 */
export function circularItemX(
  itemStart: number,
  itemWidth: number,
  phase: number,
  loopLength: number,
): number {
  return positiveModulo(itemStart - phase + itemWidth, loopLength) - itemWidth;
}
