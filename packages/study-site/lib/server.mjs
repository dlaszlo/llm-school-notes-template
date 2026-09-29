import fs from 'node:fs/promises';
import path from 'node:path';
import { createServer } from 'node:http';
export async function serveSite(directory, base, port = 0) {
  directory = await fs.realpath(directory);
  const types = { '.html':'text/html; charset=utf-8', '.css':'text/css', '.js':'application/javascript', '.mjs':'application/javascript', '.json':'application/json', '.svg':'image/svg+xml', '.webp':'image/webp', '.png':'image/png', '.jpg':'image/jpeg', '.wasm':'application/wasm', '.pdf':'application/pdf' };
  const server = createServer(async(req,res) => {
    try {
      const pathname = decodeURIComponent(new URL(req.url,'http://localhost').pathname);
      if (!pathname.startsWith(base)) throw Error('wrong base');
      let file = path.resolve(directory, './' + pathname.slice(base.length));
      if (!file.startsWith(directory + path.sep) && file !== directory) throw Error('outside root');
      if ((await fs.stat(file)).isDirectory()) file = path.join(file,'index.html');
      file = await fs.realpath(file);
      if (!file.startsWith(directory + path.sep)) throw Error('outside root');
      res.writeHead(200, {'Content-Type':types[path.extname(file)] || 'application/octet-stream','X-Content-Type-Options':'nosniff','Cache-Control':'no-store'});
      res.end(await fs.readFile(file));
    } catch { res.writeHead(404);res.end('Not found'); }
  });
  await new Promise((resolve,reject) => { server.once('error',reject);server.listen(port,'127.0.0.1',resolve); });
  return {server, origin:`http://127.0.0.1:${server.address().port}`};
}
