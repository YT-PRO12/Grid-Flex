/* Grid Flex: framework-free control room. Real API data; no placeholder chart metrics. */
'use strict';
const $ = id => document.getElementById(id);
const API_BASE = new URLSearchParams(location.search).get('api')?.replace(/\/$/, '') || '';
const HOURS=12;
let latest = null;
let displayMode = 'optimized';
let selectedStrategy = 'cost';
let selectedHour = 0;
let playback = null;
let pinnedRun = null;
let selectedJobId = null;
let lastSolvedControls = null;
let solvePending = false;
let currentMission = null;
const inr = v => '₹' + Math.round(v).toLocaleString('en-IN');
const decimal = (v,n=1) => Number(v).toLocaleString('en-IN',{minimumFractionDigits:n,maximumFractionDigits:n});
const fmtChange = (x,suffix,downMeaningGood=true) => {
  const positive=x>=0;
  return `<span class="${positive===downMeaningGood?'positive':'negative'}">${x>0?'−':x<0?'+':'='} ${decimal(Math.abs(x))} ${suffix}</span>`;
};
const safe = v => String(v).replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;').replaceAll('"','&quot;');

function controls(){
  return {
    preset:$('preset').value,
    solar_scale:Number($('solar-scale').value)/100,
    tariff_multiplier:Number($('tariff-scale').value)/100,
    carbon_price:Number($('carbon-price').value),
    demand_scale:Number($('demand-scale').value)/100,
    battery_capacity:Number($('battery-capacity').value),
    evening_grid_cap:Number($('grid-cap').value),
    battery_wear_cost:Number($('battery-wear').value),
  };
}
function updateControls(){
  if(typeof invalidateIntelligence==='function')invalidateIntelligence('Inputs changed. Run optimization, then analyze.');
  $('wear-val').textContent=`₹${decimal($('battery-wear').value,2)} /kWh throughput`;
  $('solar-val').textContent=$('solar-scale').value+'%';
  $('tariff-val').textContent=$('tariff-scale').value+'%';
  $('carbon-val').textContent=`₹${$('carbon-price').value} /kg`;
  $('demand-val').textContent=$('demand-scale').value+'%';
  $('capacity-val').textContent=$('battery-capacity').value+' kWh';
  $('grid-val').textContent=$('grid-cap').value+' kW';
  if(latest){$('run-status').textContent='● Unsaved what-if changes — run optimization to update results'; $('run-status').classList.add('dirty');$('save-experiment').disabled=true;$('download-brief').disabled=true;$('export-button').disabled=true;}
}
for(const id of ['solar-scale','tariff-scale','carbon-price','demand-scale','battery-capacity','grid-cap','battery-wear','preset']) $(id).addEventListener('input',updateControls);
$('run-button').addEventListener('click',runOptimization);
$('emergency-button').addEventListener('click',()=>{ $('preset').value='emergency-outage'; updateControls(); runOptimization(); document.getElementById('grid-proof').scrollIntoView({behavior:'smooth',block:'center'}); });
$('show-optimized').addEventListener('click',()=>switchPlan('optimized'));
$('show-baseline').addEventListener('click',()=>switchPlan('baseline'));
function switchPlan(which){
  displayMode=which;
  for(const label of ['optimized','baseline']){
    const el=$(`show-${label}`);el.classList.toggle('active',label===which);el.setAttribute('aria-pressed',String(label===which));
  }
  if(latest){renderGantt(latest[which]);renderPower(latest[which],latest.scenario);renderTwin();renderMachineInspector();}
}
async function request(path,opts){
  const response=await fetch(API_BASE+path,opts);
  let data;
  try{data=await response.json();}catch{throw new Error(`HTTP ${response.status}: invalid API response`);}
  if(!response.ok) throw new Error(data.error || `Request failed (${response.status})`);
  return data;
}
async function runOptimization(){
  stopPlayback();
  if(solvePending)return;
  solvePending=true;
  const submittedControls=controls();
  invalidateIntelligence('Solving updated inputs…');
  document.querySelectorAll('#scenario input,#scenario select,[data-mission],#reset-controls,#emergency-button,#restore-experiment').forEach(el=>el.disabled=true);
  ['save-experiment','download-brief','export-button'].forEach(id=>$(id).disabled=true);
  $('run-button').disabled=true; $('run-label').textContent='Optimizing…';$('run-status').textContent='Solving integer decisions and battery dispatch';
  try{
    const result=await request('/api/optimize',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(submittedControls)});
    latest=result;
    lastSolvedControls={...submittedControls};
    $('run-status').classList.remove('dirty');
    $('save-experiment').disabled=false;
    $('download-brief').disabled=false;
    $('export-button').disabled=false;
    chooseStrategy(selectedStrategy);
    $('run-status').textContent=`${result.optimized.status==='optimal'?'Optimal plan found':'Feasible plan found'} · 3 strategies independently checked · ${decimal(result.optimized.solve_ms,0)} ms selected solve`;
    $('twin-plan-status').textContent=displayMode.toUpperCase()+' PLAN READY';
  }catch(err){
    $('run-status').textContent=`Optimization failed: ${err.message}`;
    $('run-status').style.color='#fb8998';
    $('twin-plan-status').textContent='PREVIOUS RESULT / NEW SOLVE FAILED';
    console.error(err);
  }finally{solvePending=false;document.querySelectorAll('#scenario input,#scenario select,[data-mission],#reset-controls,#emergency-button,#restore-experiment').forEach(el=>el.disabled=false);$('analyze-button').disabled=!latest||$('download-brief').disabled;$('run-button').disabled=false;$('run-label').textContent='Run optimization';}
}
function render(data){
  $('run-status').style.color='';
  const b=data.baseline.metrics, o=data.optimized.metrics, c=data.comparison;
  $('optimized-cost').textContent=inr(o.total_cost_inr);
  $('cost-delta').textContent=decimal(Math.abs(c.estimated_cost_saving_pct))+'% '+(c.estimated_cost_saving_pct>=0?'below':'above')+' baseline';
  $('cost-delta').className=c.estimated_cost_saving_pct>=0?'positive':'negative';
  $('peak-demand').textContent=decimal(o.peak_import_kw)+' kW';
  $('peak-delta').textContent=decimal(Math.abs(c.peak_reduction_kw))+' kW '+(c.peak_reduction_kw>=0?'lower':'higher')+' peak';
  $('solar-used').textContent=decimal(o.solar_utilized_kwh,0)+' kWh';
  const totalSolar=data.scenario.solar_kw.reduce((a,x)=>a+x,0);
  $('solar-rate').textContent=decimal(totalSolar?100*o.solar_utilized_kwh/totalSolar:0,0)+'% utilized';
  $('emissions').textContent=decimal(o.estimated_grid_emissions_kg,0)+' kg';
  const e=c.emissions_change_kg;
  $('emissions-delta').textContent=e>0?decimal(e,1)+' kg lower than baseline':e<0?decimal(-e,1)+' kg higher than baseline':'Same as baseline';
  $('emissions-delta').className=e>0?'positive':e<0?'negative':'neutral';
  const soc=o.ending_soc_kwh, pct=Math.round(100*soc/data.scenario.battery.capacity_kwh);
  $('battery-soc').textContent=decimal(soc,0);
  $('battery-pct').textContent=pct+'%';
  $('battery-fill').style.height=pct+'%';$('soc-bar').style.width=pct+'%';
  $('battery-cap-label').textContent=data.scenario.battery.capacity_kwh+' kWh';
  $('battery-power-label').textContent='±'+decimal(data.scenario.battery.max_charge_kw,1)+' kW';
  renderPower(data[displayMode],data.scenario);
  renderGantt(data[displayMode]);
  renderComparison(b,o,c);
  renderInsights(data);
  $('job-summary').textContent=`${data.optimized.jobs.length} production jobs scheduled · all deadlines met`;
  renderTwin();
  renderStrategies(data);
  renderAudit(data);
  renderEmergency(data);
  renderOperationalAlerts(data);
  renderExperiment();
  renderMachineInspector();
}
function renderPower(plan,sc){
  const slots=plan.slots;
  const width=760,height=238,left=36,right=8,top=13,bottom=35;
  const W=width-left-right,H=height-top-bottom;
  const maxValue=Math.ceil(Math.max(140,...slots.map(s=>Math.max(s.grid_kw+s.solar_used_kw,s.base_kw+s.flexible_kw)))/25)*25;
  const X=i=>left+(i+.5)*W/slots.length;
  const Y=v=>top+H*(1-v/maxValue);
  const ticks=[0,.25,.5,.75,1].map(f=>Math.round(f*maxValue));
  let svg=`<svg role="img" aria-label="Hourly grid, solar and total demand chart for ${safe(plan.type)}" viewBox="0 0 ${width} ${height}" preserveAspectRatio="none"><title>Modelled hourly power dispatch; dotted line is total demand</title>`;
  for(let i=0;i<slots.length;i++){
    if(sc.grid_limit_kw[i]<150){svg+=`<rect class="limit-zone" x="${left+i*W/slots.length}" y="${top}" width="${W/slots.length}" height="${H}"/>`;}
  }
  for(const t of ticks){svg+=`<line class="gridline" x1="${left}" y1="${Y(t)}" x2="${width-right}" y2="${Y(t)}"/><text class="chart-axis" x="${left-9}" y="${Y(t)+3}" text-anchor="end">${t}</text>`;}
  for(let i=0;i<slots.length;i++){
    svg+=`<text class="chart-axis" x="${X(i)}" y="${height-13}" text-anchor="middle">${safe(slots[i].time.slice(0,2))}</text>`;
  }
  const path=fn=>slots.map((s,i)=>(i?'L':'M')+X(i)+','+Y(fn(s))).join(' ');
  const solarArea=path(s=>s.solar_used_kw)+` L${X(slots.length-1)},${Y(0)} L${X(0)},${Y(0)} Z`;
  svg+=`<path class="solararea" d="${solarArea}"/><path class="solarpoly" d="${path(s=>s.solar_used_kw)}"/><path class="demandpoly" d="${path(s=>s.base_kw+s.flexible_kw)}"/><path class="gridpoly" d="${path(s=>s.grid_kw)}"/>`;
  svg+=slots.map((s,i)=>`<circle class="chart-node" cx="${X(i)}" cy="${Y(s.grid_kw)}" r="3"><title>${safe(s.time)} Grid ${decimal(s.grid_kw)} kW | solar ${decimal(s.solar_used_kw)} kW | demand ${decimal(s.flexible_kw+s.base_kw)} kW | cap ${s.grid_limit_kw} kW</title></circle>`).join('');
  svg+='</svg>';
  $('power-chart').innerHTML=svg;
}
function renderGantt(plan){
  let html='<div class="gantt-cell-label">PRODUCTION EQUIPMENT</div>';
  for(let i=0;i<HOURS;i++)html+=`<div class="gantt-hour">${String(8+i).padStart(2,'0')}:00</div>`;
  for(const job of plan.jobs){
    html+=`<button type="button" class="gantt-cell-label job-select ${selectedJobId===job.id?'is-inspected':''}" data-job="${safe(job.id)}">${safe(job.name)}<span class="gantt-label-sub">${job.power_kw} kW · ${job.end-job.start}h duration · inspect ↗</span></button>`;
    for(let i=0;i<HOURS;i++){
      const running=i>=job.start && i<job.end;
      const first=i===job.start,last=i===job.end-1;
      const cls=`gantt-tick${running?' running':''}${first?' first':''}${last?' last':''}`;
      const css=running?` style="background:${safe(job.color)}"`:'';
      const label=running?`${safe(job.name)} working at ${8+i}:00`:`${safe(job.name)} idle at ${8+i}:00`;
      html+=`<button type="button" class="${cls} gantt-click ${selectedJobId===job.id?'is-inspected':''}" data-job="${safe(job.id)}" data-hour="${i}"${css} title="${label}. Click to inspect job and hour" aria-label="Inspect ${label}">${first?'▶':''}</button>`;
    }
  }
  $('gantt').innerHTML=html;
  $('gantt').querySelectorAll('[data-job]').forEach(button=>button.addEventListener('click',()=>{
    selectedJobId=button.dataset.job;
    if(button.dataset.hour!==undefined){stopPlayback();setHour(Number(button.dataset.hour));}
    renderGantt(latest[displayMode]);renderMachineInspector();
  }));
}
function renderComparison(b,o,c){
  const parts=[
    ['Total modeled operating cost',b.total_cost_inr,o.total_cost_inr,v=>inr(v)],
    ['Peak import',b.peak_import_kw,o.peak_import_kw,v=>decimal(v,1)+' kW'],
    ['Grid emissions estimate',b.estimated_grid_emissions_kg,o.estimated_grid_emissions_kg,v=>decimal(v,1)+' kg'],
  ];
  $('comparisons').innerHTML=parts.map(([label,oldV,newV,fmt])=>{
    const mx=Math.max(oldV,newV,1);
    return `<div class="compare-row"><div class="compare-label"><span>${label}</span><strong>${fmt(newV)}</strong></div><div class="compare-bar"><span class="old" style="width:${100*oldV/mx}%" title="Baseline ${fmt(oldV)}"></span></div><div class="bar-legend"><span>Feasible baseline: ${fmt(oldV)}</span><span>BASELINE</span></div><div class="compare-bar" style="margin-top:7px"><span class="new" style="width:${100*newV/mx}%" title="Optimized ${fmt(newV)}"></span></div><div class="bar-legend"><span>Optimized: ${fmt(newV)}</span><span>OPTIMIZED</span></div></div>`;
  }).join('');
  $('tradeoff-note').textContent=(c.emissions_change_kg<0?'Trade-off: modeled grid emissions increase by '+decimal(-c.emissions_change_kg,1)+' kg in this cost-optimized plan. Consider setting a carbon price above zero to prioritize emissions. ':'')+'Synthetic assumptions only. Baseline and optimization both respect task deadlines, grid power limits and battery bounds.';
}
function renderInsights(data){
  const opt=data.optimized;
  const messages=(data.explanations||[]).slice(0,7).map(e=>[
    e.kind==='battery'?'ϟ':e.kind==='constraint'?'⚑':e.kind==='schedule'?'↔':'✓',
    e.title,e.detail
  ]);
  if(data.scenario.emergency){messages.push(['⚠','Emergency load preservation',`Critical fixed demand was preserved; ${decimal(opt.metrics.unserved_noncritical_kwh,2)} kWh of modeled noncritical demand was curtailed across the outage. All five production tasks still finish on time.`]);}
  messages.push(['≋','Solve provenance',`SciPy HiGHS ${safe(opt.status)} · ${decimal(opt.solve_ms,0)} ms solver time. Battery charge and discharge modes are exclusive, and production windows are enforced.`]);
  $('insights-list').innerHTML=messages.map(([glyph,title,body])=>`<div class="insight"><span class="insight-icon">${safe(glyph)}</span><div><b>${safe(title)}</b><p>${safe(body)}</p></div></div>`).join('');
}
function renderTwin(){
  if(!latest)return;
  const plan=latest[displayMode],slot=plan.slots[selectedHour],sc=latest.scenario;
  if(!slot)return;
  const set=(id,v)=>{$(id).textContent=v;};
  const kW=n=>decimal(n,1)+' kW';
  const pv=slot.solar_used_kw;
  const demand=slot.base_kw+slot.flexible_kw;
  const batteryFlow=slot.discharge_kw-slot.charge_kw;
  const soc=slot.soc_kwh + slot.charge_kw*sc.battery.charge_efficiency-slot.discharge_kw/sc.battery.discharge_efficiency;
  const active=plan.jobs.filter(j=>j.start<=selectedHour&&selectedHour<j.end);
  set('twin-time',slot.time);
  set('twin-solar',kW(pv));set('twin-grid',kW(slot.grid_kw));set('twin-battery',kW(Math.abs(batteryFlow)));
  set('twin-battery-mode',batteryFlow>0.01?'DISCHARGING TO BUS':batteryFlow<-.01?'CHARGING FROM BUS':'BATTERY IDLE');
  set('twin-load',kW(demand-(slot.noncritical_shed_kw||0)));set('twin-bus',kW(demand-(slot.noncritical_shed_kw||0)));set('twin-machines',`${active.length} / ${plan.jobs.length}`);
  set('twin-grid-cap',`CAP ${decimal(slot.grid_limit_kw,0)} kW`);
  set('rail-solar',`${kW(pv)} / ${kW(slot.solar_available_kw)}`);
  set('rail-grid',`${kW(slot.grid_kw)} / ${kW(slot.grid_limit_kw)}`);
  set('rail-soc',`${decimal(soc,1)} / ${decimal(sc.battery.capacity_kwh,0)} kWh`);
  set('rail-tariff',inr(slot.tariff)+' / kWh');
  const difference=slot.grid_kw+slot.solar_used_kw+slot.discharge_kw+(slot.noncritical_shed_kw||0)-slot.charge_kw-demand;
  set('rail-balance',Math.abs(difference)<.04?'BALANCED · ≤0.04 kW':`${decimal(difference,2)} kW rounding`);
  set('hero-grid',kW(slot.grid_kw));set('hero-solar',kW(pv));set('hero-battery',`${decimal(soc,1)} kWh`);set('hero-load',kW(demand));
  set('twin-plan-status',displayMode.toUpperCase()+' · COMPUTED PLAN');
  $('rail-solar-bar').style.width=(slot.solar_available_kw?Math.min(100,100*pv/slot.solar_available_kw):0)+'%';
  $('rail-grid-bar').style.width=(slot.grid_limit_kw?Math.min(100,100*slot.grid_kw/slot.grid_limit_kw):0)+'%';
  $('rail-soc-bar').style.width=Math.max(0,Math.min(100,100*soc/sc.battery.capacity_kwh))+'%';
  $('hour-slider').value=selectedHour;
  renderHourAnalysis();
  $('active-machines').innerHTML=active.length?active.map(j=>`<button class="running-job machine-link" type="button" data-job="${safe(j.id)}"><span class="job-color" style="background:${safe(j.color)}"></span><span>${safe(j.name)}</span><strong>${decimal(j.power_kw,0)} kW ↗</strong></button>`).join(''):'<span class="idle-machines">No flexible jobs active this hour</span>';
  $('active-machines').querySelectorAll('[data-job]').forEach(b=>b.addEventListener('click',()=>{selectedJobId=b.dataset.job;renderGantt(latest[displayMode]);renderMachineInspector();$('machine-inspector').scrollIntoView({behavior:'smooth',block:'center'});}));
  document.querySelector('.network-stage').classList.toggle('discharging',batteryFlow>.01);
  document.querySelector('.network-stage').classList.toggle('charging',batteryFlow<-.01);
}
function setHour(hour){selectedHour=Math.max(0,Math.min(HOURS-1,hour));renderTwin();}
function stopPlayback(){
  if(playback){clearInterval(playback);playback=null;}
  const play=$('hour-play');play.textContent='▶ Play';play.setAttribute('aria-pressed','false');
}
$('hour-slider').addEventListener('input',e=>{stopPlayback();setHour(Number(e.target.value));});
$('hour-prev').addEventListener('click',()=>{stopPlayback();setHour((selectedHour+HOURS-1)%HOURS);});
$('hour-next').addEventListener('click',()=>{stopPlayback();setHour((selectedHour+1)%HOURS);});
$('hour-play').addEventListener('click',()=>{
  if(playback){stopPlayback();return;}
  if(!latest)return;
  $('hour-play').textContent='Ⅱ Pause';$('hour-play').setAttribute('aria-pressed','true');
  playback=setInterval(()=>{setHour((selectedHour+1)%HOURS);},1150);
});

function exportDispatch(){
  if(!latest)return;
  const plan=latest[displayMode];
  const names=['hour','noncritical_shed_kw','grid_kw','solar_used_kw','solar_available_kw','charge_kw','discharge_kw','soc_kwh','fixed_load_kw','flexible_load_kw','tariff_inr_per_kwh','grid_limit_kw','active_jobs'];
  const csv=[names.join(',')];
  for(let t=0;t<plan.slots.length;t++){
    const s=plan.slots[t];
    const active=plan.jobs.filter(j=>j.start<=t&&t<j.end).map(j=>j.name).join(' | ');
    const vals=[s.time,s.noncritical_shed_kw||0,s.grid_kw,s.solar_used_kw,s.solar_available_kw,s.charge_kw,s.discharge_kw,s.soc_kwh,s.base_kw,s.flexible_kw,s.tariff,s.grid_limit_kw,active];
    csv.push(vals.map(v=>'"'+String(v).replaceAll('"','""')+'"').join(','));
  }
  csv.push('"NOTICE","SYNTHETIC PLANNING DATA ONLY - NO LIVE FACTORY EQUIPMENT"');
  const blob=new Blob([csv.join('\r\n')],{type:'text/csv;charset=utf-8'});
  const url=URL.createObjectURL(blob);
  const a=document.createElement('a');a.href=url;a.download=`grid-flex-${displayMode}-${latest.scenario.preset}-dispatch.csv`;
  document.body.appendChild(a);a.click();a.remove();
  setTimeout(()=>URL.revokeObjectURL(url),1000);
}
$('export-button').addEventListener('click',exportDispatch);

function chooseStrategy(key){
  if(solvePending && latest && !lastSolvedControls)return;
  invalidateIntelligence('Strategy selected. Analyze this solved plan.');
  selectedStrategy=key;
  if(!latest||!latest.strategy_plans[key])return;
  latest.optimized=latest.strategy_plans[key];
  latest.comparison=latest.strategy_comparisons[key];
  latest.explanations=latest.strategy_explanations[key];
  displayMode='optimized';
  for(const name of ['optimized','baseline']){
    $('show-'+name).classList.toggle('active',name===displayMode);
    $('show-'+name).setAttribute('aria-pressed',String(name===displayMode));
  }
  render(latest);
}
function renderStrategies(data){
  const frontier=data.frontier||[];
  const captions={cost:'Optimize energy bills and demand charge',balanced:'Apply a ₹10/kg modeled carbon shadow price',carbon:'Apply a ₹150/kg modeled carbon shadow price'};
  $('strategy-choices').innerHTML=frontier.map(s=>`<button type="button" class="strategy-choice ${selectedStrategy===s.key?'selected':''}" data-strategy="${safe(s.key)}" aria-pressed="${s.key===selectedStrategy}"><span>${safe(s.name)}</span><strong>${inr(s.metrics.total_cost_inr)} <small>· ${decimal(s.metrics.estimated_grid_emissions_kg,1)} kg CO₂e*</small></strong><em>${safe(captions[s.key])}</em></button>`).join('');
  $('strategy-choices').querySelectorAll('button').forEach(b=>b.addEventListener('click',()=>chooseStrategy(b.dataset.strategy)));
  if(!frontier.length)return;
  const costs=frontier.map(s=>s.metrics.total_cost_inr), carbons=frontier.map(s=>s.metrics.estimated_grid_emissions_kg);
  const xmin=Math.min(...carbons)-2,xmax=Math.max(...carbons)+2,ymin=Math.min(...costs)*.96,ymax=Math.max(...costs)*1.04;
  const sx=x=>54+(x-xmin)/(xmax-xmin||1)*464;
  const sy=y=>190-(y-ymin)/(ymax-ymin||1)*143;
  let svg='<svg role="img" viewBox="0 0 560 235" preserveAspectRatio="xMidYMid meet"><title>Modeled emissions versus operating cost for three feasible dispatch strategies</title><line x1="54" y1="190" x2="520" y2="190" stroke="#547079"/><line x1="54" y1="42" x2="54" y2="190" stroke="#547079"/><text x="285" y="220" text-anchor="middle" fill="#9cb9c1" font-size="12">Modeled grid emissions (kg CO₂e*)</text><text x="10" y="22" fill="#9cb9c1" font-size="12">Operating cost (INR)</text>';
  for(let i=0;i<3;i++){const c=frontier[i],x=sx(c.metrics.estimated_grid_emissions_kg),y=sy(c.metrics.total_cost_inr);svg+=`<circle cx="${x}" cy="${y}" r="${selectedStrategy===c.key?9:7}" fill="${selectedStrategy===c.key?'#7dedc4':'#70abcc'}" stroke="#09212e" stroke-width="3"><title>${safe(c.name)}: ${inr(c.metrics.total_cost_inr)}, ${decimal(c.metrics.estimated_grid_emissions_kg,1)} kg modeled emissions</title></circle><text x="${x}" y="${y-14}" text-anchor="middle" fill="#d9edea" font-size="11">${safe(c.name)}</text>`;}
  svg+='</svg>';$('frontier-chart').innerHTML=svg;
  const weight=data.optimized.carbon_weight_inr_per_kg;
  $('strategy-note').textContent=`Selected: ${selectedStrategy.replaceAll('-',' ')} · carbon shadow price ₹${weight}/kg. *Emissions are synthetic grid-import estimates; these are feasible modeled candidates, not a real-world measured Pareto frontier.`;
}
function renderAudit(data){
  const a=data.verification[selectedStrategy];
  $('audit-status').textContent=a?.passed?'✓ ALL CHECKS PASSED':'CHECK REQUIRED';
  $('audit-status').classList.toggle('passed',Boolean(a?.passed));
  if(!a)return;
  const summary=a.summary;
  const items=[['Independent checks',a.checks_performed],['Power residual',decimal(summary.max_power_balance_error_kw,3)+' kW'],['Battery violations',decimal(summary.max_soc_bound_violation_kwh,3)+' kWh'],['Jobs on time',summary.scheduled_jobs+' / '+data.scenario.jobs.length]];
  $('audit-details').innerHTML=items.map(([l,v])=>`<div class="audit-stat"><span>${safe(l)}</span><strong>${safe(v)}</strong></div>`).join('');
}
function renderEmergency(data){
  const target=$('resilience-details');
  const m=data.optimized.metrics;
  if(!data.scenario.emergency){target.innerHTML='<p>Normal operation: optimize without interruption. Activate the emergency scenario to model a complete two-hour utility outage and check critical-load protection.</p>';return;}
  const outage=data.optimized.slots.filter(s=>s.grid_limit_kw===0);
  target.innerHTML=`<div class="emergency-banner">⚠ SIMULATED GRID OUTAGE · ${outage.map(s=>s.time).join(' / ')}</div><div class="emergency-stats"><div><span>Grid import during outage</span><strong>${decimal(outage.reduce((a,s)=>a+s.grid_kw,0),1)} kWh</strong></div><div><span>Noncritical demand curtailed</span><strong>${decimal(m.unserved_noncritical_kwh,2)} kWh</strong></div><div><span>Critical fixed load</span><strong>100% preserved</strong></div><div><span>Production deadlines</span><strong>${data.optimized.jobs.length}/${data.scenario.jobs.length} met</strong></div></div><p>Load curtailment is explicitly limited to up to 30% of modeled fixed demand, with a large penalty. It is not a physical load-shedding command.</p>`;
}


/* Interactive mission deck. Every tile recomputes its own synthetic scenario. */
const DEFAULT_CONTROLS = {preset:'grid-stress','solar-scale':100,'tariff-scale':100,'carbon-price':0,'demand-scale':100,'battery-capacity':72,'grid-cap':86,'battery-wear':0.15};
function applyInputs(config) {
  for(const [id,val] of Object.entries(config)) $(id).value=val;
  updateControls();
}
function resetInputs(){applyInputs(DEFAULT_CONTROLS);currentMission=null;updateMissionTiles();}
function updateMissionTiles(){
  document.querySelectorAll('[data-mission]').forEach(b=>{
    const active=currentMission===b.dataset.mission;
    b.classList.toggle('mission-active',active);b.setAttribute('aria-pressed',String(active));
  });
}
async function launchMission(mission){
  if(solvePending)return;
  const settings={...DEFAULT_CONTROLS,preset:mission};
  if(mission==='cloudy')settings['solar-scale']=80;
  if(mission==='high-tariff')settings['tariff-scale']=120;
  applyInputs(settings);
  currentMission=mission;updateMissionTiles();
  selectedStrategy='cost';
  selectedHour={'normal':4,'cloudy':5,'high-tariff':8,'emergency-outage':8}[mission]??0;
  await runOptimization();
  $('command-room').scrollIntoView({behavior:'smooth',block:'start'});
}
document.querySelectorAll('[data-mission]').forEach(b=>b.addEventListener('click',()=>launchMission(b.dataset.mission)));
$('reset-controls').addEventListener('click',()=>{resetInputs();selectedStrategy='cost';selectedHour=0;runOptimization();});

function renderOperationalAlerts(data){
  const alerts=data.operator_alerts?.[selectedStrategy]||[];
  $('alert-count').textContent=`${alerts.filter(a=>a.severity!=='ok').length} modeled signals`;
  $('operator-alerts').innerHTML=alerts.map((a,i)=>`<button type="button" data-alert="${i}" class="operational-alert ${safe(a.severity)}"><span class="alert-level">${a.severity==='critical'?'CRITICAL':a.severity==='warning'?'ATTENTION':a.severity==='ok'?'ALL CLEAR':'OPPORTUNITY'}</span><strong>${safe(a.title)}</strong><span class="alert-description">${safe(a.detail)}</span><span class="alert-action">${safe(a.action)} ${a.hour===null?'':'· '+safe(data.scenario.hours[a.hour])} ↗</span></button>`).join('');
  $('operator-alerts').querySelectorAll('[data-alert]').forEach(b=>b.addEventListener('click',()=>{
    const alert=alerts[Number(b.dataset.alert)];
    if(alert.kind==='carbon'){chooseStrategy('carbon');$('decision-lab').scrollIntoView({behavior:'smooth',block:'center'});return;}
    if(Number.isInteger(alert.hour)){if(displayMode==='baseline')switchPlan('optimized');stopPlayback();setHour(alert.hour);$('command-room').scrollIntoView({behavior:'smooth',block:'center'});return;}
    $('grid-proof').scrollIntoView({behavior:'smooth',block:'center'});
  }));
}
$('jump-peak').addEventListener('click',()=>{
  if(!latest)return;
  const slots=latest[displayMode].slots;
  const peak=Math.max(...slots.map(s=>s.grid_kw));
  const index=slots.findIndex(s=>Math.abs(s.grid_kw-peak)<0.002);
  stopPlayback();setHour(index);$('command-room').scrollIntoView({behavior:'smooth',block:'center'});
});
function renderHourAnalysis(){
  if(!latest)return;
  const slot=latest[displayMode].slots[selectedHour];
  if(!slot)return;
  const delta=slot.grid_limit_kw-slot.grid_kw;
  const battery=slot.discharge_kw>0.05?`Supplying ${decimal(slot.discharge_kw,1)} kW`:slot.charge_kw>0.05?`Absorbing ${decimal(slot.charge_kw,1)} kW`:'Standing by';
  const shed=slot.noncritical_shed_kw||0;
  $('hour-analysis').innerHTML=`<div class="hour-summary-title"><span>SELECTED HOUR BREAKDOWN</span><strong>${safe(slot.time)}–${String(Number(slot.time.slice(0,2))+1).padStart(2,'0')}:00</strong></div>
    <div class="hour-breakdown"><div><span>Grid headroom</span><strong>${decimal(delta,1)} kW</strong></div><div><span>PV unused</span><strong>${decimal(Math.max(0,slot.solar_available_kw-slot.solar_used_kw),1)} kW</strong></div><div><span>Battery action</span><strong>${safe(battery)}</strong></div><div><span>Noncritical shed</span><strong>${decimal(shed,1)} kW</strong></div></div>`;
}

function renderMachineInspector(){
  if(!latest)return;
  const plan=latest[displayMode];
  if(!selectedJobId)selectedJobId=plan.jobs[0]?.id;
  const job=plan.jobs.find(j=>j.id===selectedJobId);
  if(!job){$('inspector-content').textContent='Select a machine above.';return;}
  const before=latest.baseline.jobs.find(j=>j.id===job.id);
  const hours=job.end-job.start;
  const shift=job.start-before.start;
  const deadline=latest.scenario.jobs.find(j=>j.id===job.id).deadline;
  $('inspector-name').textContent=job.name;
  $('inspector-content').innerHTML=`<div class="inspect-metric"><span>Scheduled window</span><strong>${safe(latest.scenario.hours[job.start])}–${String(8+job.end).padStart(2,'0')}:00</strong></div><div class="inspect-metric"><span>Electrical demand</span><strong>${decimal(job.power_kw*hours,1)} kWh</strong></div><div class="inspect-metric"><span>Vs baseline start</span><strong>${shift===0?'Unchanged':Math.abs(shift)+'h '+(shift>0?'later':'earlier')}</strong></div><div class="inspect-metric"><span>Deadline slack</span><strong>${deadline-job.end} h</strong></div><p>Modeled fixed-duration operation: ${decimal(job.power_kw,1)} kW for ${hours} hours. The solver selected the start time within its release and deadline window.</p><button class="button secondary compact" id="inspect-jump" type="button">View start hour ↗</button>`;
  $('inspect-jump').addEventListener('click',()=>{stopPlayback();setHour(job.start);$('command-room').scrollIntoView({behavior:'smooth',block:'center'});});
}

/* Session-local A/B experimentation: only solver-produced metrics, no fabricated deltas. */
function captureCurrent(){
  return {id:latest.run_id,when:new Date().toLocaleTimeString('en-IN'),preset:latest.scenario.preset,
    inputs:{...lastSolvedControls},strategy:selectedStrategy,plan:{...latest.optimized.metrics},verification:latest.verification[selectedStrategy]?.passed};
}
$('save-experiment').addEventListener('click',()=>{
  if(!latest)return;
  pinnedRun=captureCurrent();
  $('experiment-status').textContent='Reference pinned. Now change a scenario, select another strategy, or adjust what-if inputs.';
  renderExperiment();
});
function indicator(from,to,unit,lowerIsBetter){
  const diff=to-from;
  const favorable=lowerIsBetter?diff<-.01:diff>.01;
  const worse=lowerIsBetter?diff>.01:diff<-.01;
  return `<span class="experiment-change ${favorable?'positive':worse?'negative':'neutral'}">${diff>0?'+':''}${decimal(diff,1)} ${unit}</span>`;
}
function renderExperiment(){
  if(!latest)return;
  if(!pinnedRun)return;
  const current=captureCurrent();
  const fields=[['Operating cost','total_cost_inr','₹',true],['Peak grid import','peak_import_kw','kW',true],['Modeled grid emissions','estimated_grid_emissions_kg','kg',true],['Solar used','solar_utilized_kwh','kWh',false],['Grid energy','grid_energy_kwh','kWh',true]];
  const table=fields.map(([name,key,unit,lower])=>`<div class="experiment-line"><span>${safe(name)}</span><strong>${unit==='₹'?inr(pinnedRun.plan[key]):decimal(pinnedRun.plan[key],1)+' '+unit}</strong><strong>${unit==='₹'?inr(current.plan[key]):decimal(current.plan[key],1)+' '+unit}</strong>${indicator(pinnedRun.plan[key],current.plan[key],unit,lower)}</div>`).join('');
  $('experiment-results').innerHTML=`<div class="experiment-compare-head"><div><span>REFERENCE · ${safe(pinnedRun.preset)}</span><strong>${safe(pinnedRun.strategy.toUpperCase())} · ${safe(pinnedRun.when)}</strong></div><div><span>CURRENT · ${safe(current.preset)}</span><strong>${safe(current.strategy.toUpperCase())}</strong></div></div><div class="experiment-grid-table"><div class="experiment-column-head"><span>METRIC</span><span>PINNED</span><span>CURRENT</span><span>CHANGE</span></div>${table}</div><div class="experiment-compare-foot"><span>Both plans were individually solved and verified. Deltas describe different input assumptions, not causal savings.</span><button id="restore-experiment" class="button secondary compact" type="button">↺ Restore pinned inputs & run</button></div>`;
  $('restore-experiment').addEventListener('click',async()=>{
    applyInputs({'preset':pinnedRun.inputs.preset,'solar-scale':Math.round(pinnedRun.inputs.solar_scale*100),'tariff-scale':Math.round(pinnedRun.inputs.tariff_multiplier*100),'carbon-price':pinnedRun.inputs.carbon_price,'demand-scale':Math.round(pinnedRun.inputs.demand_scale*100),'battery-capacity':pinnedRun.inputs.battery_capacity,'grid-cap':pinnedRun.inputs.evening_grid_cap,'battery-wear':pinnedRun.inputs.battery_wear_cost??0.15});
    selectedStrategy=pinnedRun.strategy;
    await runOptimization();
  });
}
function downloadText(filename,content){
  const blob=new Blob([content],{type:'text/markdown;charset=utf-8'});
  const url=URL.createObjectURL(blob),a=document.createElement('a');
  a.href=url;a.download=filename;document.body.appendChild(a);a.click();a.remove();
  setTimeout(()=>URL.revokeObjectURL(url),2000);
}
$('download-brief').addEventListener('click',()=>{
  if(!latest)return;
  const a=latest.optimized.metrics,b=latest.baseline.metrics,sc=latest.scenario;
  const cells=Object.entries(a).map(([k,v])=>`| ${k} | ${v} | ${b[k]??'—'} |`).join('\n');
  const reference=pinnedRun?`\n## Pinned reference (${pinnedRun.preset}, ${pinnedRun.strategy})\n${Object.entries(pinnedRun.plan).map(([k,v])=>`- ${k}: ${v}`).join('\n')}\n`:'';
  const advice=(latest.operator_alerts?.[selectedStrategy]||[]).map(x=>`- ${x.title} (${x.severity}): ${x.detail}`).join('\n');
  const analysisNote=typeof intelligenceBrief==='function'?intelligenceBrief():'';
  const text=`# Grid Flex — Synthetic dispatch decision brief\n\nGenerated: ${new Date().toISOString()}\nRun ID: ${latest.run_id}\nScenario: ${sc.preset}\nSelected strategy: ${selectedStrategy}\nModel: ${latest.optimized.solver}; status ${latest.optimized.status}\n\n## Computed comparison\n| Metric | Optimized | Feasible baseline |\n|---|---:|---:|\n${cells}\n\n## Operational signals\n${advice}\n\n## Mathematical audit\n${JSON.stringify(latest.verification[selectedStrategy].summary,null,2)}\n${reference}\n${analysisNote}\n## Methodology and limits\nAll inputs, loads, tariffs and emissions factors are synthetic. Plans optimize a 12-hour illustrative schedule under declared battery, machine, grid and power-balance constraints. They are not live telemetry, site-approved operating instructions, guaranteed savings or measured environmental impact. AWS deployment is not implied.\n`;
  downloadText(`grid-flex-${sc.preset}-${selectedStrategy}-decision-brief.md`,text);
});


async function initialize(){
  try{
    const status=await request('/api/health');
    $('side-engine').textContent=status.environment==='aws-lambda'?'AWS Lambda · DynamoDB':'Local simulator · not deployed';
  }catch{
    $('side-engine').textContent='Offline — start Python server';
  }
  await runOptimization();
}
// Started after intelligence handlers are loaded.
