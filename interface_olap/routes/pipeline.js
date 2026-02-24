const { Router } = require('express');
const { spawn } = require('child_process');
const path = require('path');

const router = Router();

let pipelineRunning = false;
let lastOutput = '';
let lastStatus = 'idle'; // idle | running | success | error

router.get('/status', (req, res) => {
  res.json({ status: lastStatus, running: pipelineRunning, output: lastOutput });
});

router.post('/run', (req, res) => {
  if (pipelineRunning) {
    return res.status(409).json({ error: 'Pipeline deja en cours' });
  }

  const force = req.body.force === true;
  const projectRoot = path.resolve(__dirname, '..', '..');
  const scriptPath = path.resolve(projectRoot, process.env.PIPELINE_SCRIPT || 'BI/run_pipeline.py');
  const cwd = projectRoot;

  const args = [scriptPath];
  if (force) args.push('--force');

  pipelineRunning = true;
  lastStatus = 'running';
  lastOutput = '';

  console.log(`[pipeline] Lancement: python ${args.join(' ')} (cwd: ${cwd})`);
  console.log(`[pipeline] Script path: ${scriptPath}`);
  console.log(`[pipeline] CWD: ${cwd}`);
  console.log(`[pipeline] Force: ${force}`);

  // Vérifier que le script existe
  const fs = require('fs');
  if (!fs.existsSync(scriptPath)) {
    pipelineRunning = false;
    lastStatus = 'error';
    const msg = `Script non trouvé: ${scriptPath}`;
    lastOutput = msg;
    console.error(`[pipeline] ${msg}`);
    return res.status(500).json({ error: msg });
  }

  const proc = spawn('py', ['-3.12', ...args], { cwd, env: { ...process.env } });

  proc.stdout.on('data', (data) => {
    lastOutput += data.toString();
  });

  proc.stderr.on('data', (data) => {
    lastOutput += data.toString();
  });

  proc.on('close', (code) => {
    pipelineRunning = false;
    lastStatus = code === 0 ? 'success' : 'error';
    console.log(`[pipeline] Termine (code ${code})`);
  });

  proc.on('error', (err) => {
    pipelineRunning = false;
    lastStatus = 'error';
    lastOutput += `\nErreur: ${err.message}`;
    console.error('[pipeline] Erreur:', err.message);
  });

  res.json({ message: 'Pipeline demarre', force });
});

module.exports = router;
