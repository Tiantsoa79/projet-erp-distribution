const express = require('express');
const cookieParser = require('cookie-parser');
const jwt = require('jsonwebtoken');
const { randomUUID } = require('crypto');
const { pool } = require('../../database/connection');
const { hashPassword, verifyPassword } = require('../../utils/password');
const { recordAudit } = require('../../utils/audit');

require('dotenv').config();

// In-memory token blacklist for development (fallback)
const tokenBlacklist = new Set();

const app = express();
app.use(express.json());
app.use(cookieParser());

const GATEWAY_PORT = Number(process.env.GATEWAY_PORT || 4000);
const JWT_SECRET = process.env.GATEWAY_JWT_SECRET || 'dev_only_insecure_secret';
const JWT_EXPIRES_IN = process.env.GATEWAY_JWT_EXPIRES_IN || '8h';
const SESSION_COOKIE_NAME = process.env.SESSION_COOKIE_NAME || 'erp_session';
const COOKIE_SECURE = (process.env.SESSION_COOKIE_SECURE || 'false').toLowerCase() === 'true';

const hasWeakJwtSecret =
  !JWT_SECRET
  || JWT_SECRET === 'change_me'
  || JWT_SECRET === 'change_me_gateway'
  || JWT_SECRET === 'dev_only_insecure_secret'
  || JWT_SECRET.length < 16;

if (hasWeakJwtSecret) {
  if ((process.env.NODE_ENV || 'development') === 'production') {
    throw new Error('GATEWAY_JWT_SECRET must be set with at least 16 characters in production.');
  }
  console.warn('[gateway] Weak or missing GATEWAY_JWT_SECRET detected (dev mode only).');
}

const SERVICE_URLS = {
  sales: process.env.SALES_SERVICE_URL || 'http://localhost:4001',
  catalog: process.env.CATALOG_SERVICE_URL || 'http://localhost:4002',
  customers: process.env.CUSTOMERS_SERVICE_URL || 'http://localhost:4003',
  suppliers: process.env.SUPPLIERS_SERVICE_URL || 'http://localhost:4004',
};

// Token blacklist functions
async function addToBlacklist(token) {
  try {
    const decoded = jwt.decode(token);
    if (!decoded || !decoded.jti) return false;

    await pool.query(
      'INSERT INTO token_blacklist (token_jti, user_id, expires_at) VALUES ($1, $2, $3) ON CONFLICT (token_jti) DO NOTHING',
      [decoded.jti, decoded.user_id, new Date(decoded.exp * 1000)]
    );
    
    // Cleanup expired tokens periodically
    await pool.query('SELECT cleanup_expired_blacklisted_tokens()');
    return true;
  } catch (error) {
    console.warn('Failed to add token to blacklist (using fallback):', error.message);
    // Fallback to in-memory blacklist
    tokenBlacklist.add(token);
    return false;
  }
}

async function isTokenBlacklisted(token) {
  try {
    const decoded = jwt.decode(token);
    if (!decoded || !decoded.jti) return false;

    const result = await pool.query(
      'SELECT 1 FROM token_blacklist WHERE token_jti = $1 AND expires_at > CURRENT_TIMESTAMP',
      [decoded.jti]
    );
    
    return result.rowCount > 0;
  } catch (error) {
    console.warn('Failed to check blacklist (using fallback):', error.message);
    // Fallback to in-memory blacklist
    return tokenBlacklist.has(token);
  }
}

function readToken(req) {
  const fromCookie = req.cookies[SESSION_COOKIE_NAME];
  if (fromCookie) return fromCookie;

  const header = req.headers.authorization || '';
  if (header.startsWith('Bearer ')) return header.slice(7);
  return null;
}

// Token versioning approach (plus professionnel)
async function logoutByTokenVersion(userId) {
  await pool.query(
    'UPDATE users SET token_version = token_version + 1 WHERE user_id = $1',
    [userId]
  );
}

async function requireAuth(req, res, next) {
  const token = readToken(req);
  if (!token) {
    return res.status(401).json({ code: 'UNAUTHORIZED', message: 'Authentication required' });
  }

  try {
    const payload = jwt.verify(token, JWT_SECRET);
    
    // Vérifier la version du token
    const userResult = await pool.query(
      'SELECT token_version FROM users WHERE user_id = $1',
      [payload.user_id]
    );
    
    if (userResult.rowCount === 0) {
      return res.status(401).json({ code: 'USER_NOT_FOUND', message: 'User not found' });
    }
    
    const currentTokenVersion = userResult.rows[0].token_version || 0;
    if (payload.token_version !== currentTokenVersion) {
      return res.status(401).json({ code: 'TOKEN_REVOKED', message: 'Token has been revoked' });
    }
    req.user = payload;
    return next();
  } catch (error) {
    return res.status(401).json({ code: 'INVALID_TOKEN', message: error.message });
  }
}

function requirePermission(permissionCode) {
  return (req, res, next) => {
    if (!req.user) {
      return res.status(401).json({ code: 'UNAUTHORIZED', message: 'Authentication required' });
    }

    const grantedPermissions = req.user.permissions || [];
    if (!grantedPermissions.includes(permissionCode)) {
      return res.status(403).json({
        code: 'FORBIDDEN',
        message: `Missing permission: ${permissionCode}`,
      });
    }

    return next();
  };
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
      'x-gateway-user': req.user?.username || 'anonymous',
      'x-gateway-user-id': String(req.user?.user_id || ''),
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

app.post('/api/v1/auth/login', async (req, res) => {
  const { username, password } = req.body;

  if (!username || !password) {
    return res.status(400).json({ code: 'BAD_REQUEST', message: 'username and password are required' });
  }

  try {
    const userResult = await pool.query(
      `
      SELECT user_id, username, password_hash, full_name, is_active
      FROM users
      WHERE username = $1
      `,
      [username]
    );

    if (userResult.rowCount === 0) {
      return res.status(401).json({ code: 'INVALID_CREDENTIALS', message: 'Invalid credentials' });
    }

    const user = userResult.rows[0];
    if (!user.is_active) {
      return res.status(403).json({ code: 'USER_DISABLED', message: 'User is inactive' });
    }

    const validPassword = verifyPassword(password, user.password_hash);
    if (!validPassword) {
      return res.status(401).json({ code: 'INVALID_CREDENTIALS', message: 'Invalid credentials' });
    }

    const accessResult = await pool.query(
      `
      SELECT
        COALESCE(array_agg(DISTINCT r.role_code) FILTER (WHERE r.role_code IS NOT NULL), '{}') AS roles,
        COALESCE(array_agg(DISTINCT p.permission_code) FILTER (WHERE p.permission_code IS NOT NULL), '{}') AS permissions
      FROM users u
      LEFT JOIN user_roles ur ON ur.user_id = u.user_id
      LEFT JOIN roles r ON r.role_id = ur.role_id
      LEFT JOIN role_permissions rp ON rp.role_id = r.role_id
      LEFT JOIN permissions p ON p.permission_id = rp.permission_id
      WHERE u.user_id = $1
      `,
      [user.user_id]
    );

    const roles = accessResult.rows[0]?.roles || [];
    const permissions = accessResult.rows[0]?.permissions || [];

    // Récupérer la version actuelle du token
    const userVersionResult = await pool.query(
      'SELECT token_version FROM users WHERE user_id = $1',
      [user.user_id]
    );
    
    const currentTokenVersion = userVersionResult.rows[0]?.token_version || 0;

    const token = jwt.sign(
      {
        user_id: user.user_id,
        username: user.username,
        full_name: user.full_name,
        roles,
        permissions,
        token_version: currentTokenVersion, // Inclure la version dans le token
      },
      JWT_SECRET,
      { expiresIn: JWT_EXPIRES_IN }
    );

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
      user: {
        user_id: user.user_id,
        username: user.username,
        full_name: user.full_name,
        roles,
        permissions,
      },
    });
  } catch (error) {
    return res.status(500).json({ code: 'AUTH_ERROR', message: error.message });
  }
});

app.post('/api/v1/auth/logout', async (req, res) => {
  try {
    const token = readToken(req);
    if (token) {
      const payload = jwt.decode(token);
      if (payload && payload.user_id) {
        // Incrémenter la version du token pour invalider tous les tokens existants
        await logoutByTokenVersion(payload.user_id);
      }
    }
    res.clearCookie(SESSION_COOKIE_NAME);
    return res.status(200).json({ message: 'Logout successful' });
  } catch (error) {
    console.error('Logout error:', error);
    return res.status(500).json({ code: 'LOGOUT_ERROR', message: 'Logout failed' });
  }
});

app.get('/api/v1/auth/me', requireAuth, (req, res) => {
  res.status(200).json({ user: req.user });
});

app.get('/api/v1/authz/matrix', (_req, res) => {
  res.status(200).json({
    items: [
      { method: 'GET', route: '/api/v1/sales/*', permission: 'orders.read' },
      { method: 'POST', route: '/api/v1/sales/*', permission: 'orders.create' },
      { method: 'PATCH', route: '/api/v1/sales/*', permission: 'orders.update' },
      { method: 'DELETE', route: '/api/v1/sales/*', permission: 'orders.delete' },
      { method: 'POST', route: '/api/v1/sales/orders/:orderId/transition', permission: 'orders.transition' },
      { method: 'GET', route: '/api/v1/admin/users', permission: 'users.manage' },
      { method: 'POST', route: '/api/v1/admin/users', permission: 'users.manage' },
      { method: 'GET', route: '/api/v1/admin/roles', permission: 'roles.manage' },
      { method: 'GET', route: '/api/v1/admin/users/:userId/roles', permission: 'roles.manage' },
      { method: 'POST', route: '/api/v1/admin/users/:userId/roles', permission: 'roles.manage' },
      { method: 'DELETE', route: '/api/v1/admin/users/:userId/roles/:roleCode', permission: 'roles.manage' },
      { method: 'GET', route: '/api/v1/catalog/*', permission: 'products.read' },
      { method: 'POST', route: '/api/v1/catalog/*', permission: 'products.create' },
      { method: 'PATCH', route: '/api/v1/catalog/products/:productId', permission: 'products.update' },
      { method: 'PATCH', route: '/api/v1/catalog/*', permission: 'products.update_stock' },
      { method: 'DELETE', route: '/api/v1/catalog/*', permission: 'products.delete' },
      { method: 'GET', route: '/api/v1/suppliers/*', permission: 'suppliers.read' },
      { method: 'POST', route: '/api/v1/suppliers/*', permission: 'suppliers.create' },
      { method: 'PATCH', route: '/api/v1/suppliers/*', permission: 'suppliers.update' },
      { method: 'DELETE', route: '/api/v1/suppliers/*', permission: 'suppliers.delete' },
      { method: 'GET', route: '/api/v1/customers/*', permission: 'customers.read' },
      { method: 'POST', route: '/api/v1/customers/*', permission: 'customers.create' },
      { method: 'PATCH', route: '/api/v1/customers/*', permission: 'customers.update' },
      { method: 'DELETE', route: '/api/v1/customers/*', permission: 'customers.delete' },
      { method: 'GET', route: '/api/v1/audit/logs', permission: 'audit.read' },
    ],
  });
});

app.get('/api/v1/admin/roles', requireAuth, requirePermission('roles.manage'), async (_req, res) => {
  try {
    const result = await pool.query(
      `
      SELECT
        r.role_id,
        r.role_code,
        r.role_name,
        COALESCE(
          array_agg(DISTINCT p.permission_code) FILTER (WHERE p.permission_code IS NOT NULL),
          '{}'
        ) AS permissions
      FROM roles r
      LEFT JOIN role_permissions rp ON rp.role_id = r.role_id
      LEFT JOIN permissions p ON p.permission_id = rp.permission_id
      GROUP BY r.role_id
      ORDER BY r.role_code
      `
    );

    return res.status(200).json({ items: result.rows });
  } catch (error) {
    return res.status(500).json({ code: 'ROLES_QUERY_ERROR', message: error.message });
  }
});

app.get('/api/v1/admin/users', requireAuth, requirePermission('users.manage'), async (req, res) => {
  const limit = Math.min(Math.max(Number(req.query.limit) || 50, 1), 200);
  const offset = Math.max(Number(req.query.offset) || 0, 0);

  try {
    const countResult = await pool.query('SELECT COUNT(*)::int AS total FROM users');

    const result = await pool.query(
      `
      SELECT
        u.user_id,
        u.username,
        u.full_name,
        u.is_active,
        u.created_at,
        u.updated_at,
        COALESCE(
          array_agg(DISTINCT r.role_code) FILTER (WHERE r.role_code IS NOT NULL),
          '{}'
        ) AS roles
      FROM users u
      LEFT JOIN user_roles ur ON ur.user_id = u.user_id
      LEFT JOIN roles r ON r.role_id = ur.role_id
      GROUP BY u.user_id
      ORDER BY u.user_id
      LIMIT $1 OFFSET $2
      `,
      [limit, offset]
    );

    return res.status(200).json({
      items: result.rows,
      pagination: { limit, offset, total: countResult.rows[0].total },
    });
  } catch (error) {
    return res.status(500).json({ code: 'USERS_QUERY_ERROR', message: error.message });
  }
});

app.post('/api/v1/admin/users', requireAuth, requirePermission('users.manage'), async (req, res) => {
  const { username, password, full_name, role_codes } = req.body;

  if (!username || !password) {
    return res.status(400).json({ code: 'BAD_REQUEST', message: 'username and password are required' });
  }

  if (role_codes !== undefined && !Array.isArray(role_codes)) {
    return res.status(400).json({ code: 'BAD_REQUEST', message: 'role_codes must be an array if provided' });
  }

  const normalizedRoleCodes = Array.isArray(role_codes)
    ? [...new Set(role_codes.map((roleCode) => String(roleCode || '').trim()).filter(Boolean))]
    : [];

  const client = await pool.connect();
  let inTransaction = false;
  try {
    await client.query('BEGIN');
    inTransaction = true;

    const userResult = await client.query(
      `
      INSERT INTO users (username, password_hash, full_name, is_active)
      VALUES ($1, $2, $3, TRUE)
      RETURNING user_id, username, full_name, is_active, created_at, updated_at
      `,
      [username, hashPassword(password), full_name || null]
    );

    const user = userResult.rows[0];

    if (normalizedRoleCodes.length > 0) {
      const rolesResult = await client.query(
        `
        SELECT role_id, role_code
        FROM roles
        WHERE role_code = ANY($1::text[])
        `,
        [normalizedRoleCodes]
      );

      const foundRoleCodes = new Set(rolesResult.rows.map((row) => row.role_code));
      const missingRoles = normalizedRoleCodes.filter((code) => !foundRoleCodes.has(code));
      if (missingRoles.length > 0) {
        await client.query('ROLLBACK');
        inTransaction = false;
        return res.status(404).json({
          code: 'ROLE_NOT_FOUND',
          message: `Unknown role codes: ${missingRoles.join(', ')}`,
        });
      }

      for (const role of rolesResult.rows) {
        await client.query(
          `
          INSERT INTO user_roles (user_id, role_id)
          VALUES ($1, $2)
          ON CONFLICT (user_id, role_id) DO NOTHING
          `,
          [user.user_id, role.role_id]
        );
      }
    }

    const assignedRolesResult = await client.query(
      `
      SELECT COALESCE(array_agg(r.role_code ORDER BY r.role_code), '{}') AS roles
      FROM user_roles ur
      JOIN roles r ON r.role_id = ur.role_id
      WHERE ur.user_id = $1
      `,
      [user.user_id]
    );

    const assignedRoles = assignedRolesResult.rows[0].roles || [];

    await recordAudit(client, {
      entityType: 'user',
      entityId: user.user_id,
      action: 'user.create',
      beforeState: null,
      afterState: {
        user_id: user.user_id,
        username: user.username,
        full_name: user.full_name,
        is_active: user.is_active,
        roles: assignedRoles,
      },
      actorUserId: req.user.user_id,
      actorUsername: req.user.username,
      requestId: req.requestId,
      sourceService: 'gateway',
    });

    await client.query('COMMIT');
    inTransaction = false;

    return res.status(201).json({ item: { ...user, roles: assignedRoles } });
  } catch (error) {
    if (inTransaction) {
      await client.query('ROLLBACK');
    }
    const status = error.code === '23505' ? 409 : 500;
    return res.status(status).json({ code: 'USER_CREATE_ERROR', message: error.message });
  } finally {
    client.release();
  }
});

app.get('/api/v1/admin/users/:userId/roles', requireAuth, requirePermission('roles.manage'), async (req, res) => {
  const userId = Number(req.params.userId);
  if (!Number.isInteger(userId) || userId <= 0) {
    return res.status(400).json({ code: 'BAD_REQUEST', message: 'userId must be a positive integer' });
  }

  try {
    const userResult = await pool.query(
      'SELECT user_id, username, full_name, is_active FROM users WHERE user_id = $1',
      [userId]
    );
    if (userResult.rowCount === 0) {
      return res.status(404).json({ code: 'USER_NOT_FOUND', message: 'User not found' });
    }

    const rolesResult = await pool.query(
      `
      SELECT r.role_code, r.role_name
      FROM user_roles ur
      JOIN roles r ON r.role_id = ur.role_id
      WHERE ur.user_id = $1
      ORDER BY r.role_code
      `,
      [userId]
    );

    return res.status(200).json({ user: userResult.rows[0], roles: rolesResult.rows });
  } catch (error) {
    return res.status(500).json({ code: 'USER_ROLES_QUERY_ERROR', message: error.message });
  }
});

app.post('/api/v1/admin/users/:userId/roles', requireAuth, requirePermission('roles.manage'), async (req, res) => {
  const userId = Number(req.params.userId);
  const { role_code } = req.body;

  if (!Number.isInteger(userId) || userId <= 0) {
    return res.status(400).json({ code: 'BAD_REQUEST', message: 'userId must be a positive integer' });
  }
  if (!role_code || typeof role_code !== 'string') {
    return res.status(400).json({ code: 'BAD_REQUEST', message: 'role_code is required' });
  }

  const client = await pool.connect();
  let inTransaction = false;
  try {
    const userResult = await client.query(
      'SELECT user_id, username FROM users WHERE user_id = $1',
      [userId]
    );
    if (userResult.rowCount === 0) {
      return res.status(404).json({ code: 'USER_NOT_FOUND', message: 'User not found' });
    }

    const roleResult = await client.query('SELECT role_id, role_code FROM roles WHERE role_code = $1', [role_code]);
    if (roleResult.rowCount === 0) {
      return res.status(404).json({ code: 'ROLE_NOT_FOUND', message: 'Role not found' });
    }

    const beforeRolesResult = await client.query(
      `
      SELECT COALESCE(array_agg(r.role_code ORDER BY r.role_code), '{}') AS roles
      FROM user_roles ur
      JOIN roles r ON r.role_id = ur.role_id
      WHERE ur.user_id = $1
      `,
      [userId]
    );
    const beforeRoles = beforeRolesResult.rows[0].roles || [];

    await client.query('BEGIN');
    inTransaction = true;

    const insertResult = await client.query(
      `
      INSERT INTO user_roles (user_id, role_id)
      VALUES ($1, $2)
      ON CONFLICT (user_id, role_id) DO NOTHING
      RETURNING user_id
      `,
      [userId, roleResult.rows[0].role_id]
    );

    if (insertResult.rowCount === 0) {
      await client.query('ROLLBACK');
      inTransaction = false;
      return res.status(409).json({
        code: 'ROLE_ALREADY_ASSIGNED',
        message: `Role ${role_code} is already assigned to user ${userId}`,
      });
    }

    const afterRolesResult = await client.query(
      `
      SELECT COALESCE(array_agg(r.role_code ORDER BY r.role_code), '{}') AS roles
      FROM user_roles ur
      JOIN roles r ON r.role_id = ur.role_id
      WHERE ur.user_id = $1
      `,
      [userId]
    );
    const afterRoles = afterRolesResult.rows[0].roles || [];

    await recordAudit(client, {
      entityType: 'user',
      entityId: userId,
      action: 'user.role.assign',
      beforeState: { roles: beforeRoles },
      afterState: { roles: afterRoles },
      actorUserId: req.user.user_id,
      actorUsername: req.user.username,
      requestId: req.requestId,
      sourceService: 'gateway',
    });

    await client.query('COMMIT');
    inTransaction = false;

    return res.status(200).json({
      message: 'Role assigned',
      user_id: userId,
      role_code,
      roles: afterRoles,
    });
  } catch (error) {
    if (inTransaction) {
      await client.query('ROLLBACK');
    }
    return res.status(500).json({ code: 'ROLE_ASSIGN_ERROR', message: error.message });
  } finally {
    client.release();
  }
});

app.delete('/api/v1/admin/users/:userId/roles/:roleCode', requireAuth, requirePermission('roles.manage'), async (req, res) => {
  const userId = Number(req.params.userId);
  const roleCode = req.params.roleCode;

  if (!Number.isInteger(userId) || userId <= 0) {
    return res.status(400).json({ code: 'BAD_REQUEST', message: 'userId must be a positive integer' });
  }

  const client = await pool.connect();
  let inTransaction = false;
  try {
    const userResult = await client.query(
      'SELECT user_id, username FROM users WHERE user_id = $1',
      [userId]
    );
    if (userResult.rowCount === 0) {
      return res.status(404).json({ code: 'USER_NOT_FOUND', message: 'User not found' });
    }

    const roleResult = await client.query('SELECT role_id, role_code FROM roles WHERE role_code = $1', [roleCode]);
    if (roleResult.rowCount === 0) {
      return res.status(404).json({ code: 'ROLE_NOT_FOUND', message: 'Role not found' });
    }

    const beforeRolesResult = await client.query(
      `
      SELECT COALESCE(array_agg(r.role_code ORDER BY r.role_code), '{}') AS roles
      FROM user_roles ur
      JOIN roles r ON r.role_id = ur.role_id
      WHERE ur.user_id = $1
      `,
      [userId]
    );
    const beforeRoles = beforeRolesResult.rows[0].roles || [];

    await client.query('BEGIN');
    inTransaction = true;

    const deleteResult = await client.query(
      'DELETE FROM user_roles WHERE user_id = $1 AND role_id = $2 RETURNING user_id',
      [userId, roleResult.rows[0].role_id]
    );

    if (deleteResult.rowCount === 0) {
      await client.query('ROLLBACK');
      inTransaction = false;
      return res.status(404).json({
        code: 'ROLE_NOT_ASSIGNED',
        message: `Role ${roleCode} is not assigned to user ${userId}`,
      });
    }

    const afterRolesResult = await client.query(
      `
      SELECT COALESCE(array_agg(r.role_code ORDER BY r.role_code), '{}') AS roles
      FROM user_roles ur
      JOIN roles r ON r.role_id = ur.role_id
      WHERE ur.user_id = $1
      `,
      [userId]
    );
    const afterRoles = afterRolesResult.rows[0].roles || [];

    await recordAudit(client, {
      entityType: 'user',
      entityId: userId,
      action: 'user.role.revoke',
      beforeState: { roles: beforeRoles },
      afterState: { roles: afterRoles },
      actorUserId: req.user.user_id,
      actorUsername: req.user.username,
      requestId: req.requestId,
      sourceService: 'gateway',
    });

    await client.query('COMMIT');
    inTransaction = false;

    return res.status(200).json({
      message: 'Role revoked',
      user_id: userId,
      role_code: roleCode,
      roles: afterRoles,
    });
  } catch (error) {
    if (inTransaction) {
      await client.query('ROLLBACK');
    }
    return res.status(500).json({ code: 'ROLE_REVOKE_ERROR', message: error.message });
  } finally {
    client.release();
  }
});

app.get('/api/v1/audit/logs', requireAuth, requirePermission('audit.read'), async (req, res) => {
  const limit = Math.min(Math.max(Number(req.query.limit) || 50, 1), 500);
  const offset = Math.max(Number(req.query.offset) || 0, 0);
  const {
    entity_type,
    entity_id,
    actor_username,
    request_id,
    source_service,
    from,
    to,
    format,
  } = req.query;

  const filters = [];
  const values = [];
  let idx = 1;

  if (entity_type) {
    filters.push(`entity_type = $${idx++}`);
    values.push(entity_type);
  }
  if (entity_id) {
    filters.push(`entity_id = $${idx++}`);
    values.push(entity_id);
  }
  if (actor_username) {
    filters.push(`actor_username = $${idx++}`);
    values.push(actor_username);
  }
  if (request_id) {
    filters.push(`request_id = $${idx++}`);
    values.push(request_id);
  }
  if (source_service) {
    filters.push(`source_service = $${idx++}`);
    values.push(source_service);
  }
  if (from) {
    filters.push(`created_at >= $${idx++}::timestamp`);
    values.push(from);
  }
  if (to) {
    filters.push(`created_at <= $${idx++}::timestamp`);
    values.push(to);
  }

  const whereClause = filters.length > 0 ? `WHERE ${filters.join(' AND ')}` : '';

  try {
    const countResult = await pool.query(
      `SELECT COUNT(*)::int AS total FROM audit_logs ${whereClause}`,
      values
    );

    const listResult = await pool.query(
      `
      SELECT
        audit_id,
        entity_type,
        entity_id,
        action,
        before_state,
        after_state,
        actor_user_id,
        actor_username,
        request_id,
        source_service,
        created_at
      FROM audit_logs
      ${whereClause}
      ORDER BY created_at DESC, audit_id DESC
      LIMIT $${idx++} OFFSET $${idx++}
      `,
      [...values, limit, offset]
    );

    const rows = listResult.rows;

    if (String(format || '').toLowerCase() === 'csv') {
      const toCsvValue = (value) => {
        if (value === null || value === undefined) return '';
        const asText = typeof value === 'object' ? JSON.stringify(value) : String(value);
        return `"${asText.replace(/"/g, '""')}"`;
      };

      const header = [
        'audit_id',
        'entity_type',
        'entity_id',
        'action',
        'actor_user_id',
        'actor_username',
        'request_id',
        'source_service',
        'created_at',
        'before_state',
        'after_state',
      ];

      const lines = [header.join(',')];
      for (const row of rows) {
        lines.push(
          [
            row.audit_id,
            row.entity_type,
            row.entity_id,
            row.action,
            row.actor_user_id,
            row.actor_username,
            row.request_id,
            row.source_service,
            row.created_at,
            row.before_state,
            row.after_state,
          ]
            .map(toCsvValue)
            .join(',')
        );
      }

      res.setHeader('content-type', 'text/csv; charset=utf-8');
      res.setHeader('content-disposition', 'attachment; filename="audit_logs.csv"');
      return res.status(200).send(lines.join('\n'));
    }

    return res.status(200).json({
      items: rows,
      pagination: { limit, offset, total: countResult.rows[0].total },
      filters: {
        entity_type: entity_type || null,
        entity_id: entity_id || null,
        actor_username: actor_username || null,
        request_id: request_id || null,
        source_service: source_service || null,
        from: from || null,
        to: to || null,
      },
    });
  } catch (error) {
    return res.status(500).json({ code: 'AUDIT_QUERY_ERROR', message: error.message });
  }
});

app.use('/api/v1', requireAuth);

app.use('/api/v1/sales', (req, res, next) => {
  let permission = 'orders.read';
  if (req.method === 'POST') {
    permission = req.path.endsWith('/transition') ? 'orders.transition' : 'orders.create';
  }
  if (req.method === 'PATCH') permission = 'orders.update';
  if (req.method === 'DELETE') permission = 'orders.delete';
  return requirePermission(permission)(req, res, next);
}, (req, res) => forwardRequest(req, res, SERVICE_URLS.sales, '/api/v1/sales'));

app.use('/api/v1/catalog', (req, res, next) => {
  let permission = 'products.read';
  if (req.method === 'POST') permission = 'products.create';
  if (req.method === 'PATCH') {
    permission = req.path.endsWith('/stock') ? 'products.update_stock' : 'products.update';
  }
  if (req.method === 'DELETE') permission = 'products.delete';
  return requirePermission(permission)(req, res, next);
}, (req, res) => forwardRequest(req, res, SERVICE_URLS.catalog, '/api/v1/catalog'));

app.use('/api/v1/customers', (req, res, next) => {
  let permission = 'customers.read';
  if (req.method === 'POST') permission = 'customers.create';
  if (req.method === 'PATCH') permission = 'customers.update';
  if (req.method === 'DELETE') permission = 'customers.delete';
  return requirePermission(permission)(req, res, next);
}, (req, res) => forwardRequest(req, res, SERVICE_URLS.customers, '/api/v1/customers', '/customers'));

app.use('/api/v1/suppliers', (req, res, next) => {
  let permission = 'suppliers.read';
  if (req.method === 'POST') permission = 'suppliers.create';
  if (req.method === 'PATCH') permission = 'suppliers.update';
  if (req.method === 'DELETE') permission = 'suppliers.delete';
  return requirePermission(permission)(req, res, next);
}, (req, res) => forwardRequest(req, res, SERVICE_URLS.suppliers, '/api/v1/suppliers', '/suppliers'));

app.use((_req, res) => {
  res.status(404).json({ code: 'NOT_FOUND', message: 'Route not found' });
});

app.listen(GATEWAY_PORT, () => {
  console.log(`Gateway running on port ${GATEWAY_PORT}`);
});
