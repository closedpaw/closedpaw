#!/usr/bin/env node

/**
 * ClosedPaw CLI - Zero-Trust AI Assistant
 * 
 * Install: npm install -g closedpaw
 * Usage: closedpaw install
 */

const { Command } = require('commander');
const { execa } = require('execa');
const chalk = require('chalk');
const ora = require('ora');
const inquirer = require('inquirer');
const boxen = require('boxen');
const path = require('path');
const fs = require('fs');
const os = require('os');
const http = require('http');

const program = new Command();

const INSTALL_DIR = path.join(os.homedir(), '.closedpaw');
const CONFIG_DIR = path.join(os.homedir(), '.config', 'closedpaw');
const DATA_DIR = path.join(CONFIG_DIR, 'data');

// Ensure directories exist
if (!fs.existsSync(CONFIG_DIR)) {
  fs.mkdirSync(CONFIG_DIR, { recursive: true });
}
if (!fs.existsSync(DATA_DIR)) {
  fs.mkdirSync(DATA_DIR, { recursive: true });
}

// Banner
function showBanner() {
  console.log(boxen(
    chalk.cyan.bold('ClosedPaw') + '\n' +
    chalk.gray('Zero-Trust AI Assistant') + '\n\n' +
    chalk.green('🔒 Security-first architecture') + '\n' +
    chalk.green('🏠 Runs 100% locally') + '\n' +
    chalk.green('✓ Hardened sandboxing'),
    {
      padding: 1,
      margin: 1,
      borderStyle: 'round',
      borderColor: 'cyan'
    }
  ));
}

// Check if Python is installed
async function checkPython() {
  const pythonCommands = process.platform === 'win32' 
    ? ['python', 'python3', 'py'] 
    : ['python3', 'python'];
  
  for (const cmd of pythonCommands) {
    try {
      const { stdout, stderr } = await execa(cmd, ['--version'], { reject: false });
      const output = stdout || stderr || '';
      const version = output.match(/Python (\d+)\.(\d+)/i);
      if (version) {
        const major = parseInt(version[1]);
        const minor = parseInt(version[2]);
        if (major > 3 || (major === 3 && minor >= 11)) {
          return true;
        }
      }
    } catch {
      continue;
    }
  }
  return false;
}

// Check if Ollama is installed
async function checkOllama() {
  try {
    await execa('ollama', ['--version']);
    return true;
  } catch {
    return false;
  }
}

// Install ClosedPaw
async function installClosedPaw(options) {
  showBanner();

  // Check dependencies
  const pythonSpinner = ora('Checking Python...').start();
  const hasPython = await checkPython();
  if (!hasPython) {
    pythonSpinner.fail('Python 3.11+ not found. Please install from https://python.org');
    process.exit(1);
  }
  pythonSpinner.succeed('Python 3.11+ found');

  const ollamaSpinner = ora('Checking Ollama...').start();
  const hasOllama = await checkOllama();
  if (!hasOllama) {
    ollamaSpinner.warn('Ollama not found (will be installed)');
  } else {
    ollamaSpinner.succeed('Ollama found');
  }

  // Ask for model download
  if (!options.skipModel && hasOllama) {
    const { downloadModel } = await inquirer.prompt([
      {
        type: 'confirm',
        name: 'downloadModel',
        message: 'Download a recommended LLM model? (2-4GB)',
        default: false
      }
    ]);

    if (downloadModel) {
      const { model } = await inquirer.prompt([
        {
          type: 'list',
          name: 'model',
          message: 'Select a model:',
          choices: [
            { name: 'llama3.2:3b - Fast, good for chat (~2GB)', value: 'llama3.2:3b' },
            { name: 'mistral:7b - Balance of speed/quality (~4GB)', value: 'mistral:7b' },
            { name: 'qwen2.5:7b - Excellent for code (~4GB)', value: 'qwen2.5:7b' }
          ]
        }
      ]);

      const modelSpinner = ora(`Downloading ${model}...`).start();
      try {
        await execa('ollama', ['pull', model], { stdio: 'inherit' });
        modelSpinner.succeed(`${model} installed`);
      } catch {
        modelSpinner.fail('Failed to download model');
      }
    }
  }

  // Create directories
  const dirSpinner = ora('Creating directories...').start();
  fs.mkdirSync(INSTALL_DIR, { recursive: true });
  fs.mkdirSync(CONFIG_DIR, { recursive: true });
  dirSpinner.succeed('Directories created');

  // Clone repository
  const cloneSpinner = ora('Downloading ClosedPaw...').start();
  try {
    // Remove existing installation
    if (fs.existsSync(path.join(INSTALL_DIR, 'backend'))) {
      fs.rmSync(path.join(INSTALL_DIR, 'backend'), { recursive: true });
    }
    if (fs.existsSync(path.join(INSTALL_DIR, 'frontend'))) {
      fs.rmSync(path.join(INSTALL_DIR, 'frontend'), { recursive: true });
    }

    // Clone
    await execa('git', [
      'clone',
      '--depth', '1',
      'https://github.com/logansin/closedpaw.git',
      INSTALL_DIR
    ], { stdio: 'pipe' });
    cloneSpinner.succeed('ClosedPaw downloaded');
  } catch (error) {
    cloneSpinner.fail('Failed to clone repository');
    console.error(chalk.red(error.message));
    process.exit(1);
  }

  // Install Python dependencies
  const pipSpinner = ora('Installing Python dependencies...').start();
  try {
    const venvPath = process.platform === 'win32'
      ? path.join(INSTALL_DIR, 'venv', 'Scripts', 'python')
      : path.join(INSTALL_DIR, 'venv', 'bin', 'python');

    await execa('python', ['-m', 'venv', path.join(INSTALL_DIR, 'venv')]);
    await execa(venvPath, ['-m', 'pip', 'install', '--upgrade', 'pip'], { stdio: 'pipe' });
    await execa(venvPath, ['-m', 'pip', 'install', 
      'fastapi', 'uvicorn', 'pydantic', 'pydantic-ai', 
      'httpx', 'sqlalchemy', 'python-multipart',
      'python-jose[cryptography]', 'passlib[bcrypt]'
    ], { stdio: 'pipe' });
    pipSpinner.succeed('Python dependencies installed');
  } catch (error) {
    pipSpinner.fail('Failed to install Python dependencies');
    console.error(chalk.red(error.message));
    process.exit(1);
  }

  // Install frontend dependencies
  const npmSpinner = ora('Installing frontend dependencies...').start();
  try {
    await execa('npm', ['install', '--legacy-peer-deps'], {
      cwd: path.join(INSTALL_DIR, 'frontend'),
      stdio: 'pipe'
    });
    npmSpinner.succeed('Frontend dependencies installed');
  } catch (error) {
    npmSpinner.fail('Failed to install frontend dependencies');
    console.error(chalk.red(error.message));
    process.exit(1);
  }

  // Success message
  console.log('\n' + boxen(
    chalk.green.bold('✓ Installation Complete!') + '\n\n' +
    chalk.white('Start ClosedPaw:') + '\n' +
    chalk.cyan('  closedpaw start') + '\n\n' +
    chalk.white('Web UI: ') + chalk.gray('http://localhost:3000') + '\n' +
    chalk.white('API:    ') + chalk.gray('http://localhost:8000'),
    {
      padding: 1,
      borderStyle: 'round',
      borderColor: 'green'
    }
  ));
}

// Start ClosedPaw
async function startClosedPaw() {
  const spinner = ora('Starting ClosedPaw...').start();

  try {
    const venvPython = process.platform === 'win32'
      ? path.join(INSTALL_DIR, 'venv', 'Scripts', 'python')
      : path.join(INSTALL_DIR, 'venv', 'bin', 'python');

    // Check if installed
    if (!fs.existsSync(venvPython)) {
      spinner.fail('ClosedPaw not installed. Run: closedpaw install');
      process.exit(1);
    }

    // Start backend
    spinner.text = 'Starting backend...';
    const backend = execa(venvPython, ['-m', 'uvicorn', 'app.main:app', 
      '--host', '127.0.0.1', '--port', '8000'], {
      cwd: path.join(INSTALL_DIR, 'backend'),
      stdio: 'inherit'
    });

    // Start frontend
    spinner.text = 'Starting frontend...';
    const frontend = execa('npm', ['run', 'dev'], {
      cwd: path.join(INSTALL_DIR, 'frontend'),
      stdio: 'inherit'
    });

    spinner.succeed('ClosedPaw started!');
    
    console.log('\n' + boxen(
      chalk.cyan.bold('ClosedPaw is running') + '\n\n' +
      chalk.white('Web UI: ') + chalk.blue('http://localhost:3000') + '\n' +
      chalk.white('API:    ') + chalk.blue('http://localhost:8000') + '\n\n' +
      chalk.gray('Press Ctrl+C to stop'),
      { padding: 1, borderStyle: 'round', borderColor: 'cyan' }
    ));

    // Wait for processes
    await Promise.race([backend, frontend]);

  } catch (error) {
    spinner.fail('Failed to start ClosedPaw');
    console.error(chalk.red(error.message));
    process.exit(1);
  }
}

// Stop ClosedPaw
async function stopClosedPaw() {
  const spinner = ora('Stopping ClosedPaw...').start();
  
  try {
    if (process.platform === 'win32') {
      await execa('taskkill', ['/F', '/IM', 'uvicorn.exe'], { reject: false });
      await execa('taskkill', ['/F', '/IM', 'node.exe'], { reject: false });
    } else {
      await execa('pkill', ['-f', 'uvicorn'], { reject: false });
      await execa('pkill', ['-f', 'next'], { reject: false });
    }
    spinner.succeed('ClosedPaw stopped');
  } catch {
    spinner.fail('Failed to stop');
  }
}

// Show status
async function showStatus() {
  console.log('\n' + chalk.cyan.bold('ClosedPaw Status') + '\n');
  
  // Check installation
  const installed = fs.existsSync(INSTALL_DIR);
  console.log(chalk.white('Installed: ') + (installed ? chalk.green('Yes') : chalk.red('No')));
  
  if (installed) {
    console.log(chalk.white('Location:  ') + chalk.gray(INSTALL_DIR));
    console.log(chalk.white('Config:    ') + chalk.gray(CONFIG_DIR));
    console.log(chalk.white('Data:      ') + chalk.gray(DATA_DIR));
  }

  // Check Python
  const hasPython = await checkPython();
  console.log(chalk.white('Python:    ') + (hasPython ? chalk.green('✓') : chalk.red('✗')));

  // Check Node.js
  try {
    const nodeVersion = process.version;
    console.log(chalk.white('Node.js:   ') + chalk.green('✓ ') + chalk.gray(nodeVersion));
  } catch {
    console.log(chalk.white('Node.js:   ') + chalk.red('✗'));
  }

  // Check Ollama
  const hasOllama = await checkOllama();
  console.log(chalk.white('Ollama:    ') + (hasOllama ? chalk.green('✓') : chalk.yellow('Not installed')));

  // Check running
  await checkAPIStatus();
}

// Check API status
async function checkAPIStatus() {
  return new Promise((resolve) => {
    const req = http.get('http://127.0.0.1:8000/api/status', (res) => {
      let data = '';
      res.on('data', chunk => data += chunk);
      res.on('end', () => {
        try {
          const status = JSON.parse(data);
          console.log(chalk.white('API:       ') + chalk.green('Running'));
          console.log(chalk.white('Ollama:    ') + (status.ollama_connected ? chalk.green('Connected') : chalk.yellow('Disconnected')));
          console.log(chalk.white('Pending:   ') + chalk.yellow(status.pending_actions + ' actions'));
          resolve(true);
        } catch {
          console.log(chalk.white('API:       ') + chalk.green('Running'));
          resolve(true);
        }
      });
    });
    req.on('error', () => {
      console.log(chalk.white('API:       ') + chalk.gray('Not running'));
      resolve(false);
    });
    req.setTimeout(2000, () => {
      console.log(chalk.white('API:       ') + chalk.gray('Not running'));
      req.destroy();
      resolve(false);
    });
  });
}

// Run diagnostics
async function runDoctor() {
  console.log('\n' + chalk.cyan.bold('ClosedPaw Diagnostics') + '\n');
  
  const checks = [];
  
  // Check 1: Installation
  const installCheck = fs.existsSync(INSTALL_DIR) && fs.existsSync(path.join(INSTALL_DIR, 'backend'));
  checks.push({
    name: 'Installation',
    status: installCheck,
    message: installCheck ? 'OK' : 'Not installed. Run: closedpaw install',
    fix: !installCheck ? 'closedpaw install' : null
  });
  
  // Check 2: Python
  let pythonVersion = null;
  try {
    const { stdout } = await execa('python', ['--version'], { reject: false });
    pythonVersion = stdout;
  } catch {}
  const pythonOk = pythonVersion && pythonVersion.includes('3.');
  checks.push({
    name: 'Python 3.11+',
    status: pythonOk,
    message: pythonVersion || 'Not found',
    fix: !pythonOk ? 'Install from https://python.org' : null
  });
  
  // Check 3: Node.js
  const nodeOk = true; // We're running in Node
  checks.push({
    name: 'Node.js',
    status: nodeOk,
    message: process.version
  });
  
  // Check 4: Ollama
  let ollamaOk = false;
  try {
    await execa('ollama', ['--version'], { reject: false });
    ollamaOk = true;
  } catch {}
  checks.push({
    name: 'Ollama',
    status: ollamaOk,
    message: ollamaOk ? 'Installed' : 'Not found (optional)',
    fix: !ollamaOk ? 'curl -fsSL https://ollama.com/install.sh | sh' : null
  });
  
  // Check 5: Virtual environment
  const venvPath = process.platform === 'win32'
    ? path.join(INSTALL_DIR, 'venv', 'Scripts', 'python.exe')
    : path.join(INSTALL_DIR, 'venv', 'bin', 'python');
  const venvOk = fs.existsSync(venvPath);
  checks.push({
    name: 'Virtual Environment',
    status: venvOk,
    message: venvOk ? 'OK' : 'Not created',
    fix: !venvOk ? 'Run: closedpaw install' : null
  });
  
  // Check 6: Frontend dependencies
  const nodeModulesOk = fs.existsSync(path.join(INSTALL_DIR, 'frontend', 'node_modules'));
  checks.push({
    name: 'Frontend Dependencies',
    status: nodeModulesOk,
    message: nodeModulesOk ? 'OK' : 'Not installed',
    fix: !nodeModulesOk ? 'cd ~/.closedpaw/frontend && npm install' : null
  });
  
  // Check 7: API endpoint
  let apiOk = false;
  try {
    await new Promise((resolve, reject) => {
      const req = http.get('http://127.0.0.1:8000/', { timeout: 2000 }, (res) => {
        apiOk = res.statusCode === 200;
        resolve();
      });
      req.on('error', reject);
      req.on('timeout', () => { req.destroy(); reject(); });
    });
  } catch {}
  checks.push({
    name: 'API Server',
    status: apiOk,
    message: apiOk ? 'Running on port 8000' : 'Not running',
    fix: !apiOk ? 'Run: closedpaw start' : null
  });
  
  // Check 8: Config directory
  const configOk = fs.existsSync(CONFIG_DIR);
  checks.push({
    name: 'Config Directory',
    status: configOk,
    message: configOk ? CONFIG_DIR : 'Not created'
  });
  
  // Print results
  console.log('Check Results:');
  console.log('─'.repeat(50));
  
  for (const check of checks) {
    const icon = check.status ? chalk.green('✓') : chalk.red('✗');
    console.log(`${icon} ${check.name.padEnd(20)} ${chalk.gray(check.message)}`);
    if (check.fix && !check.status) {
      console.log(chalk.yellow(`  → Fix: ${check.fix}`));
    }
  }
  
  // Summary
  const passed = checks.filter(c => c.status).length;
  const total = checks.length;
  
  console.log('\n' + '─'.repeat(50));
  console.log(`Summary: ${passed}/${total} checks passed`);
  
  if (passed === total) {
    console.log(chalk.green('\n✓ All systems operational!'));
  } else {
    console.log(chalk.yellow('\n⚠ Some checks failed. Follow the fix suggestions above.'));
  }
}

// Migrate from other systems
async function migrateSystem(source) {
  const spinner = ora(`Migrating from ${source}...`).start();
  
  const sources = {
    openclaw: {
      path: path.join(os.homedir(), '.openclaw'),
      dataPath: path.join(os.homedir(), '.openclaw', 'data'),
      description: 'OpenClaw memory and settings'
    },
    'securesphere': {
      path: path.join(os.homedir(), '.securesphere-ai'),
      dataPath: path.join(os.homedir(), '.config', 'securesphere-ai'),
      description: 'SecureSphere AI memory and settings'
    }
  };
  
  const sourceConfig = sources[source.toLowerCase()];
  if (!sourceConfig) {
    spinner.fail(`Unknown source: ${source}`);
    console.log('Available sources:', Object.keys(sources).join(', '));
    return;
  }
  
  if (!fs.existsSync(sourceConfig.path)) {
    spinner.fail(`${source} installation not found at ${sourceConfig.path}`);
    return;
  }
  
  try {
    // Copy memory files
    if (fs.existsSync(sourceConfig.dataPath)) {
      const files = fs.readdirSync(sourceConfig.dataPath);
      let migrated = 0;
      
      for (const file of files) {
        if (file.endsWith('.json') || file.endsWith('.md')) {
          const srcPath = path.join(sourceConfig.dataPath, file);
          const destPath = path.join(DATA_DIR, file);
          
          if (!fs.existsSync(destPath)) {
            fs.copyFileSync(srcPath, destPath);
            migrated++;
          }
        }
      }
      
      spinner.succeed(`Migrated ${migrated} files from ${source}`);
    } else {
      spinner.succeed(`No data to migrate from ${source}`);
    }
  } catch (error) {
    spinner.fail(`Migration failed: ${error.message}`);
  }
}

// Configure providers
async function configureProviders() {
  console.log('\n' + chalk.cyan.bold('Configure Providers') + '\n');
  
  const providers = [
    { name: 'Ollama (Local)', value: 'ollama', default: true },
    { name: 'OpenAI', value: 'openai' },
    { name: 'Anthropic (Claude)', value: 'anthropic' },
    { name: 'Google (Gemini)', value: 'google' },
    { name: 'Mistral', value: 'mistral' },
    { name: 'Done', value: 'done' }
  ];
  
  const configPath = path.join(CONFIG_DIR, 'providers.json');
  let config = {};
  
  if (fs.existsSync(configPath)) {
    config = JSON.parse(fs.readFileSync(configPath, 'utf8'));
  }
  
  while (true) {
    const { provider } = await inquirer.prompt([
      {
        type: 'list',
        name: 'provider',
        message: 'Select provider to configure:',
        choices: providers
      }
    ]);
    
    if (provider === 'done') break;
    
    if (provider === 'ollama') {
      const { host } = await inquirer.prompt([
        {
          type: 'input',
          name: 'host',
          message: 'Ollama host:',
          default: 'http://127.0.0.1:11434'
        }
      ]);
      config.ollama = { host, enabled: true };
    } else {
      const { apiKey, defaultModel } = await inquirer.prompt([
        {
          type: 'password',
          name: 'apiKey',
          message: `${provider} API key:`,
          mask: '*'
        },
        {
          type: 'input',
          name: 'defaultModel',
          message: 'Default model:'
        }
      ]);
      config[provider] = { apiKey, defaultModel, enabled: true };
    }
    
    console.log(chalk.green(`✓ ${provider} configured`));
  }
  
  fs.writeFileSync(configPath, JSON.stringify(config, null, 2));
  console.log(chalk.green('\n✓ Configuration saved to ' + configPath));
}

// Configure channels
async function configureChannels() {
  console.log('\n' + chalk.cyan.bold('Configure Channels') + '\n');
  
  const channels = [
    { name: 'Web UI (built-in)', value: 'webui', disabled: true },
    { name: 'Telegram', value: 'telegram' },
    { name: 'Discord', value: 'discord' },
    { name: 'Slack', value: 'slack' },
    { name: 'Done', value: 'done' }
  ];
  
  const configPath = path.join(CONFIG_DIR, 'channels.json');
  let config = { webui: { enabled: true } };
  
  if (fs.existsSync(configPath)) {
    config = { ...config, ...JSON.parse(fs.readFileSync(configPath, 'utf8')) };
  }
  
  while (true) {
    const { channel } = await inquirer.prompt([
      {
        type: 'list',
        name: 'channel',
        message: 'Select channel to configure:',
        choices: channels
      }
    ]);
    
    if (channel === 'done') break;
    
    if (channel === 'telegram') {
      const { botToken, allowedUsers } = await inquirer.prompt([
        {
          type: 'input',
          name: 'botToken',
          message: 'Telegram Bot Token (from @BotFather):'
        },
        {
          type: 'input',
          name: 'allowedUsers',
          message: 'Allowed user IDs (comma-separated):'
        }
      ]);
      config.telegram = {
        botToken,
        allowedUsers: allowedUsers.split(',').map(u => u.trim()).filter(Boolean),
        enabled: true
      };
    } else if (channel === 'discord') {
      const { botToken } = await inquirer.prompt([
        {
          type: 'input',
          name: 'botToken',
          message: 'Discord Bot Token:'
        }
      ]);
      config.discord = { botToken, enabled: true };
    } else if (channel === 'slack') {
      const { botToken, appToken } = await inquirer.prompt([
        {
          type: 'input',
          name: 'botToken',
          message: 'Slack Bot Token (xoxb-...):'
        }
      ]);
      config.slack = { botToken, enabled: true };
    }
    
    console.log(chalk.green(`✓ ${channel} configured`));
  }
  
  fs.writeFileSync(configPath, JSON.stringify(config, null, 2));
  console.log(chalk.green('\n✓ Configuration saved to ' + configPath));
}

// CLI Program
program
  .name('closedpaw')
  .description('Zero-Trust AI Assistant with Hardened Sandboxing')
  .version('1.0.0');

program
  .command('install')
  .description('Install ClosedPaw on your system')
  .option('-s, --skip-model', 'Skip model download')
  .action(installClosedPaw);

program
  .command('start')
  .description('Start ClosedPaw')
  .action(startClosedPaw);

program
  .command('stop')
  .description('Stop ClosedPaw')
  .action(stopClosedPaw);

program
  .command('status')
  .description('Show installation status')
  .action(showStatus);

program
  .command('doctor')
  .description('Run system diagnostics')
  .action(runDoctor);

program
  .command('update')
  .description('Update ClosedPaw to latest version')
  .option('-f, --force', 'Force update even if already on latest version')
  .action(async (options) => {
    console.log(boxen(
      chalk.cyan.bold('🔒 ClosedPaw Updater') + '\n' +
      chalk.gray('Updating to the latest version...'),
      { padding: 1, borderStyle: 'round', borderColor: 'cyan' }
    ));

    const steps = [];
    
    // Step 1: Update npm package
    const npmSpinner = ora('Updating ClosedPaw CLI...').start();
    try {
      await execa('npm', ['install', '-g', 'closedpaw@latest'], { stdio: 'pipe' });
      npmSpinner.succeed('CLI updated to latest version');
      steps.push({ name: 'CLI', status: 'success' });
    } catch (error) {
      npmSpinner.fail('CLI update failed');
      console.log(chalk.yellow('  Try running with administrator privileges'));
      steps.push({ name: 'CLI', status: 'failed' });
      process.exit(1);
    }

    // Step 2: Update local installation (if git install)
    if (fs.existsSync(path.join(INSTALL_DIR, '.git'))) {
      const gitSpinner = ora('Updating local installation...').start();
      try {
        await execa('git', ['pull', '--rebase'], { cwd: INSTALL_DIR, stdio: 'pipe' });
        gitSpinner.succeed('Local files updated');
        steps.push({ name: 'Local files', status: 'success' });

        // Update Python dependencies
        const pipSpinner = ora('Updating Python dependencies...').start();
        const venvPython = process.platform === 'win32'
          ? path.join(INSTALL_DIR, 'venv', 'Scripts', 'python')
          : path.join(INSTALL_DIR, 'venv', 'bin', 'python');
        
        if (fs.existsSync(venvPython)) {
          await execa(venvPython, ['-m', 'pip', 'install', '--upgrade', 
            'fastapi', 'uvicorn', 'pydantic', 'httpx', 'sqlalchemy', 
            'python-multipart', 'python-jose', 'passlib'
          ], { stdio: 'pipe' });
          pipSpinner.succeed('Python dependencies updated');
          steps.push({ name: 'Python deps', status: 'success' });
        } else {
          pipSpinner.warn('Virtual environment not found, skipping');
        }

        // Update frontend dependencies
        const npmDepsSpinner = ora('Updating frontend dependencies...').start();
        await execa('npm', ['update'], { cwd: path.join(INSTALL_DIR, 'frontend'), stdio: 'pipe' });
        npmDepsSpinner.succeed('Frontend dependencies updated');
        steps.push({ name: 'Frontend deps', status: 'success' });

      } catch (error) {
        gitSpinner.fail('Local update failed');
        steps.push({ name: 'Local files', status: 'failed' });
      }
    }

    // Step 3: Check for Ollama update (optional)
    const ollamaSpinner = ora('Checking Ollama...').start();
    try {
      await execa('ollama', ['--version'], { stdio: 'pipe' });
      ollamaSpinner.succeed('Ollama is installed');
      steps.push({ name: 'Ollama', status: 'ok' });
    } catch {
      ollamaSpinner.warn('Ollama not found');
    }

    // Summary
    console.log('\n' + boxen(
      chalk.green.bold('✓ Update Complete!') + '\n\n' +
      steps.map(s => {
        const icon = s.status === 'success' || s.status === 'ok' ? chalk.green('✓') : chalk.red('✗');
        return `${icon} ${s.name}`;
      }).join('\n') + '\n\n' +
      chalk.white('Restart ClosedPaw to apply changes:') + '\n' +
      chalk.cyan('  closedpaw stop') + '\n' +
      chalk.cyan('  closedpaw start'),
      { padding: 1, borderStyle: 'round', borderColor: 'green' }
    ));
  });

program
  .command('migrate <source>')
  .description('Migrate data from other systems (openclaw, securesphere)')
  .action(migrateSystem);

program
  .command('config')
  .description('Interactive configuration')
  .action(async () => {
    const { action } = await inquirer.prompt([
      {
        type: 'list',
        name: 'action',
        message: 'What would you like to configure?',
        choices: [
          { name: 'Providers (OpenAI, Anthropic, etc.)', value: 'providers' },
          { name: 'Channels (Telegram, Discord, Slack)', value: 'channels' },
          { name: 'Exit', value: 'exit' }
        ]
      }
    ]);
    
    if (action === 'providers') await configureProviders();
    if (action === 'channels') await configureChannels();
  });

program
  .command('bind-telegram <user-id>')
  .description('Add user to Telegram allowlist')
  .action((userId) => {
    const configPath = path.join(CONFIG_DIR, 'channels.json');
    let config = {};
    
    if (fs.existsSync(configPath)) {
      config = JSON.parse(fs.readFileSync(configPath, 'utf8'));
    }
    
    if (!config.telegram) {
      config.telegram = { enabled: true, allowedUsers: [] };
    }
    if (!config.telegram.allowedUsers) {
      config.telegram.allowedUsers = [];
    }
    
    if (!config.telegram.allowedUsers.includes(userId)) {
      config.telegram.allowedUsers.push(userId);
      fs.writeFileSync(configPath, JSON.stringify(config, null, 2));
      console.log(chalk.green(`✓ User ${userId} added to Telegram allowlist`));
    } else {
      console.log(chalk.yellow(`User ${userId} already in allowlist`));
    }
  });

program
  .command('chat [message]')
  .description('Send a chat message (CLI mode)')
  .option('-m, --model <model>', 'Model to use')
  .option('-p, --provider <provider>', 'Provider to use')
  .action(async (message, options) => {
    if (!message) {
      // Interactive mode
      const { input } = await inquirer.prompt([
        { type: 'input', name: 'input', message: '>' }
      ]);
      message = input;
    }
    
    const spinner = ora('Thinking...').start();
    
    try {
      const response = await new Promise((resolve, reject) => {
        const data = JSON.stringify({
          message,
          model: options.model || 'llama3.2:3b',
          use_cloud: false
        });
        
        const req = http.request({
          hostname: '127.0.0.1',
          port: 8000,
          path: '/api/chat',
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Content-Length': data.length
          }
        }, (res) => {
          let body = '';
          res.on('data', chunk => body += chunk);
          res.on('end', () => {
            try {
              resolve(JSON.parse(body));
            } catch (e) {
              reject(e);
            }
          });
        });
        
        req.on('error', reject);
        req.write(data);
        req.end();
      });
      
      spinner.stop();
      console.log('\n' + chalk.cyan(response.response) + '\n');
    } catch (error) {
      spinner.fail('Failed to connect to API. Is ClosedPaw running?');
      console.log('Run: closedpaw start');
    }
  });

// Default: show help
program.parse();
