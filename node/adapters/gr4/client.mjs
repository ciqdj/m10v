import { spawn } from 'node:child_process';
import { existsSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { validateGr4Operation } from './operation-schema.mjs';

const here = path.dirname(fileURLToPath(import.meta.url));
const defaultWorker = path.resolve(here, '../../../vendor/gr4/adapter_worker.py');
const bundledPython = path.resolve(here, '../../../.venv/bin/python');
const MAX_RESPONSE = 64 * 1024 * 1024;

export function createGr4Client(options = {}) {
  const python = options.python || process.env.M10V_PYTHON312 ||
    (existsSync(bundledPython) ? bundledPython : '/opt/homebrew/bin/python3.12');
  const worker = path.resolve(options.worker || defaultWorker);
  const timeoutMs = options.timeoutMs || 60_000;
  return Object.freeze({
    request(operation, payload = {}, workspace = process.cwd()) {
      validateGr4Operation(operation, payload);
      return new Promise((resolve, reject) => {
        const child = spawn(python, [worker], {
          cwd: path.dirname(worker), detached: process.platform !== 'win32',
          stdio: ['pipe', 'pipe', 'pipe'],
          env: { PATH: process.env.PATH || '', LANG: process.env.LANG || 'C.UTF-8',
            PYTHONIOENCODING: 'utf-8', PYTHONDONTWRITEBYTECODE: '1' },
        });
        let stdout = Buffer.alloc(0), stderr = Buffer.alloc(0), settled = false;
        const finish = (error, value) => {
          if (settled) return;
          settled = true;
          clearTimeout(timer);
          error ? reject(error) : resolve(value);
        };
        const kill = () => {
          try { process.kill(process.platform === 'win32' ? child.pid : -child.pid, 'SIGKILL'); }
          catch { child.kill('SIGKILL'); }
        };
        const timer = setTimeout(() => { kill(); finish(new Error('GR IV worker timed out')); }, timeoutMs);
        child.on('error', (error) => finish(error));
        child.stdout.on('data', (chunk) => {
          stdout = Buffer.concat([stdout, chunk]);
          if (stdout.length > MAX_RESPONSE) { kill(); finish(new Error('GR IV response exceeds limit')); }
        });
        child.stderr.on('data', (chunk) => {
          stderr = Buffer.concat([stderr, chunk]);
          if (stderr.length > MAX_RESPONSE) { kill(); finish(new Error('GR IV diagnostics exceed limit')); }
        });
        child.on('close', (code) => {
          if (settled) return;
          if (code !== 0) return finish(new Error(`GR IV worker failed (${code}): ${stderr.toString().trim()}`));
          const text = stdout.toString('utf8');
          if (!text.endsWith('\n') || text.trim().split('\n').length !== 1)
            return finish(new Error('GR IV worker protocol is corrupt'));
          let response;
          try { response = JSON.parse(text); } catch { return finish(new Error('GR IV worker returned invalid JSON')); }
          if (!response?.ok) return finish(new Error(response?.error || 'GR IV operation failed'));
          finish(null, response.result);
        });
        const request = JSON.stringify({ schema_version: 1, operation,
          workspace: path.resolve(workspace), payload });
        if (Buffer.byteLength(request) > 192 * 1024 * 1024) {
          kill(); return finish(new Error('GR IV request exceeds 1 MiB'));
        }
        child.stdin.end(request);
      });
    },
  });
}
