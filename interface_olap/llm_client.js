/**
 * Client LLM pour l'interface OLAP
 * Communication avec Gemini IA depuis le frontend
 */

class LLMClient {
    constructor() {
        this.provider = 'gemini';
        this.apiEndpoint = '/api/ai-chat';
        this.statusEndpoint = '/api/ai-status';
    }
    
    async generate_response(messages, temperature = 0.7, max_tokens = 1000) {
        try {
            const response = await fetch(this.apiEndpoint, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    message: messages[messages.length - 1].content,
                    history: messages.slice(0, -1)
                })
            });
            
            const data = await response.json();
            
            if (data.success) {
                return data.response;
            } else {
                throw new Error(data.error || 'Erreur inconnue');
            }
        } catch (error) {
            console.error('[LLM Client] Erreur génération:', error);
            throw error;
        }
    }
    
    async call_llm(messages, temperature = 0.7, max_tokens = 1000) {
        return this.generate_response(messages, temperature, max_tokens);
    }
    
    async get_status() {
        try {
            const response = await fetch(this.statusEndpoint);
            const data = await response.json();
            return data;
        } catch (error) {
            console.error('[LLM Client] Erreur vérification statut:', error);
            return {
                success: false,
                status: {},
                available: false
            };
        }
    }
    
    is_available() {
        return this.provider !== null;
    }
}

module.exports = { LLMClient };
