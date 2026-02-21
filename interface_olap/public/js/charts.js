/**
 * Chart helpers - Interface OLAP
 * Wrappers autour de Chart.js pour creer des graphiques standardises.
 */

const COLORS = {
  primary:  ['#e94560','#0f3460','#16213e','#533483','#2b2d42','#f39c12','#27ae60','#3498db','#9b59b6','#1abc9c'],
  green:    'rgba(39, 174, 96, 0.8)',
  blue:     'rgba(52, 152, 219, 0.8)',
  red:      'rgba(231, 76, 60, 0.8)',
  orange:   'rgba(243, 156, 18, 0.8)',
  purple:   'rgba(155, 89, 182, 0.8)',
  greenFill:'rgba(39, 174, 96, 0.15)',
  blueFill: 'rgba(52, 152, 219, 0.15)',
};

const chartInstances = {};

function destroyChart(id) {
  if (chartInstances[id]) {
    chartInstances[id].destroy();
    delete chartInstances[id];
  }
}

function destroyAllCharts() {
  Object.keys(chartInstances).forEach(destroyChart);
}

function createChart(canvasId, config) {
  destroyChart(canvasId);
  const ctx = document.getElementById(canvasId);
  if (!ctx) return null;
  chartInstances[canvasId] = new Chart(ctx, config);
  return chartInstances[canvasId];
}

// --- Line chart ---
function lineChart(canvasId, labels, datasets, title) {
  return createChart(canvasId, {
    type: 'line',
    data: { labels, datasets },
    options: {
      responsive: true, maintainAspectRatio: false,
      plugins: { legend: { display: datasets.length > 1 }, title: { display: false } },
      scales: {
        x: { grid: { display: false } },
        y: { beginAtZero: true, grid: { color: 'rgba(0,0,0,0.04)' } },
      },
      elements: { point: { radius: 3, hoverRadius: 5 }, line: { tension: 0.3 } },
    },
  });
}

// --- Bar chart (vertical) ---
function barChart(canvasId, labels, data, { color = COLORS.blue, horizontal = false, label = '' } = {}) {
  return createChart(canvasId, {
    type: 'bar',
    data: {
      labels,
      datasets: [{ label, data, backgroundColor: color, borderRadius: 4, maxBarThickness: 50 }],
    },
    options: {
      indexAxis: horizontal ? 'y' : 'x',
      responsive: true, maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales: {
        x: { grid: { display: horizontal } },
        y: { beginAtZero: true, grid: { color: 'rgba(0,0,0,0.04)' } },
      },
    },
  });
}

// --- Multi-bar chart ---
function multiBarChart(canvasId, labels, datasets) {
  return createChart(canvasId, {
    type: 'bar',
    data: { labels, datasets: datasets.map((ds, i) => ({ ...ds, borderRadius: 4, maxBarThickness: 40 })) },
    options: {
      responsive: true, maintainAspectRatio: false,
      plugins: { legend: { position: 'top' } },
      scales: {
        x: { grid: { display: false } },
        y: { beginAtZero: true, grid: { color: 'rgba(0,0,0,0.04)' } },
      },
    },
  });
}

// --- Doughnut / Pie ---
function doughnutChart(canvasId, labels, data, colors) {
  return createChart(canvasId, {
    type: 'doughnut',
    data: {
      labels,
      datasets: [{ data, backgroundColor: colors || COLORS.primary.slice(0, data.length), borderWidth: 2 }],
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      plugins: {
        legend: { position: 'right', labels: { boxWidth: 14, padding: 12, font: { size: 12 } } },
      },
      cutout: '55%',
    },
  });
}

// --- Area chart ---
function areaChart(canvasId, labels, data, { color = COLORS.blue, fill = COLORS.blueFill, label = '' } = {}) {
  return createChart(canvasId, {
    type: 'line',
    data: {
      labels,
      datasets: [{
        label, data,
        borderColor: color, backgroundColor: fill,
        fill: true, tension: 0.35, pointRadius: 2, pointHoverRadius: 5,
      }],
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales: {
        x: { grid: { display: false } },
        y: { beginAtZero: true, grid: { color: 'rgba(0,0,0,0.04)' } },
      },
    },
  });
}

// --- Helpers ---
function fmt(n) {
  if (n == null) return '0';
  return Number(n).toLocaleString('fr-FR', { maximumFractionDigits: 0 });
}
function fmtDec(n) {
  if (n == null) return '0.00';
  return Number(n).toLocaleString('fr-FR', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}
function pctVar(cur, prev) {
  const c = Number(cur || 0), p = Number(prev || 0);
  if (p === 0) return { text: 'N/A', cls: '' };
  const v = ((c - p) / Math.abs(p) * 100).toFixed(1);
  return { text: `${v > 0 ? '+' : ''}${v}%`, cls: v >= 0 ? 'up' : 'down' };
}
