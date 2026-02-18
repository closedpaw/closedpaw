#!/usr/bin/env node

/**
 * ClosedPaw - Post-install message
 */

const chalk = require('chalk');
const boxen = require('boxen');

console.log('\n' + boxen(
  chalk.cyan.bold('🔒 ClosedPaw installed!') + '\n\n' +
  chalk.white('Quick Start:') + '\n' +
  chalk.green('  closedpaw install') + chalk.gray('  # Install on your system') + '\n' +
  chalk.green('  closedpaw start') + chalk.gray('    # Start the assistant') + '\n' +
  chalk.green('  closedpaw chat "Hello"') + chalk.gray(' # Quick chat') + '\n\n' +
  chalk.white('New Features:') + '\n' +
  chalk.green('  closedpaw doctor') + chalk.gray('   # System diagnostics') + '\n' +
  chalk.green('  closedpaw config') + chalk.gray('    # Configure providers/channels') + '\n' +
  chalk.green('  closedpaw migrate openclaw') + chalk.gray(' # Migrate data') + '\n\n' +
  chalk.white('Supported Providers:') + '\n' +
  chalk.gray('  Ollama (local), OpenAI, Anthropic, Google, Mistral') + '\n\n' +
  chalk.white('Supported Channels:') + '\n' +
  chalk.gray('  WebUI, Telegram, Discord, Slack, CLI') + '\n\n' +
  chalk.gray('Documentation: https://github.com/logansin/closedpaw'),
  {
    padding: 1,
    borderStyle: 'round',
    borderColor: 'cyan'
  }
) + '\n');
