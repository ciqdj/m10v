import assert from 'node:assert/strict';
import { existsSync, readFileSync } from 'node:fs';
import { mkdtemp, readFile, rm } from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import { test } from 'node:test';
import { createServer } from './server.mjs';
import { Store } from './storage.mjs';
import { prepareOfficialSd } from './sd-write.mjs';
import { decodeFrameMap } from './gr3-frames.mjs';
import { findCollabo } from './gr3-jpeg.mjs';

test('retired external film pack download is unavailable', async () => {
  const folder = await mkdtemp(path.join(os.tmpdir(), 'm10v-local-film-pack-'));
  const server = createServer(new Store(folder));
  await new Promise((resolve) => server.listen(0, '127.0.0.1', resolve));
  const base = `http://127.0.0.1:${server.address().port}`;
  const url = `${base}/api/gr3/film-bay/pack`;
  try {
    const token = (await (await fetch(`${base}/api/status`)).json()).session_token;
    const body = JSON.stringify({films:['hb-hncs']});
    assert.equal((await fetch(url, {method:'POST',body})).status, 403);
    const response = await fetch(url, {method:'POST',body,
      headers:{'X-M10V-Token':token,'Content-Type':'application/json'}});
    assert.equal(response.status, 410);
    assert.match((await response.json()).error, /废弃|不可用/);
  } finally {
    await new Promise((resolve) => server.close(resolve));
    await rm(folder,{recursive:true,force:true});
  }
});

test('GR III LUT fit route stays local and requires the session token', async () => {
  if (!existsSync(new URL('../.runtime/grlife/web/firmware-store/film-fit.js', import.meta.url))) return;
  const folder = await mkdtemp(path.join(os.tmpdir(), 'm10v-lut-http-'));
  const server = createServer(new Store(folder));
  await new Promise((resolve) => server.listen(0, '127.0.0.1', resolve));
  const base = `http://127.0.0.1:${server.address().port}`;
  const cube = 'LUT_3D_SIZE 2\n0 0 0\n1 0 0\n0 1 0\n1 1 0\n0 0 1\n1 0 1\n0 1 1\n1 1 1\n';
  try {
    const status = await (await fetch(`${base}/api/status`)).json();
    const route = `${base}/api/gr3/film/fit`;
    assert.equal((await fetch(route, { method: 'POST', body: cube })).status, 403);
    const response = await fetch(route, { method: 'POST', body: cube,
      headers: { 'X-M10V-Token': status.session_token, 'X-M10V-Filename': 'identity.cube' } });
    assert.equal(response.status, 200);
    const fitted = await response.json();
    assert.equal(fitted.choices.tone.look.curves[0].length, 256);
  } finally {
    await new Promise((resolve) => server.close(resolve));
    await rm(folder, { recursive: true, force: true });
  }
});

test('HTTP exposes truthful multi-model adapter evidence', async () => {
  const folder = await mkdtemp(path.join(os.tmpdir(), 'm10v-platform-http-'));
  const server = createServer(new Store(folder));
  await new Promise((resolve) => server.listen(0, '127.0.0.1', resolve));
  const base = `http://127.0.0.1:${server.address().port}`;
  try {
    const catalog = await (await fetch(`${base}/api/platform/adapters`)).json();
    assert.deepEqual(catalog.adapters.map((row) => row.id), ['gr3', 'gr4', 'gr2']);
    const gr4 = catalog.adapters.find((row) => row.id === 'gr4');
    assert.equal(gr4.evidence, 'reference_verified');
    assert.equal(gr4.capabilities.build.hardware, 'not_tested');
    assert.equal(gr4.capabilities.version.first_generated, '1.11.10.10');
  } finally {
    await new Promise((resolve) => server.close(resolve));
    await rm(folder, { recursive: true, force: true });
  }
});

test('HTTP serves isolated product workspaces and authorizes GR IV mutations', async () => {
  const folder = await mkdtemp(path.join(os.tmpdir(), 'm10v-shell-http-'));
  const calls = [];
  const gr4 = {
    call: async (operation, payload) => {
      calls.push({ operation, payload });
      if (operation === 'status') return { projects: [], version: 'test' };
      if (operation === 'settings') return { theme: 'system' };
      throw new Error(`unexpected operation: ${operation}`);
    },
    original: async (sha256) => {
      assert.equal(sha256, 'a'.repeat(64));
      return Buffer.from('official-gr4');
    },
  };
  const server = createServer(new Store(folder), undefined, gr4);
  await new Promise((resolve) => server.listen(0, '127.0.0.1', resolve));
  const base = `http://127.0.0.1:${server.address().port}`;
  try {
    const home = await (await fetch(`${base}/`)).text();
    assert.match(home, /为你的 GR 定制/);
    const gr3 = await (await fetch(`${base}/gr3/`)).text();
    assert.match(gr3, /id="feature-list"/);
    const gr4Page = await (await fetch(`${base}/gr4/`)).text();
    assert.match(gr4Page, /id="build-firmware"/);

    const statusResponse = await fetch(`${base}/api/gr4/status`);
    assert.equal(statusResponse.status, 200);
    const status = await statusResponse.json();
    assert.equal(status.evidence, 'reference_verified');
    assert.equal(status.hardware, 'not_tested');
    assert.match(status.session_token, /^[A-Za-z0-9_-]{43}$/);

    assert.equal((await fetch(`${base}/api/gr4/settings`, {
      method: 'POST', body: JSON.stringify({ theme: 'dark' }),
      headers: { 'Content-Type': 'application/json' },
    })).status, 403);
    const saved = await fetch(`${base}/api/gr4/settings`, {
      method: 'POST', body: JSON.stringify({ theme: 'dark' }),
      headers: { 'Content-Type': 'application/json', 'X-M10V-Token': status.session_token },
    });
    assert.equal(saved.status, 200);
    assert.deepEqual(calls.at(-1), { operation: 'settings', payload: { theme: 'dark' } });
    const original = await fetch(`${base}/api/gr4/original?sha256=${'a'.repeat(64)}`);
    assert.equal(original.status, 200);
    assert.equal(await original.text(), 'official-gr4');
    assert.match(original.headers.get('content-disposition'), /fwdc248b-original\.bin/);
  } finally {
    await new Promise((resolve) => server.close(resolve));
    await rm(folder, { recursive: true, force: true });
  }
});

test('GR III customization preflight authenticates and requires a matching risk acknowledgement', async () => {
  if (!existsSync(sample) || !existsSync(new URL('../.runtime/grlife/reconstruction/firmware_store/browser_engine.py', import.meta.url))) return;
  const folder = await mkdtemp(path.join(os.tmpdir(), 'm10v-recipe-http-'));
  const server = createServer(new Store(folder));
  await new Promise((resolve) => server.listen(0, '127.0.0.1', resolve));
  const base = `http://127.0.0.1:${server.address().port}`;
  try {
    const token = (await (await fetch(`${base}/api/status`)).json()).session_token;
    const original = readFileSync(sample);
    const imported = await (await fetch(`${base}/api/import`, { method: 'POST', body: original,
      headers: { 'X-M10V-Token': token, 'Content-Type': 'application/octet-stream' } })).json();
    const body = JSON.stringify({ selection: { variant: 'street', features: ['timestamp'], recipes: [] } });
    const url = `${base}/api/projects/${imported.sha256}/edit/prepare`;
    assert.equal((await fetch(url, { method: 'POST', body })).status, 403);
    const prepared = await fetch(url, { method: 'POST', body,
      headers: { 'X-M10V-Token': token, 'Content-Type': 'application/json' } });
    assert.equal(prepared.status, 200);
    const report = await prepared.json();
    assert.equal(report.ready, true);
    assert.equal(report.camera_tested, false);
    const built = await fetch(`${base}/api/projects/${imported.sha256}/edit/build`, {
      method: 'POST', body, headers: { 'X-M10V-Token': token, 'Content-Type': 'application/json' },
    });
    assert.equal(built.status, 409);
  } finally {
    await new Promise((resolve) => server.close(resolve));
    await rm(folder, { recursive: true, force: true });
  }
});

const sample = new URL('../fwdc239b.bin', import.meta.url);

test('Node-only HTTP workflow imports, backs up and rehearses recovery',
  { skip: !existsSync(sample) }, async () => {
    const folder = await mkdtemp(path.join(os.tmpdir(), 'm10v-node-test-'));
    const server = createServer(new Store(folder));
    await new Promise((resolve) => server.listen(0, '127.0.0.1', resolve));
    const base = `http://127.0.0.1:${server.address().port}`;
    try {
      const page = await (await fetch(`${base}/gr3/`)).text();
      assert.match(page, /id="feature-list"/);
      assert.match(page, /id="recipe-dialog"/);
      assert.match(page, /id="build-firmware"/);
      assert.match(page, /id="source-report"/);
      assert.doesNotMatch(page, /id="sd-volume"|id="prepare-official-sd"|SD 卡准备/);
      assert.doesNotMatch(page, /id="build-button"/);
      const status = await (await fetch(`${base}/api/status`)).json();
      assert.equal(status.can_generate, true);
      assert.equal(status.version_strategy, 'same_version_first');
      assert.equal(status.version_probe_available, true);
      assert.equal(status.candidate_export_allowed, true);
      assert.ok(status.blockers.includes('hardware_recovery_not_verified'));
      assert.equal((await fetch(`${base}/candidate.bin`)).status, 404);
      const original = readFileSync(sample);
      const headers = { 'X-M10V-Token': status.session_token, 'Content-Type': 'application/octet-stream' };
      assert.equal((await fetch(`${base}/api/import`, { method: 'POST', body: original })).status, 403);
      const imported = await fetch(`${base}/api/import`, { method: 'POST', body: original, headers });
      assert.equal(imported.status, 200);
      const report = await imported.json();
      assert.equal(report.sections.length, 14);
      const catalogResponse = await fetch(`${base}/api/projects/${report.sha256}/shutdown-catalog`);
      assert.equal(catalogResponse.status, 200);
      const catalog = await catalogResponse.json();
      assert.equal(catalog.resources.length, 5);
      assert.equal(catalog.can_generate, false);
      const backup = await fetch(`${base}/api/projects/${report.sha256}/backup`,
        { method: 'POST', body: '', headers: { 'X-M10V-Token': status.session_token } });
      assert.equal(backup.status, 200);
      const archive = Buffer.from(await backup.arrayBuffer());
      const inspected = await fetch(`${base}/api/backup/inspect`,
        { method: 'POST', body: archive, headers });
      assert.equal(inspected.status, 200);
      const backupReport = await inspected.json();
      assert.equal(backupReport.original_sha256, report.sha256);
      assert.equal(backupReport.recovery_scope, 'computer_official_package_only');
      assert.equal(backupReport.camera_flash_included, false);
      const restored = await fetch(`${base}/api/backup/restore`,
        { method: 'POST', body: archive, headers });
      assert.equal(restored.status, 200);
      const restoredReport = await restored.json();
      assert.equal(restoredReport.project_id, report.sha256);
      assert.equal(restoredReport.recovery_scope, 'computer_official_package_only');
      assert.equal(restoredReport.camera_flash_included, false);
    } finally {
      await new Promise((resolve) => server.close(resolve));
      await rm(folder, { recursive: true, force: true });
    }
  });

test('HTTP prepares only official BIN on an explicitly selected SD volume',
  { skip: !existsSync(sample) }, async () => {
    const folder = await mkdtemp(path.join(os.tmpdir(), 'm10v-sd-http-'));
    const card = path.join(folder, 'card');
    const { mkdir } = await import('node:fs/promises');
    await mkdir(card);
    const volume = { device_identifier: 'disk7s1', mount_point: card,
      free_bytes: 64_000_000, total_bytes: 128_000_000, file_system: 'FAT32' };
    const sd = {
      listSdVolumes: async () => [volume],
      resolveSdVolume: async (id) => {
        if (id !== 'disk7s1') throw new Error('invalid SD device');
        return volume;
      },
      prepareOfficialSd,
    };
    const server = createServer(new Store(path.join(folder, 'data')), sd);
    await new Promise((resolve) => server.listen(0, '127.0.0.1', resolve));
    const base = `http://127.0.0.1:${server.address().port}`;
    try {
      const status = await (await fetch(`${base}/api/status`)).json();
      assert.equal(status.official_sd_supported, true);
      assert.equal(status.candidate_sd_blocked, true);
      const headers = { 'X-M10V-Token': status.session_token };
      const original = readFileSync(sample);
      const report = await (await fetch(`${base}/api/import`,
        { method: 'POST', body: original, headers })).json();
      const volumes = await (await fetch(`${base}/api/sd/volumes`)).json();
      assert.equal(volumes[0].device_identifier, 'disk7s1');
      const endpoint = `${base}/api/projects/${report.sha256}/sd/prepare`;
      const body = JSON.stringify({ device_identifier: 'disk7s1' });
      assert.equal((await fetch(endpoint, { method: 'POST', body })).status, 403);
      assert.equal((await fetch(endpoint, { method: 'POST', body,
        headers: { ...headers, Origin: 'https://elsewhere.example' } })).status, 403);
      const prepared = await fetch(endpoint, { method: 'POST', body, headers });
      assert.equal(prepared.status, 200);
      assert.equal((await prepared.json()).status, 'official_sd_ready');
      assert.ok((await readFile(path.join(card, 'fwdc239b.bin'))).equals(original));
      assert.equal((await fetch(`${base}/api/projects/${report.sha256}/candidate/sd/prepare`,
        { method: 'POST', body, headers })).status, 404);
    } finally {
      await new Promise((resolve) => server.close(resolve));
      await rm(folder, { recursive: true, force: true });
    }
  });

test('verified GR III shutdown modification exports a same-version BIN and keeps other egress closed',
  { skip: !existsSync(sample) }, async () => {
    const folder = await mkdtemp(path.join(os.tmpdir(), 'm10v-candidate-http-'));
    const server = createServer(new Store(folder));
    await new Promise((resolve) => server.listen(0, '127.0.0.1', resolve));
    const base = `http://127.0.0.1:${server.address().port}`;
    try {
      const status = await (await fetch(`${base}/api/status`)).json();
      assert.equal(status.candidate_offline_analysis, true);
      assert.equal(status.candidate_export_allowed, true);
      const original = readFileSync(sample);
      const headers = { 'X-M10V-Token': status.session_token };
      const imported = await (await fetch(`${base}/api/import`,
        { method: 'POST', body: original, headers })).json();
      const decoded = decodeFrameMap(original).decoded;
      const { start, end } = findCollabo(decoded);
      const jpeg = Buffer.from(decoded.subarray(start, end));
      const at = jpeg.findIndex((byte, index) => index > 10_000 && index < jpeg.length - 100 &&
        byte !== 0xff && jpeg[index - 1] !== 0xff && byte !== 0x00);
      jpeg[at] ^= 1;
      const endpoint = `${base}/api/projects/${imported.sha256}/candidates/shutdown/analyze`;
      assert.equal((await fetch(endpoint, { method: 'POST', body: jpeg })).status, 403);
      assert.equal((await fetch(endpoint, { method: 'POST', body: jpeg,
        headers: { ...headers, Origin: 'https://elsewhere.example' } })).status, 403);
      const analyzed = await fetch(endpoint, { method: 'POST', body: jpeg, headers });
      assert.equal(analyzed.status, 200);
      const responseBytes = Buffer.from(await analyzed.arrayBuffer());
      const report = JSON.parse(responseBytes.toString());
      assert.equal(report.status, 'candidate_offline_verified');
      assert.equal(report.candidate_export_allowed, true);
      assert.ok(responseBytes.length < 4096);
      const exportEndpoint = `${base}/api/projects/${imported.sha256}/candidates/shutdown/export`;
      assert.equal((await fetch(exportEndpoint, { method: 'POST', body: jpeg })).status, 403);
      const exported = await fetch(exportEndpoint, { method: 'POST', body: jpeg, headers });
      assert.equal(exported.status, 200);
      assert.match(exported.headers.get('content-disposition'), /fwdc239b\.bin/);
      const candidate = Buffer.from(await exported.arrayBuffer());
      assert.equal(candidate.readUInt32BE(0x38), original.readUInt32BE(0x38));
      assert.equal(candidate.readUInt32BE(0x50), original.readUInt32BE(0x50));
      assert.equal(candidate.equals(original), false);
      for (const suffix of ['/candidate.bin', '/candidates/shutdown/download',
        '/candidate/sd/prepare', '/build']) {
        assert.equal((await fetch(`${base}/api/projects/${imported.sha256}${suffix}`,
          { method: 'POST', body: '', headers })).status, 404);
      }
      assert.equal((await fetch(`${base}/api/build`,
        { method: 'POST', body: '', headers })).status, 404);
    } finally {
      await new Promise((resolve) => server.close(resolve));
      await rm(folder, { recursive: true, force: true });
    }
  });

test('version probe is authorized, report-only and has no modified BIN route',
  { skip: !existsSync(sample) }, async () => {
    const folder = await mkdtemp(path.join(os.tmpdir(), 'm10v-version-http-'));
    const server = createServer(new Store(folder));
    await new Promise((resolve) => server.listen(0, '127.0.0.1', resolve));
    const base = `http://127.0.0.1:${server.address().port}`;
    try {
      const status = await (await fetch(`${base}/api/status`)).json();
      assert.equal(status.version_strategy, 'same_version_first');
      assert.equal(status.version_probe_available, true);
      assert.equal(status.candidate_export_allowed, true);
      assert.equal(status.candidate_sd_blocked, true);
      const headers = { 'X-M10V-Token': status.session_token };
      const imported = await (await fetch(`${base}/api/import`, {
        method: 'POST', body: readFileSync(sample), headers,
      })).json();
      const endpoint = `${base}/api/projects/${imported.sha256}/versions/probe`;
      assert.equal((await fetch(endpoint, { method: 'POST', body: '' })).status, 403);
      assert.equal((await fetch(endpoint, { method: 'POST', body: '',
        headers: { ...headers, Origin: 'https://elsewhere.example' } })).status, 403);
      assert.equal((await fetch(endpoint, { method: 'POST', body: 'unexpected', headers })).status, 400);
      const response = await fetch(endpoint, { method: 'POST', body: '', headers });
      assert.equal(response.status, 200);
      const responseBytes = Buffer.from(await response.arrayBuffer());
      const report = JSON.parse(responseBytes.toString('utf8'));
      assert.equal(report.status, 'version_probe_offline_verified');
      assert.equal(report.strategy, 'same_version_first');
      assert.equal(report.probe_version, '2.10.21.28');
      assert.equal(report.candidate_export_allowed, false);
      assert.equal(report.candidate_sd_allowed, false);
      assert.ok(responseBytes.length < 4096);
      assert.equal(Object.values(report).some(Buffer.isBuffer), false);
      for (const suffix of ['/versions/download', '/versions/2.10.21.28.bin',
        '/versions/sd/prepare']) {
        assert.equal((await fetch(`${base}/api/projects/${imported.sha256}${suffix}`,
          { method: 'POST', body: '', headers })).status, 404);
      }
    } finally {
      await new Promise((resolve) => server.close(resolve));
      await rm(folder, { recursive: true, force: true });
    }
  });
