import { mkdir, readFile, writeFile } from 'node:fs/promises';
import path from 'node:path';
import { PDFDocument, StandardFonts, rgb } from 'pdf-lib';
import { expect, test, type Page } from '@playwright/test';
import { listInkAnnotations } from '../packages/core/dist/index.js';

const fixture = path.join(process.cwd(), 'e2e', 'fixtures', 'sample.pdf');

async function darkPixels(
  page: Page,
  ratios: { x0: number; y0: number; x1: number; y1: number },
): Promise<number> {
  return page.locator('.pdf-canvas').evaluate((canvas, region) => {
    const context = canvas.getContext('2d');
    if (!context) return 0;
    const startX = region.x0 * canvas.width;
    const startY = region.y0 * canvas.height;
    const endX = region.x1 * canvas.width;
    const endY = region.y1 * canvas.height;
    const left = Math.max(0, Math.floor(Math.min(startX, endX) - 6));
    const top = Math.max(0, Math.floor(Math.min(startY, endY) - 6));
    const right = Math.min(canvas.width, Math.ceil(Math.max(startX, endX) + 6));
    const bottom = Math.min(canvas.height, Math.ceil(Math.max(startY, endY) + 6));
    const width = Math.max(1, right - left);
    const height = Math.max(1, bottom - top);
    const image = context.getImageData(left, top, width, height);
    let dark = 0;
    for (let index = 0; index < image.data.length; index += 4) {
      const red = image.data[index] ?? 255;
      const green = image.data[index + 1] ?? 255;
      const blue = image.data[index + 2] ?? 255;
      if (red < 200 && green < 200 && blue < 200) dark += 1;
    }
    return dark;
  }, ratios);
}

test.beforeAll(async () => {
  const doc = await PDFDocument.create();
  const page = doc.addPage([595, 842]);
  const font = await doc.embedFont(StandardFonts.Helvetica);
  page.drawText('Study Partner sample', {
    x: 48,
    y: 780,
    size: 28,
    font,
    color: rgb(0.12, 0.28, 0.2),
  });
  await mkdir(path.dirname(fixture), { recursive: true });
  await writeFile(fixture, await doc.save());
});

async function stroke(page: Page, box: { x: number; y: number; width: number; height: number }): Promise<void> {
  const startX = box.x + box.width * 0.3;
  const startY = box.y + box.height * 0.45;
  const endX = box.x + box.width * 0.62;
  const endY = box.y + box.height * 0.62;
  await page.mouse.move(startX, startY);
  await page.mouse.down();
  await page.mouse.move(endX, endY, { steps: 8 });
  await page.mouse.up();
}

test('opens a PDF, draws, undoes, changes page, and saves ink', async ({ page }) => {
  await page.goto('/');
  await expect(page).toHaveTitle('Study Partner');
  const chooserPromise = page.waitForEvent('filechooser');
  await page.getByRole('button', { name: 'Open PDF' }).click();
  const chooser = await chooserPromise;
  await chooser.setFiles(fixture);

  const surface = page.getByTestId('ink-surface');
  await expect(surface).toHaveAttribute('data-ready', 'true');
  const box = await surface.boundingBox();
  if (!box) throw new Error('The page surface has no box');
  const ratios = { x0: 0.3, y0: 0.45, x1: 0.62, y1: 0.62 };
  expect(await darkPixels(page, ratios)).toBe(0);

  await stroke(page, box);
  await expect(page.getByTestId('history')).toHaveText('1 / 1');
  await page.getByRole('button', { name: 'Undo', exact: true }).click();
  await expect(page.getByTestId('history')).toHaveText('0 / 1');
  await page.getByRole('button', { name: 'Redo', exact: true }).click();
  await expect(page.getByTestId('history')).toHaveText('1 / 1');
  await page.getByRole('button', { name: 'Undo', exact: true }).click();
  await stroke(page, box);
  await expect(page.getByTestId('history')).toHaveText('1 / 1');
  expect(await darkPixels(page, ratios)).toBe(0);

  await page.getByRole('button', { name: 'Next page', exact: true }).click();
  await expect(page.getByTestId('page-number')).toHaveValue('2');
  await expect(surface).toHaveAttribute('data-ready', 'true');
  await expect(surface).toHaveAttribute('data-stroke-count', '0');
  await page.getByRole('button', { name: 'Previous page', exact: true }).click();
  await expect(page.getByTestId('page-number')).toHaveValue('1');
  await expect(surface).toHaveAttribute('data-stroke-count', '1');

  const downloadPromise = page.waitForEvent('download');
  await page.getByRole('button', { name: 'Save', exact: true }).click();
  const download = await downloadPromise;
  const savedPath = await download.path();
  if (!savedPath) throw new Error('Save did not produce a file');
  await expect(page.getByRole('status')).toContainText('Saved');
  await expect(surface).toHaveAttribute('data-stroke-count', '0');
  await expect(surface).toHaveAttribute('data-ready', 'true');
  expect(await darkPixels(page, ratios)).toBeGreaterThan(0);

  const ink = await listInkAnnotations(await readFile(savedPath));
  expect(ink).toHaveLength(1);

  const reopen = page.waitForEvent('filechooser');
  await page.getByRole('button', { name: 'Open PDF' }).click();
  await (await reopen).setFiles(savedPath);
  await expect(surface).toHaveAttribute('data-ready', 'true');
  await expect(surface).toHaveAttribute('data-stroke-count', '0');
  expect(await darkPixels(page, ratios)).toBeGreaterThan(0);
});

test('starts a new note and draws on the first page', async ({ page }) => {
  await page.goto('/');
  await page.getByRole('button', { name: 'New Note' }).click();
  const surface = page.getByTestId('ink-surface');
  await expect(surface).toHaveAttribute('data-ready', 'true');
  await expect(page.getByTestId('page-number')).toHaveValue('1');
  await expect(page.getByRole('status')).toHaveText('Untitled note');
  const box = await surface.boundingBox();
  if (!box) throw new Error('The page surface has no box');
  await stroke(page, box);
  await expect(page.getByTestId('history')).toHaveText('1 / 1');
  await expect(surface).toHaveAttribute('data-stroke-count', '1');
});
