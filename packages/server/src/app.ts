import { createServer, type IncomingMessage, type Server, type ServerResponse } from 'node:http';
import { existsSync, readFileSync, statSync } from 'node:fs';
import { extname, join, normalize, resolve, sep } from 'node:path';
import {
  AllFeaturesEntitled,
  isRecord,
  MemoryContextStore,
  SingleUserAuth,
  type AuthProvider,
  type ContextItem,
  type ContextStore,
  type EntitlementService,
  type FeatureFlag,
} from '@study-lens/core';

export interface ServerOptions {
  auth: AuthProvider;
  entitlements: EntitlementService;
  contexts: ContextStore;
  promptsFile: string;
  configFile: string | null;
  staticDir: string | null;
}

const MIME: Record<string, string> = {
  '.html': 'text/html; charset=utf-8',
  '.js': 'text/javascript; charset=utf-8',
  '.mjs': 'text/javascript; charset=utf-8',
  '.css': 'text/css; charset=utf-8',
  '.json': 'application/json; charset=utf-8',
  '.svg': 'image/svg+xml',
  '.png': 'image/png',
  '.jpg': 'image/jpeg',
  '.jpeg': 'image/jpeg',
  '.webp': 'image/webp',
  '.pdf': 'application/pdf',
  '.wasm': 'application/wasm',
  '.map': 'application/json',
  '.woff2': 'font/woff2',
  '.ico': 'image/x-icon',
};

export function defaultServerOptions(root: string): ServerOptions {
  return {
    auth: new SingleUserAuth(),
    entitlements: new AllFeaturesEntitled(),
    contexts: new MemoryContextStore(),
    promptsFile: join(root, 'prompts.json'),
    configFile: join(root, 'config.json'),
    staticDir: join(root, 'packages', 'web', 'dist'),
  };
}

export function createStudyServer(options: ServerOptions): Server {
  return createServer((request, response) => {
    void handle(request, response, options).catch((error: unknown) => {
      const message = error instanceof Error ? error.message : 'Server error';
      sendJson(response, 500, { message });
    });
  });
}

async function handle(request: IncomingMessage, response: ServerResponse, options: ServerOptions): Promise<void> {
  const url = new URL(request.url ?? '/', 'http://127.0.0.1');
  const method = request.method ?? 'GET';
  const accept = request.headers.accept ?? '';

  if (url.pathname === '/' && method === 'GET' && !prefersHtml(accept)) {
    sendJson(response, 200, { message: 'Study Partner Backend is running' });
    return;
  }

  if (url.pathname === '/context') {
    await handleContext(method, request, response, options);
    return;
  }

  if (url.pathname === '/prompts' && method === 'GET') {
    await handlePrompts(response, options);
    return;
  }

  if (url.pathname === '/prompts') {
    sendJson(response, 405, { message: 'Method not allowed' });
    return;
  }

  if (url.pathname === '/config.json' && method === 'GET' && options.configFile && existsSync(options.configFile)) {
    sendFile(response, options.configFile, 'application/json; charset=utf-8');
    return;
  }

  if (method !== 'GET' && method !== 'HEAD') {
    sendJson(response, 404, { message: 'Not found' });
    return;
  }

  if (options.staticDir && serveStatic(response, options.staticDir, url.pathname, method)) return;
  sendJson(response, 404, { message: 'Not found' });
}

async function handleContext(
  method: string,
  request: IncomingMessage,
  response: ServerResponse,
  options: ServerOptions,
): Promise<void> {
  const allowed = await authorize(response, options, 'context');
  if (!allowed) return;
  if (method === 'GET') {
    sendJson(response, 200, await options.contexts.list(allowed.userId));
    return;
  }
  if (method === 'POST') {
    let parsed: unknown;
    try {
      parsed = await readJson(request);
    } catch {
      sendJson(response, 400, { message: 'Context item requires type, content, and optional metadata' });
      return;
    }
    const item = parseContextItem(parsed);
    if (!item) {
      sendJson(response, 400, { message: 'Context item requires type, content, and optional metadata' });
      return;
    }
    await options.contexts.add(allowed.userId, item);
    sendJson(response, 200, { message: 'Context added' });
    return;
  }
  if (method === 'DELETE') {
    await options.contexts.clear(allowed.userId);
    sendJson(response, 200, { message: 'Context cleared' });
    return;
  }
  sendJson(response, 405, { message: 'Method not allowed' });
}

async function handlePrompts(response: ServerResponse, options: ServerOptions): Promise<void> {
  const allowed = await authorize(response, options, 'prompts');
  if (!allowed) return;
  if (!existsSync(options.promptsFile)) {
    sendJson(response, 200, {});
    return;
  }
  try {
    sendJson(response, 200, JSON.parse(readFileSync(options.promptsFile, 'utf8')) as unknown);
  } catch (error: unknown) {
    const message = error instanceof Error ? error.message : 'Could not read prompts';
    sendJson(response, 500, { message });
  }
}

async function authorize(
  response: ServerResponse,
  options: ServerOptions,
  flag: FeatureFlag,
): Promise<{ userId: string } | null> {
  const session = await options.auth.getSession();
  if (!session) {
    sendJson(response, 401, { message: 'Sign-in required' });
    return null;
  }
  if (!(await options.entitlements.isEnabled(flag, session))) {
    sendJson(response, 403, { message: 'Feature not included in this plan' });
    return null;
  }
  return session;
}

function parseContextItem(value: unknown): ContextItem | null {
  if (!isRecord(value)) return null;
  if (typeof value.type !== 'string' || value.type.length === 0) return null;
  if (typeof value.content !== 'string') return null;
  const metadata = value.metadata === undefined ? {} : value.metadata;
  if (!isRecord(metadata)) return null;
  return { type: value.type, content: value.content, metadata };
}

function explicitQuality(accept: string, mediaType: string): { q: number; index: number } | null {
  let best: { q: number; index: number } | null = null;
  const parts = accept.split(',');
  for (let index = 0; index < parts.length; index += 1) {
    const [rawName, ...params] = (parts[index] ?? '').split(';');
    if (rawName?.trim().toLowerCase() !== mediaType) continue;
    let q = 1;
    for (const param of params) {
      const separator = param.indexOf('=');
      if (separator === -1) continue;
      if (param.slice(0, separator).trim().toLowerCase() !== 'q') continue;
      const parsed = Number(param.slice(separator + 1).trim());
      q = Number.isFinite(parsed) ? Math.min(1, Math.max(0, parsed)) : 0;
    }
    if (!best || q > best.q) best = { q, index };
  }
  return best;
}

function prefersHtml(accept: string): boolean {
  const html = explicitQuality(accept, 'text/html');
  if (!html || html.q <= 0) return false;
  const json = explicitQuality(accept, 'application/json');
  if (!json || json.q <= 0) return true;
  if (html.q !== json.q) return html.q > json.q;
  return html.index < json.index;
}

function sendJson(response: ServerResponse, status: number, body: unknown): void {
  if (response.headersSent) return;
  const payload = JSON.stringify(body);
  response.writeHead(status, {
    'content-type': 'application/json; charset=utf-8',
    'content-length': Buffer.byteLength(payload),
    'x-content-type-options': 'nosniff',
  });
  response.end(payload);
}

async function readJson(request: IncomingMessage): Promise<unknown> {
  const raw = await readBody(request);
  if (raw.trim().length === 0) return null;
  return JSON.parse(raw) as unknown;
}

function readBody(request: IncomingMessage): Promise<string> {
  return new Promise((resolveBody, reject) => {
    const chunks: Buffer[] = [];
    let size = 0;
    request.on('data', (chunk: Buffer) => {
      size += chunk.length;
      if (size > 1_000_000) {
        reject(new Error('Body too large'));
        request.destroy();
        return;
      }
      chunks.push(chunk);
    });
    request.on('end', () => resolveBody(Buffer.concat(chunks).toString('utf8')));
    request.on('error', reject);
  });
}

function serveStatic(response: ServerResponse, root: string, pathname: string, method: string): boolean {
  let decoded: string;
  try {
    decoded = decodeURIComponent(pathname);
  } catch {
    return false;
  }
  const relative = decoded.replace(/^\/+/, '');
  const rootPath = resolve(root);
  const full = resolve(rootPath, normalize(relative.length === 0 ? 'index.html' : relative));
  if (full !== rootPath && !full.startsWith(rootPath + sep)) return false;
  const file = resolveFile(full, rootPath);
  if (!file) return false;
  const type = MIME[extname(file)] ?? 'application/octet-stream';
  const body = method === 'HEAD' ? undefined : readFileSync(file);
  response.writeHead(method === 'HEAD' ? 200 : 200, {
    'content-type': type,
    'content-length': statSync(file).size,
    'x-content-type-options': 'nosniff',
    'cache-control': extname(file) === '.html' ? 'no-cache' : 'public, max-age=3600',
  });
  response.end(body);
  return true;
}

function resolveFile(full: string, root: string): string | null {
  if (existsSync(full) && statSync(full).isFile()) return full;
  if (existsSync(full) && statSync(full).isDirectory()) {
    const index = join(full, 'index.html');
    if (existsSync(index)) return index;
  }
  if (extname(full).length > 0) return null;
  const index = join(root, 'index.html');
  return existsSync(index) ? index : null;
}

function sendFile(response: ServerResponse, file: string, type: string): void {
  const body = readFileSync(file);
  response.writeHead(200, {
    'content-type': type,
    'content-length': body.byteLength,
    'cache-control': 'no-cache',
    'x-content-type-options': 'nosniff',
  });
  response.end(body);
}
