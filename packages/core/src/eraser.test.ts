import { describe, expect, it } from 'vitest';
import { UndoManager } from './commands.js';
import { strokeHitsEraser } from './geometry.js';
import { PageModel } from './page-model.js';
import { DEFAULT_PEN, type Stroke } from './types.js';

function stroke(width: number, points: Array<[number, number]>): Stroke {
  return {
    id: 'stroke',
    width,
    saved: false,
    color: { r: 0, g: 0, b: 0, a: 255 },
    points: points.map(([x, y]) => ({ x, y, pressure: 1 })),
  };
}

function drawLine(page: PageModel, y: number, width = 4): void {
  page.pointerDown('pencil', 0, y, 1, { ...DEFAULT_PEN, width });
  page.pointerMove(100, y, 1);
  page.pointerUp(100, y, 1);
}

describe('eraser hit testing', () => {
  it('hits a stroke inside the pen radius and misses outside it', () => {
    const thin = stroke(4, [[0, 0], [100, 0]]);
    expect(strokeHitsEraser(thin, 50, 0)).toBe(true);
    expect(strokeHitsEraser(thin, 50, 30)).toBe(false);

    const thick = stroke(40, [[0, 0], [100, 0]]);
    expect(strokeHitsEraser(thick, 50, 15)).toBe(true);
    expect(strokeHitsEraser(thick, 50, 30)).toBe(false);
  });

  it('removes each touched stroke and fades it out', () => {
    const page = new PageModel();
    const history = new UndoManager();
    drawLine(page, 0);
    drawLine(page, 1);
    page.pointerDown('eraser', 40, 0, 1, DEFAULT_PEN);
    page.pointerMove(40, 1, 1);
    const commands = page.pointerUp(40, 1, 1);
    for (const command of commands) history.push(command);

    expect(page.strokeCount).toBe(0);
    expect(page.hasFade()).toBe(true);
    expect(commands).toHaveLength(2);
    for (let step = 0; step < 10; step += 1) page.stepFade(0.1);
    expect(page.hasFade()).toBe(false);
    history.undo(page, 2);
    expect(page.strokeCount).toBe(2);
  });

  it('deselects a selected stroke instead of deleting it', () => {
    const page = new PageModel();
    drawLine(page, 0);
    page.pointerDown('lasso', -20, -20, 1, DEFAULT_PEN);
    page.pointerMove(120, -20, 1);
    page.pointerMove(120, 20, 1);
    page.pointerMove(-20, 20, 1);
    page.pointerUp(-20, -20, 1);
    expect(page.getRenderState().selectionRect).not.toBeNull();

    page.pointerDown('eraser', 50, 0, 1, DEFAULT_PEN);
    page.pointerUp(50, 0, 1);
    expect(page.strokeCount).toBe(1);
    expect(page.getRenderState().selectionRect).toBeNull();

    page.pointerDown('eraser', 50, 0, 1, DEFAULT_PEN);
    page.pointerUp(50, 0, 1);
    expect(page.strokeCount).toBe(0);
  });
});
