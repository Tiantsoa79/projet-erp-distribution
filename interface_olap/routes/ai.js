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

module.exports = router;
