export const spacingScale = Object.freeze([4, 8, 12, 16, 20, 24, 32, 40]);
export const rowScale = Object.freeze([44, 48, 52]);
export const radiusScale = Object.freeze([8, 10, 12, 14]);

export const statusTone = Object.freeze({
  waiting: "slate",
  ready: "blue",
  running: "cyan",
  attention: "amber",
  complete: "green",
  failed: "red",
  unknown: "neutral"
} as const);
