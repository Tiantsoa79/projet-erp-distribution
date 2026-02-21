/**
 * SPA Router - ERP Distribution Interface Decisionnelle
 * Hash-based routing (#/page)
 */
const App = {
  currentPage: null,

  pages: {
    pipeline:    PipelinePage,
    strategic:   StrategicPage,
    tactical:    TacticalPage,
    operational: OperationalPage,
    mining:      MiningPage,
    ai:          AIPage,
  },

  init() {
    window.addEventListener('hashchange', () => this.route());
    this.route();
  },

  async route() {
    const hash = window.location.hash.replace('#', '') || '/';
    const pageName = hash.replace('/', '') || 'pipeline';

    // Cleanup previous page
    if (this.currentPage && this.pages[this.currentPage] && this.pages[this.currentPage].destroy) {
      this.pages[this.currentPage].destroy();
    }

    // Update sidebar active state
    document.querySelectorAll('#sidebar .nav-link').forEach(link => {
      link.classList.remove('active');
      if (link.getAttribute('data-page') === pageName) {
        link.classList.add('active');
      }
    });

    const content = document.getElementById('page-content');
    const loading = document.getElementById('page-loading');

    if (!this.pages[pageName]) {
      content.innerHTML = '<div style="text-align:center;padding:80px 0;color:var(--text-secondary);"><h2>Page non trouvee</h2><p>Utilisez le menu de gauche pour naviguer.</p></div>';
      this.currentPage = null;
      return;
    }

    const page = this.pages[pageName];
    content.innerHTML = page.render ? page.render() : '';
    this.currentPage = pageName;

    // Load data if page has a load method (dashboards)
    if (page.load) {
      loading.style.display = 'flex';
      content.style.opacity = '0.4';
      try {
        await page.load();
      } catch (err) {
        console.error(`[${pageName}]`, err);
        content.innerHTML += `
          <div class="chart-card" style="border-left:4px solid var(--danger);margin-top:20px;">
            <h3 style="color:var(--danger);">Erreur de chargement</h3>
            <p style="color:var(--text-secondary);margin-top:8px;">${err.message}</p>
            <p style="color:var(--text-secondary);margin-top:4px;font-size:13px;">
              Verifiez que le pipeline ETL a ete execute et que le DWH contient des donnees.
            </p>
          </div>`;
      }
      loading.style.display = 'none';
      content.style.opacity = '1';
    }
  },
};

// Start
document.addEventListener('DOMContentLoaded', () => App.init());
