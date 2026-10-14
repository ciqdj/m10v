module.exports={apps:[{
 name:'m10v',cwd:'/www/wwwroot/m10v',script:'node/server.mjs',
 instances:1,exec_mode:'fork',autorestart:true,
 env:{NODE_ENV:'production',M10V_PORT:'3000',M10V_PUBLIC_ORIGIN:'https://m10v.izhaoo.com',M10V_NO_BROWSER:'1',M10V_LLVM_CLANG:'/usr/bin/clang',M10V_PYTHON:'/www/wwwroot/m10v/.venv/bin/python'}
}]};
