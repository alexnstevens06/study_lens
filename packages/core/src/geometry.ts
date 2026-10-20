import type { Point, Stroke } from './types.js';

/** Half-size of the Python eraser hit rect (4×4 centered on the pointer). */
export const ERASER_REACH = 2;

export interface Rect {
  x: number;
  y: number;
  w: number;
  h: number;
}

function orient(ax: number, ay: number, bx: number, by: number, cx: number, cy: number): number {
  return (bx - ax) * (cy - ay) - (by - ay) * (cx - ax);
}

function onSegment(
  ax: number,
  ay: number,
  bx: number,
  by: number,
  cx: number,
  cy: number,
): boolean {
  return (
    Math.min(ax, bx) - 1e-9 <= cx &&
    cx <= Math.max(ax, bx) + 1e-9 &&
    Math.min(ay, by) - 1e-9 <= cy &&
    cy <= Math.max(ay, by) + 1e-9
  );
}

export function segmentsIntersect(
  ax1: number,
  ay1: number,
  ax2: number,
  ay2: number,
  bx1: number,
  by1: number,
  bx2: number,
  by2: number,
): boolean {
  const o1 = orient(ax1, ay1, ax2, ay2, bx1, by1);
  const o2 = orient(ax1, ay1, ax2, ay2, bx2, by2);
  const o3 = orient(bx1, by1, bx2, by2, ax1, ay1);
  const o4 = orient(bx1, by1, bx2, by2, ax2, ay2);
  if (o1 === 0 && onSegment(ax1, ay1, ax2, ay2, bx1, by1)) return true;
  if (o2 === 0 && onSegment(ax1, ay1, ax2, ay2, bx2, by2)) return true;
  if (o3 === 0 && onSegment(bx1, by1, bx2, by2, ax1, ay1)) return true;
  if (o4 === 0 && onSegment(bx1, by1, bx2, by2, ax2, ay2)) return true;
  return o1 > 0 !== o2 > 0 && o3 > 0 !== o4 > 0;
}

export function pointSegmentDistance(
  px: number,
  py: number,
  x1: number,
  y1: number,
  x2: number,
  y2: number,
): number {
  const dx = x2 - x1;
  const dy = y2 - y1;
  const lengthSquared = dx * dx + dy * dy;
  if (lengthSquared === 0) return Math.hypot(px - x1, py - y1);
  const t = Math.max(0, Math.min(1, ((px - x1) * dx + (py - y1) * dy) / lengthSquared));
  return Math.hypot(px - (x1 + t * dx), py - (y1 + t * dy));
}

export function segmentSegmentDistance(
  ax1: number,
  ay1: number,
  ax2: number,
  ay2: number,
  bx1: number,
  by1: number,
  bx2: number,
  by2: number,
): number {
  if (segmentsIntersect(ax1, ay1, ax2, ay2, bx1, by1, bx2, by2)) return 0;
  return Math.min(
    pointSegmentDistance(ax1, ay1, bx1, by1, bx2, by2),
    pointSegmentDistance(ax2, ay2, bx1, by1, bx2, by2),
    pointSegmentDistance(bx1, by1, ax1, ay1, ax2, ay2),
    pointSegmentDistance(bx2, by2, ax1, ay1, ax2, ay2),
  );
}

function segmentIntersectsRect(
  x1: number,
  y1: number,
  x2: number,
  y2: number,
  left: number,
  top: number,
  right: number,
  bottom: number,
): boolean {
  if (x1 >= left && x1 <= right && y1 >= top && y1 <= bottom) return true;
  if (x2 >= left && x2 <= right && y2 >= top && y2 <= bottom) return true;
  const edges: Array<[number, number, number, number]> = [
    [left, top, right, top],
    [right, top, right, bottom],
    [right, bottom, left, bottom],
    [left, bottom, left, top],
  ];
  for (const [ex1, ey1, ex2, ey2] of edges) {
    if (segmentsIntersect(x1, y1, x2, y2, ex1, ey1, ex2, ey2)) return true;
  }
  return false;
}

function segmentNearRect(
  x1: number,
  y1: number,
  x2: number,
  y2: number,
  left: number,
  top: number,
  right: number,
  bottom: number,
  radius: number,
): boolean {
  if (segmentIntersectsRect(x1, y1, x2, y2, left, top, right, bottom)) return true;
  const edges: Array<[number, number, number, number]> = [
    [left, top, right, top],
    [right, top, right, bottom],
    [right, bottom, left, bottom],
    [left, bottom, left, top],
  ];
  for (const [ex1, ey1, ex2, ey2] of edges) {
    if (segmentSegmentDistance(x1, y1, x2, y2, ex1, ey1, ex2, ey2) <= radius) return true;
  }
  return false;
}

export function strokeHitsEraser(stroke: Stroke, x: number, y: number): boolean {
  const left = x - ERASER_REACH;
  const top = y - ERASER_REACH;
  const right = x + ERASER_REACH;
  const bottom = y + ERASER_REACH;
  const radius = stroke.width / 2;
  const points = stroke.points;
  if (points.length === 0) return false;
  if (points.length === 1) {
    const only = points[0];
    if (!only) return false;
    const closestX = Math.max(left, Math.min(only.x, right));
    const closestY = Math.max(top, Math.min(only.y, bottom));
    return Math.hypot(only.x - closestX, only.y - closestY) <= radius;
  }
  for (let index = 1; index < points.length; index += 1) {
    const start = points[index - 1];
    const end = points[index];
    if (!start || !end) continue;
    if (segmentNearRect(start.x, start.y, end.x, end.y, left, top, right, bottom, radius)) {
      return true;
    }
  }
  return false;
}

export function pointInPolygon(x: number, y: number, polygon: Point[]): boolean {
  if (polygon.length < 3) return false;
  let inside = false;
  for (let index = 0, previous = polygon.length - 1; index < polygon.length; previous = index, index += 1) {
    const current = polygon[index];
    const prior = polygon[previous];
    if (!current || !prior) continue;
    if (pointSegmentDistance(x, y, current.x, current.y, prior.x, prior.y) <= 1e-6) return true;
    const crosses = current.y > y !== prior.y > y;
    if (!crosses) continue;
    const xAtY = ((prior.x - current.x) * (y - current.y)) / (prior.y - current.y) + current.x;
    if (x < xAtY) inside = !inside;
  }
  return inside;
}

function distanceToPolygon(x: number, y: number, polygon: Point[]): number {
  let best = Number.POSITIVE_INFINITY;
  for (let index = 0; index < polygon.length; index += 1) {
    const start = polygon[index];
    const end = polygon[(index + 1) % polygon.length];
    if (!start || !end) continue;
    best = Math.min(best, pointSegmentDistance(x, y, start.x, start.y, end.x, end.y));
  }
  return best;
}

export function strokeIntersectsPolygon(stroke: Stroke, polygon: Point[]): boolean {
  if (polygon.length < 3 || stroke.points.length === 0) return false;
  const radius = stroke.width / 2;
  for (const point of stroke.points) {
    if (pointInPolygon(point.x, point.y, polygon)) return true;
    if (distanceToPolygon(point.x, point.y, polygon) <= radius) return true;
  }
  for (let index = 1; index < stroke.points.length; index += 1) {
    const start = stroke.points[index - 1];
    const end = stroke.points[index];
    if (!start || !end) continue;
    for (let edge = 0; edge < polygon.length; edge += 1) {
      const a = polygon[edge];
      const b = polygon[(edge + 1) % polygon.length];
      if (!a || !b) continue;
      if (segmentSegmentDistance(start.x, start.y, end.x, end.y, a.x, a.y, b.x, b.y) <= radius) {
        return true;
      }
    }
  }
  return false;
}

export function rectIntersectsPolygon(
  x: number,
  y: number,
  width: number,
  height: number,
  polygon: Point[],
): boolean {
  if (polygon.length < 3 || width < 0 || height < 0) return false;
  const corners: Point[] = [
    { x, y, pressure: 1 },
    { x: x + width, y, pressure: 1 },
    { x: x + width, y: y + height, pressure: 1 },
    { x, y: y + height, pressure: 1 },
  ];
  for (const corner of corners) {
    if (pointInPolygon(corner.x, corner.y, polygon)) return true;
  }
  for (const point of polygon) {
    if (point.x >= x && point.x <= x + width && point.y >= y && point.y <= y + height) return true;
  }
  const rectEdges: Array<[Point, Point]> = [
    [corners[0]!, corners[1]!],
    [corners[1]!, corners[2]!],
    [corners[2]!, corners[3]!],
    [corners[3]!, corners[0]!],
  ];
  for (const [start, end] of rectEdges) {
    for (let index = 0; index < polygon.length; index += 1) {
      const a = polygon[index];
      const b = polygon[(index + 1) % polygon.length];
      if (!a || !b) continue;
      if (segmentsIntersect(start.x, start.y, end.x, end.y, a.x, a.y, b.x, b.y)) return true;
    }
  }
  return false;
}
