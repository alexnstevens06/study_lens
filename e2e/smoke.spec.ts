import { mkdir, readFile, writeFile } from 'node:fs/promises';
import path from 'node:path';
import { PDFDocument, StandardFonts, rgb } from 'pdf-lib';
import { expect, test } from '@playwright/test';
import { listInkAnnotations } from '../packages/core/dist/index.js';

const fixture = path.join(process.cwd(), 'e2e', 'fixtures', 'sample.pdf');

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

test('opens a PDF, draws, undoes, and saves ink', async ({ page }) => {
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
  const startX = box.x + box.width * 0.35;
  const startY = box.y + box.height * 0.4;
  await page.mouse.move(startX, startY);
  await page.mouse.down();
  await page.mouse.move(startX + 120, startY + 70, { steps: 8 });
  await page.mouse.up();

  await expect(page.getByTestId('history')).toHaveText('1 / 1');
  await page.getByRole('button', { name: 'Undo', exact: true }).click();
  await expect(page.getByTestId('history')).toHaveText('0 / 1');

  await page.mouse.move(startX, startY + 30);
  await page.mouse.down();
  await page.mouse.move(startX + 140, startY + 90, { steps: 8 });
  await page.mouse.up();
  await expect(page.getByTestId('history')).toHaveText('1 / 1');

  const downloadPromise = page.waitForEvent('download');
  await page.getByRole('button', { name: 'Save', exact: true }).click();
  const download = await downloadPromise;
  const savedPath = await download.path();
  if (!savedPath) throw new Error('Save did not produce a file');
  const ink = await listInkAnnotations(await readFile(savedPath));
  expect(ink).toHaveLength(1);
});
