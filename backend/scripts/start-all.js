const path = require('path');
const { spawn } = require('child_process');

const services = [
  { name: 'gateway', entry: 'services/gateway/server.js' },
  { name: 'sales', entry: 'services/sales/server.js' },
  { name: 'catalog', entry: 'services/catalog/server.js' },
  { name: 'suppliers', entry: 'services/suppliers/server.js' },
  { name: 'customers', entry: 'services/customers/server.js' },
];

const backendRoot = path.resolve(__dirname, '..');
const children = [];
let shuttingDown = false;

function log(name, message) {
  process.stdout.write(`[${name}] ${message}`);
}

function stopAll(exitCode = 0) {
  if (shuttingDown) return;
  shuttingDown = true;

  for (const child of children) {
    if (!child.killed) {
      child.kill('SIGTERM');
    }
  }

  setTimeout(() => process.exit(exitCode), 1000);
}

for (const service of services) {
  const child = spawn(process.execPath, [service.entry], {
    cwd: backendRoot,
    stdio: ['ignore', 'pipe', 'pipe'],
    shell: false,
    windowsHide: true,
  });

  child.on('error', (error) => {
    log(service.name, `failed to start: ${error.message}\n`);
    if (!shuttingDown) {
      stopAll(1);
    }
  });

  child.stdout.on('data', (data) => log(service.name, data.toString()));
  child.stderr.on('data', (data) => log(service.name, data.toString()));

  child.on('exit', (code) => {
    log(service.name, `process exited with code ${code}\n`);
    if (!shuttingDown && code !== 0) {
      stopAll(code || 1);
    }
  });

  children.push(child);
}

process.on('SIGINT', () => stopAll(0));
process.on('SIGTERM', () => stopAll(0));
