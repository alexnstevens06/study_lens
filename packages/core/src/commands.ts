import { assertNever } from './assert-never.js';
import type { PageModel } from './page-model.js';
import type { ItemMove, PlacedImage, Stroke } from './types.js';

export type Command =
  | { kind: 'add-stroke'; stroke: Stroke }
  | { kind: 'erase-stroke'; stroke: Stroke; index: number }
  | { kind: 'add-image'; image: PlacedImage }
  | { kind: 'move-items'; moves: ItemMove[] };

export type HistoryDirection = 'undo' | 'redo';

export function applyCommand(page: PageModel, command: Command, direction: HistoryDirection): void {
  switch (command.kind) {
    case 'add-stroke':
      if (direction === 'redo') page.insertStroke(command.stroke);
      else page.deleteStroke(command.stroke.id);
      break;
    case 'erase-stroke':
      if (direction === 'undo') page.insertStroke(command.stroke, command.index);
      else page.deleteStroke(command.stroke.id);
      break;
    case 'add-image':
      if (direction === 'redo') page.insertImage(command.image);
      else page.deleteImage(command.image.id);
      break;
    case 'move-items':
      page.translateItems(command.moves, direction === 'redo' ? 1 : -1);
      page.clearSelection();
      break;
    default:
      assertNever(command);
  }
}

export class UndoManager {
  private undoStack: Command[] = [];
  private redoStack: Command[] = [];
  private readonly listeners = new Set<(current: number, total: number) => void>();

  subscribe(listener: (current: number, total: number) => void): () => void {
    this.listeners.add(listener);
    return () => {
      this.listeners.delete(listener);
    };
  }

  position(): { current: number; total: number } {
    return {
      current: this.undoStack.length,
      total: this.undoStack.length + this.redoStack.length,
    };
  }

  push(command: Command): void {
    this.undoStack.push(command);
    this.redoStack = [];
    this.emit();
  }

  undo(page: PageModel, steps = 1): void {
    for (let step = 0; step < steps; step += 1) {
      const command = this.undoStack.pop();
      if (!command) break;
      applyCommand(page, command, 'undo');
      this.redoStack.push(command);
    }
    this.emit();
  }

  redo(page: PageModel, steps = 1): void {
    for (let step = 0; step < steps; step += 1) {
      const command = this.redoStack.pop();
      if (!command) break;
      applyCommand(page, command, 'redo');
      this.undoStack.push(command);
    }
    this.emit();
  }

  clear(): void {
    this.undoStack = [];
    this.redoStack = [];
    this.emit();
  }

  private emit(): void {
    const { current, total } = this.position();
    for (const listener of this.listeners) listener(current, total);
  }
}
