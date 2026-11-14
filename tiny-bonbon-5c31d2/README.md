# Roblox archived page snapshots

This repository is a **read-only local archive** of captured Roblox pages, assets, and recorded API responses. It is not a live Roblox client: accounts, login, purchases, submissions, and current Roblox data require Roblox's own services and are not provided here.

## Run it

Requires Python 3.8+; no npm install or third-party packages are needed.

```bash
npm start
```

Or run directly with Python:

```bash
python3 serve.py
```

Open <http://localhost:3000/>. The server binds to `0.0.0.0` by default so it works in containers and hosted previews. Choose another port or bind address with `python3 serve.py --port 8080 --host 127.0.0.1`.

## Routes

The archive includes 101 captured HTML pages at the root. Both the original `.html` filenames and many familiar extensionless Roblox URLs are supported. For example:

- `/` and `/home` → archived Roblox landing page (`home.html`)
- `/catalog` → `catalog.html` (saved items can be searched by name/creator and sorted locally)
- `/upgrades/robux` → archived Robux page (`index.html`)
- `/charts/top-trending` → `charts-top-trending.html`
- `/charts/trending-in/action` → `charts-trending-in-action.html`
- `/de/charts/trending-in/rpg` → `de-charts-trending-in-rpg.html`

Captured local assets are served from `/assets/`. Unknown paths return 404; query strings are ignored for route selection and retained in the browser URL.

## API replay and limits

Captured GET responses are replayed locally by the page's offline fetch/XHR shim, using the recorded fixtures in the `assets/` directory. External connections are blocked by each snapshot's Content Security Policy. POST/mutation requests, authentication, and live API access are intentionally not emulated; no request reaches Roblox from this archive. Snapshots reflect their capture time and may not match current Roblox content.

## Checks

```bash
npm test          # route, server, static asset, and replay regression tests
npm run check     # validate local HTML src/href/poster/action references
npm run test:all  # run both checks
```

## Project notes

This is a static archive served by Python's standard library rather than a Node application. `package.json` provides convenient npm scripts only; there are no JavaScript runtime dependencies. The archive is large (about 200 MB); keep the `assets/` directory intact because pages depend on its captured scripts, styles, images, and API fixtures.
