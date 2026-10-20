import {
  PDFArray,
  PDFDict,
  PDFDocument,
  PDFName,
  PDFNumber,
  PDFRawStream,
  PDFRef,
  type PDFPage,
} from 'pdf-lib';
import { cloneSnapshot, type PageSnapshot, type PlacedImage, type Stroke } from './types.js';

export interface InkAnnotationRecord {
  pageIndex: number;
  color: [number, number, number];
  opacity: number;
  width: number;
  traces: number[][];
}

function pdfNumber(value: number): string {
  if (!Number.isFinite(value)) return '0';
  const fixed = value.toFixed(4);
  return fixed.replace(/\.?0+$/, '') || '0';
}

function asNumber(value: unknown): number | null {
  return value instanceof PDFNumber ? value.asNumber() : null;
}

function numberArray(value: unknown): number[] {
  if (!(value instanceof PDFArray)) return [];
  const numbers: number[] = [];
  for (let index = 0; index < value.size(); index += 1) {
    const number = asNumber(value.lookup(index));
    if (number !== null) numbers.push(number);
  }
  return numbers;
}

function addInk(page: PDFPage, stroke: Stroke, scale: number): boolean {
  if (stroke.points.length < 1 || stroke.saved) return false;
  const origin = stroke.points[0];
  if (!origin) return false;
  // A tap is one sample. Nudge a second sample so round caps still paint a dot.
  const samples =
    stroke.points.length === 1 ? [origin, { ...origin, x: origin.x + 0.01 * scale }] : stroke.points;
  const doc = page.doc;
  const context = doc.context;
  const height = page.getHeight();
  const pdfPoints = samples.map((point) => ({
    x: point.x / scale,
    y: height - point.y / scale,
  }));
  let minX = Number.POSITIVE_INFINITY;
  let minY = Number.POSITIVE_INFINITY;
  let maxX = Number.NEGATIVE_INFINITY;
  let maxY = Number.NEGATIVE_INFINITY;
  for (const point of pdfPoints) {
    minX = Math.min(minX, point.x);
    minY = Math.min(minY, point.y);
    maxX = Math.max(maxX, point.x);
    maxY = Math.max(maxY, point.y);
  }
  const width = Math.max(stroke.width / scale, 0.1);
  const pad = width / 2 + 0.75;
  const llx = minX - pad;
  const lly = minY - pad;
  const urx = maxX + pad;
  const ury = maxY + pad;
  const red = stroke.color.r / 255;
  const green = stroke.color.g / 255;
  const blue = stroke.color.b / 255;
  const opacity = Math.min(1, Math.max(0, stroke.color.a / 255));
  const commands = [
    '/GS1 gs',
    `${pdfNumber(red)} ${pdfNumber(green)} ${pdfNumber(blue)} RG`,
    `${pdfNumber(width)} w`,
    '1 J',
    '1 j',
  ];
  const first = pdfPoints[0];
  if (!first) return false;
  commands.push(`${pdfNumber(first.x - llx)} ${pdfNumber(first.y - lly)} m`);
  for (const point of pdfPoints.slice(1)) {
    commands.push(`${pdfNumber(point.x - llx)} ${pdfNumber(point.y - lly)} l`);
  }
  commands.push('S');

  const graphicsState = context.register(
    context.obj({
      Type: PDFName.of('ExtGState'),
      CA: opacity,
      ca: opacity,
    }),
  );
  const appearance = context.register(
    context.stream(commands.join('\n'), {
      Type: PDFName.of('XObject'),
      Subtype: PDFName.of('Form'),
      FormType: 1,
      BBox: [0, 0, urx - llx, ury - lly],
      Resources: context.obj({
        ExtGState: context.obj({ GS1: graphicsState }),
      }),
    }),
  );
  const coords = pdfPoints.flatMap((point) => [point.x, point.y]);
  const annot = context.obj({
    Type: PDFName.of('Annot'),
    Subtype: PDFName.of('Ink'),
    Rect: [llx, lly, urx, ury],
    InkList: [coords],
    C: [red, green, blue],
    CA: opacity,
    F: 4,
    BS: context.obj({
      Type: PDFName.of('Border'),
      W: width,
      S: PDFName.of('S'),
    }),
    AP: context.obj({ N: appearance }),
  });
  const annotRef = context.register(annot);
  const existing = page.node.lookup(PDFName.of('Annots'));
  if (existing instanceof PDFArray) {
    existing.push(annotRef);
  } else {
    page.node.set(PDFName.of('Annots'), context.obj([annotRef]));
  }
  return true;
}

async function addImage(page: PDFPage, image: PlacedImage, scale: number): Promise<boolean> {
  if (image.saved || image.width <= 0 || image.height <= 0) return false;
  const embedded =
    image.mime === 'image/jpeg' ? await page.doc.embedJpg(image.bytes) : await page.doc.embedPng(image.bytes);
  const width = image.width / scale;
  const height = image.height / scale;
  page.drawImage(embedded, {
    x: image.x / scale,
    y: page.getHeight() - image.y / scale - height,
    width,
    height,
  });
  return true;
}

export async function bakeAnnotations(
  pdfBytes: Uint8Array,
  pages: ReadonlyMap<number, PageSnapshot>,
  scale: number,
): Promise<{ bytes: Uint8Array; pages: Map<number, PageSnapshot> }> {
  if (!(scale > 0)) throw new Error('Render scale must be positive');
  const doc = await PDFDocument.load(pdfBytes);
  const baked = new Map<number, PageSnapshot>();
  const pdfPages = doc.getPages();
  for (const [pageIndex, snapshot] of pages) {
    const next = cloneSnapshot(snapshot);
    const page = pdfPages[pageIndex];
    if (!page) {
      baked.set(pageIndex, next);
      continue;
    }
    for (const stroke of next.strokes) {
      if (stroke.saved) continue;
      if (addInk(page, stroke, scale)) stroke.saved = true;
    }
    for (const image of next.images) {
      if (image.saved) continue;
      if (await addImage(page, image, scale)) image.saved = true;
    }
    baked.set(pageIndex, next);
  }
  return { bytes: await doc.save(), pages: baked };
}

function dictWidth(dict: PDFDict): number {
  const border = dict.lookup(PDFName.of('BS'));
  if (border instanceof PDFDict) {
    const width = asNumber(border.lookup(PDFName.of('W')));
    if (width !== null) return width;
  }
  const fallback = numberArray(dict.lookup(PDFName.of('Border')));
  return fallback[2] ?? 0;
}

function inkRecord(dict: PDFDict, pageIndex: number): InkAnnotationRecord | null {
  const subtype = dict.lookup(PDFName.of('Subtype'));
  if (!subtype || !String(subtype).includes('Ink')) return null;
  const color = numberArray(dict.lookup(PDFName.of('C')));
  const inkList = dict.lookup(PDFName.of('InkList'));
  const traces: number[][] = [];
  if (inkList instanceof PDFArray) {
    for (let index = 0; index < inkList.size(); index += 1) {
      traces.push(numberArray(inkList.lookup(index)));
    }
  }
  const opacity = asNumber(dict.lookup(PDFName.of('CA'))) ?? 1;
  return {
    pageIndex,
    color: [color[0] ?? 0, color[1] ?? 0, color[2] ?? 0],
    opacity,
    width: dictWidth(dict),
    traces,
  };
}

export async function listInkAnnotations(pdfBytes: Uint8Array): Promise<InkAnnotationRecord[]> {
  const doc = await PDFDocument.load(pdfBytes);
  const records: InkAnnotationRecord[] = [];
  doc.getPages().forEach((page, pageIndex) => {
    const annots = page.node.lookup(PDFName.of('Annots'));
    if (!(annots instanceof PDFArray)) return;
    for (let index = 0; index < annots.size(); index += 1) {
      const annot = annots.lookup(index);
      if (annot instanceof PDFDict) {
        const record = inkRecord(annot, pageIndex);
        if (record) records.push(record);
      }
    }
  });
  return records;
}

export async function countPageImages(pdfBytes: Uint8Array, pageIndex: number): Promise<number> {
  const doc = await PDFDocument.load(pdfBytes);
  const page = doc.getPages()[pageIndex];
  if (!page) return 0;
  const resources = page.node.lookup(PDFName.of('Resources'));
  if (!(resources instanceof PDFDict)) return 0;
  const xobjects = resources.lookup(PDFName.of('XObject'));
  if (!(xobjects instanceof PDFDict)) return 0;
  let count = 0;
  for (const [, value] of xobjects.entries()) {
    const object = value instanceof PDFRef ? doc.context.lookup(value) : value;
    if (!(object instanceof PDFRawStream)) continue;
    const subtype = object.dict.lookup(PDFName.of('Subtype'));
    if (subtype && String(subtype).includes('Image')) count += 1;
  }
  return count;
}
