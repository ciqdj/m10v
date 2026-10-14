import assert from 'node:assert/strict';
import { existsSync, readFileSync } from 'node:fs';
import { test } from 'node:test';
import { shutdownCatalog } from './features.mjs';

const sample = new URL('../fwdc239b.bin', import.meta.url);

test('GR III shutdown-related RES JPEGs are inventoried without write capability',
  { skip: !existsSync(sample) }, () => {
    const result = shutdownCatalog(readFileSync(sample));
    assert.deepEqual(result.resources.map((item) => item.filename),
      ['Collabo.jpg', 'GoodBye.jpg', 'GB_Diary.jpg', 'GB_ING.jpg', 'GB_Urban.jpg']);
    assert.equal(result.resources[0].sha256,
      '4a4b4fa95706bb7aa2caab05689a4143eba5337a5f0e46c6cabd3b2a1bd70410');
    for (const image of result.resources) {
      assert.equal(image.width, 720);
      assert.equal(image.height, 480);
      assert.match(image.sha256, /^[a-f0-9]{64}$/);
      assert.match(image.preview_data_url, /^data:image\/jpeg;base64,/);
    }
    assert.equal(result.can_generate, false);
    assert.equal(result.selection_verified, false);
  });
