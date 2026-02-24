const { Router } = require('express');
const { spawn } = require('child_process');
const path = require('path');
const fs = require('fs');
const { GoogleGenerativeAI } = require('@google/generative-ai');

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

  const proc = spawn('py', ['-3.12', ...args], { cwd, env: { ...process.env } });

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

// POST /ai-chat
router.post('/ai-chat', async (req, res) => {
  try {
    const { message, history = [] } = req.body;
    
    if (!message) {
      return res.status(400).json({ error: 'Message requis' });
    }

    const apiKey = process.env.GEMINI_API_KEY;
    if (!apiKey) {
      return res.status(500).json({ error: 'Clé API Gemini non configurée' });
    }

    // Récupérer le dernier rapport IA si disponible
    let aiReportContext = '';
    try {
      const resultsDir = path.resolve(__dirname, '..', '..', 'ai-reporting', 'results');
      if (fs.existsSync(resultsDir)) {
        const files = fs.readdirSync(resultsDir).filter(f => f.endsWith('.json')).sort();
        if (files.length > 0) {
          const latestFile = files[files.length - 1];
          const reportContent = fs.readFileSync(path.join(resultsDir, latestFile), 'utf8');
          const report = JSON.parse(reportContent);
          
          // Créer un résumé du rapport pour le contexte
          aiReportContext = `
CONTEXTE - DERNIER RAPPORT IA GÉNÉRÉ:
Date: ${report.generated_at || 'N/A'}
IA disponible: ${report.ai_available ? 'Oui' : 'Non (mode statistique)'}

RECOMMANDATIONS PRINCIPALES:
${report.recommendations?.statistical?.slice(0, 3).map((rec, i) => 
  `${i+1}. ${rec.priorite.toUpperCase()} - ${rec.domaine}: ${rec.recommandation.substring(0, 100)}...`
).join('\n') || 'Aucune recommandation'}

INSIGHTS CLÉS:
${report.insights?.statistical?.slice(0, 3).map((insight, i) => 
  `${i+1}. ${insight.titre}: ${insight.description.substring(0, 100)}...`
).join('\n') || 'Aucun insight'}

STORYTELLING:
${report.storytelling?.ai_story?.substring(0, 200) || report.storytelling?.statistical_story?.substring(0, 200) || 'Aucun storytelling'}...
`;
        }
      }
    } catch (error) {
      console.log('Erreur lecture rapport IA:', error.message);
    }

    const genAI = new GoogleGenerativeAI(apiKey);
    const model = genAI.getGenerativeModel({ model: "gemini-2.5-flash" });

    // Construire le contexte avec l'historique et le rapport
    const chatHistory = history.map(msg => ({
      role: msg.role === 'user' ? 'user' : 'model',
      parts: [{ text: msg.content }]
    }));

    // Message système avec contexte du rapport
    const systemMessage = aiReportContext ? 
      `Tu es un assistant IA pour l'analyse de données ERP. ${aiReportContext}

Utilise ce contexte pour répondre aux questions de l'utilisateur sur les données, les recommandations et les insights. 
Si l'utilisateur pose des questions sur le rapport, base-toi sur ces informations.
Sois précis et utile.` : 
      'Tu es un assistant IA pour l\'analyse de données ERP. Aide l\'utilisateur à comprendre ses données et à prendre des décisions.';

    const chat = model.startChat({
      history: [
        { role: 'user', parts: [{ text: systemMessage }] },
        ...chatHistory
      ],
      generationConfig: {
        maxOutputTokens: 1000,
        temperature: 0.7,
      },
    });

    const result = await chat.sendMessage(message);
    const response = await result.response;
    const text = response.text();

    res.json({
      success: true,
      response: text,
      timestamp: new Date().toISOString(),
      hasContext: !!aiReportContext
    });

  } catch (error) {
    console.error('Erreur chat AI:', error);
    res.status(500).json({ 
      success: false, 
      error: error.message 
    });
  }
});

// GET /ai-status
router.get('/ai-status', (req, res) => {
  const apiKey = process.env.GEMINI_API_KEY;
  const provider = process.env.AI_PROVIDER || 'gemini';
  
  res.json({
    success: true,
    available: !!apiKey,
    provider: provider,
    status: apiKey ? 'configured' : 'missing_key'
  });
});

module.exports = router;
