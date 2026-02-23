/**
 * Page AI Reporting
 */
const AIPage = {
  pollInterval: null,

  render() {
    return `
      <div class="page-header">
        <h1>AI Reporting</h1>
        <p>Insights et recommandations assistées par IA</p>
      </div>

      <div class="ai-controls">
        <button id="btn-ai-run" class="btn btn-primary" onclick="AIPage.run(false)">
          🤖 Générer rapport IA
        </button>
        <button id="btn-ai-stat" class="btn btn-outline" onclick="AIPage.run(true)">
          📊 Statistique uniquement
        </button>
        <span id="ai-status" class="status-badge status-idle">Prêt</span>
      </div>

      <!-- Chat compact -->
      <div class="chart-card">
        <h3>💬 Chat IA</h3>
        <div class="chat-compact">
          <div id="chat-messages" class="chat-messages-compact">
            <div class="chat-welcome-compact">
              👋 Posez vos questions sur les données business
            </div>
          </div>
          
          <div class="chat-input-compact">
            <textarea 
              id="chat-input" 
              placeholder="Votre question..."
              rows="2"
              onkeypress="if(event.key==='Enter' && !event.shiftKey){event.preventDefault();AIPage.sendChatMessage();}"
            ></textarea>
            <button id="btn-chat-send" onclick="AIPage.sendChatMessage()" class="btn btn-primary btn-sm">
              <span id="send-icon">💬</span>
              <span id="send-text">Envoyer</span>
            </button>
            <div id="typing-indicator" class="typing-indicator" style="display:none;">
              <span>🤖 L'IA réfléchit...</span>
            </div>
          </div>
        </div>
      </div>

      <div id="ai-results">
        <div class="chart-card" style="text-align:center;padding:40px 20px;">
          <p style="color:var(--text-secondary);">
            Cliquez sur <strong>Générer rapport IA</strong> pour démarrer
          </p>
        </div>
      </div>

      <div id="ai-terminal-section" style="display:none;">
        <div class="chart-card">
          <h3>📋 Logs</h3>
          <div id="ai-terminal" class="terminal-compact">En attente...</div>
        </div>
      </div>
    `;
  },

  async run(noAi) {
    const btnRun = document.getElementById('btn-ai-run');
    const btnStat = document.getElementById('btn-ai-stat');
    if (btnRun) btnRun.disabled = true;
    if (btnStat) btnStat.disabled = true;
    this.setStatus('running');

    document.getElementById('ai-terminal-section').style.display = 'block';
    document.getElementById('ai-terminal').textContent = 
      'Lancement du pipeline AI Reporting...\n\n' +
      'Etapes :\n' +
      '  1. Collecte des donnees business depuis le DWH\n' +
      '  2. Generation des insights automatiques\n' +
      '  3. Elaboration des recommandations\n' +
      '  4. Data storytelling (narration)\n\n' +
      'Vous pouvez naviguer dans les autres sections en attendant.\n\n' +
      '--- Logs ---\n';

    try {
      await fetch('/api/ai/run', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ noAi })
      });
      this.startPolling();
    } catch (err) {
      this.setStatus('error');
      document.getElementById('ai-terminal').textContent = 'Erreur: ' + err.message;
      if (btnRun) btnRun.disabled = false;
      if (btnStat) btnStat.disabled = false;
    }
  },

  startPolling() {
    if (this.pollInterval) clearInterval(this.pollInterval);
    this.pollInterval = setInterval(async () => {
      try {
        const resp = await fetch('/api/ai/status');
        const data = await resp.json();
        const term = document.getElementById('ai-terminal');
        if (term && data.output) {
          term.textContent = data.output;
          term.scrollTop = term.scrollHeight;
        }
        if (!data.running) {
          clearInterval(this.pollInterval);
          this.pollInterval = null;
          this.setStatus(data.status);
          const btnRun = document.getElementById('btn-ai-run');
          const btnStat = document.getElementById('btn-ai-stat');
          if (btnRun) btnRun.disabled = false;
          if (btnStat) btnStat.disabled = false;
          if (data.status === 'success') {
            this.loadResults();
          }
        }
      } catch (e) { /* ignore */ }
    }, 1500);
  },

  async loadResults() {
    try {
      const resp = await fetch('/api/ai/results/latest');
      if (!resp.ok) return;
      const report = await resp.json();
      this.displayReport(report);
    } catch (e) {
      console.error('Erreur chargement resultats AI:', e);
    }
  },

  displayReport(report) {
    const container = document.getElementById('ai-results');
    if (!container) return;

    const providerEl = document.getElementById('ai-provider');
    if (providerEl) {
      if (report.ai_available) {
        providerEl.className = 'ai-status-badge available';
        providerEl.textContent = 'IA: ' + (report.ai_provider || 'actif');
      } else {
        providerEl.className = 'ai-status-badge fallback';
        providerEl.textContent = 'Mode: statistique';
      }
    }

    let html = '';

    // Storytelling
    const story = report.storytelling || {};
    const storyText = story.ai_story || story.statistical_story || '';
    if (storyText) {
      html += `
        <div class="chart-card" style="margin-bottom:24px;">
          <h3>&#128214; Data Storytelling</h3>
          <div class="story-card">${this.escapeHtml(storyText)}</div>
        </div>`;
    }

    // Insights
    const insights = report.insights || {};
    const statInsights = insights.statistical || [];
    if (statInsights.length > 0) {
      html += '<h3 style="margin:24px 0 16px;font-size:18px;font-weight:600;">Insights automatiques</h3>';
      for (const ins of statInsights) {
        const impactClass = ins.impact || 'medium';
        html += `
          <div class="insight-card ${impactClass}">
            <span class="insight-type">${ins.type || 'insight'}</span>
            <h4>${this.escapeHtml(ins.titre)}</h4>
            <p>${this.escapeHtml(ins.description)}</p>
          </div>`;
      }
    }

    // AI Analysis
    if (insights.ai_analysis) {
      html += `
        <div class="chart-card" style="margin:24px 0;">
          <h3>&#9733; Analyse IA enrichie</h3>
          <div class="ai-text-content">${this.escapeHtml(insights.ai_analysis)}</div>
        </div>`;
    }

    // Recommendations
    const recs = report.recommendations || {};
    const statRecs = recs.statistical || [];
    if (statRecs.length > 0) {
      html += '<h3 style="margin:24px 0 16px;font-size:18px;font-weight:600;">Recommandations decisionnelles</h3>';
      for (const rec of statRecs) {
        html += `
          <div class="recommendation-card">
            <span class="priority ${rec.priorite}">${rec.priorite}</span>
            <strong style="margin-left:8px;">${this.escapeHtml(rec.domaine)}</strong>
            <p style="margin:8px 0;color:var(--text-secondary);line-height:1.6;">
              ${this.escapeHtml(rec.recommandation)}
            </p>
            <p style="font-size:12px;color:var(--text-secondary);font-style:italic;">
              Impact : ${this.escapeHtml(rec.impact_estime)}
            </p>
          </div>`;
      }
    }

    // AI Recommendations
    if (recs.ai_recommendations) {
      html += `
        <div class="chart-card" style="margin:24px 0;">
          <h3>&#9733; Recommandations IA</h3>
          <div class="ai-text-content">${this.escapeHtml(recs.ai_recommendations)}</div>
        </div>`;
    }

    if (!html) {
      html = '<div class="chart-card" style="text-align:center;padding:40px;"><p style="color:var(--text-secondary)">Aucun resultat disponible</p></div>';
    }

    container.innerHTML = html;
  },

  setStatus(status) {
    const el = document.getElementById('ai-status');
    if (!el) return;
    const labels = { idle: 'Pret', running: 'En cours...', success: 'Termine', error: 'Erreur' };
    el.textContent = labels[status] || status;
    el.className = `status-badge status-${status}`;
  },

  escapeHtml(str) {
    if (!str) return '';
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  },

  // Fonction pour le chat avec Gemini
  async sendChatMessage() {
    const input = document.getElementById('chat-input');
    const messagesContainer = document.getElementById('chat-messages');
    const sendButton = document.getElementById('btn-chat-send');
    const sendIcon = document.getElementById('send-icon');
    const sendText = document.getElementById('send-text');
    const typingIndicator = document.getElementById('typing-indicator');
    
    const message = input.value.trim();
    if (!message) return;
    
    // Désactiver le champ et le bouton
    input.disabled = true;
    sendButton.disabled = true;
    
    // Afficher l'indicateur de chargement
    typingIndicator.style.display = 'flex';
    sendIcon.textContent = '⏳';
    sendText.textContent = 'Envoi...';
    
    // Ajouter le message utilisateur
    this.addChatMessage(message, 'user');
    
    // Vider le champ
    input.value = '';
    
    try {
      // Appeler l'API Gemini
      const response = await fetch('/api/ai/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          message: message,
          context: 'business_analysis'
        })
      });
      
      const data = await response.json();
      
      if (data.success) {
        this.addChatMessage(data.response, 'assistant', data.provider);
      } else {
        this.addChatMessage('❌ Erreur: ' + (data.error || 'Erreur inconnue'), 'assistant', 'error');
      }
      
    } catch (error) {
      console.error('[Chat] Erreur:', error);
      this.addChatMessage('❌ Erreur de connexion avec Gemini', 'assistant', 'error');
    } finally {
      // Réactiver le champ et le bouton
      input.disabled = false;
      sendButton.disabled = false;
      typingIndicator.style.display = 'none';
      sendIcon.textContent = '💬';
      sendText.textContent = 'Envoyer';
      
      // Remettre le focus sur le champ
      input.focus();
    }
  },

  addChatMessage(content, type, provider = 'gemini') {
    const messagesContainer = document.getElementById('chat-messages');
    
    // Supprimer le message de bienvenue si c'est le premier message
    const welcomeMessage = messagesContainer.querySelector('.chat-welcome');
    if (welcomeMessage) {
      welcomeMessage.remove();
    }
    
    const messageDiv = document.createElement('div');
    messageDiv.className = `chat-message ${type}`;
    messageDiv.style.cssText = `
      margin: 15px 0;
      padding: 16px 20px;
      border-radius: 16px;
      background: ${type === 'user' ? 'linear-gradient(135deg, #007bff 0%, #0056b3 100%)' : 'linear-gradient(135deg, #ffffff 0%, #f8f9fa 100%)'};
      color: ${type === 'user' ? 'white' : 'var(--text-primary)'};
      border-left: 4px solid ${type === 'user' ? '#0056b3' : '#28a745'};
      box-shadow: 0 4px 12px rgba(0,0,0,0.1);
      animation: slideInUp 0.3s ease;
      position: relative;
    `;
    
    const timestamp = new Date().toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' });
    
    messageDiv.innerHTML = `
      <div style="
        font-weight:600;
        margin-bottom:8px;
        font-size:13px;
        opacity:0.9;
        display:flex;
        justify-content:space-between;
        align-items:center;
      ">
        <span>${type === 'user' ? '👤 Vous' : '🤖 Gemini IA'}</span>
        <span style="font-weight:400;">${timestamp}</span>
      </div>
      <div style="
        line-height:1.6;
        white-space:pre-wrap;
        font-size:15px;
      ">${this.escapeHtml(content)}</div>
      ${type === 'assistant' && provider !== 'error' ? `
        <div style="
          position:absolute;
          top:8px;
          right:8px;
          background:rgba(40, 167, 69, 0.1);
          color:#28a745;
          padding:4px 8px;
          border-radius:12px;
          font-size:11px;
          font-weight:600;
        ">${provider.toUpperCase()}</div>
      ` : ''}
    `;
    
    messagesContainer.appendChild(messageDiv);
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
  },

  destroy() {
    if (this.pollInterval) {
      clearInterval(this.pollInterval);
      this.pollInterval = null;
    }
  },
};
