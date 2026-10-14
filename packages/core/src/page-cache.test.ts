import { describe, expect, it } from 'vitest';
import { appendMatchingPage, createBlankPdf } from './pdf-document.js';
import { PageCache } from './page-cache.js';
import { PageModel } from './page-model.js';
import { UndoManager } from './commands.js';
import { parsePageNumber } from './pointer.js';
import { StudySession } from './session.js';
import { A4_HEIGHT, A4_WIDTH } from './pdf-document.js';
import { DEFAULT_PEN } from './types.js';

describe('page cache', () => {
  it('restores strokes per page and clears history on a page change', async () => {
    const first = await createBlankPdf(320, 240);
    const document = await appendMatchingPage(first);
    const session = new StudySession();
    await session.openPdf('pages.pdf', document.bytes);

    session.pointerDown('pencil', 12, 18, 1);
    session.pointerMove(40, 30, 1);
    session.pointerUp(40, 30, 1);
    expect(session.getView().historyCurrent).toBe(1);
    expect(session.getView().pageWidth).toBe(320);
    expect(session.getView().pageHeight).toBe(240);

    await session.goTo(1);
    expect(session.getView().pageIndex).toBe(1);
    expect(session.getView().strokeCount).toBe(0);
    expect(session.getView().historyCurrent).toBe(0);
    expect(session.getView().historyTotal).toBe(0);

    await session.goTo(0);
    expect(session.getView().strokeCount).toBe(1);
    expect(session.getView().historyTotal).toBe(0);
    expect(session.page.getRenderState().strokes[0]?.stroke.points[0]).toMatchObject({ x: 12, y: 18 });
  });

  it('adds one page the size of the last page when navigation passes the end', async () => {
    const session = new StudySession();
    await session.newNote();
    expect(session.getView().pageWidth).toBe(A4_WIDTH);
    expect(session.getView().pageHeight).toBe(A4_HEIGHT);

    const custom = await createBlankPdf(320, 240);
    await session.openPdf('custom.pdf', custom);
    await session.goTo(8);
    const view = session.getView();
    expect(view.pageCount).toBe(2);
    expect(view.pageIndex).toBe(1);
    expect(view.pageWidth).toBe(320);
    expect(view.pageHeight).toBe(240);
  });

  it('parses the 1-based page field', () => {
    expect(parsePageNumber('2.6')).toBe(3);
    expect(parsePageNumber(' 4 ')).toBe(4);
    expect(parsePageNumber('next')).toBeNull();
  });

  it('keeps an untouched page empty in the cache', () => {
    const page = new PageModel();
    const history = new UndoManager();
    const cache = new PageCache(page, history);
    page.pointerDown('pencil', 1, 1, 1, DEFAULT_PEN);
    page.pointerUp(4, 5, 1);
    cache.switchTo(1);
    expect(page.strokeCount).toBe(0);
    expect(history.position()).toEqual({ current: 0, total: 0 });
    expect(cache.stored(0)?.strokes).toHaveLength(1);
    cache.switchTo(0);
    expect(page.strokeCount).toBe(1);
  });
});
