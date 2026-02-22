/**
 * Route simple pour le chat IA
 */

const express = require('express');
const router = express.Router();

/**
 * POST /api/ai-chat
 * Endpoint simple pour le chat IA
 */
router.post('/api/ai-chat', async (req, res) => {
    try {
        const { message } = req.body;
        
        if (!message || message.trim() === '') {
            return res.status(400).json({ 
                error: 'Message requis' 
            });
        }
        
        // Réponse simple de test (remplacer par Gemini plus tard)
        const response = `🤖 Assistant IA: J'ai reçu votre message "${message}". 
        
        Je suis votre assistant pour ERP Distribution. Je peux vous aider avec :
        - Analyse des ventes
        - Recommandations stratégiques  
        - Interprétation des données
        
        Pour l'instant, je fonctionne en mode démo. L'intégration complète avec Gemini sera bientôt disponible !`;
        
        res.json({
            success: true,
            response: response,
            provider: 'demo',
            timestamp: new Date().toISOString()
        });
        
    } catch (error) {
        console.error('[AI Chat] Erreur:', error);
        res.status(500).json({ 
            error: 'Erreur serveur',
            details: error.message 
        });
    }
});

/**
 * GET /api/ai-status
 * Vérifier le statut de l'IA
 */
router.get('/api/ai-status', (req, res) => {
    res.json({
        success: true,
        status: {
            demo: {
                configured: true,
                has_key: true
            },
            active_provider: 'demo',
            ai_available: true
        },
        available: true
    });
});

module.exports = router;
