import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { createStudyServer, defaultServerOptions } from './app.js';

const here = dirname(fileURLToPath(import.meta.url));
const root = join(here, '../../..');
const port = Number(process.env.PORT ?? 8787);
const host = process.env.HOST ?? '0.0.0.0';

const server = createStudyServer(defaultServerOptions(root));
server.listen(port, host, () => {
  process.stdout.write(`Study Partner listening on http://${host}:${port}\n`);
});
