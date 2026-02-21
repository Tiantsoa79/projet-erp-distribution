/**
 * Page Dashboard Strategique - Direction Generale
 */
const StrategicPage = {
  render() {
    return `
      <div class="page-header">
        <h1>Dashboard Strategique</h1>
        <p>Direction Generale — Vue d'ensemble de l'entreprise</p>
      </div>
      <div id="strat-kpis" class="kpi-grid"></div>
      <div class="chart-grid">
        <div class="chart-card">
          <h3>Evolution du CA mensuel</h3>
          <div style="height:320px"><canvas id="strat-monthly"></canvas></div>
        </div>
        <div class="chart-card">
          <h3>Repartition CA par segment client</h3>
          <div style="height:320px"><canvas id="strat-segments"></canvas></div>
        </div>
      </div>
      <div class="chart-grid">
        <div class="chart-card">
          <h3>Top regions par CA</h3>
          <div style="height:320px"><canvas id="strat-geo"></canvas></div>
        </div>
        <div class="chart-card">
          <h3>Top 10 produits par CA</h3>
          <div style="height:320px"><canvas id="strat-products"></canvas></div>
        </div>
      </div>
    `;
  },

  async load() {
    const data = await API.getStrategic();

    // KPIs
    const k = data.kpis || {};
    const kpis = [
      { label: "Chiffre d'affaires", value: fmtDec(k.ca_cur), prev: k.ca_prev, cur: k.ca_cur, color: 'green' },
      { label: 'Commandes', value: fmt(k.ord_cur), prev: k.ord_prev, cur: k.ord_cur, color: 'blue' },
      { label: 'Clients actifs', value: fmt(k.cli_cur), prev: k.cli_prev, cur: k.cli_cur, color: 'purple' },
      { label: 'Panier moyen', value: fmtDec(k.avg_cur), prev: k.avg_prev, cur: k.avg_cur, color: 'orange' },
    ];
    document.getElementById('strat-kpis').innerHTML = kpis.map(kpi => {
      const v = pctVar(kpi.cur, kpi.prev);
      return `<div class="kpi-card ${kpi.color}">
        <div class="kpi-label">${kpi.label}</div>
        <div class="kpi-value">${kpi.value}</div>
        <div class="kpi-variation ${v.cls}">${v.text} vs mois prec.</div>
      </div>`;
    }).join('');

    // Monthly chart
    const monthly = data.monthly || [];
    lineChart('strat-monthly',
      monthly.map(r => r.month_name + ' ' + r.year_number),
      [{
        label: 'CA', data: monthly.map(r => Number(r.ca)),
        borderColor: COLORS.green, backgroundColor: COLORS.greenFill,
        fill: true, tension: 0.3,
      }]
    );

    // Segments doughnut
    const segments = data.segments || [];
    doughnutChart('strat-segments',
      segments.map(r => r.segment),
      segments.map(r => Number(r.ca))
    );

    // Geo bar
    const geo = data.geo || [];
    barChart('strat-geo',
      geo.map(r => r.region),
      geo.map(r => Number(r.ca)),
      { horizontal: true, color: COLORS.primary.slice(0, geo.length), label: 'CA' }
    );

    // Top products bar
    const products = data.products || [];
    barChart('strat-products',
      products.map(r => r.product_name ? r.product_name.substring(0, 25) : ''),
      products.map(r => Number(r.ca)),
      { horizontal: true, color: COLORS.primary.slice(0, products.length), label: 'CA' }
    );
  },

  destroy() { destroyAllCharts(); },
};
