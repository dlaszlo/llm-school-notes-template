import fs from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { execFileSync } from 'node:child_process';
import { chromium } from 'playwright';
import { sha256 } from './paths.mjs';
import { serveSite } from './server.mjs';
const root = fileURLToPath(new URL('../', import.meta.url));
export async function printFingerprint(browserPath) {
  if (!browserPath) throw Error('PDF generation requires an explicit Chromium executable');
  const browserVersion = execFileSync(browserPath,['--version'],{encoding:'utf8'}).trim();
  const major = Number(browserVersion.match(/(?:Chromium|Chrome|HeadlessChrome)[^\d]*(\d+)/)?.[1]);
  if (!major || major < 131) throw Error('PDF page-margin headers require Chromium 131 or newer');
  const files = ['lib/pdf.mjs','lib/markdown.mjs','src/pages/nyomtatas/[id].astro','src/styles.css','src/print-fonts.css','package-lock.json'];
  const bundled = (await fs.readdir(path.join(root,'src/fonts/source-sans-3'))).filter(f=>f.endsWith('.woff2')).sort();
  files.push(...bundled.map(f=>'src/fonts/source-sans-3/'+f));
  const code = await Promise.all(files.map(async f => [f,sha256(await fs.readFile(path.join(root,f)))]));
  const fonts = await Promise.all(['Noto Color Emoji'].map(async name => {
    const file = execFileSync('fc-match',['-f','%{file}',name],{encoding:'utf8'});
    return [name,sha256(await fs.readFile(file))];
  }));
  return sha256(JSON.stringify({code,fonts,node:process.version,browser:browserVersion}));
}
export async function generatePdfs({output,payload,browserPath,cacheDirectory}) {
  const documents = payload.collections.filter(c => c.pdf);
  if (!documents.length) return;
  const cache = path.resolve(cacheDirectory);
  await fs.mkdir(cache,{recursive:true,mode:0o700});
  await fs.mkdir(path.join(output,'site','pdf'),{recursive:true});
  const {server,origin} = await serveSite(path.join(output,'site'),payload.base);
  let browser;
  const report = [];
  try {
    browser = await chromium.launch({executablePath:browserPath});
    const page = await browser.newPage({viewport:{width:794,height:1123},locale:'hu-HU'});
    // PDFs must not depend on live network content or send private text elsewhere.
    await page.route('**/*',route => new URL(route.request().url()).origin === origin ? route.continue() : route.abort());
    await page.emulateMedia({media:'print',colorScheme:'light'});
    for (const doc of documents) {
      const key = doc.pdf.key, pdfFile = path.join(cache,key+'.pdf'), recordFile = path.join(cache,key+'.json');
      let record, bytes;
      try {record=JSON.parse(await fs.readFile(recordFile,'utf8'));bytes=await fs.readFile(pdfFile);
        if (record.key!==key || sha256(bytes)!==record.sha256 || bytes.subarray(0,5).toString()!=='%PDF-') record=null;
      } catch {record=null;}
      let reused=Boolean(record);
      if (!record) {
        const response=await page.goto(origin+payload.base+'nyomtatas/'+doc.id+'/');
        if (response.status()!==200) throw Error('Missing print page: '+doc.id);
        await page.evaluate(async()=>{await document.fonts.ready;await Promise.all([...document.images].map(i=>{i.loading='eager';return i.decode();}));});
        const failures=await page.evaluate(()=>[...document.querySelectorAll('.print-figure, table, mjx-container[display="true"]')].filter(e=>e.scrollWidth>e.clientWidth+2 || (e.matches('.print-figure')&&e.getBoundingClientRect().height>850)).map(e=>e.tagName));
        if(failures.length)throw Error('Oversized print elements: '+doc.id+' '+failures.join(','));
        await page.evaluate(() => document.querySelectorAll('a[href^="/"]').forEach(a => a.removeAttribute('href')));
        const date=new Date().toLocaleDateString('hu-HU',{timeZone:'Europe/Budapest'});
        // The exact version stays in PDF metadata and the private receipt, not the lesson.
        await page.evaluate(({title,key})=>{
          document.title=title+' — változat '+key;
          document.body.classList.add('pdf-export');
        },{title:doc.title,key});
        // Chromium 131+ page margin boxes use the same local webfont as the body.
        // No external header resources or platform-dependent header font substitutions.
        const cssString = value => '"'+value.replace(/\\/g,'\\\\').replace(/"/g,'\\"').replace(/[\n\r\f]/g,' ')+'"';
        await page.addStyleTag({content:`@page {
          @top-left { content: ${cssString(doc.title)}; font-family: 'Source Sans 3'; font-size: 9pt; line-height: 1.2; font-weight: 400; color: #404040; vertical-align: middle; }
          @bottom-left { content: ${cssString(date)}; font-family: 'Source Sans 3'; font-size: 9pt; color: #404040; }
          ${payload.license ? `@bottom-center { content: ${cssString(payload.license.id+' · kivételek: lásd a jelöléseket')}; font-family: 'Source Sans 3'; font-size: 8pt; color: #404040; }` : ''}
          @bottom-right { content: counter(page) ' / ' counter(pages); font-family: 'Source Sans 3'; font-size: 9pt; color: #404040; }
        }`});
        await page.evaluate(async()=>{
          await document.fonts.ready;
          for (const face of ['400 11.5pt "Source Sans 3"','600 16pt "Source Sans 3"','700 11.5pt "Source Sans 3"','italic 400 11.5pt "Source Sans 3"']) {
            if (!(await document.fonts.load(face,'Árvíztűrő tükörfúrógép ŐŰ')).length) throw Error('Missing print font: '+face);
          }
        });
        bytes=await page.pdf({format:'A4',preferCSSPageSize:true,printBackground:true,displayHeaderFooter:false,tagged:true,outline:true});
        record={key,sha256:sha256(bytes),bytes:bytes.length,createdAt:new Date().toISOString(),id:doc.id,title:doc.title,inputs:doc.inputs};
        await fs.writeFile(pdfFile+'.tmp',bytes,{mode:0o600});await fs.rename(pdfFile+'.tmp',pdfFile);
        await fs.writeFile(recordFile,JSON.stringify(record,null,2)+'\n',{mode:0o600});
      }
      await fs.writeFile(path.join(output,'site','pdf',doc.pdf.filename),bytes);
      report.push({...record,reused,filename:doc.pdf.filename});
    }
  } finally {try {await browser?.close();} finally {await new Promise(resolve=>server.close(resolve));}}
  await fs.writeFile(path.join(output,'pdf-receipt.private.json'),JSON.stringify(report,null,2)+'\n');
  console.log(`PDFs: ${report.filter(r=>!r.reused).length} generated, ${report.filter(r=>r.reused).length} reused`);
}
