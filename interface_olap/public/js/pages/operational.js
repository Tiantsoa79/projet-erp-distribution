/**
 * Page Dashboard Operationnel - Equipes
 */
const OperationalPage = {
  render() {
    return `
      <div class="page-header">
        <h1>Dashboard Operationnel</h1>
        <p>Equipes — Actions quotidiennes et alertes</p>
      </div>
      <div id="oper-kpis" class="kpi-grid"></div>

      <div style="display:grid;grid-template-columns:58% 40%;gap:20px;margin-bottom:24px;">
        <div class="table-card">
          <h3>Commandes recentes</h3>
          <div id="oper-orders-table" style="max-height:400px;overflow-y:auto;"></div>
        </div>
        <div class="table-card">
          <h3>Alertes stock (quantites les plus basses)</h3>
          <div id="oper-stock-table" style="max-height:400px;overflow-y:auto;"></div>
        </div>
      </div>

      <div class="chart-grid">
        <div class="chart-card">
          <h3>Transitions par statut</h3>
          <div style="height:320px"><canvas id="oper-transitions"></canvas></div>
        </div>
        <div class="chart-card">
          <h3>Commandes par region (30 derniers jours)</h3>
          <div style="height:320px"><canvas id="oper-geo"></canvas></div>
        </div>
      </div>
    `;
  },

  async load() {
    const data = await API.getOperational();
    const orders = data.orders || [];
    const stock = data.stock || [];
    const transitions = data.transitions || [];
    const geo = data.geo || [];

    // KPIs
    const lowStock = stock.filter(r => Number(r.quantity_on_hand) < 10).length;
    document.getElementById('oper-kpis').innerHTML = [
      { label: 'Commandes recentes', value: orders.length, color: 'blue' },
      { label: 'Produits stock faible', value: lowStock, color: 'red' },
      { label: 'Types de transitions', value: transitions.length, color: 'orange' },
      { label: 'Regions actives', value: geo.length, color: 'green' },
    ].map(k => `<div class="kpi-card ${k.color}">
      <div class="kpi-label">${k.label}</div>
      <div class="kpi-value">${k.value}</div>
    </div>`).join('');

    // Orders table
    document.getElementById('oper-orders-table').innerHTML = orders.length > 0 ? `
      <table>
        <thead><tr>
          <th>Commande</th><th>Client</th><th>Ville</th>
          <th>Statut</th><th>Mode</th><th>Date</th><th class="text-right">Total</th>
        </tr></thead>
        <tbody>${orders.slice(0, 20).map(r => `<tr>
          <td>${r.order_id || ''}</td>
          <td>${(r.customer_name || '').substring(0, 22)}</td>
          <td>${r.city || ''}</td>
          <td><span class="badge badge-${r.status === 'Delivered' ? 'success' : r.status === 'Returned' ? 'danger' : 'warning'}">${r.status || ''}</span></td>
          <td>${r.ship_mode || ''}</td>
          <td>${r.order_date ? new Date(r.order_date).toLocaleDateString('fr-FR') : ''}</td>
          <td class="text-right">${fmtDec(r.total)}</td>
        </tr>`).join('')}</tbody>
      </table>` : '<p style="color:var(--text-secondary)">Aucune donnee</p>';

    // Stock table
    document.getElementById('oper-stock-table').innerHTML = stock.length > 0 ? `
      <table>
        <thead><tr>
          <th>Produit</th><th>Categorie</th>
          <th class="text-right">Stock</th><th class="text-right">Valeur</th>
        </tr></thead>
        <tbody>${stock.slice(0, 15).map(r => {
          const qty = Number(r.quantity_on_hand);
          const cls = qty < 10 ? 'badge-danger' : qty < 50 ? 'badge-warning' : 'badge-success';
          return `<tr>
            <td>${(r.product_name || '').substring(0, 28)}</td>
            <td>${r.category || ''}</td>
            <td class="text-right"><span class="badge ${cls}">${qty}</span></td>
            <td class="text-right">${fmtDec(r.stock_value)}</td>
          </tr>`;
        }).join('')}</tbody>
      </table>` : '<p style="color:var(--text-secondary)">Aucune donnee</p>';

    // Transitions chart
    barChart('oper-transitions',
      transitions.map(r => r.status),
      transitions.map(r => Number(r.transitions)),
      { color: COLORS.primary.slice(0, transitions.length), label: 'Transitions' }
    );

    // Geo chart
    barChart('oper-geo',
      geo.map(r => r.region),
      geo.map(r => Number(r.orders)),
      { horizontal: true, color: COLORS.primary.slice(0, geo.length), label: 'Commandes' }
    );
  },

  destroy() { destroyAllCharts(); },
};
