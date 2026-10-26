import test from 'node:test';
import assert from 'node:assert/strict';
import {createServer} from './server.mjs';

test('test package page serves without JavaScript and links the exact GitHub asset', async () => {
  const server=createServer();
  await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
  try {
    for(const path of ['/test-packages','/test-packages/']) {
      const response=await fetch(`http://127.0.0.1:${server.address().port}${path}`);
      assert.equal(response.status,200);
      assert.match(response.headers.get('content-type'),/text\/html/);
      const html=await response.text();
      assert.match(html,/<h1>测试包<\/h1>/);
      assert.match(html,/仅 GR III · 2.10/);
      assert.match(html,/尚未确认修复/);
      assert.match(html,/https:\/\/github.com\/zhaoo\/m10v\/releases\/download\/gr3-2\.10-isp-test-20261026-rc1\/m10v-gr3-2\.10-isp-test-20261026-rc1\.zip/);
      assert.match(html,/efa0706c519e54bf90d384201d329cdf4ef41004e7249d84b0e6835cf72355b2/);
    }
  } finally {await new Promise(resolve=>server.close(resolve));}
});
