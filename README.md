# Study Partner

StudyLens is a PDF annotation app. The window is titled **Study Partner**. One TypeScript codebase ships a self-hosted web app and a desktop app with the same ink tools.

The previous PyQt6 app is frozen in [`legacy/`](legacy/README.md).

## Architecture

| Path | Role |
| --- | --- |
| `packages/core` | Ink, undo, lasso, page cache, PDF writing, config, and the auth/storage interfaces |
| `packages/web` | React + Vite interface |
| `packages/server` | Node API plus the static web build |
| `packages/desktop` | Tauri shell around the same interface |
| `config.json` | Which toolbar modules and gestures are on, ordered by priority |
| `prompts.json` | Prompt text served by `GET /prompts` |

pdf.js (Apache-2.0) rasterizes pages. pdf-lib (MIT) writes unsaved strokes back as PDF ink annotations and pastes images into the page. Scene coordinates are the PDF point size times a render scale of 2. Stroke width stored in the annotation is the pen width divided by that scale. Pen pressure changes the on-screen width only. A mouse has no pressure sensor, so it draws at the full pen width. A tap is saved as a dot.

Touch pans, pinches to zoom, and swipes left or right to change pages. A pen tip draws with the pencil. The stylus eraser end switches to the eraser, and the barrel or right button switches to the lasso. A mouse uses the Pencil, Eraser, and Lasso buttons; the right button lassos for that stroke. The wheel zooms. Space-drag or the middle button pans.

`config.json` accepts the module and gesture ids, and it still accepts the old Python file paths from `legacy/config.json`.

## Auth and billing seams

There is no account system and no billing. These interfaces are the places a later multi-user free tier and bundle subscription would plug in:

- `AuthProvider` (`SingleUserAuth` always returns the local user)
- `EntitlementService` (`AllFeaturesEntitled` enables `annotations`, `context`, and `prompts`)
- `ContextStore` and `DocumentStore` (in-memory, keyed by user id)

The API asks the auth provider and the entitlement service before `/context` and `/prompts`. A missing session is 401. A disabled feature is 403. The defaults never do that.

## Dev setup

Node.js 22 or newer.

```sh
npm ci
npm run dev
```

The web app is at <http://localhost:5173> and the API is at <http://127.0.0.1:8787>. Vite proxies `/context`, `/prompts`, and `/config.json` to the API.

## Web build and self-hosting

```sh
npm run build
PORT=8080 npm start
```

Or with Docker, which is the intended self-host shape behind a reverse proxy or tunnel:

```sh
docker build -t study-partner .
docker run --rm -p 8080:8080 study-partner
```

`GET /` returns the app to browsers (`Accept: text/html`) and `{ "message": "Study Partner Backend is running" }` to API clients. The other routes are:

- `GET /context`, `POST /context`, `DELETE /context` with items `{ type, content, metadata }`
- `GET /prompts`, which reads `prompts.json`
- `GET /config.json`

On the web, Open uses the browser file picker and Save downloads the PDF. The desktop shell writes through native dialogs instead.

## Desktop build

Install a Rust stable toolchain, then:

```sh
npm run dev -w @study-lens/desktop    # webview pointed at the Vite server
npm run build -w @study-lens/desktop  # OS bundle
npm run desktop:build                 # compile the Linux binary without packaging
npm run desktop:build:macos           # compile the macOS binary without packaging
npm run desktop:build:windows         # compile the Windows binary without packaging
```

Linux also needs the Tauri system libraries: `libwebkit2gtk-4.1-dev`, `build-essential`, `libssl-dev`, `libayatana-appindicator3-dev`, `librsvg2-dev`, and `patchelf`. macOS needs Xcode command line tools. Windows needs the Microsoft C++ build tools and WebView2. CI compiles the Linux, macOS, and Windows binaries with `--no-bundle`.

The desktop shell links the operating system webview. On Linux that is WebKitGTK, which is LGPL and is not vendored. JavaScript dependencies are checked in CI and must not be GPL or AGPL.

## Tests

```sh
npm test                 # unit tests
npm run e2e              # build, then Playwright smoke test
npm run check-licenses   # fail on GPL/AGPL npm packages
npm run lint
npm run typecheck
```

Unit tests cover undo/redo, eraser hit testing, lasso move, the page cache, ink save and reload (including taps and multi-page saves), config and page-number parsing, pointer pressure, and the API routes. Reopening a saved PDF loads its ink into the page model, with the annotations removed from the working file, so the eraser and lasso can edit those strokes and the next save writes the edit once. The smoke tests open a sample PDF, draw, undo, redo, change page, save, and check that reloaded ink can be erased or moved and saved again.

## License

MIT. See [LICENSE](LICENSE).
