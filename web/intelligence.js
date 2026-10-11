/* On-demand calculations are scoped to one successful run and strategy. */
let intelligence=null, intelligenceGeneration=0, analysisPending=false;
function invalidateIntelligence(message){
  intelligenceGeneration++;intelligence=null;
  $('intelligence-results').hidden=true;
  $('intelligence-status').textContent=message;
  $('analyze-button').disabled=analysisPending||solvePending||!latest||$('download-brief').disabled;
}
function analysisTable(headers,rows){return `<div class="analysis-scroll"><table class="analysis-table"><thead><tr>${headers.map(x=>`<th scope="col">${safe(x)}</th>`).join('')}</tr></thead><tbody>${rows.map(row=>`<tr>${row.map((x,i)=>i===0?`<th scope="row">${safe(x)}</th>`:`<td>${safe(x)}</td>`).join('')}</tr>`).join('')}</tbody></table></div>`;}
function analysisMetric(label,value,detail){return `<div class="analysis-stat"><span>${safe(label)}</span><strong>${safe(value)}</strong><small>${safe(detail)}</small></div>`;}
function renderRisk(){
  const a=intelligence,cur=a.current.stress,alt=a.conservative.stress;
  const nominal=cur.cases[0].feasible_metrics,other=alt?.cases[0].feasible_metrics;
  $('risk-view').innerHTML=`<div class="analysis-kpis">${analysisMetric('Existing plan',`${cur.passed_count} / ${cur.tested_count} · ${cur.pass_pct}%`,'Stress cases satisfying all modeled constraints')}${analysisMetric('60% solar alternative',alt?`${alt.passed_count} / ${alt.tested_count} · ${alt.pass_pct}%`:'No feasible plan',alt?'Same five stress cases':'Check solar and outage constraints')}${analysisMetric('High-risk hours',cur.hours.filter(h=>h.high_risk).length,'Existing plan fails at least two stress cases')}</div>
    <p class="analysis-note">${safe(a.method)}</p>
    ${a.conservative.error?`<p class="analysis-warning" role="status">Conservative alternative unavailable: ${safe(a.conservative.error)}</p>`:''}
    ${analysisTable(['Solar stress case','Available PV (kWh)','Existing plan','60% alternative'],cur.cases.map((c,i)=>[c.name,decimal(c.solar_kw.reduce((s,x)=>s+x,0),1),c.passed?'PASS':`${decimal(c.shortfall_kwh,2)} kWh shortfall`,alt?(alt.cases[i].passed?'PASS':`${decimal(alt.cases[i].shortfall_kwh,2)} kWh shortfall`):'Unavailable']))}
    <div class="analysis-controls"><label for="stress-case">Inspect solar profile</label><select id="stress-case">${cur.cases.map((c,i)=>`<option value="${i}">${safe(c.name)}</option>`).join('')}</select></div><div id="solar-profile"></div>
    <h4>Planning trade-offs · evaluated at expected solar</h4>
    ${analysisTable(['Metric','Existing plan','60% alternative'],[['Modeled total cost',inr(nominal.total_cost_inr),other?inr(other.total_cost_inr):'Unavailable'],['Peak grid import',decimal(nominal.peak_import_kw)+' kW',other?decimal(other.peak_import_kw)+' kW':'—'],['Battery throughput',decimal(nominal.battery_throughput_kwh)+' kWh',other?decimal(other.battery_throughput_kwh)+' kWh':'—'],['End-of-horizon battery',decimal(nominal.ending_soc_kwh)+' kWh',other?decimal(other.ending_soc_kwh)+' kWh':'—'],['Jobs within deadlines',a.current.plan.jobs.length,other?a.conservative.plan.jobs.length:'—']])}
    <p class="analysis-note">Costs above apply the same expected solar, tariff, carbon weight and wear allowance to each fixed dispatch policy. Infeasible stress cases have no comparable operating-cost figure. The alternative keeps its lower planned PV use and may leave extra solar unused.</p>
    ${other?analysisTable(['Production job','Existing window','Alternative window'],a.current.plan.jobs.map(j=>{const k=a.conservative.plan.jobs.find(x=>x.id===j.id);return [j.name,`${8+j.start}:00–${8+j.end}:00`,`${8+k.start}:00–${8+k.end}:00`]})):''}`;
  $('stress-case').addEventListener('change',renderSolarProfile);renderSolarProfile();
}
function renderSolarProfile(){
  const a=intelligence,index=Number($('stress-case').value),cur=a.current.stress,c=cur.cases[index],alt=a.conservative.stress?.cases[index];
  $('solar-profile').innerHTML=analysisTable(['Hour','Expected PV kW','Stressed PV kW','Existing deficit kWh','Alternative deficit kWh','Existing risk count'],c.solar_kw.map((pv,t)=>[a.current.plan.slots[t].time,decimal(a.expected_solar_kw[t]),decimal(pv),decimal(c.shortfall_by_hour_kwh[t],2),alt?decimal(alt.shortfall_by_hour_kwh[t],2):'—',`${cur.hours[t].failing_cases}/5${cur.hours[t].high_risk?' · HIGH':''}`]));
}
function renderHealth(){
  const a=intelligence,b=a.battery,off=b.without_wear,on=b.with_wear;
  const delta=off.throughput_kwh-on.throughput_kwh;
  $('health-view').innerHTML=`<div class="analysis-kpis">${analysisMetric('Wear allowance',`₹${decimal(b.wear_rate_inr_per_kwh,2)}/kWh`,'Applied to charge + discharge throughput')}${analysisMetric('Approx. equivalent cycles',decimal(on.equivalent_full_cycles,3),'For this 12-hour plan; not a lifetime prediction')}${analysisMetric('Throughput change',`${delta>=0?'−':'+'}${decimal(Math.abs(delta),1)} kWh`,'With wear relative to the no-wear optimization')}</div>
    <p class="analysis-note">${safe(b.efc_formula)}. ${safe(a.battery_disclosure)}</p>
    ${analysisTable(['Same scenario and strategy','Wear ignored in solve','Wear included in solve'],[['Operating cost excluding wear',inr(off.operating_cost_inr),inr(on.operating_cost_inr)],['Wear valued at selected rate',inr(off.wear_at_common_rate_inr),inr(on.wear_at_common_rate_inr)],['Total at common wear rate',inr(off.total_at_common_rate_inr),inr(on.total_at_common_rate_inr)],['AC battery throughput',decimal(off.throughput_kwh)+' kWh',decimal(on.throughput_kwh)+' kWh'],['Approx. equivalent full cycles',decimal(off.equivalent_full_cycles,3),decimal(on.equivalent_full_cycles,3)],['Peak demand',decimal(off.peak_import_kw)+' kW',decimal(on.peak_import_kw)+' kW'],['Jobs within deadlines',off.jobs_completed,on.jobs_completed]])}
    <p class="analysis-note">Both plans share physical constraints, initial/end reserve, tariffs and carbon weight. Both are valued at the selected wear rate for a fair comparison. Zero or small wear assumptions may leave dispatch unchanged. Adjust the wear slider, run optimization, then analyze again.</p>
    <h4>Dispatch sensitivity · AC power (kW)</h4>
    ${analysisTable(['Hour','No wear: charge / discharge','With wear: charge / discharge'],a.current.plan.slots.map((s,t)=>{const n=b.without_wear_plan.slots[t];return [s.time,`${decimal(n.charge_kw)} / ${decimal(n.discharge_kw)}`,`${decimal(s.charge_kw)} / ${decimal(s.discharge_kw)}`]}))}`;
}
$('analyze-button').addEventListener('click',async()=>{
  if(!latest||analysisPending||solvePending||$('download-brief').disabled)return;
  const generation=++intelligenceGeneration,runId=latest.run_id,strategy=selectedStrategy;
  analysisPending=true;$('analyze-button').disabled=true;$('intelligence-results').hidden=true;
  $('intelligence-status').textContent='Solving conservative solar and wear comparisons…';
  try{
    const result=await request('/api/intelligence',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({...lastSolvedControls,strategy,plan:latest.optimized})});
    if(generation!==intelligenceGeneration)return;
    intelligence={...result,run_id:runId};renderRisk();renderHealth();$('intelligence-results').hidden=false;
    $('intelligence-status').textContent=`Verified analysis · ${strategy} strategy · ${latest.scenario.preset} · solver: ${result.current.plan.status}. Synthetic scenarios only.`;
  }catch(err){if(generation===intelligenceGeneration)$('intelligence-status').textContent=`Analysis unavailable: ${err.message}`;}
  finally{analysisPending=false;$('analyze-button').disabled=solvePending||!latest||$('download-brief').disabled;}
});
for(const view of ['risk','health'])$(view+'-tab').addEventListener('click',()=>{
  for(const name of ['risk','health']){$(name+'-view').hidden=name!==view;$(name+'-tab').classList.toggle('active',name===view);$(name+'-tab').setAttribute('aria-pressed',String(name===view));}
});
function intelligenceBrief(){
  if(!intelligence)return '## Forecast / battery analysis\nNot run for this selected plan.\n';
  const a=intelligence,b=a.battery;
  return `## Forecast risk and battery economics\n${a.method}\n\nExisting plan: ${a.current.stress.passed_count}/5 pass. Conservative alternative: ${a.conservative.stress?.passed_count??'unavailable'}/5.\n\nWear rate: INR ${b.wear_rate_inr_per_kwh}/kWh AC throughput.\n${JSON.stringify({without_wear:b.without_wear,with_wear:b.with_wear,hour_risk:a.current.stress.hours},null,2)}\n\n${a.battery_disclosure}\n`;
}

initialize();
