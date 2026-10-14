import { execFileSync } from 'node:child_process';
import { existsSync, readdirSync, readFileSync, realpathSync } from 'node:fs';
import { join } from 'node:path';
import process from 'node:process';

const offenders = [];

function splitTop(expression, keyword) {
  const parts = [];
  let current = '';
  let depth = 0;
  let index = 0;
  const upper = expression.toUpperCase();
  const needle = ` ${keyword} `;
  while (index < expression.length) {
    const char = expression[index];
    if (char === '(') depth += 1;
    if (char === ')') depth = Math.max(0, depth - 1);
    if (depth === 0 && upper.startsWith(needle, index)) {
      parts.push(current.trim());
      current = '';
      index += needle.length;
      continue;
    }
    current += char;
    index += 1;
  }
  if (current.trim()) parts.push(current.trim());
  return parts;
}

function isForbidden(expression) {
  const text = expression.trim();
  if (!text) return false;
  const orParts = splitTop(text, 'OR');
  if (orParts.length > 1) return orParts.every(isForbidden);
  const andParts = splitTop(text, 'AND');
  if (andParts.length > 1) return andParts.some(isForbidden);
  const token = text.replace(/[()]/g, '').trim();
  if (!token || token.toUpperCase() === 'UNLICENSED') return false;
  return /(?<!L)GPL|AGPL/i.test(token);
}

function licenseText(license) {
  if (!license) return '';
  if (typeof license === 'string') return license;
  if (Array.isArray(license)) return license.map((entry) => licenseText(entry)).filter(Boolean).join(' OR ');
  if (typeof license === 'object' && license && typeof license.type === 'string') return license.type;
  return '';
}

function visitPackage(directory, seen) {
  const manifestPath = join(directory, 'package.json');
  if (!existsSync(manifestPath)) return;
  let real = directory;
  try {
    real = realpathSync(directory);
  } catch {
    return;
  }
  if (seen.has(real)) return;
  seen.add(real);
  const manifest = JSON.parse(readFileSync(manifestPath, 'utf8'));
  const license = licenseText(manifest.license);
  if (license && isForbidden(license)) {
    offenders.push(`${manifest.name}@${manifest.version ?? '0'} ${license}`);
  }
  visitNodeModules(join(directory, 'node_modules'), seen);
}

function visitNodeModules(directory, seen) {
  if (!existsSync(directory)) return;
  for (const entry of readdirSync(directory, { withFileTypes: true })) {
    if (entry.name.startsWith('.')) continue;
    const full = join(directory, entry.name);
    if (entry.name.startsWith('@')) {
      for (const scoped of readdirSync(full, { withFileTypes: true })) {
        if (scoped.name.startsWith('.')) continue;
        visitPackage(join(full, scoped.name), seen);
      }
      continue;
    }
    visitPackage(full, seen);
  }
}

const seen = new Set();
visitNodeModules(join(process.cwd(), 'node_modules'), seen);

const cargoFlag = process.argv.indexOf('--cargo');
if (cargoFlag !== -1) {
  const cargoDir = process.argv[cargoFlag + 1];
  if (!cargoDir) {
    process.stderr.write('check-licenses: --cargo needs a directory\n');
    process.exit(1);
  }
  const metadata = execFileSync('cargo', ['metadata', '--format-version', '1'], {
    cwd: cargoDir,
    encoding: 'utf8',
    maxBuffer: 64 * 1024 * 1024,
    stdio: ['ignore', 'pipe', 'inherit'],
  });
  const parsed = JSON.parse(metadata);
  for (const pkg of parsed.packages) {
    const license = typeof pkg.license === 'string' ? pkg.license : '';
    if (license && isForbidden(license)) offenders.push(`cargo ${pkg.name}@${pkg.version} ${license}`);
  }
}

if (offenders.length > 0) {
  process.stderr.write(`GPL/AGPL dependencies are not allowed:\n${offenders.join('\n')}\n`);
  process.exit(1);
}

const cargoNote = cargoFlag === -1 ? '' : ' Cargo metadata included.';
process.stdout.write(`License check passed (${seen.size} npm packages).${cargoNote}\n`);
