/**
 * Page AI Reporting
 */
const AIPage = {
  pollInterval: null,
  chatHistory: [],

  render() {
    return `
      <div class="page-header">
        <h1>AI Reporting</h1>
        <p>Reporting assiste par l'Intelligence Artificielle — Insights, recommandations et data storytelling</p>
      </div>

      <div class="ai-tabs">
        <button class="tab-btn active" onclick="AIPage.switchTab('reports')">Rapports IA</button>
        <button class="tab-btn" onclick="AIPage.switchTab('chat')">Chat IA</button>
      </div>

      <!-- Rapports Section -->
      <div id="reports-section" class="tab-content active">
        <div class="ai-controls">
          <button id="btn-ai-run" class="btn btn-primary" onclick="AIPage.run(false)">
            &#9733; Generer le rapport IA
          </button>
          <button id="btn-ai-stat" class="btn btn-outline" onclick="AIPage.run(true)">
            Statistique uniquement
          </button>
          <span id="ai-status" class="status-badge status-idle">Pret</span>
          <span id="ai-provider" class="ai-status-badge fallback">Mode: en attente</span>
        </div>

        <div id="ai-results">
          <div class="chart-card" style="text-align:center;padding:60px 20px;">
            <p style="color:var(--text-secondary);font-size:15px;">
              Cliquez sur <strong>Generer le rapport IA</strong> pour lancer l'analyse.<br>
              Le rapport fonctionne meme sans cle API (mode statistique).
            </p>
          </div>
        </div>

        <div id="ai-terminal-section" style="display:none;margin-top:20px;">
          <div class="chart-card">
            <h3>Logs d'execution</h3>
            <div id="ai-terminal" class="terminal">En attente...</div>
          </div>
        </div>
      </div>

      <!-- Chat Section -->
      <div id="chat-section" class="tab-content" style="display:none;">
        <div class="chat-container">
          <div class="chat-header">
            <h3>&#128172; Chat avec l'IA</h3>
            <button class="btn btn-outline btn-sm" onclick="AIPage.clearChat()">Effacer</button>
          </div>
          
          <div id="chat-messages" class="chat-messages">
            <div class="chat-message ai-message">
              <div class="message-content">
                Bonjour ! Je suis votre assistant IA pour l'analyse de données ERP. Posez-moi des questions sur vos données, demandez des insights ou des recommandations.
              </div>
            </div>
          </div>

          <div class="chat-input-container">
            <div class="chat-input-wrapper">
              <input type="text" id="chat-input" placeholder="Tapez votre message ici..." 
                     onkeypress="if(event.key==='Enter') AIPage.sendMessage()">
              <button id="chat-send-btn" class="btn btn-primary" onclick="AIPage.sendMessage()">
                Envoyer
              </button>
            </div>
          </div>
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

  destroy() {
    if (this.pollInterval) {
      clearInterval(this.pollInterval);
      this.pollInterval = null;
    }
  },

  // Chat methods
  switchTab(tab) {
    const reportsSection = document.getElementById('reports-section');
    const chatSection = document.getElementById('chat-section');
    const tabBtns = document.querySelectorAll('.tab-btn');

    tabBtns.forEach(btn => btn.classList.remove('active'));
    
    if (tab === 'reports') {
      reportsSection.style.display = 'block';
      reportsSection.classList.add('active');
      chatSection.style.display = 'none';
      chatSection.classList.remove('active');
      tabBtns[0].classList.add('active');
    } else {
      reportsSection.style.display = 'none';
      reportsSection.classList.remove('active');
      chatSection.style.display = 'block';
      chatSection.classList.add('active');
      tabBtns[1].classList.add('active');
    }
  },

  async sendMessage() {
    const input = document.getElementById('chat-input');
    const message = input.value.trim();
    
    if (!message) return;

    // Ajouter le message utilisateur
    this.addMessage(message, 'user');
    input.value = '';

    // Désactiver le bouton pendant l'envoi
    const sendBtn = document.getElementById('chat-send-btn');
    sendBtn.disabled = true;
    sendBtn.textContent = 'Envoi...';

    try {
      const response = await fetch('/api/ai/ai-chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          message: message,
          history: this.chatHistory
        })
      });

      const data = await response.json();

      if (data.success) {
        this.addMessage(data.response, 'ai');
        this.chatHistory.push(
          { role: 'user', content: message },
          { role: 'assistant', content: data.response }
        );
        
        // Afficher l'indicateur de contexte si disponible
        if (data.hasContext) {
          this.showContextIndicator();
        }
      } else {
        this.addMessage(`Erreur: ${data.error}`, 'ai', true);
      }
    } catch (error) {
      this.addMessage(`Erreur de connexion: ${error.message}`, 'ai', true);
    } finally {
      sendBtn.disabled = false;
      sendBtn.textContent = 'Envoyer';
    }
  },

  addMessage(content, sender, isError = false) {
    const messagesContainer = document.getElementById('chat-messages');
    const messageDiv = document.createElement('div');
    messageDiv.className = `chat-message ${sender}-message ${isError ? 'error' : ''}`;
    
    messageDiv.innerHTML = `
      <div class="message-content">
        ${this.escapeHtml(content)}
      </div>
    `;

    messagesContainer.appendChild(messageDiv);
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
  },

  clearChat() {
    const messagesContainer = document.getElementById('chat-messages');
    messagesContainer.innerHTML = `
      <div class="chat-message ai-message">
        <div class="message-content">
          Chat effacé. Je suis votre assistant IA pour l'analyse de données ERP. Posez-moi des questions sur vos données.
        </div>
      </div>
    `;
    this.chatHistory = [];
  },

  showContextIndicator() {
    const messagesContainer = document.getElementById('chat-messages');
    const indicator = document.createElement('div');
    indicator.className = 'context-indicator';
    indicator.innerHTML = `
      <div class="context-badge">
        📊 Contexte du rapport IA chargé
      </div>
      <p style="font-size: 12px; color: var(--text-secondary); margin: 8px 0;">
        Je peux maintenant répondre aux questions sur le dernier rapport généré.
      </p>
    `;
    
    // Insérer après le premier message de bienvenue
    const firstMessage = messagesContainer.querySelector('.chat-message');
    if (firstMessage) {
      messagesContainer.insertBefore(indicator, firstMessage.nextSibling);
    }
  },
};
