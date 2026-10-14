import { execFile } from 'node:child_process';
import { mkdtemp, readFile, writeFile, rm, mkdir } from 'node:fs/promises';
import { promisify } from 'node:util';
import { fileURLToPath } from 'node:url';
import path from 'node:path';
import os from 'node:os';
import { runtimeAvailable } from './gr3-runtime.mjs';
import { audit800TCandidate } from './gr3-800t-audit.mjs';

const root = path.dirname(path.dirname(fileURLToPath(import.meta.url)));
const exec = promisify(execFile);
export async function run800TBuild(source, prepared) {
  if (!await runtimeAvailable()) throw new Error('本机兼容运行时缺失或校验失败，请重新同步运行时。');
  const directory = await mkdtemp(path.join(os.tmpdir(), 'm10v-800t-'));
  const input = path.join(directory, 'source.bin'), plan = path.join(directory, 'prepared.json');
  const output = path.join(directory, 'candidate.bin');
  try {
    await Promise.all([writeFile(input, source, { mode: 0o600 }),
      writeFile(plan, JSON.stringify(prepared), { mode: 0o600 })]);
    try {
      await exec(process.env.M10V_PYTHON || '/opt/homebrew/bin/python3.12',
        [path.join(root, 'node/gr3-800t-worker.py'), input, plan, output, '1'],
        { cwd: root, env: { ...process.env, PYTHONPATH: path.join(root, '.runtime/grlife') },
          timeout: 180000, maxBuffer: 1024 * 1024 });
    } catch (error) {
      throw new Error((error.stderr || error.message).trim().slice(-1600));
    }
    const [candidate, receiptText, expectedText] = await Promise.all([readFile(output),
      readFile(path.join(directory, 'candidate.research.json'), 'utf8'),
      readFile(path.join(directory, 'candidate.expected.json'), 'utf8')]);
    const receipt = JSON.parse(receiptText), expectation = JSON.parse(expectedText);
    const audit = audit800TCandidate(source, candidate, expectation,prepared);
    if (audit.candidateSha256 !== receipt.candidate_sha256 ||
        audit.configurationSha256 !== prepared.configuration_sha256 || receipt.camera_tested !== false)
      throw new Error('800T 独立回读与构建回执不一致。');
    const retained = path.join(root, 'builds/gr3-800t-output');
    await mkdir(retained, { recursive: true });
    const record = { ...receipt, status: 'OFFLINE_VERIFIED_EXPERIMENTAL_CANDIDATE',
      source_sha256: prepared.source_sha256, configuration_sha256: prepared.configuration_sha256,
      chroma_order: 'CbCr', color_provenance: prepared.color_provenance, audit };
    await Promise.all([writeFile(path.join(retained, audit.candidateSha256 + '.expected.json'), expectedText),
      writeFile(path.join(retained, audit.candidateSha256 + '.prepared.json'), JSON.stringify(prepared,null,2)+'\n'),
      writeFile(path.join(retained, audit.candidateSha256 + '.receipt.json'), JSON.stringify(record, null, 2) + '\n')]);
    return { candidate, receipt: record, audit };
  } finally { await rm(directory, { recursive: true, force: true }); }
}
