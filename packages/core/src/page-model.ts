import { assertNever } from './assert-never.js';
import type { Command } from './commands.js';
import { rectIntersectsPolygon, strokeHitsEraser, strokeIntersectsPolygon, type Rect } from './geometry.js';
import {
  cloneImage,
  cloneSnapshot,
  cloneStroke,
  newId,
  normalizePressure,
  type ItemMove,
  type PageSnapshot,
  type PenSettings,
  type PlacedImage,
  type Point,
  type Rgba,
  type Stroke,
  type Tool,
} from './types.js';

const SELECTION_MARGIN = 5;

interface Selection {
  strokeIds: string[];
  imageIds: string[];
  dx: number;
  dy: number;
}

interface FadeGhost {
  stroke: Stroke;
  opacity: number;
}

interface LassoGhost {
  points: Point[];
  color: Rgba;
  width: number;
  opacity: number;
}

type Activity =
  | { type: 'idle' }
  | { type: 'drawing'; stroke: Stroke }
  | { type: 'erasing'; removed: Array<{ stroke: Stroke; index: number }>; deselected: Set<string> }
  | { type: 'lasso'; points: Point[]; color: Rgba; width: number }
  | { type: 'moving'; lastX: number; lastY: number };

export interface DrawnStroke {
  stroke: Stroke;
  dx: number;
  dy: number;
  selected: boolean;
}

export interface DrawnImage {
  image: PlacedImage;
  dx: number;
  dy: number;
  selected: boolean;
}

export interface RenderState {
  strokes: DrawnStroke[];
  images: DrawnImage[];
  live: Stroke | null;
  lasso: { points: Point[]; color: Rgba; width: number } | null;
  ghosts: FadeGhost[];
  lassoGhost: LassoGhost | null;
  selectionRect: Rect | null;
}

export class PageModel {
  private strokes: Stroke[] = [];
  private images: PlacedImage[] = [];
  private selection: Selection | null = null;
  private activity: Activity = { type: 'idle' };
  private ghosts: FadeGhost[] = [];
  private lassoGhost: LassoGhost | null = null;

  get strokeCount(): number {
    return this.strokes.length;
  }

  get imageCount(): number {
    return this.images.length;
  }

  pointerDown(tool: Tool, x: number, y: number, pressure: number, pen: PenSettings): void {
    if (this.activity.type !== 'idle') return;
    const point = this.sample(x, y, pressure);
    switch (tool) {
      case 'eraser': {
        const deselected = new Set<string>();
        this.activity = { type: 'erasing', removed: [], deselected };
        this.activity.removed.push(...this.eraseAt(point.x, point.y));
        break;
      }
      case 'pencil':
        if (this.selection && this.pointInSelection(point.x, point.y)) {
          this.activity = { type: 'moving', lastX: point.x, lastY: point.y };
          break;
        }
        this.clearSelection();
        this.activity = {
          type: 'drawing',
          stroke: {
            id: newId(),
            points: [point],
            color: { ...pen.color },
            width: pen.width,
            saved: false,
          },
        };
        break;
      case 'lasso':
        this.activity = {
          type: 'lasso',
          points: [point],
          color: { ...pen.color },
          width: pen.width,
        };
        break;
      default:
        assertNever(tool);
    }
  }

  pointerMove(x: number, y: number, pressure: number): void {
    const point = this.sample(x, y, pressure);
    switch (this.activity.type) {
      case 'idle':
        return;
      case 'drawing': {
        const previous = this.activity.stroke.points[this.activity.stroke.points.length - 1];
        if (!previous) return;
        if (Math.hypot(point.x - previous.x, point.y - previous.y) < 0.25) return;
        this.activity.stroke.points.push(point);
        return;
      }
      case 'erasing':
        this.activity.removed.push(...this.eraseAt(point.x, point.y));
        return;
      case 'lasso':
        this.activity.points.push(point);
        return;
      case 'moving': {
        if (!this.selection) return;
        this.selection.dx += point.x - this.activity.lastX;
        this.selection.dy += point.y - this.activity.lastY;
        this.activity.lastX = point.x;
        this.activity.lastY = point.y;
        return;
      }
      default:
        assertNever(this.activity);
    }
  }

  pointerUp(x: number, y: number, pressure: number): Command[] {
    this.pointerMove(x, y, pressure);
    return this.finish();
  }

  /** Finish an in-progress gesture so a page change or save keeps its ink. */
  flush(): Command[] {
    return this.finish();
  }

  private finish(): Command[] {
    const activity = this.activity;
    this.activity = { type: 'idle' };
    switch (activity.type) {
      case 'idle':
        return [];
      case 'drawing':
        this.strokes.push(activity.stroke);
        return [{ kind: 'add-stroke', stroke: cloneStroke(activity.stroke) }];
      case 'erasing':
        return activity.removed.map((entry) => ({
          kind: 'erase-stroke' as const,
          stroke: entry.stroke,
          index: entry.index,
        }));
      case 'lasso':
        this.finishLasso(activity.points, activity.color, activity.width);
        return [];
      case 'moving': {
        const command = this.bakeMove();
        return command ? [command] : [];
      }
      default:
        return assertNever(activity);
    }
  }

  addImage(image: PlacedImage): Command {
    this.images.push(image);
    return { kind: 'add-image', image: cloneImage(image) };
  }

  insertStroke(stroke: Stroke, index?: number): void {
    if (this.strokes.some((item) => item.id === stroke.id)) return;
    const copy = cloneStroke(stroke);
    if (index === undefined || index < 0 || index >= this.strokes.length) {
      this.strokes.push(copy);
      return;
    }
    this.strokes.splice(index, 0, copy);
  }

  deleteStroke(id: string): void {
    this.strokes = this.strokes.filter((stroke) => stroke.id !== id);
    if (!this.selection) return;
    this.selection = {
      ...this.selection,
      strokeIds: this.selection.strokeIds.filter((strokeId) => strokeId !== id),
    };
    this.dropEmptySelection();
  }

  insertImage(image: PlacedImage): void {
    if (this.images.some((item) => item.id === image.id)) return;
    this.images.push(cloneImage(image));
  }

  deleteImage(id: string): void {
    this.images = this.images.filter((image) => image.id !== id);
    if (!this.selection) return;
    this.selection = {
      ...this.selection,
      imageIds: this.selection.imageIds.filter((imageId) => imageId !== id),
    };
    this.dropEmptySelection();
  }

  translateItems(moves: ItemMove[], sign: number): void {
    const byId = new Map(moves.map((move) => [move.id, move]));
    for (const stroke of this.strokes) {
      const move = byId.get(stroke.id);
      if (!move) continue;
      for (const point of stroke.points) {
        point.x += sign * move.dx;
        point.y += sign * move.dy;
      }
    }
    for (const image of this.images) {
      const move = byId.get(image.id);
      if (!move) continue;
      image.x += sign * move.dx;
      image.y += sign * move.dy;
    }
  }

  clearSelection(): void {
    this.selection = null;
  }

  stepFade(amount: number): void {
    const step = Math.max(0, amount);
    this.ghosts = this.ghosts
      .map((ghost) => ({ stroke: ghost.stroke, opacity: ghost.opacity - step }))
      .filter((ghost) => ghost.opacity > 0.001);
    if (!this.lassoGhost) return;
    const opacity = this.lassoGhost.opacity - step;
    this.lassoGhost = opacity > 0.001 ? { ...this.lassoGhost, opacity } : null;
  }

  hasFade(): boolean {
    return this.ghosts.length > 0 || this.lassoGhost !== null;
  }

  snapshot(): PageSnapshot {
    return cloneSnapshot({ strokes: this.strokes, images: this.images });
  }

  restore(snapshot: PageSnapshot): void {
    const copy = cloneSnapshot(snapshot);
    this.strokes = copy.strokes;
    this.images = copy.images;
    this.selection = null;
    this.activity = { type: 'idle' };
    this.ghosts = [];
    this.lassoGhost = null;
  }

  getRenderState(): RenderState {
    const strokeIds = new Set(this.selection?.strokeIds ?? []);
    const imageIds = new Set(this.selection?.imageIds ?? []);
    const dx = this.selection?.dx ?? 0;
    const dy = this.selection?.dy ?? 0;
    return {
      strokes: this.strokes.map((stroke) => ({
        stroke,
        dx: strokeIds.has(stroke.id) ? dx : 0,
        dy: strokeIds.has(stroke.id) ? dy : 0,
        selected: strokeIds.has(stroke.id),
      })),
      images: this.images.map((image) => ({
        image,
        dx: imageIds.has(image.id) ? dx : 0,
        dy: imageIds.has(image.id) ? dy : 0,
        selected: imageIds.has(image.id),
      })),
      live: this.activity.type === 'drawing' ? this.activity.stroke : null,
      lasso:
        this.activity.type === 'lasso'
          ? { points: this.activity.points, color: this.activity.color, width: this.activity.width }
          : null,
      ghosts: this.ghosts.map((ghost) => ({ stroke: ghost.stroke, opacity: ghost.opacity })),
      lassoGhost: this.lassoGhost,
      selectionRect: this.selectionRect(),
    };
  }

  private sample(x: number, y: number, pressure: number): Point {
    return { x, y, pressure: normalizePressure(pressure) };
  }

  private eraseAt(x: number, y: number): Array<{ stroke: Stroke; index: number }> {
    const removed: Array<{ stroke: Stroke; index: number }> = [];
    const deselected = this.activity.type === 'erasing' ? this.activity.deselected : new Set<string>();
    for (let index = this.strokes.length - 1; index >= 0; index -= 1) {
      const stroke = this.strokes[index];
      if (!stroke || deselected.has(stroke.id)) continue;
      const offset = this.offsetFor(stroke.id);
      if (!strokeHitsEraser(stroke, x - offset.dx, y - offset.dy)) continue;
      if (this.selection?.strokeIds.includes(stroke.id)) {
        this.deselect(stroke.id);
        deselected.add(stroke.id);
        continue;
      }
      const [taken] = this.strokes.splice(index, 1);
      if (!taken) continue;
      this.ghosts.push({ stroke: cloneStroke(taken), opacity: 1 });
      removed.push({ stroke: cloneStroke(taken), index });
    }
    return removed;
  }

  private deselect(id: string): void {
    if (!this.selection) return;
    this.selection = {
      ...this.selection,
      strokeIds: this.selection.strokeIds.filter((strokeId) => strokeId !== id),
      imageIds: this.selection.imageIds.filter((imageId) => imageId !== id),
    };
    this.dropEmptySelection();
  }

  private dropEmptySelection(): void {
    if (!this.selection) return;
    if (this.selection.strokeIds.length === 0 && this.selection.imageIds.length === 0) {
      this.selection = null;
    }
  }

  private offsetFor(id: string): { dx: number; dy: number } {
    if (!this.selection) return { dx: 0, dy: 0 };
    if (!this.selection.strokeIds.includes(id) && !this.selection.imageIds.includes(id)) {
      return { dx: 0, dy: 0 };
    }
    return { dx: this.selection.dx, dy: this.selection.dy };
  }

  private finishLasso(points: Point[], color: Rgba, width: number): void {
    this.lassoGhost = { points, color, width, opacity: 1 };
    const hits = this.hitsInPolygon(points);
    const hasSelection =
      this.selection !== null &&
      (this.selection.strokeIds.length > 0 || this.selection.imageIds.length > 0);
    if (hasSelection && this.selection) {
      const strokeIds = new Set(this.selection.strokeIds);
      const imageIds = new Set(this.selection.imageIds);
      for (const id of hits.strokeIds) strokeIds.add(id);
      for (const id of hits.imageIds) imageIds.add(id);
      this.selection = { strokeIds: [...strokeIds], imageIds: [...imageIds], dx: 0, dy: 0 };
      return;
    }
    if (hits.strokeIds.length === 0 && hits.imageIds.length === 0) {
      this.selection = null;
      return;
    }
    this.selection = { strokeIds: hits.strokeIds, imageIds: hits.imageIds, dx: 0, dy: 0 };
  }

  private hitsInPolygon(polygon: Point[]): { strokeIds: string[]; imageIds: string[] } {
    return {
      strokeIds: this.strokes
        .filter((stroke) => strokeIntersectsPolygon(stroke, polygon))
        .map((stroke) => stroke.id),
      imageIds: this.images
        .filter((image) => rectIntersectsPolygon(image.x, image.y, image.width, image.height, polygon))
        .map((image) => image.id),
    };
  }

  private pointInSelection(x: number, y: number): boolean {
    const rect = this.selectionRect();
    if (!rect) return false;
    return x >= rect.x && x <= rect.x + rect.w && y >= rect.y && y <= rect.y + rect.h;
  }

  private selectionRect(): Rect | null {
    if (!this.selection) return null;
    const dx = this.selection.dx;
    const dy = this.selection.dy;
    let minX = Number.POSITIVE_INFINITY;
    let minY = Number.POSITIVE_INFINITY;
    let maxX = Number.NEGATIVE_INFINITY;
    let maxY = Number.NEGATIVE_INFINITY;
    for (const stroke of this.strokes) {
      if (!this.selection.strokeIds.includes(stroke.id)) continue;
      const pad = stroke.width / 2;
      for (const point of stroke.points) {
        minX = Math.min(minX, point.x + dx - pad);
        minY = Math.min(minY, point.y + dy - pad);
        maxX = Math.max(maxX, point.x + dx + pad);
        maxY = Math.max(maxY, point.y + dy + pad);
      }
    }
    for (const image of this.images) {
      if (!this.selection.imageIds.includes(image.id)) continue;
      minX = Math.min(minX, image.x + dx);
      minY = Math.min(minY, image.y + dy);
      maxX = Math.max(maxX, image.x + dx + image.width);
      maxY = Math.max(maxY, image.y + dy + image.height);
    }
    if (!Number.isFinite(minX)) return null;
    return {
      x: minX - SELECTION_MARGIN,
      y: minY - SELECTION_MARGIN,
      w: maxX - minX + SELECTION_MARGIN * 2,
      h: maxY - minY + SELECTION_MARGIN * 2,
    };
  }

  private bakeMove(): Command | null {
    if (!this.selection) return null;
    const { dx, dy } = this.selection;
    if (dx === 0 && dy === 0) return null;
    const moves: ItemMove[] = [];
    for (const stroke of this.strokes) {
      if (!this.selection.strokeIds.includes(stroke.id)) continue;
      for (const point of stroke.points) {
        point.x += dx;
        point.y += dy;
      }
      moves.push({ id: stroke.id, dx, dy });
    }
    for (const image of this.images) {
      if (!this.selection.imageIds.includes(image.id)) continue;
      image.x += dx;
      image.y += dy;
      moves.push({ id: image.id, dx, dy });
    }
    this.selection = { ...this.selection, dx: 0, dy: 0 };
    if (moves.length === 0) return null;
    return { kind: 'move-items', moves };
  }
}
