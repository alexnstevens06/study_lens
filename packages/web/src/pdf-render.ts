import { AnnotationMode, getDocument, GlobalWorkerOptions } from 'pdfjs-dist';
import workerUrl from 'pdfjs-dist/build/pdf.worker.min.mjs?url';

GlobalWorkerOptions.workerSrc = workerUrl;

export async function renderPdfPage(
  bytes: Uint8Array,
  pageIndex: number,
  canvas: HTMLCanvasElement,
  scale: number,
): Promise<void> {
  const loading = getDocument({ data: bytes.slice() });
  const pdf = await loading.promise;
  try {
    const page = await pdf.getPage(pageIndex + 1);
    const viewport = page.getViewport({ scale });
    canvas.width = Math.ceil(viewport.width);
    canvas.height = Math.ceil(viewport.height);
    const context = canvas.getContext('2d');
    if (!context) throw new Error('Canvas is unavailable');
    context.fillStyle = '#fffefb';
    context.fillRect(0, 0, canvas.width, canvas.height);
    await page.render({ canvasContext: context, viewport, annotationMode: AnnotationMode.ENABLE }).promise;
  } finally {
    await pdf.destroy();
  }
}
