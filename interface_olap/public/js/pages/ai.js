/**
 * Page AI Reporting
 */
const AIPage = {
  pollInterval: null,

  render() {
    return `
      <div class="page-header">
        <h1>AI Reporting</h1>
        <p>Reporting assiste par l'Intelligence Artificielle — Insights, recommandations et data storytelling</p>
      </div>

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
};
