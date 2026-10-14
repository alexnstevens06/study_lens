import type { Tool } from './types.js';

export type PointerKind = 'mouse' | 'pen' | 'touch';

export type PointerAction =
  | { type: 'draw'; tool: Tool; stick: boolean }
  | { type: 'ignore' };

const ERASER_BUTTON = 32;
const SECONDARY_BUTTON = 2;
const AUXILIARY_BUTTON = 4;

export const MIN_VIEW_ZOOM = 0.3;
export const MAX_VIEW_ZOOM = 6;

export function pointerKind(pointerType: string): PointerKind {
  if (pointerType === 'pen') return 'pen';
  if (pointerType === 'touch') return 'touch';
  return 'mouse';
}

/**
 * Stylus eraser end selects the eraser and the pen tip selects the pencil.
 * The barrel / right button selects the lasso. Mouse primary uses the active tool.
 */
export function resolvePointerAction(input: {
  kind: PointerKind;
  button: number;
  buttons: number;
  activeTool: Tool;
  penEnabled: boolean;
}): PointerAction {
  if (!input.penEnabled) return { type: 'ignore' };
  if (input.kind === 'touch') return { type: 'ignore' };
  const eraser = input.button === 5 || (input.buttons & ERASER_BUTTON) !== 0;
  const secondary = input.button === 2 || (input.buttons & SECONDARY_BUTTON) !== 0;
  if (input.kind === 'pen') {
    if (eraser) return { type: 'draw', tool: 'eraser', stick: true };
    if (secondary) return { type: 'draw', tool: 'lasso', stick: true };
    return { type: 'draw', tool: 'pencil', stick: true };
  }
  if (input.button === 1 || (input.buttons & AUXILIARY_BUTTON) !== 0) return { type: 'ignore' };
  if (secondary) return { type: 'draw', tool: 'lasso', stick: false };
  if (input.button === 0) return { type: 'draw', tool: input.activeTool, stick: false };
  return { type: 'ignore' };
}

/** Finger moving left asks for the next page. A slow drag is a pan, not a swipe. */
export function classifySwipe(
  dx: number,
  dy: number,
  elapsedMs: number,
): 'next' | 'previous' | null {
  if (elapsedMs > 500) return null;
  if (Math.abs(dx) < 56) return null;
  if (Math.abs(dx) < Math.abs(dy) * 1.25) return null;
  return dx < 0 ? 'next' : 'previous';
}

export function nextViewZoom(current: number, factor: number): number {
  if (!Number.isFinite(factor) || factor <= 0) return current;
  return Math.min(MAX_VIEW_ZOOM, Math.max(MIN_VIEW_ZOOM, current * factor));
}

/** 1-based page field. Returns null when the text is not a number. */
export function parsePageNumber(text: string): number | null {
  const value = Number(text.trim());
  if (!Number.isFinite(value)) return null;
  return Math.round(value);
}
