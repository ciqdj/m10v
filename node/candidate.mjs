import { decodeFrameMap, repackWithTarget } from './gr3-frames.mjs';
import { replaceCollabo } from './gr3-jpeg.mjs';
import { verifyCandidate } from './candidate-verify.mjs';

export function analyzeStreetCandidate(official, jpeg) {
  const { report, replay } = assembleStreetCandidate(official, jpeg);
  return { ...report, candidate_export_allowed: true, reused_frames: replay.reused_frames,
    replaced_frames: replay.replaced_frames };
}

function assembleStreetCandidate(official, jpeg) {
  const { decoded } = decodeFrameMap(official);
  const { targetDecoded } = replaceCollabo(decoded, jpeg);
  const replay = repackWithTarget(official, targetDecoded);
  const report = verifyCandidate(official, replay.candidate, jpeg);
  return { report, replay };
}

export function buildStreetCandidate(official, jpeg) {
  const { report, replay } = assembleStreetCandidate(official, jpeg);
  return { candidate: replay.candidate, report: { ...report,
    candidate_export_allowed: true, candidate_sd_allowed: false,
    reused_frames: replay.reused_frames, replaced_frames: replay.replaced_frames } };
}
