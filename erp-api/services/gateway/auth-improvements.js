// Approche 1: Token Versioning (plus simple et performant)
async function logoutByTokenVersion(userId) {
  await pool.query(
    'UPDATE users SET token_version = token_version + 1 WHERE user_id = $1',
    [userId]
  );
}

// Dans le token JWT
const token = jwt.sign({
  user_id: user.user_id,
  token_version: user.token_version, // Version actuelle
  // ... autres champs
}, JWT_SECRET, { expiresIn: '15m' });

// Vérification
const payload = jwt.verify(token, JWT_SECRET);
const user = await getUserById(payload.user_id);
if (user.token_version !== payload.token_version) {
  return res.status(401).json({ code: 'TOKEN_REVOKED' });
}

// ------------------------------------------------

// Approche 2: Refresh Token Pattern (plus sécurisé)
app.post('/api/v1/auth/login', async (req, res) => {
  // Access token : 15 minutes
  const accessToken = jwt.sign({ user_id, type: 'access' }, JWT_SECRET, { expiresIn: '15m' });
  
  // Refresh token : 7 jours, stocké en DB
  const refreshToken = randomUUID();
  await pool.query(
    'INSERT INTO refresh_tokens (token, user_id, expires_at) VALUES ($1, $2, $3)',
    [refreshToken, user_id, new Date(Date.now() + 7 * 24 * 60 * 60 * 1000)]
  );
  
  res.json({ accessToken, refreshToken });
});

app.post('/api/v1/auth/refresh', async (req, res) => {
  const { refreshToken } = req.body;
  // Valider refresh token en DB
  // Générer nouveau access token
});

app.post('/api/v1/auth/logout', async (req, res) => {
  const { refreshToken } = req.body;
  // Supprimer refresh token de la DB
  await pool.query('DELETE FROM refresh_tokens WHERE token = $1', [refreshToken]);
});

// ------------------------------------------------

// Approche 3: Redis Blacklist (plus performant)
const redis = require('redis');
const client = redis.createClient();

async function addToBlacklist(token) {
  const decoded = jwt.decode(token);
  const ttl = decoded.exp - Math.floor(Date.now() / 1000);
  await client.setEx(`blacklist:${decoded.jti}`, ttl, '1');
}

async function isTokenBlacklisted(token) {
  const decoded = jwt.decode(token);
  const result = await client.get(`blacklist:${decoded.jti}`);
  return result === '1';
}
