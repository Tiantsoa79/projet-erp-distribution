const crypto = require('crypto');

const SCRYPT_KEYLEN = 64;

function hashPassword(plainPassword) {
  const password = String(plainPassword || '');
  const salt = crypto.randomBytes(16).toString('hex');
  const derived = crypto.scryptSync(password, salt, SCRYPT_KEYLEN).toString('hex');
  return `scrypt$${salt}$${derived}`;
}

function verifyPassword(plainPassword, storedHash) {
  if (!storedHash || typeof storedHash !== 'string') return false;

  const [algorithm, salt, expectedHex] = storedHash.split('$');
  if (algorithm !== 'scrypt' || !salt || !expectedHex) return false;

  const expected = Buffer.from(expectedHex, 'hex');
  const actual = crypto.scryptSync(String(plainPassword || ''), salt, expected.length);

  if (actual.length !== expected.length) return false;
  return crypto.timingSafeEqual(actual, expected);
}

module.exports = {
  hashPassword,
  verifyPassword,
};
