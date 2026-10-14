import path from 'node:path';

export const GR4_ROUTE_INVENTORY = new Set(['status', 'settings', 'import', 'import-official', 'project',
  'project-import', 'export', 'original', 'add-filter', 'remove-filter', 'xmp', 'icon',
  'calibration-state', 'calibration-output', 'calibration/register', 'calibration/run',
  'crop-preview', 'shutdown-item', 'shutdown-image', 'shutdown-export', 'toolchain',
  'build', 'download', 'history', 'history/open', 'history/rollback', 'history/download']);

const binary = new Set(['import', 'xmp', 'icon', 'shutdown-image']);
const operation = new Map([
  ['status', 'status'], ['settings', 'settings'], ['project', 'project'],
  ['project-import', 'project_import'], ['export', 'project_export'],
  ['add-filter', 'filter_add'], ['remove-filter', 'filter_remove'],
  ['xmp', 'xmp_import'], ['icon', 'icon_import'], ['calibration-state', 'calibration_state'],
  ['calibration-output', 'calibration_output'], ['calibration/register', 'calibration_register'],
  ['calibration/run', 'calibration_run'], ['crop-preview', 'crop_preview'],
  ['shutdown-item', 'shutdown_item'], ['shutdown-image', 'shutdown_image'],
  ['shutdown-export', 'shutdown_export'], ['toolchain', 'toolchain_save'],
  ['build', 'build'], ['download', 'build_download'], ['history', 'history'],
  ['history/open', 'history_open'], ['history/rollback', 'history_rollback'],
  ['history/download', 'history_download'],
]);

function queryPayload(search) {
  return Object.fromEntries([...search.entries()].map(([key, value]) => [key, value]));
}
function normalizedResult(value) {
  if (!value || typeof value !== 'object') return value;
  const result = structuredClone(value);
  const rewrite = (node) => {
    if (!node || typeof node !== 'object') return;
    for (const [key, child] of Object.entries(node)) {
      if (typeof child === 'string' && (key === 'download_url' || key === 'manifest_url'))
        node[key] = child.replace('/api/', '/api/gr4/');
      else rewrite(child);
    }
  };
  rewrite(result);
  return result;
}

export async function handleGr4Request({ request, response, runtime, token, readBody, send, origin }) {
  const url = new URL(request.url, origin);
  if (!url.pathname.startsWith('/api/gr4/')) return false;
  const route = url.pathname.slice('/api/gr4/'.length);
  if (!GR4_ROUTE_INVENTORY.has(route)) { send(response, 404, { error: '接口不存在' }); return true; }
  if (request.method === 'POST' && (request.headers['x-m10v-token'] !== token ||
      (request.headers.origin && request.headers.origin !== origin))) {
    send(response, 403, { error: 'authorization failed' }); return true;
  }
  try {
    let payload = queryPayload(url.searchParams);
    if (route === 'original') {
      if (request.method !== 'GET') throw new Error('原始固件只支持下载');
      const bytes = await runtime.original(payload.sha256);
      return send(response, 200, bytes, 'application/octet-stream', 'fwdc248b-original.bin'), true;
    }
    if (request.method === 'POST') {
      const body = await readBody(request, route === 'import-official' ? 4096 : 192 * 1024 * 1024);
      if (route === 'import-official') {
        if (body.length > 4096) throw new Error('local import request exceeds limit');
        return send(response, 200, normalizedResult(await runtime.importOfficial())), true;
      }
      if (binary.has(route)) {
        if (route === 'import') return send(response, 200,
          normalizedResult(await runtime.import(body, payload.name || 'fwdc248b.bin'))), true;
        const suffix = route === 'xmp' ? '.xmp' : route === 'icon' ? '.image' : '.image';
        payload.input_path = await runtime.stage(body, suffix);
        payload.filename = payload.name || path.basename(payload.input_path);
      } else payload = { ...payload, ...JSON.parse(body.toString('utf8') || '{}') };
    }
    if (route === 'import-official') throw new Error('local firmware import requires POST');
    if (route === 'project') payload.project_id = payload.project_id || payload.id;
    if (route === 'export') payload.project_id = payload.id;
    if (route === 'shutdown-export') payload.project_id = payload.project_id;
    if (route === 'project-import') payload = { project: payload };
    const result = await runtime.call(operation.get(route), payload);
    if (['download', 'history/download', 'calibration-output'].includes(route)) {
      const artifact = await runtime.readWorkerArtifact(result);
      return send(response, 200, artifact.bytes,
        route === 'calibration-output' ? 'application/octet-stream' :
          artifact.filename.endsWith('.json') ? 'application/json; charset=utf-8' : 'application/octet-stream',
        artifact.filename), true;
    }
    if (route === 'shutdown-export') {
      const artifact = await runtime.readWorkerArtifact(result);
      return send(response, 200, artifact.bytes, 'application/zip', artifact.filename), true;
    }
    return send(response, 200, normalizedResult(route === 'status' ? { ...result,
      session_token: token, evidence: 'reference_verified', hardware: 'not_tested' } : result)), true;
  } catch (error) {
    send(response, 400, { error: error.message || 'GR IV operation failed' }); return true;
  }
}
