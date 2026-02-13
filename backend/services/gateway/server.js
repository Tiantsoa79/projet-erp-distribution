const express = require('express');
const cookieParser = require('cookie-parser');
const jwt = require('jsonwebtoken');
const { randomUUID } = require('crypto');

require('dotenv').config();

const app = express();
app.use(express.json());
app.use(cookieParser());

const GATEWAY_PORT = Number(process.env.GATEWAY_PORT || 4000);
const JWT_SECRET = process.env.GATEWAY_JWT_SECRET || 'change_me';
const SESSION_COOKIE_NAME = process.env.SESSION_COOKIE_NAME || 'erp_session';
const COOKIE_SECURE = (process.env.SESSION_COOKIE_SECURE || 'false').toLowerCase() === 'true';

const ADMIN_USER = process.env.ADMIN_USER || 'admin';
const ADMIN_PASSWORD = process.env.ADMIN_PASSWORD || 'admin123';

const SERVICE_URLS = {
  sales: process.env.SALES_SERVICE_URL || 'http://localhost:4001',
  catalog: process.env.CATALOG_SERVICE_URL || 'http://localhost:4002',
  customers: process.env.CUSTOMERS_SERVICE_URL || 'http://localhost:4003',
  suppliers: process.env.SUPPLIERS_SERVICE_URL || 'http://localhost:4004',
};

function readToken(req) {
  const fromCookie = req.cookies[SESSION_COOKIE_NAME];
  if (fromCookie) return fromCookie;

  const header = req.headers.authorization || '';
  if (header.startsWith('Bearer ')) return header.slice(7);
  return null;
}

function requireAuth(req, res, next) {
  const token = readToken(req);
  if (!token) {
    return res.status(401).json({ code: 'UNAUTHORIZED', message: 'Authentication required' });
  }

  try {
    const payload = jwt.verify(token, JWT_SECRET);
    req.user = payload;
    return next();
  } catch (error) {
    return res.status(401).json({ code: 'INVALID_TOKEN', message: error.message });
  }
}

function requestContext(req, _res, next) {
  req.requestId = randomUUID();
  next();
}

async function forwardRequest(req, res, serviceUrl, gatewayPrefix, upstreamBasePath = '') {
  const pathAfterPrefix = req.originalUrl.replace(gatewayPrefix, '') || '/';
  const normalizedBasePath = upstreamBasePath.endsWith('/')
    ? upstreamBasePath.slice(0, -1)
    : upstreamBasePath;
  const targetUrl = `${serviceUrl}${normalizedBasePath}${pathAfterPrefix}`;

  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 15000);

  try {
    const headers = {
      'x-request-id': req.requestId,
      'x-gateway-user': req.user?.sub || 'anonymous',
    };

    if (req.headers['content-type']) {
      headers['content-type'] = req.headers['content-type'];
    }

    const canHaveBody = !['GET', 'HEAD'].includes(req.method.toUpperCase());
    const options = {
      method: req.method,
      headers,
      signal: controller.signal,
    };

    if (canHaveBody && Object.keys(req.body || {}).length > 0) {
      options.body = JSON.stringify(req.body);
    }

    const response = await fetch(targetUrl, options);
    const contentType = response.headers.get('content-type') || 'application/json';
    const raw = await response.text();

    res.status(response.status);
    res.setHeader('content-type', contentType);
    return res.send(raw);
  } catch (error) {
    return res.status(502).json({
      code: 'UPSTREAM_ERROR',
      message: `Unable to reach upstream service: ${error.message}`,
      requestId: req.requestId,
    });
  } finally {
    clearTimeout(timeout);
  }
}

app.use(requestContext);

app.get('/health', (_req, res) => {
  res.status(200).json({ service: 'gateway', status: 'ok' });
});

app.post('/api/v1/auth/login', (req, res) => {
  const { username, password } = req.body;

  if (!username || !password) {
    return res.status(400).json({ code: 'BAD_REQUEST', message: 'username and password are required' });
  }

  if (username !== ADMIN_USER || password !== ADMIN_PASSWORD) {
    return res.status(401).json({ code: 'INVALID_CREDENTIALS', message: 'Invalid credentials' });
  }

  const token = jwt.sign({ sub: username, role: 'admin' }, JWT_SECRET, { expiresIn: '8h' });

  res.cookie(SESSION_COOKIE_NAME, token, {
    httpOnly: true,
    sameSite: 'lax',
    secure: COOKIE_SECURE,
    maxAge: 8 * 60 * 60 * 1000,
  });

  return res.status(200).json({
    message: 'Login successful',
    token,
    token_type: 'Bearer',
    expires_in: 28800,
  });
});

app.post('/api/v1/auth/logout', (_req, res) => {
  res.clearCookie(SESSION_COOKIE_NAME);
  return res.status(200).json({ message: 'Logout successful' });
});

app.get('/api/v1/auth/me', requireAuth, (req, res) => {
  res.status(200).json({ user: req.user });
});

app.use('/api/v1', requireAuth);

app.use('/api/v1/sales', (req, res) => forwardRequest(req, res, SERVICE_URLS.sales, '/api/v1/sales'));
app.use('/api/v1/catalog', (req, res) => forwardRequest(req, res, SERVICE_URLS.catalog, '/api/v1/catalog'));
app.use('/api/v1/customers', (req, res) =>
  forwardRequest(req, res, SERVICE_URLS.customers, '/api/v1/customers', '/customers')
);
app.use('/api/v1/suppliers', (req, res) =>
  forwardRequest(req, res, SERVICE_URLS.suppliers, '/api/v1/suppliers', '/suppliers')
);

app.use((_req, res) => {
  res.status(404).json({ code: 'NOT_FOUND', message: 'Route not found' });
});

app.listen(GATEWAY_PORT, () => {
  console.log(`Gateway running on port ${GATEWAY_PORT}`);
});
