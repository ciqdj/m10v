"use strict";
fetch('/api/platform/adapters',{cache:'no-store'}).then(async response=>{if(!response.ok)throw new Error('工作区状态不可用');const data=await response.json();document.getElementById('platform-status').textContent='GR III / GR IIIx 统一工作台 · 本地服务已连接';}).catch(error=>{document.getElementById('platform-status').textContent=error.message;});
