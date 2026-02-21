const path = require('path');
const net = require('net');
const { spawn } = require('child_process');

const services = [
  { name: 'gateway', entry: 'services/gateway/server.js', envPortKey: 'GATEWAY_PORT', defaultPort: 4000 },
  { name: 'sales', entry: 'services/sales/server.js', envPortKey: 'SALES_SERVICE_PORT', defaultPort: 4001 },
  { name: 'catalog', entry: 'services/catalog/server.js', envPortKey: 'CATALOG_SERVICE_PORT', defaultPort: 4002 },
  { name: 'suppliers', entry: 'services/suppliers/server.js', envPortKey: 'SUPPLIERS_SERVICE_PORT', defaultPort: 4004 },
  { name: 'customers', entry: 'services/customers/server.js', envPortKey: 'CUSTOMERS_SERVICE_PORT', defaultPort: 4003 },
];

const apiRoot = path.resolve(__dirname, '..');
const children = [];
let shuttingDown = false;

function log(name, message) {
  process.stdout.write(`[${name}] ${message}`);
}

function getServicePort(service) {
  const raw = process.env[service.envPortKey];
  const parsed = Number(raw);
  return Number.isFinite(parsed) && parsed > 0 ? parsed : service.defaultPort;
}

function isPortInUse(port) {
  return new Promise((resolve) => {
    const socket = new net.Socket();
    socket.setTimeout(700);

    socket.once('connect', () => {
      socket.destroy();
      resolve(true);
    });

    socket.once('timeout', () => {
      socket.destroy();
      resolve(false);
    });

    socket.once('error', (error) => {
      if (error.code === 'ECONNREFUSED' || error.code === 'EHOSTUNREACH') {
        resolve(false);
        return;
      }
      resolve(true);
    });

    socket.connect(port, '127.0.0.1');
  });
}

async function verifyPortsAvailable() {
  const blocked = [];

  for (const service of services) {
    const port = getServicePort(service);
    const inUse = await isPortInUse(port);
    if (inUse) {
      blocked.push({ name: service.name, port, envPortKey: service.envPortKey });
    }
  }

  if (blocked.length === 0) {
    return true;
  }

  process.stderr.write('[start-all] Port conflict detected.\n');
  for (const item of blocked) {
    process.stderr.write(`- ${item.name}: port ${item.port} already in use (env: ${item.envPortKey}).\n`);
  }
  process.stderr.write('Close existing processes or change ports in your environment before running start:all.\n');
  process.stderr.write('Windows help: netstat -ano | findstr :<PORT> then taskkill /PID <PID> /F\n');
  return false;
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

async function startAll() {
  const ok = await verifyPortsAvailable();
  if (!ok) {
    process.exit(1);
    return;
  }

  for (const service of services) {
    const child = spawn(process.execPath, [service.entry], {
      cwd: apiRoot,
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
}

process.on('SIGINT', () => stopAll(0));
process.on('SIGTERM', () => stopAll(0));

startAll().catch((error) => {
  process.stderr.write(`[start-all] Unexpected startup error: ${error.message}\n`);
  process.exit(1);
});
