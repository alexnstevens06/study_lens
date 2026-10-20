import { UndoManager } from './commands.js';
import { PageCache } from './page-cache.js';
import { PageModel } from './page-model.js';
import {
  A4_HEIGHT,
  A4_WIDTH,
  appendMatchingPage,
  createBlankPdf,
  noteFileName,
  readPdfStructure,
  type PageSize,
} from './pdf-document.js';
import { bakeAnnotations } from './annotations.js';
import {
  clonePen,
  DEFAULT_PEN,
  emptyPage,
  RENDER_SCALE,
  type PenSettings,
  type PlacedImage,
  type Tool,
} from './types.js';

export interface SessionView {
  hasDocument: boolean;
  fileName: string;
  isNew: boolean;
  pageCount: number;
  pageIndex: number;
  pageWidth: number;
  pageHeight: number;
  documentGeneration: number;
  tool: Tool;
  pen: PenSettings;
  historyCurrent: number;
  historyTotal: number;
  strokeCount: number;
  imageCount: number;
}

export interface SavedPdf {
  name: string;
  bytes: Uint8Array;
}

export class StudySession {
  readonly page = new PageModel();
  readonly history = new UndoManager();
  readonly cache = new PageCache(this.page, this.history);
  readonly renderScale = RENDER_SCALE;

  private bytes: Uint8Array | null = null;
  private fileName = '';
  private isNew = false;
  private pageCount = 0;
  private pageSizes: PageSize[] = [];
  private documentGeneration = 0;
  private tool: Tool = 'pencil';
  private pen: PenSettings = clonePen(DEFAULT_PEN);
  private view: SessionView = this.buildView();
  private readonly viewListeners = new Set<() => void>();
  private readonly inkListeners = new Set<() => void>();

  get documentBytes(): Uint8Array | null {
    return this.bytes ? this.bytes.slice() : null;
  }

  getView = (): SessionView => this.view;

  subscribeView = (listener: () => void): (() => void) => {
    this.viewListeners.add(listener);
    return () => {
      this.viewListeners.delete(listener);
    };
  };

  subscribeInk = (listener: () => void): (() => void) => {
    this.inkListeners.add(listener);
    return () => {
      this.inkListeners.delete(listener);
    };
  };

  async openPdf(name: string, bytes: Uint8Array): Promise<void> {
    const structure = await readPdfStructure(bytes);
    if (structure.pageCount < 1) throw new Error('PDF has no pages');
    this.bytes = bytes.slice();
    this.fileName = name;
    this.isNew = false;
    this.pageCount = structure.pageCount;
    this.pageSizes = structure.pageSizes;
    this.resetPages();
  }

  async newNote(): Promise<void> {
    this.bytes = await createBlankPdf();
    this.fileName = '';
    this.isNew = true;
    this.pageCount = 1;
    this.pageSizes = [{ width: A4_WIDTH, height: A4_HEIGHT }];
    this.resetPages();
  }

  clear(): void {
    this.bytes = null;
    this.fileName = '';
    this.isNew = false;
    this.pageCount = 0;
    this.pageSizes = [];
    this.resetPages();
  }

  async goTo(index: number): Promise<void> {
    if (this.bytes === null || !Number.isFinite(index)) return;
    let target = index;
    if (target < 0) target = 0;
    if (target >= this.pageCount) {
      await this.appendPage();
      return;
    }
    if (target === this.cache.currentIndex) return;
    this.cache.switchTo(target);
    this.emitView();
  }

  async changePage(delta: number): Promise<void> {
    if (this.bytes === null) return;
    await this.goTo(this.cache.currentIndex + delta);
  }

  setTool(tool: Tool): void {
    if (this.tool === tool) return;
    this.tool = tool;
    this.emitView();
  }

  setPen(pen: PenSettings): void {
    this.pen = clonePen(pen);
    this.emitView();
  }

  pointerDown(tool: Tool, x: number, y: number, pressure: number): void {
    if (this.bytes === null) return;
    this.page.pointerDown(tool, x, y, pressure, this.pen);
    this.emitInk();
  }

  pointerMove(x: number, y: number, pressure: number): void {
    if (this.bytes === null) return;
    this.page.pointerMove(x, y, pressure);
    this.emitInk();
  }

  pointerUp(x: number, y: number, pressure: number): void {
    if (this.bytes === null) return;
    const commands = this.page.pointerUp(x, y, pressure);
    for (const command of commands) this.history.push(command);
    if (commands.length > 0) this.emitView();
    else this.emitInk();
  }

  pasteImage(image: PlacedImage): void {
    if (this.bytes === null) return;
    const command = this.page.addImage(image);
    this.history.push(command);
    this.emitView();
  }

  undo(steps = 1): void {
    this.history.undo(this.page, steps);
    this.emitView();
  }

  redo(steps = 1): void {
    this.history.redo(this.page, steps);
    this.emitView();
  }

  stepFade(amount: number): boolean {
    this.page.stepFade(amount);
    this.emitInk();
    return this.page.hasFade();
  }

  /** Bytes to write. Overlays stay until `commitSave`, so a cancelled dialog loses nothing. */
  async buildSavedPdf(now = new Date()): Promise<SavedPdf> {
    if (this.bytes === null) throw new Error('No document open');
    const snapshots = this.cache.snapshotAll();
    // Finishing an in-progress stroke updates history. Refresh before a save dialog can cancel.
    this.emitView();
    const baked = await bakeAnnotations(this.bytes, snapshots, this.renderScale);
    const name = this.isNew || this.fileName.length === 0 ? noteFileName(now) : this.fileName;
    return { name, bytes: baked.bytes };
  }

  commitSave(bytes: Uint8Array, name: string): void {
    this.bytes = bytes.slice();
    this.fileName = name;
    this.isNew = false;
    this.page.restore(emptyPage());
    this.cache.drop();
    this.history.clear();
    this.documentGeneration += 1;
    this.emitView();
  }

  private async appendPage(): Promise<void> {
    if (this.bytes === null) return;
    this.cache.capture();
    const appended = await appendMatchingPage(this.bytes);
    this.bytes = appended.bytes;
    this.pageCount = appended.pageCount;
    this.pageSizes = [...this.pageSizes, appended.pageSize];
    this.cache.currentIndex = this.pageCount - 1;
    this.page.restore(emptyPage());
    this.history.clear();
    this.documentGeneration += 1;
    this.emitView();
  }

  private resetPages(): void {
    this.page.restore(emptyPage());
    this.history.clear();
    this.cache.reset();
    this.documentGeneration += 1;
    this.emitView();
  }

  private currentPageSize(): PageSize {
    return this.pageSizes[this.cache.currentIndex] ?? { width: 0, height: 0 };
  }

  private buildView(): SessionView {
    const size = this.currentPageSize();
    const history = this.history.position();
    return {
      hasDocument: this.bytes !== null,
      fileName: this.fileName,
      isNew: this.isNew,
      pageCount: this.pageCount,
      pageIndex: this.cache.currentIndex,
      pageWidth: size.width,
      pageHeight: size.height,
      documentGeneration: this.documentGeneration,
      tool: this.tool,
      pen: clonePen(this.pen),
      historyCurrent: history.current,
      historyTotal: history.total,
      strokeCount: this.page.strokeCount,
      imageCount: this.page.imageCount,
    };
  }

  private emitView(): void {
    this.view = this.buildView();
    for (const listener of this.viewListeners) listener();
    this.emitInk();
  }

  private emitInk(): void {
    for (const listener of this.inkListeners) listener();
  }
}
