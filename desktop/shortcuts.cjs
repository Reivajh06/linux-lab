const { app, shell } = require('electron');
const fs = require('node:fs');
const path = require('node:path');

function registerWindowsShortcuts(executable = process.execPath) {
  if (process.platform !== 'win32') return;
  const menu = path.join(app.getPath('appData'), 'Microsoft', 'Windows', 'Start Menu', 'Programs');
  fs.mkdirSync(menu, { recursive: true });
  const details = { target: executable, cwd: path.dirname(executable), icon: executable, iconIndex: 0,
    description: 'Linux Lab', appUserModelId: 'local.linuxlab.desktop' };
  shell.writeShortcutLink(path.join(menu, 'Linux Lab.lnk'), 'create', details);
  shell.writeShortcutLink(path.join(app.getPath('desktop'), 'Linux Lab.lnk'), 'create', details);
}

module.exports = { registerWindowsShortcuts };
if (require.main === module) {
  app.whenReady().then(() => { registerWindowsShortcuts(process.argv[2]); app.quit(); });
}
