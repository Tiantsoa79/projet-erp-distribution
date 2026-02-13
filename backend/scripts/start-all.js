const { spawn } = require('child_process');

const services = [
  { name: 'gateway', script: 'gateway:start' },
  { name: 'sales', script: 'sales:start' },
  { name: 'catalog', script: 'catalog:start' },
  { name: 'suppliers', script: 'suppliers:start' },
  { name: 'customers', script: 'customers:start' },
];

const npmCommand = process.platform === 'win32' ? 'npm.cmd' : 'npm';
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
      child.kill('SIGINT');
    }
  }

  setTimeout(() => process.exit(exitCode), 400);
}

for (const service of services) {
  const child = spawn(npmCommand, ['run', service.script], {
    stdio: ['ignore', 'pipe', 'pipe'],
    shell: false,
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
