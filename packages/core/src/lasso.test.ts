import { describe, expect, it } from 'vitest';
import { UndoManager } from './commands.js';
import { PageModel } from './page-model.js';
import { DEFAULT_PEN, newId, type PlacedImage } from './types.js';

function draw(page: PageModel, points: Array<[number, number]>): void {
  const first = points[0];
  if (!first) return;
  page.pointerDown('pencil', first[0], first[1], 0.8, DEFAULT_PEN);
  for (const [x, y] of points.slice(1)) page.pointerMove(x, y, 0.4);
  const last = points[points.length - 1] ?? first;
  page.pointerUp(last[0], last[1], 0.4);
}

describe('lasso select and move', () => {
  it('moves the enclosed strokes and images together, then undoes the bake', () => {
    const page = new PageModel();
    const history = new UndoManager();
    draw(page, [[0, 0], [80, 0]]);
    draw(page, [[0, 300], [80, 300]]);
    const image: PlacedImage = {
      id: newId(),
      bytes: new Uint8Array([9]),
      mime: 'image/png',
      x: 10,
      y: 40,
      width: 30,
      height: 20,
      saved: false,
    };
    history.push(page.addImage(image));

    page.pointerDown('lasso', -10, -10, 1, DEFAULT_PEN);
    page.pointerMove(120, -10, 1);
    page.pointerMove(120, 80, 1);
    page.pointerMove(-10, 80, 1);
    page.pointerUp(-10, -10, 1);

    page.pointerDown('pencil', 20, 0, 1, DEFAULT_PEN);
    page.pointerMove(25, 6, 1);
    const [move] = page.pointerUp(25, 6, 1);
    if (move) history.push(move);

    const state = page.getRenderState();
    const movedStroke = state.strokes.find((item) => item.stroke.points[0]?.y !== 300);
    const stillStroke = state.strokes.find((item) => Math.round(item.stroke.points[0]?.y ?? 0) === 300);
    expect(movedStroke?.stroke.points[0]).toMatchObject({ x: 5, y: 6 });
    expect(movedStroke?.stroke.points[1]).toMatchObject({ x: 85, y: 6 });
    expect(stillStroke?.stroke.points[0]).toMatchObject({ x: 0, y: 300 });
    expect(state.images[0]?.image).toMatchObject({ x: 15, y: 46 });

    history.undo(page);
    const restored = page.getRenderState();
    const back = restored.strokes.find((item) => item.stroke.points[0]?.y === 0);
    expect(back?.stroke.points[0]).toMatchObject({ x: 0, y: 0 });
    expect(back?.stroke.points[1]).toMatchObject({ x: 80, y: 0 });
    expect(restored.images[0]?.image).toMatchObject({ x: 10, y: 40 });
    expect(restored.selectionRect).toBeNull();
  });
});
