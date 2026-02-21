-- Ajouter la colonne token_version à la table users
ALTER TABLE users ADD COLUMN IF NOT EXISTS token_version INTEGER DEFAULT 0;

-- Mettre à jour les utilisateurs existants avec une version par défaut
UPDATE users SET token_version = 0 WHERE token_version IS NULL;

-- Index pour optimiser les performances
CREATE INDEX IF NOT EXISTS idx_users_token_version ON users(user_id, token_version);
