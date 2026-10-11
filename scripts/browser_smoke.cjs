const {chromium}=require('playwright');
const path=require('path'), os=require('os');
const root=path.resolve(__dirname,'..');
const output=fsOutput();
function fsOutput(){return require('fs').mkdtempSync(require('path').join(require('os').tmpdir(),'grid-flex-browser-'));}
const {spawn}=require('child_process');
const fs=require('fs');
const assert=require('assert');
(async()=>{
 const server=spawn('python',['server.py'],{cwd:root,env:{...process.env,PORT:'8012'},stdio:'ignore'});
 let browser;
 try{
  browser=await chromium.launch({args:['--no-sandbox'],headless:true});
  const context=await browser.newContext({viewport:{width:1440,height:1000},acceptDownloads:true});
  const page=await context.newPage();const errors=[];page.on('pageerror',e=>errors.push(e.message));
  for(let i=0;i<40;i++){try{const r=await fetch('http://127.0.0.1:8012/api/health');if(r.ok)break}catch{}await new Promise(r=>setTimeout(r,200));}
  await page.goto('http://127.0.0.1:8012');
  const ready=()=>page.waitForFunction(()=>latest&&!solvePending&&!document.getElementById('download-brief').disabled,{},{timeout:30000});
  await ready();
  assert.equal(await page.locator('#analyze-button').isEnabled(),true);
  const analyze=async()=>{await page.click('#analyze-button');await page.waitForFunction(()=>intelligence&&!analysisPending,{},{timeout:30000})};
  await analyze();
  assert.equal(await page.evaluate(()=>intelligence.current.plan===latest.optimized),false);
  assert.deepEqual(await page.evaluate(()=>intelligence.current.plan),await page.evaluate(()=>latest.optimized));
  await page.selectOption('#stress-case','4');
  assert((await page.locator('#solar-profile').innerText()).includes('19:00'));
  await page.locator('#forecast-risk').screenshot({path:output+'/risk-desktop.png'});
  await page.click('#health-tab');assert(await page.locator('#health-view').isVisible());
  await page.click('#save-experiment');
  await page.locator('#battery-wear').fill('8');await page.locator('#battery-wear').dispatchEvent('input');
  assert(await page.locator('#intelligence-results').isHidden());assert(await page.locator('#download-brief').isDisabled());
  await page.click('#run-button');await ready();await analyze();
  assert(await page.evaluate(()=>intelligence.battery.with_wear.throughput_kwh<intelligence.battery.without_wear.throughput_kwh));
  await page.locator('#forecast-risk').screenshot({path:output+'/battery-desktop.png'});
  const dl=page.waitForEvent('download');await page.click('#download-brief');const d=await dl;await d.saveAs(output+'/brief.md');assert(fs.readFileSync(output+'/brief.md','utf8').includes('Forecast risk and battery economics'));
  const csvdl=page.waitForEvent('download');await page.click('#export-button');const csv=await csvdl;await csv.saveAs(output+'/dispatch.csv');assert(fs.readFileSync(output+'/dispatch.csv','utf8').includes('SYNTHETIC'));
  await page.click('#restore-experiment');await ready();assert.equal(await page.locator('#battery-wear').inputValue(),'0.15');
  for(const k of ['balanced','carbon','cost']){await page.click(`[data-strategy="${k}"]`);assert.equal(await page.evaluate(()=>selectedStrategy),k);assert(await page.locator('#intelligence-results').isHidden())}
  await page.click('[data-mission="emergency-outage"]');await ready();await analyze();
  assert.equal(await page.evaluate(()=>intelligence.current.stress.passed_count),1);
  assert.equal(await page.evaluate(()=>intelligence.conservative.stress.passed_count),4);
  await page.click('#risk-tab');await page.selectOption('#stress-case','4');
  await page.click('#show-baseline');await page.click('#show-optimized');
  await page.locator('.job-select').first().click();await page.click('#inspect-jump');
  await page.click('#jump-peak');await page.click('#hour-next');await page.click('#hour-prev');
  await page.click('#hour-play');await page.waitForTimeout(1200);await page.click('#hour-play');
  await page.locator('.operational-alert').first().click();
  const cursors=await page.evaluate(()=>({label:getComputedStyle(document.querySelector('.gantt-hour')).cursor,button:getComputedStyle(document.querySelector('#run-button')).cursor}));assert.deepEqual(cursors,{label:'default',button:'pointer'});
  assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
  await page.setViewportSize({width:390,height:844});await page.locator('#forecast-risk').scrollIntoViewIfNeeded();
  assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
  await page.screenshot({path:output+'/mobile.png'});
  await page.focus('#risk-tab');await page.keyboard.press('Tab');assert.equal(await page.evaluate(()=>document.activeElement.id),'health-tab');
  assert.deepEqual(errors,[]);
  console.log('PASS: desktop + 390px mobile; exact-plan analysis; risk selector; wear sensitivity; pin/restore; three strategies; outage; machine/alert/peak/playback; both exports; stale invalidation; keyboard and cursor; no page overflow or JS runtime errors.');
 }finally{if(browser)await browser.close();server.kill()}
})().catch(e=>{console.error(e);process.exit(1)});
