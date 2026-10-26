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
      assert.match(html,/GR III 用户实机确认修复/);
      assert.match(html,/v2026\.10\.26\.7\/m10v-gr3-2\.10-isp-20261026\.zip/);
      assert.match(html,/140a12d7e91a01eca796758eac8b920a97d895940dedb861bf829a5b988dffc0/);
      assert.match(html,/历史候选 · 已由上方修复版取代/);
      assert.match(html,/尚未确认修复/);
      assert.match(html,/https:\/\/github.com\/zhaoo\/m10v\/releases\/download\/gr3-2\.10-isp-test-20261026-rc1\/m10v-gr3-2\.10-isp-test-20261026-rc1\.zip/);
      assert.match(html,/efa0706c519e54bf90d384201d329cdf4ef41004e7249d84b0e6835cf72355b2/);
    }
  } finally {await new Promise(resolve=>server.close(resolve));}
});
