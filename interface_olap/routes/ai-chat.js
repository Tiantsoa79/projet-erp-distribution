/**
 * Route pour le chat IA avec Gemini
 * Permet aux utilisateurs de chatter directement avec l'IA
 */

const express = require('express');
const router = express.Router();
const path = require('path');

// Importer le client Gemini directement
const { GoogleGenerativeAI } = require('@google/generative-ai');

// Configuration
class SimpleLLMClient {
    constructor() {
        this.provider = 'gemini';
        // Charger la clé depuis .env
        require('dotenv').config({ path: path.resolve(__dirname, '../.env') });
        this.apiKey = process.env.GEMINI_API_KEY;
        this.model = process.env.GEMINI_MODEL || 'gemini-2.5-flash';
    }
    
    async generate_response(messages, temperature = 0.7, max_tokens = 1000) {
        try {
            if (!this.apiKey) {
                throw new Error('Clé API Gemini non configurée');
            }
            
            // Convertir les messages en prompt
            let prompt = '';
            messages.forEach(msg => {
                if (msg.role === 'system') {
                    prompt += `System: ${msg.content}\n\n`;
                } else if (msg.role === 'user') {
                    prompt += `User: ${msg.content}\n\n`;
                } else if (msg.role === 'assistant') {
                    prompt += `Assistant: ${msg.content}\n\n`;
                }
            });
            
            // Appeler Gemini
            const genAI = new GoogleGenerativeAI(this.apiKey);
            const model = genAI.getGenerativeModel({ model: this.model });
            
            const result = await model.generateContent(prompt);
            return result.response.text();
            
        } catch (error) {
            console.error('[SimpleLLMClient] Erreur:', error);
            throw error;
        }
    }
    
    get_status() {
        return {
            gemini: {
                configured: !!this.apiKey,
                has_key: !!this.apiKey
            },
            active_provider: this.provider,
            ai_available: !!this.apiKey
        };
    }
    
    is_available() {
        return !!this.apiKey;
    }
}

const llmClient = new SimpleLLMClient();

/**
 * POST /api/ai-chat
 * Endpoint pour chatter avec Gemini IA
 */
router.post('/api/ai-chat', async (req, res) => {
    try {
        const { message, history = [] } = req.body;
        
        if (!message || message.trim() === '') {
            return res.status(400).json({ 
                error: 'Message requis' 
            });
        }
        
        // Préparer l'historique de conversation
        const messages = [
            {
                role: 'system',
                content: `Tu es un assistant business expert pour l'entreprise ERP Distribution. 
                Tu aides les utilisateurs à analyser leurs données commerciales, à prendre des décisions 
                et à comprendre leurs rapports. Sois professionnel, concis et orienté action.
                
                Contexte disponible :
                - CA total : 2,261,537 EUR
                - 4,922 commandes, 793 clients
                - Marge : 23.6%
                - Baisse récente de 35.4% du CA
                
                Réponds en français avec un ton professionnel.`
            },
            ...history,
            {
                role: 'user',
                content: message
            }
        ];
        
        // Appeler Gemini
        const response = await llmClient.generate_response(
            messages,
            0.7,
            1000
        );
        
        if (response) {
            res.json({
                success: true,
                response: response,
                provider: llmClient.provider,
                timestamp: new Date().toISOString()
            });
        } else {
            res.status(500).json({ 
                error: 'Erreur lors de la génération de réponse' 
            });
        }
        
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
 * Vérifier le statut du provider IA
 */
router.get('/api/ai-status', (req, res) => {
    try {
        const status = llmClient.get_status();
        res.json({
            success: true,
            status: status,
            available: llmClient.is_available()
        });
    } catch (error) {
        res.status(500).json({ 
            error: 'Erreur lors de la vérification du statut' 
        });
    }
});

module.exports = router;
