const { app, BrowserWindow, dialog, shell, Menu, nativeTheme } = require('electron');
const { spawn } = require('node:child_process');
const { createServer } = require('node:net');
const { randomBytes } = require('node:crypto');
const fs = require('node:fs');
const path = require('node:path');
const { registerWindowsShortcuts } = require('./shortcuts.cjs');

let backend, window, origin;
const root = app.isPackaged ? process.resourcesPath : path.resolve(__dirname, '..');
app.setName('Linux Lab');
app.setAppUserModelId('local.linuxlab.desktop');
nativeTheme.themeSource = 'dark';

async function unusedPort() {
  return new Promise((resolve, reject) => {
    const server = createServer();
    server.once('error', reject);
    server.listen(0, '127.0.0.1', () => {
      const port = server.address().port;
      server.close(() => resolve(port));
    });
  });
}

function preferences() {
  return { sandbox: true, contextIsolation: true, nodeIntegration: false, webSecurity: true };
}

function protect(win) {
  win.webContents.on('will-navigate', (event, url) => {
    if (new URL(url).origin !== origin) event.preventDefault();
  });
  win.webContents.setWindowOpenHandler(({ url }) => {
    const target = new URL(url);
    if (target.origin === origin) {
      const viewer = new BrowserWindow({ width: 1000, height: 800, parent: window, autoHideMenuBar: true, webPreferences: preferences() });
      protect(viewer);
      viewer.loadURL(url);
    } else if (target.protocol === 'https:') {
      shell.openExternal(url);
    }
    return { action: 'deny' };
  });
  win.webContents.session.setPermissionRequestHandler((_contents, permission, callback) => {
    callback(permission === 'clipboard-sanitized-write');
  });
}

async function boot() {
  if (app.isPackaged) registerWindowsShortcuts();
  const dataDir = path.join(process.env.LOCALAPPDATA || app.getPath('userData'), 'LinuxLab');
  fs.mkdirSync(path.join(dataDir, 'logs'), { recursive: true });
  const logfile = fs.createWriteStream(path.join(dataDir, 'logs', 'backend.log'), { flags: 'w' });
  const port = await unusedPort();
  const nonce = randomBytes(24).toString('hex');
  origin = `http://127.0.0.1:${port}`;
  const executable = app.isPackaged
    ? path.join(root, 'backend', 'linux-lab-server.exe')
    : path.join(root, '.venv', 'Scripts', 'python.exe');
  const args = app.isPackaged ? [] : [path.join(root, 'backend', 'desktop_server.py')];
  args.push('--port', String(port));
  backend = spawn(executable, args, {
    cwd: root, windowsHide: true,
    env: { ...process.env, LAB_DATA_DIR: dataDir, LAB_RESOURCE_DIR: root,
      LAB_HOST_RUNTIME: '1', LAB_DESKTOP_NONCE: nonce,
      OLLAMA_BASE_URL: process.env.OLLAMA_BASE_URL || 'http://127.0.0.1:11434' },
    stdio: ['ignore', 'pipe', 'pipe']
  });
  let bootError = null;
  backend.on('error', error => { bootError = error; });
  backend.stdout.pipe(logfile, { end: false });
  backend.stderr.pipe(logfile, { end: false });
  backend.on('exit', code => {
    if (window && !app.isQuitting) {
      dialog.showErrorBox('Linux Lab stopped', `The local service exited (${code}). Reopen the app. Details: ${path.join(dataDir, 'logs', 'backend.log')}`);
      app.quit();
    }
  });
  let ready = false;
  for (let attempt = 0; attempt < 120; attempt++) {
    if (bootError) throw bootError;
    if (backend.exitCode !== null) throw new Error(`Local service exited. See ${path.join(dataDir, 'logs', 'backend.log')}`);
    try {
      const response = await fetch(origin + '/api/desktop/ready', { signal: AbortSignal.timeout(1000) });
      ready = (await response.json()).nonce === nonce;
      if (ready) break;
    } catch {}
    await new Promise(resolve => setTimeout(resolve, 250));
  }
  if (!ready) throw new Error(`Local service did not start. See ${path.join(dataDir, 'logs', 'backend.log')}`);
  window = new BrowserWindow({ title: 'Linux Lab', width: 1440, height: 960,
    minWidth: 1000, minHeight: 700, backgroundColor: '#191919', show: false, skipTaskbar: false, icon: path.join(__dirname, 'icon.ico'),
    autoHideMenuBar: true, webPreferences: preferences() });
  protect(window);
  if (process.platform === 'win32' && app.isPackaged) window.setAppDetails({
    appId: 'local.linuxlab.desktop', appIconPath: process.execPath, appIconIndex: 0,
    relaunchCommand: `"${process.execPath}"`, relaunchDisplayName: 'Linux Lab'
  });
  Menu.setApplicationMenu(Menu.buildFromTemplate([
    { label: 'File', submenu: [{ label: 'Open data folder', click: () => shell.openPath(dataDir) }, { type: 'separator' }, { role: 'quit' }] },
    { label: 'Edit', submenu: [{ role: 'undo' }, { role: 'redo' }, { type: 'separator' }, { role: 'cut' }, { role: 'copy' }, { role: 'paste' }, { role: 'selectAll' }] },
    { label: 'View', submenu: [{ role: 'reload' }, { role: 'resetZoom' }, { role: 'zoomIn' }, { role: 'zoomOut' }, { role: 'togglefullscreen' }] },
    { label: 'Help', submenu: [{ label: 'Exercise format', click: () => { const help = new BrowserWindow({ width: 900, height: 800, webPreferences: preferences() }); protect(help); help.loadURL(origin + '/api/docs/exercise-format'); } }] }
  ]));
  window.once('ready-to-show', () => window.show());
  await window.loadURL(origin);
}

if (!app.requestSingleInstanceLock()) app.quit();
else {
  app.on('second-instance', () => { if (window) { if (window.isMinimized()) window.restore(); window.show(); window.focus(); } });
  app.whenReady().then(boot).catch(error => { dialog.showErrorBox('Could not open Linux Lab', String(error.message || error)); app.quit(); });
  app.on('window-all-closed', () => app.quit());
  app.on('before-quit', () => { app.isQuitting = true; if (backend) backend.kill(); });
}
