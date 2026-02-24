const { Router } = require('express');
const { spawn } = require('child_process');
const path = require('path');
const fs = require('fs');

const router = Router();

let miningRunning = false;
let lastOutput = '';
let lastStatus = 'idle'; // idle | running | success | error

router.get('/status', (req, res) => {
  res.json({ status: lastStatus, running: miningRunning, output: lastOutput });
});

router.post('/run', (req, res) => {
  if (miningRunning) {
    return res.status(409).json({ error: 'Data Mining déjà en cours' });
  }

  const analysis = req.body.analysis || 'all'; // exploratory, clustering, anomaly, rfm, all
  const quick = req.body.quick === true;
  const scriptPath = path.resolve(__dirname, '..', '..', 'data_mining', 'run_mining.py');
  const cwd = path.resolve(__dirname, '..', '..');

  const args = [scriptPath];
  if (analysis !== 'all') args.push('--analysis', analysis);
  if (quick) args.push('--quick');

  miningRunning = true;
  lastStatus = 'running';
  lastOutput = '';

  console.log(`[mining] Lancement: python ${args.join(' ')} (cwd: ${cwd})`);

  const proc = spawn('py', ['-3.12', ...args], { cwd, env: { ...process.env } });

  proc.stdout.on('data', (data) => {
    lastOutput += data.toString();
  });

  proc.stderr.on('data', (data) => {
    lastOutput += data.toString();
  });

  proc.on('close', (code) => {
    miningRunning = false;
    lastStatus = code === 0 ? 'success' : 'error';
    console.log(`[mining] Termine (code ${code})`);
  });

  proc.on('error', (err) => {
    miningRunning = false;
    lastStatus = 'error';
    lastOutput += `\nErreur: ${err.message}`;
    console.error('[mining] Erreur:', err.message);
  });

  res.json({ message: 'Data Mining démarré', analysis, quick });
});

// GET /mining/results/latest
router.get('/results/latest', (req, res) => {
  try {
    const reportsDir = path.resolve(__dirname, '..', '..', 'data_mining', 'results', 'reports');
    const files = fs.readdirSync(reportsDir).filter(f => f.endsWith('.html'));
    
    if (files.length === 0) {
      return res.status(404).json({ error: 'Aucun rapport disponible' });
    }

    // Trouver le fichier le plus récent
    const latestFile = files.sort().pop();
    const reportPath = path.join(reportsDir, latestFile);
    
    // Lire le rapport HTML
    const htmlContent = fs.readFileSync(reportPath, 'utf8');
    
    // Extraire les résultats du rapport (simplifié)
    const results = {
      run_id: latestFile.replace('data_mining_report_', '').replace('.html', ''),
      timestamp: latestFile,
      report_path: `/api/mining/report/${latestFile}`,
      summary: extractSummaryFromReport(htmlContent)
    };

    res.json(results);
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// GET /mining/report/:filename
router.get('/report/:filename', (req, res) => {
  try {
    const filename = req.params.filename;
    const reportPath = path.resolve(__dirname, '..', '..', 'data_mining', 'results', 'reports', filename);
    
    if (!fs.existsSync(reportPath)) {
      return res.status(404).json({ error: 'Rapport non trouvé' });
    }

    res.sendFile(reportPath);
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// GET /mining/results/clusters
router.get('/results/clusters', (req, res) => {
  try {
    const clustersPath = path.resolve(__dirname, '..', '..', 'data_mining', 'results', 'data', 'customers_with_clusters.csv');
    
    if (!fs.existsSync(clustersPath)) {
      return res.status(404).json({ error: 'Donnees de clustering non disponibles' });
    }

    const csvContent = fs.readFileSync(clustersPath, 'utf8');
    const lines = csvContent.split('\n').filter(l => l.trim());
    const headers = lines[0].split(',').map(h => h.trim());

    // Index dynamique par nom de colonne
    const col = (name) => headers.indexOf(name);
    const iName = col('customer_name');
    const iCA = col('ca_total');
    const iOrders = col('nb_commandes');
    const iCluster = col('cluster');

    if (iCluster < 0) {
      return res.status(500).json({ error: 'Colonne cluster introuvable dans le CSV' });
    }

    const clusters = {};
    for (let i = 1; i < lines.length; i++) {
      const values = lines[i].split(',');
      const clusterId = values[iCluster >= 0 ? iCluster : values.length - 1];
      if (clusterId == null || clusterId.trim() === '') continue;

      if (!clusters[clusterId]) {
        clusters[clusterId] = { cluster_id: parseInt(clusterId), n_customers: 0, customers: [] };
      }
      clusters[clusterId].n_customers++;
      clusters[clusterId].customers.push({
        customer_name: iName >= 0 ? values[iName] : '',
        ca_total: iCA >= 0 ? parseFloat(values[iCA] || 0) : 0,
        nb_commandes: iOrders >= 0 ? parseInt(values[iOrders] || 0) : 0
      });
    }

    const totalCustomers = Object.values(clusters).reduce((s, c) => s + c.n_customers, 0);

    // Calculer moyennes et profil dynamique
    const clusterList = Object.values(clusters);
    clusterList.forEach(cluster => {
      const totalCA = cluster.customers.reduce((s, c) => s + c.ca_total, 0);
      const totalOrd = cluster.customers.reduce((s, c) => s + c.nb_commandes, 0);
      cluster.avg_ca_total = totalCA / cluster.n_customers;
      cluster.avg_nb_commandes = totalOrd / cluster.n_customers;
      cluster.percentage = (cluster.n_customers / totalCustomers) * 100;
      delete cluster.customers;
    });

    // Profils dynamiques : trier par CA moyen desc pour attribuer les labels
    const sorted = [...clusterList].sort((a, b) => b.avg_ca_total - a.avg_ca_total);
    const labels = [
      'Clients VIP - Forte valeur',
      'Clients reguliers - Valeur moyenne',
      'Clients occasionnels - Faible valeur',
      'Clients inactifs - Tres faible valeur',
    ];
    sorted.forEach((c, i) => { c.profile = labels[Math.min(i, labels.length - 1)]; });

    res.json({ n_clusters: clusterList.length, clusters: clusterList });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// GET /mining/results/anomalies
router.get('/results/anomalies', (req, res) => {
  try {
    const anomaliesPath = path.resolve(__dirname, '..', '..', 'data_mining', 'results', 'data', 'transactions_with_anomalies.csv');

    if (!fs.existsSync(anomaliesPath)) {
      return res.status(404).json({ error: 'Donnees d\'anomalies non disponibles' });
    }

    const csvContent = fs.readFileSync(anomaliesPath, 'utf8');
    const lines = csvContent.split('\n').filter(l => l.trim());
    const headers = lines[0].split(',').map(h => h.trim());

    const col = (name) => headers.indexOf(name);
    const iOrderId = col('order_id');
    const iSales = col('sales_amount');
    const iCustomer = col('customer_name');
    const iCountry = col('country');
    const iNbLignes = col('nb_lignes');
    const iIsAnomaly = col('is_anomaly');
    const iScore = col('anomaly_score');

    const anomalies = [];
    const normal = [];

    for (let i = 1; i < lines.length; i++) {
      const values = lines[i].split(',');
      const isAnomaly = (iIsAnomaly >= 0 ? values[iIsAnomaly] : '').trim() === 'True';

      const transaction = {
        order_id: iOrderId >= 0 ? values[iOrderId] : '',
        customer_name: iCustomer >= 0 ? values[iCustomer] : '',
        sales_amount: iSales >= 0 ? parseFloat(values[iSales] || 0) : 0,
        nb_lignes: iNbLignes >= 0 ? parseInt(values[iNbLignes] || 0) : 0,
        country: iCountry >= 0 ? values[iCountry] : '',
        anomaly_score: iScore >= 0 ? parseFloat(values[iScore] || 0) : 0
      };

      if (isAnomaly) { anomalies.push(transaction); }
      else { normal.push(transaction); }
    }

    const totalTransactions = anomalies.length + normal.length;
    const anomalyRate = totalTransactions > 0 ? (anomalies.length / totalTransactions) * 100 : 0;

    const avgNormal = normal.length > 0
      ? normal.reduce((s, t) => s + t.sales_amount, 0) / normal.length : 0;
    const avgAnomaly = anomalies.length > 0
      ? anomalies.reduce((s, a) => s + a.sales_amount, 0) / anomalies.length : 0;

    // Types d'anomalies
    const highThreshold = avgNormal * 3;
    const highAmountAnomalies = anomalies.filter(a => a.sales_amount > highThreshold);
    const lowAmountAnomalies = anomalies.filter(a => a.sales_amount < avgNormal * 0.1 && a.sales_amount > 0);

    const anomalyTypes = [];
    if (highAmountAnomalies.length > 0) {
      anomalyTypes.push({
        type: 'Montants anormalement eleves',
        count: highAmountAnomalies.length,
        description: `Transactions > ${highThreshold.toFixed(0)} EUR (3x la moyenne)`,
        avg_amount: highAmountAnomalies.reduce((s, a) => s + a.sales_amount, 0) / highAmountAnomalies.length
      });
    }
    if (lowAmountAnomalies.length > 0) {
      anomalyTypes.push({
        type: 'Montants anormalement bas',
        count: lowAmountAnomalies.length,
        description: `Transactions < ${(avgNormal * 0.1).toFixed(0)} EUR`,
        avg_amount: lowAmountAnomalies.reduce((s, a) => s + a.sales_amount, 0) / lowAmountAnomalies.length
      });
    }
    const otherCount = anomalies.length - highAmountAnomalies.length - lowAmountAnomalies.length;
    if (otherCount > 0) {
      anomalyTypes.push({
        type: 'Autres patterns atypiques',
        count: otherCount,
        description: 'Combinaisons inhabituelles de quantite, prix ou frequence'
      });
    }

    // Trier anomalies par score (les plus anormales d'abord)
    anomalies.sort((a, b) => a.anomaly_score - b.anomaly_score);

    res.json({
      total_transactions: totalTransactions,
      n_anomalies: anomalies.length,
      anomaly_rate: anomalyRate,
      anomaly_types: anomalyTypes,
      anomalies: anomalies.slice(0, 30),
      stats: { avg_amount_normal: avgNormal, avg_amount_anomaly: avgAnomaly }
    });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// GET /mining/results/rfm
router.get('/results/rfm', (req, res) => {
  try {
    const rfmPath = path.resolve(__dirname, '..', '..', 'data_mining', 'results', 'data', 'rfm_segments.csv');

    if (!fs.existsSync(rfmPath)) {
      return res.status(404).json({ error: 'Donnees RFM non disponibles' });
    }

    const csvContent = fs.readFileSync(rfmPath, 'utf8');
    const lines = csvContent.split('\n').filter(l => l.trim());
    const headers = lines[0].split(',').map(h => h.trim());

    const col = (name) => headers.indexOf(name);
    const iSeg = col('segment');
    const iN = col('n_customers');
    const iPct = col('percentage');
    const iRec = col('avg_recency');
    const iFreq = col('avg_frequency');
    const iMon = col('avg_monetary');
    const iOV = col('avg_order_value');

    const segments = [];
    for (let i = 1; i < lines.length; i++) {
      const values = lines[i].split(',');
      segments.push({
        segment: iSeg >= 0 ? values[iSeg] : values[0],
        n_customers: parseInt(values[iN >= 0 ? iN : 1] || 0),
        percentage: parseFloat(values[iPct >= 0 ? iPct : 2] || 0),
        avg_recency: parseFloat(values[iRec >= 0 ? iRec : 3] || 0),
        avg_frequency: parseFloat(values[iFreq >= 0 ? iFreq : 4] || 0),
        avg_monetary: parseFloat(values[iMon >= 0 ? iMon : 5] || 0),
        avg_order_value: parseFloat(values[iOV >= 0 ? iOV : 7] || 0)
      });
    }

    // Recommandations par segment
    const recMap = {
      'Champions': 'Programme VIP, offres exclusives, early access nouveaux produits',
      'Clients fideles': 'Programme de fidelite, remises progressives, service prioritaire',
      'Clients potentiels': 'Cross-selling, up-selling, programmes de recommandation',
      'Nouveaux clients': 'Programme de bienvenue, tutoriels produits, offre decouverte',
      'Clients a risque': 'Campagne de reactivation, enquetes satisfaction, offres speciales',
      'Clients perdus': 'Campagne de reconquete, enquetes sur les raisons du depart',
      'Autres segments': 'Analyse comportementale approfondie, segmentation affinee',
    };

    const recommendations = segments.map(seg => {
      // Matching flexible (accents ou pas)
      const key = Object.keys(recMap).find(k =>
        seg.segment.toLowerCase().includes(k.toLowerCase().slice(0, 8))
      );
      return {
        segment: seg.segment,
        n_customers: seg.n_customers,
        avg_monetary: seg.avg_monetary,
        recommendation: key ? recMap[key] : 'Analyse specifique recommandee'
      };
    });

    res.json({
      n_customers: segments.reduce((s, seg) => s + seg.n_customers, 0),
      n_segments: segments.length,
      segments,
      recommendations
    });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// GET /mining/plot/:plot_name
router.get('/plot/:plotName', (req, res) => {
  try {
    const plotName = req.params.plotName;
    const plotPath = path.resolve(__dirname, '..', '..', 'data_mining', 'results', 'plots', `${plotName}.png`);
    
    if (!fs.existsSync(plotPath)) {
      return res.status(404).json({ error: 'Graphique non trouvé' });
    }

    res.sendFile(plotPath);
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

function extractSummaryFromReport(htmlContent) {
  // Extraction simplifiée du résumé depuis le HTML
  const summary = {};
  
  // Chercher les sections d'analyses
  const analyses = ['Exploratoire', 'Clustering', 'Anomalies', 'RFM'];
  analyses.forEach(analysis => {
    const regex = new RegExp(`${analysis}.*?\\[OK\\].*?([\\d,]+) ([^\\n]+)`, 'i');
    const match = htmlContent.match(regex);
    if (match) {
      summary[analysis.toLowerCase()] = {
        success: true,
        message: `${match[1]} ${match[2]}`
      };
    } else {
      summary[analysis.toLowerCase()] = {
        success: false,
        message: 'Non disponible'
      };
    }
  });
  
  return summary;
}

module.exports = router;
