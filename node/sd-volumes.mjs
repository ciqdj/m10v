import { spawn } from 'node:child_process';
import path from 'node:path';

function run(program, args, input) {
  return new Promise((resolve, reject) => {
    const child = spawn(program, args, { stdio: ['pipe', 'pipe', 'pipe'] });
    const chunks = [];
    let size = 0;
    let stderr = '';
    const timer = setTimeout(() => child.kill(), 10000);
    child.stdout.on('data', (chunk) => {
      size += chunk.length;
      if (size > 1024 * 1024) child.kill();
      else chunks.push(chunk);
    });
    child.stderr.on('data', (chunk) => { stderr += chunk.toString().slice(0, 256); });
    child.on('error', reject);
    child.on('close', (code) => {
      clearTimeout(timer);
      if (code !== 0 || size > 1024 * 1024) reject(new Error(`volume command failed: ${stderr.slice(0, 256)}`));
      else resolve(Buffer.concat(chunks));
    });
    child.stdin.end(input);
  });
}

async function defaultRunner(args) {
  if (process.platform !== 'darwin') throw new Error('SD volume discovery requires macOS');
  const plist = await run('diskutil', args);
  return JSON.parse((await run('plutil', ['-convert', 'json', '-o', '-', '-'], plist)).toString());
}

function checkId(id) {
  if (typeof id !== 'string' || !/^disk[0-9]+s[0-9]+$/.test(id)) {
    throw new Error('invalid SD device identifier');
  }
  return id;
}

function fromInfo(info, id) {
  const fileSystem = info?.FilesystemName || info?.FilesystemType;
  if (!info || info.DeviceIdentifier !== id || info.Internal !== false ||
      !(info.Removable === true || info.RemovableMedia === true) ||
      info.Ejectable !== true || info.Writable !== true || info.WritableVolume !== true ||
      typeof info.MountPoint !== 'string' || !info.MountPoint.startsWith('/Volumes/') ||
      path.normalize(info.MountPoint) !== info.MountPoint ||
      path.resolve(info.MountPoint) === '/Volumes' ||
      typeof fileSystem !== 'string' || !/^(?:MS-DOS(?: FAT(?:12|16|32))?|FAT(?:12|16|32)|ExFAT)$/i.test(fileSystem) ||
      !Number.isSafeInteger(info.FreeSpace) || info.FreeSpace < 0) {
    throw new Error('device is not a mounted writable removable SD volume');
  }
  return {
    device_identifier: id, mount_point: info.MountPoint,
    total_bytes: info.VolumeSize || info.TotalSize,
    free_bytes: info.FreeSpace,
    file_system: fileSystem,
  };
}

async function listedIds(runDiskutil) {
  const list = await runDiskutil(['list', '-plist', 'external', 'physical']);
  if (!Array.isArray(list.AllDisksAndPartitions)) throw new Error('invalid diskutil list');
  return list.AllDisksAndPartitions.flatMap((disk) =>
    Array.isArray(disk.Partitions) ? disk.Partitions.map((part) => part.DeviceIdentifier) : []);
}

export async function listSdVolumes(runDiskutil = defaultRunner) {
  const volumes = [];
  for (const id of await listedIds(runDiskutil)) {
    try {
      checkId(id);
      volumes.push(fromInfo(await runDiskutil(['info', '-plist', id]), id));
    } catch { /* A disk is listed, but not a writable removable mounted card. */ }
  }
  return volumes;
}

export async function resolveSdVolume(deviceIdentifier, runDiskutil = defaultRunner) {
  const id = checkId(deviceIdentifier);
  if (!(await listedIds(runDiskutil)).includes(id)) throw new Error('SD device is no longer external');
  return fromInfo(await runDiskutil(['info', '-plist', id]), id);
}
