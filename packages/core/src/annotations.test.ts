import { describe, expect, it } from 'vitest';
import { bakeAnnotations, countPageImages, listInkAnnotations } from './annotations.js';
import { createBlankPdf } from './pdf-document.js';
import { RENDER_SCALE, type PageSnapshot, type PlacedImage, type Stroke } from './types.js';

const TINY_PNG = Uint8Array.from(
  Buffer.from(
    'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==',
    'base64',
  ),
);

function stroke(): Stroke {
  return {
    id: 'ink-1',
    width: 4,
    saved: false,
    color: { r: 255, g: 0, b: 0, a: 128 },
    points: [
      { x: 20, y: 10, pressure: 1 },
      { x: 60, y: 30, pressure: 0.5 },
    ],
  };
}

describe('annotation save round-trip', () => {
  it('writes ink with zoom-scaled width and does not write it twice', async () => {
    const bytes = await createBlankPdf(200, 100);
    const pages = new Map<number, PageSnapshot>([[0, { strokes: [stroke()], images: [] }]]);
    const first = await bakeAnnotations(bytes, pages, RENDER_SCALE);
    const written = await listInkAnnotations(first.bytes);
    expect(written).toHaveLength(1);
    const ink = written[0];
    expect(ink?.width).toBeCloseTo(2, 4);
    expect(ink?.opacity).toBeCloseTo(128 / 255, 4);
    expect(ink?.color[0]).toBeCloseTo(1, 4);
    expect(ink?.color[1]).toBeCloseTo(0, 4);
    expect(ink?.color[2]).toBeCloseTo(0, 4);
    const trace = ink?.traces[0] ?? [];
    expect(trace[0]).toBeCloseTo(10, 3);
    expect(trace[1]).toBeCloseTo(95, 3);
    expect(trace[2]).toBeCloseTo(30, 3);
    expect(trace[3]).toBeCloseTo(85, 3);
    expect(first.pages.get(0)?.strokes[0]?.saved).toBe(true);

    const second = await bakeAnnotations(first.bytes, first.pages, RENDER_SCALE);
    expect(await listInkAnnotations(second.bytes)).toHaveLength(1);

    const duplicated = await bakeAnnotations(first.bytes, pages, RENDER_SCALE);
    expect(await listInkAnnotations(duplicated.bytes)).toHaveLength(2);
  });

  it('embeds an image once', async () => {
    const bytes = await createBlankPdf(200, 100);
    const image: PlacedImage = {
      id: 'paste-1',
      bytes: TINY_PNG,
      mime: 'image/png',
      x: 10,
      y: 20,
      width: 2,
      height: 2,
      saved: false,
    };
    const pages = new Map<number, PageSnapshot>([[0, { strokes: [], images: [image] }]]);
    const first = await bakeAnnotations(bytes, pages, RENDER_SCALE);
    expect(await countPageImages(first.bytes, 0)).toBe(1);
    expect(first.pages.get(0)?.images[0]?.saved).toBe(true);
    const second = await bakeAnnotations(first.bytes, first.pages, RENDER_SCALE);
    expect(await countPageImages(second.bytes, 0)).toBe(1);
  });

  it('saves a one-point tap as a dot and does not write an empty stroke', async () => {
    const bytes = await createBlankPdf(200, 100);
    const dot: Stroke = {
      id: 'dot',
      width: 4,
      saved: false,
      color: { r: 0, g: 0, b: 0, a: 255 },
      points: [{ x: 20, y: 10, pressure: 1 }],
    };
    const empty: Stroke = { ...dot, id: 'empty', points: [] };
    const pages = new Map<number, PageSnapshot>([[0, { strokes: [dot, empty], images: [] }]]);
    const saved = await bakeAnnotations(bytes, pages, RENDER_SCALE);
    const written = await listInkAnnotations(saved.bytes);
    expect(written).toHaveLength(1);
    expect(written[0]?.width).toBeCloseTo(2, 4);
    expect(written[0]?.traces[0]).toHaveLength(4);
    expect(saved.pages.get(0)?.strokes[0]?.saved).toBe(true);
    expect(saved.pages.get(0)?.strokes[1]?.saved).toBe(false);
  });
});
