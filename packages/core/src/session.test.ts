import { describe, expect, it } from 'vitest';
import { listInkAnnotations } from './annotations.js';
import { StudySession } from './session.js';

function draw(session: StudySession, points: Array<[number, number]>): void {
  const first = points[0];
  if (!first) throw new Error('A stroke needs a point');
  session.pointerDown('pencil', first[0], first[1], 1);
  for (const [x, y] of points.slice(1)) session.pointerMove(x, y, 1);
  const last = points[points.length - 1] ?? first;
  session.pointerUp(last[0], last[1], 1);
}

describe('session save', () => {
  it('keeps a cancelled save from dropping or duplicating ink', async () => {
    const session = new StudySession();
    await session.newNote();
    draw(session, [[10, 10], [40, 30]]);
    const when = new Date(2026, 0, 2, 3, 4, 5);
    const first = await session.buildSavedPdf(when);
    expect(first.name).toBe('2026-01-02_03-04-05.pdf');
    expect(await listInkAnnotations(first.bytes)).toHaveLength(1);
    expect(session.getView().strokeCount).toBe(1);
    expect(session.getView().historyCurrent).toBe(1);

    const second = await session.buildSavedPdf(when);
    expect(await listInkAnnotations(second.bytes)).toHaveLength(1);

    session.commitSave(second.bytes, second.name);
    expect(session.getView()).toMatchObject({
      strokeCount: 0,
      historyCurrent: 0,
      historyTotal: 0,
      isNew: false,
      fileName: second.name,
    });

    const third = await session.buildSavedPdf();
    expect(third.name).toBe(second.name);
    expect(await listInkAnnotations(third.bytes)).toHaveLength(1);

    const reopened = new StudySession();
    await reopened.openPdf(third.name, third.bytes);
    const fourth = await reopened.buildSavedPdf();
    expect(await listInkAnnotations(fourth.bytes)).toHaveLength(1);
  });

  it('writes a tap and the ink on every page that was drawn on', async () => {
    const session = new StudySession();
    await session.newNote();
    session.pointerDown('pencil', 30, 40, 1);
    session.pointerUp(30, 40, 1);
    expect(session.page.getRenderState().strokes[0]?.stroke.points).toHaveLength(1);
    await session.changePage(1);
    expect(session.getView()).toMatchObject({ pageCount: 2, pageIndex: 1, strokeCount: 0, historyTotal: 0 });
    draw(session, [[8, 8], [20, 24]]);
    const saved = await session.buildSavedPdf();
    const ink = await listInkAnnotations(saved.bytes);
    expect(ink.map((item) => item.pageIndex).sort()).toEqual([0, 1]);
  });

  it('finishes an in-progress stroke before saving or leaving the page', async () => {
    const session = new StudySession();
    await session.newNote();
    session.pointerDown('pencil', 6, 6, 1);
    session.pointerMove(16, 20, 1);
    const saved = await session.buildSavedPdf();
    expect(await listInkAnnotations(saved.bytes)).toHaveLength(1);
    expect(session.getView().strokeCount).toBe(1);

    const paging = new StudySession();
    await paging.newNote();
    paging.pointerDown('pencil', 6, 6, 1);
    paging.pointerMove(16, 20, 1);
    await paging.changePage(1);
    await paging.goTo(0);
    expect(paging.getView().strokeCount).toBe(1);
    expect(paging.page.getRenderState().strokes[0]?.stroke.points[0]).toMatchObject({ x: 6, y: 6 });
  });

  it('ignores a page index that is not a finite number', async () => {
    const session = new StudySession();
    await session.newNote();
    draw(session, [[1, 1], [4, 4]]);
    await session.goTo(Number.NaN);
    await session.goTo(Number.POSITIVE_INFINITY);
    expect(session.getView()).toMatchObject({ pageIndex: 0, pageCount: 1, strokeCount: 1 });
  });
});
