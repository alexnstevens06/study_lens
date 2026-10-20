import type { UndoManager } from './commands.js';
import type { PageModel } from './page-model.js';
import { cloneSnapshot, emptyPage, type PageSnapshot } from './types.js';

/**
 * Per-page strokes and images. Switching pages stores the page you left and
 * clears the undo stack, matching the Python viewer.
 */
export class PageCache {
  private readonly pages = new Map<number, PageSnapshot>();
  currentIndex = 0;

  constructor(
    private readonly page: PageModel,
    private readonly history: UndoManager,
  ) {}

  capture(): void {
    const commands = this.page.flush();
    for (const command of commands) this.history.push(command);
    this.pages.set(this.currentIndex, this.page.snapshot());
  }

  switchTo(index: number): void {
    this.capture();
    this.currentIndex = index;
    this.page.restore(this.pages.get(index) ?? emptyPage());
    this.history.clear();
  }

  /** Install ink read from a PDF. Does not record undo commands. */
  loadSnapshots(pages: ReadonlyMap<number, PageSnapshot>): void {
    for (const [index, snapshot] of pages) {
      this.pages.set(index, cloneSnapshot(snapshot));
    }
    this.page.restore(this.pages.get(this.currentIndex) ?? emptyPage());
  }

  /** Drop cached ink after it has been written into the PDF. */
  drop(): void {
    this.pages.clear();
  }

  reset(): void {
    this.pages.clear();
    this.currentIndex = 0;
  }

  snapshotAll(): Map<number, PageSnapshot> {
    this.capture();
    const copies = new Map<number, PageSnapshot>();
    for (const [index, snapshot] of this.pages) {
      copies.set(index, cloneSnapshot(snapshot));
    }
    return copies;
  }

  stored(index: number): PageSnapshot | undefined {
    const snapshot = this.pages.get(index);
    return snapshot ? cloneSnapshot(snapshot) : undefined;
  }
}
