/**
 * Page Assistant IA - Interface de chat avec Gemini
 * Permet aux utilisateurs de chatter directement avec l'IA
 */

class AIChatPage {
    constructor() {
        this.history = [];
        this.isLoading = false;
        this.init();
    }
    
    async init() {
        try {
            // Vérifier le statut de l'IA
            await this.checkAIStatus();
            
            // Initialiser l'interface
            this.setupChatInterface();
            this.bindEvents();
            this.loadHistory();
            
            console.log('[AI Chat] Assistant IA initialisé');
        } catch (error) {
            console.error('[AI Chat] Erreur d\'initialisation:', error);
        }
    }
    
    async checkAIStatus() {
        try {
            const response = await fetch('/api/ai-status');
            const data = await response.json();
            
            this.updateAIStatus(data);
        } catch (error) {
            console.error('[AI Chat] Erreur vérification statut:', error);
            this.updateAIStatus({ available: false });
        }
    }
    
    updateAIStatus(status) {
        const statusElement = document.getElementById('ai-status');
        const chatContainer = document.getElementById('chat-container');
        
        if (status.available) {
            statusElement.innerHTML = `
                <span class="status-active">🤖 ${status.active_provider.toUpperCase()} Actif</span>
            `;
            statusElement.className = 'ai-status active';
            chatContainer.classList.remove('disabled');
        } else {
            statusElement.innerHTML = `
                <span class="status-inactive">❌ IA Indisponible</span>
            `;
            statusElement.className = 'ai-status inactive';
            chatContainer.classList.add('disabled');
        }
    }
    
    setupChatInterface() {
        const content = document.getElementById('page-content');
        
        content.innerHTML = `
            <div class="ai-chat-container">
                <div class="chat-header">
                    <h1>🤖 Assistant IA</h1>
                    <div id="ai-status" class="ai-status">
                        <span class="status-loading">🔄 Vérification...</span>
                    </div>
                </div>
                
                <div class="chat-main">
                    <div class="chat-sidebar">
                        <div class="chat-info">
                            <h3>💡 À propos</h3>
                            <p>Discutez directement avec <strong>Gemini IA</strong> pour analyser vos données business.</p>
                            
                            <h4>📊 Contexte disponible</h4>
                            <ul>
                                <li>CA total : 2,261,537 EUR</li>
                                <li>4,922 commandes</li>
                                <li>793 clients</li>
                                <li>Marge : 23.6%</li>
                            </ul>
                            
                            <button onclick="aiChat.clearHistory()" class="btn btn-secondary">
                                🗑️ Effacer l'historique
                            </button>
                        </div>
                    </div>
                    
                    <div class="chat-content">
                        <div id="chat-container" class="chat-container">
                            <div class="chat-welcome">
                                <h2>👋 Bienvenue !</h2>
                                <p>Je suis votre assistant IA pour ERP Distribution. Posez-moi vos questions sur :</p>
                                <ul>
                                    <li>📈 Analyse des ventes</li>
                                    <li>👥 Segmentation clients</li>
                                    <li>📊 Recommandations stratégiques</li>
                                    <li>💰 Optimisation de la rentabilité</li>
                                </ul>
                            </div>
                        </div>
                        
                        <div class="chat-input-container">
                            <div class="input-group">
                                <textarea 
                                    id="message-input" 
                                    placeholder="Posez votre question sur les données business..."
                                    rows="3"
                                    maxlength="1000"
                                ></textarea>
                                <button 
                                    id="send-button" 
                                    onclick="aiChat.sendMessage()"
                                    class="btn btn-primary"
                                >
                                    <span id="send-text">💬 Envoyer</span>
                                    <span id="loading-text" style="display:none;">⏳ Envoi...</span>
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
                
                <div class="chat-footer">
                    <p><strong>Provider :</strong> <span id="provider-name">Vérification...</span></p>
                    <p><strong>Mode :</strong> Conversation IA avec contexte business</p>
                </div>
            </div>
        `;
        
        // Focus sur le champ de saisie
        setTimeout(() => {
            document.getElementById('message-input').focus();
        }, 100);
    }
    
    bindEvents() {
        const input = document.getElementById('message-input');
        const sendButton = document.getElementById('send-button');
        
        // Envoyer avec Entrée
        input.addEventListener('keypress', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.sendMessage();
            }
        });
        
        // Activer/désactiver le bouton
        input.addEventListener('input', () => {
            const hasText = input.value.trim().length > 0;
            sendButton.disabled = !hasText || this.isLoading;
        });
    }
    
    async sendMessage() {
        const input = document.getElementById('message-input');
        const message = input.value.trim();
        
        if (!message || this.isLoading) return;
        
        this.isLoading = true;
        this.updateSendButton(true);
        
        // Ajouter le message à l'historique
        this.addMessage(message, 'user');
        
        // Vider le champ
        input.value = '';
        
        try {
            // Envoyer à l'API
            const response = await fetch('/api/ai-chat', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    message: message,
                    history: this.history
                })
            });
            
            const data = await response.json();
            
            if (data.success) {
                this.addMessage(data.response, 'assistant');
                this.updateProviderInfo(data.provider);
                this.saveHistory();
            } else {
                this.addMessage('❌ Erreur: ' + data.error, 'assistant');
            }
            
        } catch (error) {
            console.error('[AI Chat] Erreur envoi message:', error);
            this.addMessage('❌ Erreur de connexion', 'assistant');
        } finally {
            this.isLoading = false;
            this.updateSendButton(false);
        }
    }
    
    addMessage(content, type) {
        const chatContainer = document.getElementById('chat-container');
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${type}`;
        
        const timestamp = new Date().toLocaleTimeString('fr-FR');
        
        messageDiv.innerHTML = `
            <div class="message-content">
                <div class="message-header">
                    <span class="message-type">${type === 'user' ? '👤 Vous' : '🤖 Assistant IA'}</span>
                    <span class="message-time">${timestamp}</span>
                </div>
                <div class="message-text">${content}</div>
            </div>
        `;
        
        chatContainer.appendChild(messageDiv);
        chatContainer.scrollTop = chatContainer.scrollHeight;
        
        // Ajouter à l'historique
        this.history.push({ role: type, content });
    }
    
    updateSendButton(isLoading) {
        const sendText = document.getElementById('send-text');
        const loadingText = document.getElementById('loading-text');
        
        if (isLoading) {
            sendText.style.display = 'none';
            loadingText.style.display = 'inline';
        } else {
            sendText.style.display = 'inline';
            loadingText.style.display = 'none';
        }
    }
    
    updateProviderInfo(provider) {
        const providerElement = document.getElementById('provider-name');
        if (providerElement) {
            providerElement.textContent = provider.toUpperCase();
        }
    }
    
    saveHistory() {
        try {
            localStorage.setItem('ai-chat-history', JSON.stringify(this.history));
        } catch (error) {
            console.error('[AI Chat] Erreur sauvegarde historique:', error);
        }
    }
    
    loadHistory() {
        try {
            const saved = localStorage.getItem('ai-chat-history');
            if (saved) {
                this.history = JSON.parse(saved);
            }
        } catch (error) {
            console.error('[AI Chat] Erreur chargement historique:', error);
        }
    }
    
    clearHistory() {
        if (confirm('Êtes-vous sûr de vouloir effacer tout l\'historique ?')) {
            this.history = [];
            localStorage.removeItem('ai-chat-history');
            
            // Vider le chat sauf le message de bienvenue
            const chatContainer = document.getElementById('chat-container');
            const welcomeMessage = chatContainer.querySelector('.chat-welcome');
            chatContainer.innerHTML = '';
            chatContainer.appendChild(welcomeMessage);
        }
    }
}

// Initialiser la page au chargement
document.addEventListener('DOMContentLoaded', () => {
    window.aiChat = new AIChatPage();
});
