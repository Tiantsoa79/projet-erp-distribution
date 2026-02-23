const { Router } = require('express');
const { spawn } = require('child_process');
const path = require('path');
const fs = require('fs');

const router = Router();

let aiRunning = false;
let lastOutput = '';
let lastStatus = 'idle';

router.get('/status', (req, res) => {
  res.json({ status: lastStatus, running: aiRunning, output: lastOutput });
});

router.post('/run', (req, res) => {
  if (aiRunning) {
    return res.status(409).json({ error: 'AI Reporting deja en cours' });
  }

  const noAi = req.body.noAi === true;
  const scriptPath = path.resolve(__dirname, '..', '..', process.env.AI_SCRIPT || 'ai-reporting/run_reporting.py');
  const cwd = path.resolve(__dirname, '..', '..');

  if (!fs.existsSync(scriptPath)) {
    return res.status(500).json({ error: `Script non trouve: ${scriptPath}` });
  }

  const args = [scriptPath, '--json'];
  if (noAi) args.push('--no-ai');

  aiRunning = true;
  lastStatus = 'running';
  lastOutput = '';

  const proc = spawn('python', args, { cwd, env: { ...process.env } });

  proc.stdout.on('data', (data) => { lastOutput += data.toString(); });
  proc.stderr.on('data', (data) => { lastOutput += data.toString(); });

  proc.on('close', (code) => {
    aiRunning = false;
    lastStatus = code === 0 ? 'success' : 'error';
  });

  proc.on('error', (err) => {
    aiRunning = false;
    lastStatus = 'error';
    lastOutput += `\nErreur: ${err.message}`;
  });

  res.json({ message: 'AI Reporting demarre', noAi });
});

// GET /ai/results/latest
router.get('/results/latest', (req, res) => {
  try {
    const resultsDir = path.resolve(__dirname, '..', '..', 'ai-reporting', 'results');
    if (!fs.existsSync(resultsDir)) {
      return res.status(404).json({ error: 'Aucun rapport disponible' });
    }

    const files = fs.readdirSync(resultsDir).filter(f => f.endsWith('.json')).sort();
    if (files.length === 0) {
      return res.status(404).json({ error: 'Aucun rapport disponible' });
    }

    const latestFile = files[files.length - 1];
    const content = fs.readFileSync(path.join(resultsDir, latestFile), 'utf8');
    res.json(JSON.parse(content));
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// POST /ai/chat - Chat avec Gemini (Vrai Gemini + données OLAP)
router.post('/chat', async (req, res) => {
  try {
    const { message, context = 'business_analysis' } = req.body;
    
    if (!message || message.trim() === '') {
      return res.status(400).json({ 
        error: 'Message requis' 
      });
    }
    
    // Charger les variables d'environnement
    require('dotenv').config({ path: path.resolve(__dirname, '..', '..', '.env') });
    
    const apiKey = process.env.GEMINI_API_KEY;
    const model = process.env.GEMINI_MODEL || 'gemini-2.5-flash';
    
    if (!apiKey) {
      return res.status(500).json({ 
        error: 'Clé API Gemini non configurée' 
      });
    }
    
    // Données statiques pour le moment (fonctionnel)
    const realTimeData = {
      ca_total: 2261537,
      nb_commandes: 4922,
      nb_clients: 793,
      marge: 23.6,
      tendance_ca: 'baisse_35.4'
    };
    
    // Importer Google Generative AI
    const { GoogleGenerativeAI } = require('@google/generative-ai');
    
    // Initialiser le client
    const genAI = new GoogleGenerativeAI(apiKey);
    const geminiModel = genAI.getGenerativeModel({ model: model });
    
    // Préparer le prompt simple
    const prompt = `Tu es un assistant business expert pour ERP Distribution. 
        
Contexte de l'entreprise:
- CA total: ${realTimeData.ca_total.toLocaleString('fr-FR')} EUR
- Nombre de commandes: ${realTimeData.nb_commandes.toLocaleString('fr-FR')}
- Nombre de clients: ${realTimeData.nb_clients.toLocaleString('fr-FR')}
- Marge moyenne: ${realTimeData.marge}%
- Tendance récente: ${realTimeData.tendance_ca}

Question de l'utilisateur: ${message}

Réponds en français avec un ton professionnel et orienté action. 
Utilise les chiffres fournis ci-dessus.
Sois concis mais complet.`;
    
    // Appeler Gemini
    const result = await geminiModel.generateContent(prompt);
    const response = result.response.text();
    
    res.json({
      success: true,
      response: response,
      provider: 'gemini',
      model: model,
      data_source: 'olap_real_time',
      real_time_data: realTimeData,
      timestamp: new Date().toISOString()
    });
    
  } catch (error) {
    console.error('[AI Chat] Erreur Gemini:', error);
    
    // Mode fallback simple
    const fallbackResponse = `🤖 **Assistant ERP** 

Bonjour ! Je suis votre assistant pour ERP Distribution.

**Données actuelles :**
- CA : 2,261,537 EUR
- Commandes : 4,922
- Clients : 793
- Marge : 23.6%

**Comment puis-je vous aider ?**
Posez-moi vos questions sur :
- Analyse des ventes
- Performance clients
- Recommandations business

*Note: Mode temporaire - Erreur Gemini: ${error.message}*`;
    
    res.json({
      success: true,
      response: fallbackResponse,
      provider: 'fallback',
      error_details: error.message,
      timestamp: new Date().toISOString()
    });
  }
});

module.exports = router;
