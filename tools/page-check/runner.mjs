import fs from 'node:fs';
import path from 'node:path';
import http from 'node:http';
import {fileURLToPath} from 'node:url';
import {createRequire} from 'node:module';
import {digest,escape,inside,inspectPage} from './core.mjs';
const require=createRequire(import.meta.url), {chromium}=require('playwright');
const here=path.dirname(fileURLToPath(import.meta.url));
const usage='node tools/page_check.mjs --subject wiki/SUBJECT [--pages wiki/SUBJECT/page.md ...] [--repo PATH] [--out .visual-runs/page-check] [--force] [--browser /installed/chromium]';
function options(argv){
  const o={repo:path.resolve(here,'../..'),out:'.visual-runs/page-check',pages:[],widths:[390,1100],force:false};
  for(let i=0;i<argv.length;i++){
    const a=argv[i];
    if(a==='--help'){console.log(usage);return null;}
    if(a==='--force'){o.force=true;continue;}
    if(a==='--pages'){while(argv[i+1]&&!argv[i+1].startsWith('--'))o.pages.push(argv[++i]);continue;}
    if(['--repo','--out','--subject','--browser'].includes(a)){if(!argv[i+1])throw Error('Missing argument: '+a);o[a.slice(2)]=argv[++i];continue;}
    throw Error('Unknown argument: '+a);
  }
  o.repo=fs.realpathSync(o.repo);o.out=path.resolve(o.repo,o.out);
  if(!inside(path.join(o.repo,'.visual-runs'),o.out))throw Error('Output must be under this checkout .visual-runs/');
  if(o.subject){const dir=path.resolve(o.repo,o.subject);if(!inside(path.join(o.repo,'wiki'),dir))throw Error('Subject must be within wiki/');o.pages.push(...fs.readdirSync(dir).filter(x=>x.endsWith('.md')).map(x=>path.relative(o.repo,path.join(dir,x))));}
  o.pages=[...new Set(o.pages)].sort();if(!o.pages.length)throw Error(usage);
  for(const p of o.pages)if(!p.endsWith('.md')||!inside(path.join(o.repo,'wiki'),path.resolve(o.repo,p)))throw Error('Only wiki Markdown pages are accepted');
  return o;
}
const css=fs.readFileSync(require.resolve('github-markdown-css/github-markdown.css'),'utf8')+'\n'+fs.readFileSync(path.join(here,'style.css'),'utf8');
const mime=p=>({'.png':'image/png','.jpg':'image/jpeg','.jpeg':'image/jpeg','.webp':'image/webp','.svg':'image/svg+xml','.gif':'image/gif'}[path.extname(p).toLowerCase()]||'application/octet-stream');
export async function run(argv){
 const started=performance.now(),o=options(argv);if(!o)return;
 const outputPath=p=>{
  const absolute=path.resolve(p),cache=path.join(o.repo,'.visual-runs');
  if(!inside(cache,absolute))throw Error('Output leaves cache');
  let current=o.repo;
  for(const part of path.relative(o.repo,absolute).split(path.sep)){
   current=path.join(current,part);
   try{if(fs.lstatSync(current).isSymbolicLink())throw Error('Symlink in output path');}
   catch(e){if(e.code!=='ENOENT')throw e;}
  }
  return absolute;
 };
 fs.mkdirSync(outputPath(o.out),{recursive:true});
 const docs=new Map(),assets=new Map();
 const server=http.createServer((req,res)=>{
  const u=new URL(req.url,'http://localhost');
  // Only generated HTML and explicitly registered local image bytes are served.
  if(docs.has(u.pathname)){res.setHeader('Content-Type','text/html; charset=utf-8');res.setHeader('Content-Security-Policy',"default-src 'none'; img-src 'self' data:; style-src 'unsafe-inline'; script-src 'self'; font-src 'none'; connect-src 'none'");res.end(docs.get(u.pathname));return;}
  if(assets.has(u.pathname)){const p=assets.get(u.pathname);res.setHeader('Content-Type',mime(p));res.end(fs.readFileSync(p));return;}
  if(u.pathname==='/mermaid.js'){res.setHeader('Content-Type','application/javascript');res.end(fs.readFileSync(path.join(here,'node_modules/mermaid/dist/mermaid.min.js')));return;}
  res.writeHead(404);res.end('Not found');
 });
 await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
 const origin=`http://127.0.0.1:${server.address().port}`;
 let browser;const results=[];
 try{
  browser=await chromium.launch({headless:true, ...(o.browser?{executablePath:o.browser}:{}),args:['--disable-background-networking']});
  const version=browser.version();const toolHash=digest(['core.mjs','runner.mjs','style.css','package-lock.json'].map(f=>fs.readFileSync(path.join(here,f))).join('\0')+version);
  for(const rel of o.pages){
   const pageStart=performance.now(),file=path.resolve(o.repo,rel),data=inspectPage(o.repo,file);
   const fingerprint=digest(JSON.stringify({dependencies:data.dependencies,toolHash,widths:o.widths,disclosures:['closed','open'],tileHeight:900}));
   const folder=path.join(o.out,digest(rel).slice(0,16));fs.mkdirSync(outputPath(folder),{recursive:true});
   const receiptPath=outputPath(path.join(folder,'page.json'));let old;
   try{old=JSON.parse(fs.readFileSync(receiptPath));}catch{}
   if(!o.force && !data.errors.length && old?.fingerprint===fingerprint && old.errors.length===0 && old.outputs.length && old.outputs.every(a=>{
     const p=path.resolve(o.repo,a.path);return inside(o.out,p)&&fs.existsSync(outputPath(p))&&digest(fs.readFileSync(p))===a.sha256;
   })) {results.push({...old,reused:true,elapsed_seconds:(performance.now()-pageStart)/1000});continue;}
   let html=data.html;const blocked=[],errors=[...data.errors],outputs=[],views=[];
   for(const [uri,p] of data.imageFiles){const key='/asset/'+digest(p);assets.set(key,p);html=html.replaceAll(`src="${escape(uri)}"`,`src="${key}"`);}
   const docPath='/page/'+digest(rel);
   const document='<!doctype html><html lang="hu"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><style>'+css+'</style></head><body><main class="markdown-body">'+html+'</main></body></html>';
   docs.set(docPath,document);
   const page=await browser.newPage({viewport:{width:390,height:900},colorScheme:'light',reducedMotion:'reduce'});
   await page.route('**/*',route=>{const url=route.request().url();if(url.startsWith(origin+'/'))return route.continue();blocked.push(url);return route.abort();});
   page.on('pageerror',e=>errors.push({kind:'browser',message:e.message}));
   await page.goto(origin+docPath,{waitUntil:'load',timeout:30000});
   if(data.mermaidCount)await page.addScriptTag({url:origin+'/mermaid.js'});
   try{if(data.mermaidCount)await page.evaluate(async()=>{mermaid.initialize({startOnLoad:false,securityLevel:'strict',theme:'default',fontFamily:'Arial, sans-serif',flowchart:{htmlLabels:false}});await mermaid.run({nodes:document.querySelectorAll('.mermaid')});});}
   catch(e){errors.push({kind:'mermaid',message:e.message});}
   for(const width of o.widths) for(const open of [false,true]){
    await page.setViewportSize({width,height:900});
    await page.evaluate(open=>{document.querySelectorAll('details').forEach(d=>d.open=open);window.scrollTo(0,0);},open);
    await page.evaluate(async()=>{await document.fonts.ready;await Promise.all([...document.images].map(i=>i.decode().catch(()=>{})));});
    const metrics=await page.evaluate(()=>({width:document.documentElement.clientWidth,scrollWidth:document.documentElement.scrollWidth,height:document.documentElement.scrollHeight,
      brokenImages:[...document.images].filter(i=>!i.complete||!i.naturalWidth).map(i=>i.getAttribute('src')),
      details:document.querySelectorAll('details').length,mermaids:document.querySelectorAll('.mermaid svg').length,
      clippedText:[...document.querySelectorAll('.mermaid svg text')].filter(t=>{const a=t.getBoundingClientRect(),b=t.closest('svg').getBoundingClientRect();return a.width&& (a.right>b.right+2||a.left<b.left-2||a.bottom>b.bottom+2||a.top<b.top-2);}).map(t=>t.textContent)}));
    const view={width,disclosure:open?'open':'closed',...metrics};views.push(view);
    if(metrics.scrollWidth>width+1)errors.push({kind:'page-overflow',width,open,scrollWidth:metrics.scrollWidth});
    if(metrics.brokenImages.length)errors.push({kind:'broken-images',width,open,images:metrics.brokenImages});
    if(metrics.clippedText.length)errors.push({kind:'clipped-diagram-text',width,open,text:metrics.clippedText});
    if(metrics.mermaids!==data.mermaidCount)errors.push({kind:'mermaid-count',expected:data.mermaidCount,actual:metrics.mermaids});
    const name=`${width}-${open?'open':'closed'}`;const full=path.join(folder,name+'.png');
    await page.screenshot({path:outputPath(full),fullPage:true});outputs.push({path:path.relative(o.repo,full),sha256:digest(fs.readFileSync(full)),kind:'full-page',width,disclosure:view.disclosure});
    // Native-width tiles remain legible even when a full-page image is extremely tall.
    if(width===390 && metrics.height>1300){
     for(let y=0,i=0;y<metrics.height;y+=800,i++){
      await page.evaluate(y=>window.scrollTo(0,y),y);const tile=path.join(folder,`${name}-tile-${String(i).padStart(3,'0')}.png`);
      await page.screenshot({path:outputPath(tile)});outputs.push({path:path.relative(o.repo,tile),sha256:digest(fs.readFileSync(tile)),kind:'phone-tile',offset:y,disclosure:view.disclosure});
     }
    }
   }
   await page.close();if(blocked.length)errors.push({kind:'network-blocked',urls:[...new Set(blocked)]});
   const record={page:rel,fingerprint,dependencies:data.dependencies,toolHash,browser:version,
    checks:'rendered-awaiting-review',visual_review:'not-performed',semantic_review:'not-performed',human_acceptance:'not-requested',
    mathCount:data.mathCount,mermaidCount:data.mermaidCount,errors,warnings:data.warnings,views,outputs,reused:false,elapsed_seconds:(performance.now()-pageStart)/1000};
   fs.writeFileSync(outputPath(receiptPath),JSON.stringify(record,null,2)+'\n');results.push(record);
  }
 } finally {if(browser)await browser.close();await new Promise(resolve=>server.close(resolve));}
 const result={checked_at:new Date().toISOString(),renderer:'local-preview-not-exact-GitHub',network:'blocked-except-loopback-assets',
  elapsed_seconds:(performance.now()-started)/1000,pages:results,errors:results.flatMap(p=>p.errors.map(e=>({page:p.page,...e})))};
 const report=path.join(o.out,'report.json');fs.writeFileSync(outputPath(report),JSON.stringify(result,null,2)+'\n');
 console.log(JSON.stringify({report,pages:results.length,reused:results.filter(x=>x.reused).length,errors:result.errors.length,elapsed_seconds:result.elapsed_seconds}));
 if(result.errors.length)process.exitCode=1;return result;
}
