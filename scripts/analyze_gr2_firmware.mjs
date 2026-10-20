#!/usr/bin/env node
// Compatibility CLI; force GR II identity while sharing the strict extractor.
process.argv.push('--model','gr2');
await import('./analyze_unity_firmware.mjs');
