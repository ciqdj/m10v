import { createHash, randomBytes } from 'node:crypto';
import { execFile } from 'node:child_process';
import { open, lstat, readFile, realpath, rm, statfs } from 'node:fs/promises';
import path from 'node:path';
import { promisify } from 'node:util';
import { inspectOfficial, SHA256 } from './firmware.mjs';

const FILENAME = 'fwdc239b.bin';
const hash = (bytes) => createHash('sha256').update(bytes).digest('hex');
const run = promisify(execFile);

async function atomicNoReplace(stage, destination) {
  await run('/bin/mv', ['-n', stage, destination], { timeout: 30_000, maxBuffer: 64 * 1024 });
  try {
    await lstat(stage);
    throw new Error('firmware already exists at publication time');
  } catch (error) {
    if (error.code !== 'ENOENT') throw error;
  }
}

async function syncDirectory(directory) {
  const handle = await open(directory, 'r');
  try { await handle.sync(); } finally { await handle.close(); }
}

async function ensureAbsent(file) {
  try { await lstat(file); throw new Error('firmware already exists on SD volume'); }
  catch (error) { if (error.code !== 'ENOENT') throw error; }
}

export async function prepareOfficialSd(original, volume, options = {}) {
  inspectOfficial(original);
  if (!volume || !/^disk[0-9]+s[0-9]+$/.test(volume.device_identifier || '') ||
      typeof volume.mount_point !== 'string' || !Number.isSafeInteger(volume.free_bytes) ||
      volume.free_bytes < original.length) throw new Error('SD volume has insufficient space or identity');
  const mount = path.resolve(volume.mount_point);
  const info = await lstat(mount);
  if (!info.isDirectory() || info.isSymbolicLink()) throw new Error('unsafe SD mount point');
  if (mount.startsWith('/Volumes/') && !(await realpath(mount)).startsWith('/Volumes/')) {
    throw new Error('SD mount escapes /Volumes');
  }
  const free = await statfs(mount);
  if (Number(free.bavail) * Number(free.bsize) < original.length) {
    throw new Error('SD volume has insufficient space');
  }
  const destination = path.join(mount, FILENAME);
  await ensureAbsent(destination);
  const stage = path.join(mount, `.m10v-${randomBytes(12).toString('hex')}.tmp`);
  let published = false;
  try {
    const file = await open(stage, 'wx', 0o600);
    try { await file.writeFile(original); await file.sync(); } finally { await file.close(); }
    await ensureAbsent(destination);
    if (options.beforePublish) await options.beforePublish({ stage, destination });
    try {
      await (options.publish || atomicNoReplace)(stage, destination);
      published = true;
    } catch (error) {
      try { await lstat(stage); }
      catch (stageError) {
        if (stageError.code === 'ENOENT') published = true;
        else throw stageError;
      }
      throw error;
    }
    const finalFile = await open(destination, 'r');
    try { await finalFile.sync(); } finally { await finalFile.close(); }
    await syncDirectory(mount);
    const verified = await (options.readback || readFile)(destination);
    if (!Buffer.isBuffer(verified) || verified.length !== original.length || hash(verified) !== SHA256) {
      throw new Error('SD readback hash or length differs');
    }
    return {
      status: 'official_sd_ready', device_identifier: volume.device_identifier,
      mount_point: mount, filename: FILENAME, bytes: verified.length, sha256: SHA256,
    };
  } catch (error) {
    if (published) await rm(destination, { force: true }).catch(() => {});
    throw error;
  } finally { await rm(stage, { force: true }).catch(() => {}); }
}
