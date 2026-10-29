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

/** Moves the phase by a signed velocity: a fling to the right runs the stream backwards. */
export function advancePhase(
  phase: number,
  velocityPixelsPerSecond: number,
  elapsedMilliseconds: number,
  loopLength: number,
): number {
  if (elapsedMilliseconds <= 0) return positiveModulo(phase, loopLength);
  return positiveModulo(phase + velocityPixelsPerSecond * (elapsedMilliseconds / 1_000), loopLength);
}

/**
 * Frame-rate independent exponential approach of a velocity toward its target.
 * After `settleSeconds` it has covered about 63% of the gap, after three times
 * that about 95% -- the stream eases to rest under a pointer instead of braking.
 */
export function approachVelocity(
  current: number,
  target: number,
  elapsedMilliseconds: number,
  settleSeconds: number,
): number {
  if (elapsedMilliseconds <= 0) return current;
  if (settleSeconds <= 0) return target;
  const blend = 1 - Math.exp(-elapsedMilliseconds / 1_000 / settleSeconds);
  return current + (target - current) * blend;
}

/**
 * Launch velocity, on top of the cruising speed, whose exponential decay
 * travels exactly `distance` pixels: the integral of v0·e^(-t/τ) is v0·τ.
 */
export function impulseForDistance(distance: number, settleSeconds: number): number {
  return settleSeconds > 0 ? distance / settleSeconds : 0;
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
