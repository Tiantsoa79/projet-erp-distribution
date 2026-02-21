/**
 * Page Dashboard Tactique - Managers
 */
const TacticalPage = {
  allDaily: [],

  render() {
    return `
      <div class="page-header">
        <h1>Dashboard Tactique</h1>
        <p>Managers — Performance operationnelle</p>
      </div>

      <div class="filter-bar">
        <label for="tact-period">Periode :</label>
        <select id="tact-period" onchange="TacticalPage.applyFilter()">
          <option value="30">30 jours</option>
          <option value="60">60 jours</option>
          <option value="90" selected>90 jours</option>
          <option value="9999">Tout</option>
        </select>
      </div>

      <div id="tact-kpis" class="kpi-grid"></div>

      <div class="chart-grid">
        <div class="chart-card">
          <h3>Tendance CA quotidien</h3>
          <div style="height:320px"><canvas id="tact-daily"></canvas></div>
        </div>
        <div class="chart-card">
          <h3>Performance par categorie</h3>
          <div style="height:320px"><canvas id="tact-categories"></canvas></div>
        </div>
      </div>
      <div class="chart-grid">
        <div class="chart-card">
          <h3>Distribution des statuts commandes</h3>
          <div style="height:320px"><canvas id="tact-status"></canvas></div>
        </div>
        <div class="chart-card">
          <h3>CA par mode de livraison</h3>
          <div style="height:320px"><canvas id="tact-ship"></canvas></div>
        </div>
      </div>
    `;
  },

  async load() {
    const data = await API.getTactical();
    this.allDaily = data.daily || [];
    this.categories = data.categories || [];
    this.statusData = data.status || [];
    this.shipData = data.shipModes || [];

    this.applyFilter();
    this.renderStatic();
  },

  applyFilter() {
    const period = parseInt(document.getElementById('tact-period')?.value || '90', 10);
    let daily = this.allDaily;
    if (period < 9999 && daily.length > 0) {
      const maxDate = new Date(daily[daily.length - 1].full_date);
      const cutoff = new Date(maxDate);
      cutoff.setDate(cutoff.getDate() - period);
      daily = daily.filter(r => new Date(r.full_date) >= cutoff);
    }

    // KPIs
    const totalCA = daily.reduce((s, r) => s + Number(r.ca || 0), 0);
    const totalOrders = daily.reduce((s, r) => s + Number(r.orders || 0), 0);
    const totalProfit = daily.reduce((s, r) => s + Number(r.profit || 0), 0);
    const avgDaily = daily.length > 0 ? totalCA / daily.length : 0;
    const marginPct = totalCA > 0 ? (totalProfit / totalCA * 100).toFixed(1) : '0.0';

    const kpisEl = document.getElementById('tact-kpis');
    if (kpisEl) {
      kpisEl.innerHTML = [
        { label: 'CA periode', value: fmtDec(totalCA), color: 'green' },
        { label: 'Commandes', value: fmt(totalOrders), color: 'blue' },
        { label: 'Moyenne / jour', value: fmtDec(avgDaily), color: 'orange' },
        { label: 'Marge globale', value: marginPct + '%', color: 'purple' },
      ].map(k => `<div class="kpi-card ${k.color}">
        <div class="kpi-label">${k.label}</div>
        <div class="kpi-value">${k.value}</div>
      </div>`).join('');
    }

    // Daily area chart
    areaChart('tact-daily',
      daily.map(r => new Date(r.full_date).toLocaleDateString('fr-FR', { day: '2-digit', month: 'short' })),
      daily.map(r => Number(r.ca)),
      { color: COLORS.blue, fill: COLORS.blueFill, label: 'CA' }
    );
  },

  renderStatic() {
    // Categories
    const cats = this.categories;
    multiBarChart('tact-categories',
      cats.map(r => r.category),
      [
        { label: 'CA', data: cats.map(r => Number(r.ca)), backgroundColor: COLORS.blue },
        { label: 'Profit', data: cats.map(r => Number(r.profit)), backgroundColor: COLORS.green },
      ]
    );

    // Status
    const st = this.statusData;
    barChart('tact-status',
      st.map(r => r.status),
      st.map(r => Number(r.orders)),
      { color: COLORS.primary.slice(0, st.length), label: 'Commandes' }
    );

    // Ship modes
    const sm = this.shipData;
    barChart('tact-ship',
      sm.map(r => r.mode),
      sm.map(r => Number(r.ca)),
      { color: [COLORS.blue, COLORS.green, COLORS.orange, COLORS.purple, COLORS.red], label: 'CA' }
    );
  },

  destroy() { destroyAllCharts(); },
};
