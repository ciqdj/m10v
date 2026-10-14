import assert from 'node:assert/strict';
import { test } from 'node:test';
import { listSdVolumes, resolveSdVolume } from './sd-volumes.mjs';

const sd = {
  DeviceIdentifier: 'disk7s1', MountPoint: '/Volumes/GR3CARD',
  Internal: false, Removable: true, Ejectable: true,
  Writable: true, WritableVolume: true, VolumeSize: 64_000_000,
  FreeSpace: 40_000_000, FilesystemName: 'MS-DOS FAT32',
};
const internal = { ...sd, DeviceIdentifier: 'disk1s1', MountPoint: '/', Internal: true };
const unmounted = { ...sd, DeviceIdentifier: 'disk8s1', MountPoint: '' };
const externalDrive = { ...sd, DeviceIdentifier: 'disk9s1', Removable: false };
const wrongFormat = { ...sd, DeviceIdentifier: 'disk10s1', FilesystemName: 'APFS' };
const escapedMount = { ...sd, DeviceIdentifier: 'disk11s1', MountPoint: '/Volumes/../tmp' };

function diskutilFixture(args) {
  if (args.join(' ') === 'list -plist external physical') {
    return { AllDisks: ['disk7', 'disk8', 'disk9', 'disk10', 'disk11'],
      AllDisksAndPartitions: [{ DeviceIdentifier: 'disk7', Partitions: [{ DeviceIdentifier: 'disk7s1' }] },
        { DeviceIdentifier: 'disk8', Partitions: [{ DeviceIdentifier: 'disk8s1' }] },
        { DeviceIdentifier: 'disk9', Partitions: [{ DeviceIdentifier: 'disk9s1' }] },
        { DeviceIdentifier: 'disk10', Partitions: [{ DeviceIdentifier: 'disk10s1' }] },
        { DeviceIdentifier: 'disk11', Partitions: [{ DeviceIdentifier: 'disk11s1' }] }] };
  }
  if (args[0] === 'info' && args[1] === '-plist') {
    return ({ disk7s1: sd, disk8s1: unmounted, disk9s1: externalDrive,
      disk10s1: wrongFormat,
      disk11s1: escapedMount,
      disk1s1: internal })[args[2]];
  }
  throw new Error(`unexpected diskutil args: ${args.join(' ')}`);
}

test('lists only a mounted removable writable card and resolves it freshly', async () => {
  const volumes = await listSdVolumes(diskutilFixture);
  assert.equal(volumes.length, 1);
  assert.equal(volumes[0].device_identifier, 'disk7s1');
  assert.equal(volumes[0].mount_point, '/Volumes/GR3CARD');
  assert.equal((await resolveSdVolume('disk7s1', diskutilFixture)).free_bytes, 40_000_000);
});

test('rejects malformed identifiers, internal, unmounted and nonremovable disks', async () => {
  for (const id of ['disk7s1/../../', 'disk7s1;touch /tmp/no', 'disk1s1', 'disk8s1', 'disk9s1', 'disk10s1', 'disk11s1']) {
    await assert.rejects(resolveSdVolume(id, diskutilFixture));
  }
});
