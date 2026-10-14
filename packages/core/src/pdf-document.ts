import { PDFDocument } from 'pdf-lib';

export const A4_WIDTH = 595;
export const A4_HEIGHT = 842;

export interface PageSize {
  width: number;
  height: number;
}

export async function createBlankPdf(width = A4_WIDTH, height = A4_HEIGHT): Promise<Uint8Array> {
  const doc = await PDFDocument.create();
  doc.addPage([width, height]);
  return doc.save();
}

export async function readPdfStructure(
  bytes: Uint8Array,
): Promise<{ pageCount: number; pageSizes: PageSize[] }> {
  const doc = await PDFDocument.load(bytes);
  const pageSizes = doc.getPages().map((page) => ({
    width: page.getWidth(),
    height: page.getHeight(),
  }));
  return { pageCount: pageSizes.length, pageSizes };
}

export async function appendMatchingPage(
  bytes: Uint8Array,
): Promise<{ bytes: Uint8Array; pageCount: number; pageSize: PageSize }> {
  const doc = await PDFDocument.load(bytes);
  const pages = doc.getPages();
  const last = pages[pages.length - 1];
  if (!last) throw new Error('PDF has no pages');
  const pageSize = { width: last.getWidth(), height: last.getHeight() };
  doc.addPage([pageSize.width, pageSize.height]);
  const saved = await doc.save();
  return { bytes: saved, pageCount: doc.getPageCount(), pageSize };
}

export function noteFileName(date: Date): string {
  const pad = (value: number) => String(value).padStart(2, '0');
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}_${pad(date.getHours())}-${pad(date.getMinutes())}-${pad(date.getSeconds())}.pdf`;
}
