import { randomBytes } from 'node:crypto';

const PROJECT = /^prj_[0-9a-f]{24}$/;
const SHA = /^[0-9a-f]{64}$/;

export const newProjectId = () => `prj_${randomBytes(12).toString('hex')}`;
export function checkProjectId(value) {
  if (typeof value !== 'string' || !PROJECT.test(value)) throw new Error('invalid project id');
  return value;
}
export function checkSha256(value) {
  if (typeof value !== 'string' || !SHA.test(value)) throw new Error('invalid object sha256');
  return value;
}
