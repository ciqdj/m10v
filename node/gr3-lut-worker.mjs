import { parentPort, workerData } from 'node:worker_threads';
import { parseCube, sampleLut } from '../.runtime/grlife/web/recipes/custom-recipe-core.js';
import { fitLookChoices, fitSummary } from '../.runtime/grlife/web/firmware-store/film-fit.js';

try {
  const lut = parseCube(workerData.cube, workerData.filename);
  const fits = fitLookChoices((red, green, blue) => sampleLut(lut, red, green, blue));
  const choices = Object.fromEntries(Object.entries(fits).map(([id, fit]) => [id, {
    look: { matrixQ13: fit.matrixQ13, postQ512: fit.postQ512,
      curves: fit.curves, knots: fit.knots },
    note: { lutName: workerData.filename.slice(0, 80), ...fitSummary(fit) },
  }]));
  parentPort.postMessage({ choices });
} catch (error) { parentPort.postMessage({ error: error.message }); }
