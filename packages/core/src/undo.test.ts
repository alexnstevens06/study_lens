import { describe, expect, it } from 'vitest';
import { UndoManager } from './commands.js';
import { PageModel } from './page-model.js';
import { DEFAULT_PEN, type PlacedImage } from './types.js';

function draw(page: PageModel, points: Array<[number, number]>, history?: UndoManager): void {
  const first = points[0];
  if (!first) throw new Error('A stroke needs a point');
  page.pointerDown('pencil', first[0], first[1], 1, DEFAULT_PEN);
  for (const [x, y] of points.slice(1)) page.pointerMove(x, y, 1);
  const last = points[points.length - 1] ?? first;
  const commands = page.pointerUp(last[0], last[1], 1);
  if (history) {
    for (const command of commands) history.push(command);
  }
}

function eraseThrough(page: PageModel, points: Array<[number, number]>, history?: UndoManager): void {
  const first = points[0];
  if (!first) throw new Error('An erase needs a point');
  page.pointerDown('eraser', first[0], first[1], 1, DEFAULT_PEN);
  for (const [x, y] of points.slice(1)) page.pointerMove(x, y, 1);
  const last = points[points.length - 1] ?? first;
  const commands = page.pointerUp(last[0], last[1], 1);
  if (history) {
    for (const command of commands) history.push(command);
  }
}

describe('undo and redo', () => {
  it('adds, undoes, and redoes a stroke', () => {
    const page = new PageModel();
    const history = new UndoManager();
    draw(page, [[10, 10], [20, 20]], history);
    expect(page.strokeCount).toBe(1);
    expect(history.position()).toEqual({ current: 1, total: 1 });

    history.undo(page);
    expect(page.strokeCount).toBe(0);
    expect(history.position()).toEqual({ current: 0, total: 1 });

    history.redo(page);
    expect(page.strokeCount).toBe(1);
    expect(history.position()).toEqual({ current: 1, total: 1 });
  });

  it('undoes and redoes several steps', () => {
    const page = new PageModel();
    const history = new UndoManager();
    for (let index = 0; index < 3; index += 1) {
      draw(page, [[10, index], [20, index + 5]], history);
    }
    history.undo(page, 2);
    expect(page.strokeCount).toBe(1);
    expect(history.position()).toEqual({ current: 1, total: 3 });
    history.redo(page, 2);
    expect(page.strokeCount).toBe(3);
    expect(history.position()).toEqual({ current: 3, total: 3 });
  });

  it('reports history to listeners and drops redo after a new stroke', () => {
    const page = new PageModel();
    const history = new UndoManager();
    const seen: Array<[number, number]> = [];
    history.subscribe((current, total) => {
      seen.push([current, total]);
    });
    draw(page, [[0, 0], [4, 4]], history);
    history.undo(page);
    history.redo(page);
    history.undo(page);
    draw(page, [[8, 8], [12, 12]], history);
    expect(seen).toEqual([
      [1, 1],
      [0, 1],
      [1, 1],
      [0, 1],
      [1, 1],
    ]);
    expect(page.strokeCount).toBe(1);
  });

  it('restores an erased stroke and then undoes the original add', () => {
    const page = new PageModel();
    const history = new UndoManager();
    draw(page, [[0, 0], [30, 0]], history);
    eraseThrough(page, [[15, 0]], history);
    expect(page.strokeCount).toBe(0);

    history.undo(page);
    expect(page.strokeCount).toBe(1);
    history.undo(page);
    expect(page.strokeCount).toBe(0);
    history.redo(page, 2);
    expect(page.strokeCount).toBe(0);
  });

  it('undoes and redoes an added image', () => {
    const page = new PageModel();
    const history = new UndoManager();
    const image: PlacedImage = {
      id: 'image-1',
      bytes: new Uint8Array([1, 2, 3, 4]),
      mime: 'image/png',
      x: 10,
      y: 12,
      width: 8,
      height: 6,
      saved: false,
    };
    history.push(page.addImage(image));
    expect(page.imageCount).toBe(1);
    history.undo(page);
    expect(page.imageCount).toBe(0);
    history.redo(page);
    expect(page.imageCount).toBe(1);
    expect(page.getRenderState().images[0]?.image.x).toBe(10);
  });
});
