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

  it('reloads saved ink so the eraser can remove it and the next save keeps that edit', async () => {
    const session = new StudySession();
    await session.newNote();
    draw(session, [[10, 10], [80, 10]]);
    const saved = await session.buildSavedPdf();
    session.commitSave(saved.bytes, saved.name);

    const reopened = new StudySession();
    await reopened.openPdf(saved.name, saved.bytes);
    expect(reopened.getView()).toMatchObject({ strokeCount: 1, historyCurrent: 0, historyTotal: 0 });
    expect(await listInkAnnotations(reopened.documentBytes ?? new Uint8Array())).toHaveLength(0);
    const loaded = reopened.page.getRenderState().strokes[0]?.stroke;
    expect(loaded?.saved).toBe(false);
    expect(loaded?.points[0]).toMatchObject({ x: 10, y: 10 });
    expect(loaded?.points[1]).toMatchObject({ x: 80, y: 10 });

    reopened.pointerDown('eraser', 40, 10, 1);
    reopened.pointerUp(40, 10, 1);
    expect(reopened.getView().strokeCount).toBe(0);
    const erased = await reopened.buildSavedPdf();
    expect(await listInkAnnotations(erased.bytes)).toHaveLength(0);

    reopened.undo();
    expect(reopened.getView().strokeCount).toBe(1);
    const restored = await reopened.buildSavedPdf();
    expect(await listInkAnnotations(restored.bytes)).toHaveLength(1);
  });

  it('moves reloaded ink with the lasso and saves the new position once', async () => {
    const session = new StudySession();
    await session.newNote();
    draw(session, [[10, 10], [80, 10]]);
    const saved = await session.buildSavedPdf();

    const reopened = new StudySession();
    await reopened.openPdf(saved.name, saved.bytes);
    reopened.pointerDown('lasso', -20, -20, 1);
    reopened.pointerMove(120, -20, 1);
    reopened.pointerMove(120, 40, 1);
    reopened.pointerMove(-20, 40, 1);
    reopened.pointerUp(-20, -20, 1);
    expect(reopened.page.getRenderState().selectionRect).not.toBeNull();

    reopened.pointerDown('pencil', 20, 10, 1);
    reopened.pointerMove(20, 40, 1);
    reopened.pointerUp(20, 40, 1);
    const moved = reopened.page.getRenderState().strokes[0]?.stroke.points[0];
    expect(moved).toMatchObject({ x: 10, y: 40 });
    expect(reopened.getView().strokeCount).toBe(1);

    const rewritten = await reopened.buildSavedPdf();
    const ink = await listInkAnnotations(rewritten.bytes);
    expect(ink).toHaveLength(1);
    const trace = ink[0]?.traces[0] ?? [];
    expect(trace[0]).toBeCloseTo(5, 2);
    expect(trace[1]).toBeCloseTo(822, 2);
    expect(trace[2]).toBeCloseTo(40, 2);
    expect(trace[3]).toBeCloseTo(822, 2);

    draw(reopened, [[12, 200], [40, 220]]);
    const beside = await reopened.buildSavedPdf();
    expect(await listInkAnnotations(beside.bytes)).toHaveLength(2);
  });

  it('reloads ink on each saved page and keeps pages the eraser did not touch', async () => {
    const session = new StudySession();
    await session.newNote();
    draw(session, [[10, 12], [30, 12]]);
    await session.changePage(1);
    draw(session, [[14, 18], [40, 18]]);
    const saved = await session.buildSavedPdf();

    const reopened = new StudySession();
    await reopened.openPdf('notes.pdf', saved.bytes);
    expect(reopened.getView()).toMatchObject({ pageIndex: 0, strokeCount: 1, pageCount: 2 });
    await reopened.goTo(1);
    expect(reopened.getView().strokeCount).toBe(1);
    reopened.pointerDown('eraser', 20, 18, 1);
    reopened.pointerUp(20, 18, 1);
    expect(reopened.getView().strokeCount).toBe(0);
    const rewritten = await reopened.buildSavedPdf();
    expect((await listInkAnnotations(rewritten.bytes)).map((item) => item.pageIndex)).toEqual([0]);
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
