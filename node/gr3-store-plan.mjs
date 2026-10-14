const featureVersions = { recipes: 3, timestamp: 2, aspect: 2, film: 1, level: 1 };
const slots = { 'builtin-0b': 'Standard', 'builtin-11': 'Positive Film',
  'builtin-15': 'Cross Processing', 'builtin-16': 'Negative Film',
  custom1: 'Standard', custom2: 'Standard' };
const fields = ['saturation', 'hue', 'high_low_key', 'contrast', 'highlight_contrast',
  'shadow_contrast', 'sharpness', 'shading', 'clarity'];

function requireValue(ok, message) { if (!ok) throw new Error(message); }

function recipe(item) {
  requireValue(item && Object.hasOwn(slots, item.slotId), 'unsupported recipe slot');
  requireValue(item.baseEffect === slots[item.slotId], 'recipe base differs from slot');
  requireValue(typeof item.cameraName === 'string' &&
    /^(?=.{1,11}$)(?=.*[A-Za-z])[A-Za-z0-9 -]+$/.test(item.cameraName) &&
    item.cameraName.trim() === item.cameraName, 'camera name must be 1–11 ASCII characters');
  requireValue(item.iconMode === 'original' || item.iconMode === 'preset' ||
    item.iconMode === 'custom', 'unsupported icon mode');
  requireValue(['manual', 'community_reference'].includes(item.source), 'unsupported recipe source');
  const parameters = {};
  for (const field of fields) {
    const value = item.parameters?.[field];
    requireValue(Number.isInteger(value) && value >= -4 && value <= 4,
      `${field} must be between -4 and +4`);
    parameters[field] = value;
  }
  return { slotId: item.slotId, cameraName: item.cameraName, baseEffect: item.baseEffect,
    parameters, iconMode: item.iconMode, source: item.source,
    ...(item.id ? { id: item.id } : {}),
    ...(item.iconMode === 'custom' ? { customIcon: item.customIcon } : {}) };
}

export function createStorePlan(selection) {
  requireValue(selection?.variant === 'street', 'only GR III Street 2.10 is verified offline');
  requireValue(!selection.features?.includes('filmbay'), '旧 SD 胶片库方案已废弃，不可用于固件构建');
  const requested = new Set(selection.features);
  requireValue(requested.size > 0 && requested.size === selection.features.length &&
    [...requested].every((id) => Object.hasOwn(featureVersions, id)), 'select one to six known features');
  const recipes = requested.has('recipes') ? (selection.recipes || []).map(recipe) : [];
  requireValue(!requested.has('recipes') || recipes.length > 0, 'configure at least one recipe');
  requireValue(new Set(recipes.map(({ slotId }) => slotId)).size === recipes.length, 'duplicate recipe slot');
  requireValue(!(requested.has('film') && recipes.some(({ slotId }) => slotId === 'builtin-15')),
    'Cross Processing is occupied by film simulation');
  const config = {
    recipes: { items: recipes },
    timestamp: { package: 'full-menu' },
    aspect: { ratios: ['4:3', '65:24'], output: 'jpeg_preview', liveviewMask: true },
    film: requested.has('film') ? createFilmPlan(selection.filmIds ||
      ['ektar100', 'gold200', 'pro400h', 'portra400', 'vision3-250d'], selection.filmLibrary, selection.filmTexture) : null,
    level: { style: 'slider', replaces: 'center' },
  };
  return { schema: 'grlife-firmware-customization-plan/v1',
    target: { model: 'gr3', variant: 'street', version: '2.10', filename: 'fwdc239b.bin' },
    features: Object.keys(featureVersions).filter((id) => requested.has(id)).map((id) =>
      ({ id, version: featureVersions[id], configuration: config[id] })) };
}
import { createFilmPlan } from './gr3-film-plan.mjs';

