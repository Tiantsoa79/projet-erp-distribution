/**
 * API client - Interface OLAP
 */
const API = {
  base: '',

  async get(path) {
    const res = await fetch(`${this.base}${path}`);
    if (!res.ok) throw new Error(`API ${res.status}: ${res.statusText}`);
    return res.json();
  },

  async post(path, body = {}) {
    const res = await fetch(`${this.base}${path}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    if (!res.ok && res.status !== 409) throw new Error(`API ${res.status}: ${res.statusText}`);
    return res.json();
  },

  // Pipeline endpoints
  getPipelineStatus() { return this.get('/api/pipeline/status'); },
  runPipeline(force = false) { return this.post('/api/pipeline/run', { force }); },

  
  // Dashboard endpoints
  getStrategic()  { return this.get('/api/dashboard/strategic'); },
  getTactical()   { return this.get('/api/dashboard/tactical'); },
  getOperational(){ return this.get('/api/dashboard/operational'); },

  // Data Mining endpoints
  async runMining(analysis = 'all', quick = false) {
    const response = await fetch('/api/mining/run', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ analysis, quick })
    });
    return response.json();
  },

  async getMiningStatus() {
    const response = await fetch('/api/mining/status');
    return response.json();
  },

  async getMiningResults() {
    const response = await fetch('/api/mining/results/latest');
    return response.json();
  },

  async getMiningClusters() {
    const response = await fetch('/api/mining/results/clusters');
    return response.json();
  },

  async getMiningAnomalies() {
    const response = await fetch('/api/mining/results/anomalies');
    return response.json();
  },

  async getMiningRFM() {
    const response = await fetch('/api/mining/results/rfm');
    return response.json();
  },

  async getMiningPlot(plotName) {
    const response = await fetch(`/api/mining/plot/${plotName}`);
    return response.blob();
  },
};
