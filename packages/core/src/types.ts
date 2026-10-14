export const RENDER_SCALE = 2;
export const RECENT_PEN_LIMIT = 6;

export interface Rgba {
  r: number;
  g: number;
  b: number;
  a: number;
}

export interface Point {
  x: number;
  y: number;
  pressure: number;
}

export interface PenSettings {
  color: Rgba;
  width: number;
}

export interface Stroke {
  id: string;
  points: Point[];
  color: Rgba;
  width: number;
  saved: boolean;
}

export interface PlacedImage {
  id: string;
  bytes: Uint8Array;
  mime: 'image/png' | 'image/jpeg';
  x: number;
  y: number;
  width: number;
  height: number;
  saved: boolean;
}

export interface PageSnapshot {
  strokes: Stroke[];
  images: PlacedImage[];
}

export type Tool = 'pencil' | 'eraser' | 'lasso';

export interface ItemMove {
  id: string;
  dx: number;
  dy: number;
}

export const DEFAULT_PEN: PenSettings = {
  color: { r: 0, g: 0, b: 0, a: 255 },
  width: 2,
};

export function newId(): string {
  return crypto.randomUUID();
}

export function cloneStroke(stroke: Stroke): Stroke {
  return {
    id: stroke.id,
    points: stroke.points.map((point) => ({ ...point })),
    color: { ...stroke.color },
    width: stroke.width,
    saved: stroke.saved,
  };
}

export function cloneImage(image: PlacedImage): PlacedImage {
  return {
    id: image.id,
    bytes: image.bytes.slice(),
    mime: image.mime,
    x: image.x,
    y: image.y,
    width: image.width,
    height: image.height,
    saved: image.saved,
  };
}

export function cloneSnapshot(snapshot: PageSnapshot): PageSnapshot {
  return {
    strokes: snapshot.strokes.map(cloneStroke),
    images: snapshot.images.map(cloneImage),
  };
}

export function emptyPage(): PageSnapshot {
  return { strokes: [], images: [] };
}

export function clonePen(pen: PenSettings): PenSettings {
  return { color: { ...pen.color }, width: pen.width };
}

export function samePen(a: PenSettings, b: PenSettings): boolean {
  return (
    a.width === b.width &&
    a.color.r === b.color.r &&
    a.color.g === b.color.g &&
    a.color.b === b.color.b &&
    a.color.a === b.color.a
  );
}

export function cssColor(color: Rgba): string {
  return `rgba(${color.r}, ${color.g}, ${color.b}, ${color.a / 255})`;
}

export function rememberPen(
  recent: PenSettings[],
  next: PenSettings,
  limit = RECENT_PEN_LIMIT,
): PenSettings[] {
  const kept = recent.filter((pen) => !samePen(pen, next));
  return [clonePen(next), ...kept].slice(0, limit);
}

export function normalizePressure(pressure: number): number {
  if (!Number.isFinite(pressure) || pressure <= 0) return 0.5;
  return Math.min(1, pressure);
}

/** On-screen width. PDF ink stores the nominal pen width, matching the Python app. */
export function pressureWidth(base: number, pressure: number): number {
  const scaled = normalizePressure(pressure);
  return base * Math.min(1, Math.max(0.15, scaled));
}
