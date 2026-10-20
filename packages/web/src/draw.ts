import { cssColor, pressureWidth, type PlacedImage, type Point, type RenderState, type Rgba } from '@study-lens/core';

const images = new Map<string, HTMLImageElement>();

export function drawScene(
  canvas: HTMLCanvasElement,
  state: RenderState,
  width: number,
  height: number,
  onNeedRedraw: () => void,
): void {
  const bitmapWidth = Math.max(1, Math.round(width));
  const bitmapHeight = Math.max(1, Math.round(height));
  if (canvas.width !== bitmapWidth || canvas.height !== bitmapHeight) {
    canvas.width = bitmapWidth;
    canvas.height = bitmapHeight;
  }
  const context = canvas.getContext('2d');
  if (!context) return;
  context.clearRect(0, 0, canvas.width, canvas.height);

  for (const ghost of state.ghosts) {
    paintStroke(context, ghost.stroke.points, ghost.stroke.width, ghost.stroke.color, ghost.opacity, 0, 0);
  }
  for (const item of state.images) {
    const element = loadImage(item.image, onNeedRedraw);
    if (!element) continue;
    context.drawImage(
      element,
      item.image.x + item.dx,
      item.image.y + item.dy,
      item.image.width,
      item.image.height,
    );
  }
  for (const item of state.strokes) {
    const color = item.selected ? { ...item.stroke.color, r: 255, g: 0, b: 0 } : item.stroke.color;
    paintStroke(context, item.stroke.points, item.stroke.width, color, 1, item.dx, item.dy);
  }
  if (state.live) {
    paintStroke(context, state.live.points, state.live.width, state.live.color, 1, 0, 0);
  }
  if (state.lasso) paintLasso(context, state.lasso.points, state.lasso.color, state.lasso.width, 1);
  if (state.lassoGhost) {
    paintLasso(context, state.lassoGhost.points, state.lassoGhost.color, state.lassoGhost.width, state.lassoGhost.opacity);
  }
  if (state.selectionRect) {
    const rect = state.selectionRect;
    context.save();
    context.strokeStyle = '#1d4e89';
    context.lineWidth = 1;
    context.setLineDash([5, 4]);
    context.strokeRect(rect.x, rect.y, rect.w, rect.h);
    context.restore();
  }
}

function paintStroke(
  context: CanvasRenderingContext2D,
  points: Point[],
  width: number,
  color: Rgba,
  alpha: number,
  dx: number,
  dy: number,
): void {
  if (points.length === 0) return;
  context.save();
  context.globalAlpha = alpha;
  context.strokeStyle = cssColor(color);
  context.fillStyle = cssColor(color);
  context.lineCap = 'round';
  context.lineJoin = 'round';
  const first = points[0];
  if (points.length === 1 && first) {
    context.beginPath();
    context.arc(first.x + dx, first.y + dy, pressureWidth(width, first.pressure) / 2, 0, Math.PI * 2);
    context.fill();
    context.restore();
    return;
  }
  for (let index = 1; index < points.length; index += 1) {
    const previous = points[index - 1];
    const point = points[index];
    if (!previous || !point) continue;
    context.lineWidth = pressureWidth(width, point.pressure);
    context.beginPath();
    context.moveTo(previous.x + dx, previous.y + dy);
    context.lineTo(point.x + dx, point.y + dy);
    context.stroke();
  }
  context.restore();
}

function paintLasso(
  context: CanvasRenderingContext2D,
  points: Point[],
  color: Rgba,
  width: number,
  alpha: number,
): void {
  const first = points[0];
  if (!first) return;
  context.save();
  context.globalAlpha = alpha;
  context.strokeStyle = cssColor(color);
  context.lineWidth = Math.max(1, width);
  context.setLineDash([4, 4]);
  context.lineCap = 'round';
  context.beginPath();
  context.moveTo(first.x, first.y);
  for (const point of points.slice(1)) context.lineTo(point.x, point.y);
  context.closePath();
  context.stroke();
  context.restore();
}

function loadImage(image: PlacedImage, onNeedRedraw: () => void): HTMLImageElement | null {
  const cached = images.get(image.id);
  if (cached?.complete && cached.naturalWidth > 0) return cached;
  if (cached) return null;
  const copy = new Uint8Array(image.bytes.byteLength);
  copy.set(image.bytes);
  const blob = new Blob([copy], { type: image.mime });
  const url = URL.createObjectURL(blob);
  const element = new Image();
  element.onload = () => {
    URL.revokeObjectURL(url);
    onNeedRedraw();
  };
  element.onerror = () => URL.revokeObjectURL(url);
  element.src = url;
  images.set(image.id, element);
  return null;
}
