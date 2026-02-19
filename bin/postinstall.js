#!/usr/bin/env node

/**
 * ClosedPaw - Auto-install after npm install -g closedpaw
 */

const { spawn } = require('child_process');
const path = require('path');

// Run closedpaw install automatically
const installer = spawn(process.execPath, [path.join(__dirname, 'closedpaw.js'), 'install'], {
  stdio: 'inherit',
  env: { ...process.env, CLOSEDPAW_AUTO_INSTALL: '1' }
});

installer.on('close', (code) => {
  process.exit(code || 0);
});
