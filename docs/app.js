'use strict';
const ui = Object.fromEntries(['query','band','technicalBand','company','germanyOnly','degreeFocus','results','count','total','priority','sources','updated','health','status'].map(id=>[id, document.getElementById(id)]));
let data = {jobs:[],sources:[]};
const berlinDate = s => {if(!s) return 'Not yet';const d=new Date(s);return Number.isNaN(+d)?'Unknown':new Intl.DateTimeFormat('en-GB',{timeZone:'Europe/Berlin',day:'2-digit',month:'short',hour:'2-digit',minute:'2-digit'}).format(d)};
const hoursSince = s => s ? (Date.now()-new Date(s).getTime())/36e5 : Infinity;
const sortWeight = { 'Review first':0, 'Possible':1, 'Low':2, 'Not target':3 };
function el(tag, className, text){let a=document.createElement(tag);if(className)a.className=className;if(text!==undefined)a.textContent=String(text);return a}
function chip(text, cls=''){return el('span','chip '+cls,text)}
function render(){
  const search=ui.query.value.trim().toLocaleLowerCase(); const company=ui.company.value;const band=ui.band.value;const technicalBand=ui.technicalBand.value;
  const jobs=data.jobs.filter(j=>{const hay=[j.company,j.title,j.location,j.description,(j.matched_topics||[]).join(' '),(j.method_overlap||[]).join(' '),(j.technical_gaps_to_verify||[]).join(' '),(j.core_documented_tasks||[]).join(' '),(j.core_specializations_to_verify||[]).join(' '),j.worksite_city||'',j.worksite_state||'',j.worksite_country||''].join(' ').toLocaleLowerCase();const level=j.technical_review||'';const techOk=technicalBand==='all'||(technicalBand==='multiple'&&level.startsWith('Multiple'))||(technicalBand==='some'&&level.startsWith('Some'))||(technicalBand==='adjacent'&&level.startsWith('Adjacent'))||(technicalBand==='limited'&&(level.startsWith('Limited')||level==='Outside preferred job families'))||(technicalBand==='unknown'&&level.startsWith('Insufficient'));return techOk&&(company==='all'||company===j.company)&&(band==='all'||band===j.match_band)&&(!ui.germanyOnly.checked||j.location_status==='germany')&&(!ui.degreeFocus.checked||!j.hide_by_default)&&(!search||hay.includes(search))});
  const sourceDate=j=>(j.at_startup?(j.published_at||j.first_detected):(j.first_detected||j.published_at)||'');
  jobs.sort((a,b)=>(sortWeight[a.match_band]??9)-(sortWeight[b.match_band]??9)||sourceDate(b).localeCompare(sourceDate(a)));
  ui.results.replaceChildren();const hidden = ui.degreeFocus.checked ? data.jobs.filter(j=>j.hide_by_default).length : 0;ui.count.textContent=`${jobs.length} shown${hidden ? ` · ${hidden} filtered by preference` : ''}`;
  if(!jobs.length){ui.results.append(el('p','muted','No positions match these filters. Try changing the filter or checking source health.'));return;}
  for(const job of jobs){
    const card=el('article','job');const left=el('div');left.append(el('div','company',job.company),el('strong','',job.title));
    const place=(value)=>value||'Not specified';
    left.append(el('div','meta',`City: ${job.worksite_multiple?'Multiple':place(job.worksite_city)} · State: ${job.worksite_multiple?'Multiple':place(job.worksite_state)} · Country: ${place(job.worksite_country)}`));
    if(job.worksite_multiple && (job.worksite_sites||[]).length){
      left.append(el('div','muted','Advertised worksites: '+job.worksite_sites.map(p=>`${p.city||'City unspecified'}, ${p.state||'State unspecified'}, ${p.country||'Country unspecified'}`).join(' ; ')));
    } else if(job.worksite_note){left.append(el('div','muted',job.worksite_note));}
    left.append(el('div','meta',`Source date ${berlinDate(job.published_at)} · First detected ${berlinDate(job.first_detected)}`));
    const tags=el('div','chips');const cls=job.match_band==='Review first'?'strong':job.match_band==='Possible'?'possible':'low';tags.append(chip(job.match_band,cls));
    if(job.technical_review){const methodCls=job.technical_review.startsWith('Multiple')?'strong':job.technical_review.startsWith('Some')||job.technical_review.startsWith('Adjacent')?'possible':'low';tags.append(chip(job.technical_review,methodCls))}
    if(!job.at_startup&&hoursSince(job.first_detected)>=0&&hoursSince(job.first_detected)<24)tags.append(chip('Detected in last 24h','strong'));
    if(job.location_status!=='germany')tags.append(chip('Verify country','possible'));
    if(job.source_mode==='html_fallback')tags.append(chip('Title-only source; verify full criteria','possible'));
    if(job.hide_by_default)tags.append(chip(job.career_track==='training'?'Training/student':job.career_track==='vocational'?'Vocational title':'Unrelated job family','possible'));
    for (const flag of (job.screening_flags||[]).filter(s=>!s.startsWith('Title-only')).slice(0,4)) tags.append(chip(flag,'possible'));
    for(const topic of (job.matched_topics||[]).slice(0,3))tags.append(chip(topic));
    left.append(tags);
    if(job.core_review && job.core_review!=='Outside preferred job families'){
      left.append(el('div','muted','Core tasks: '+job.core_review));
      if((job.core_documented_tasks||[]).length)left.append(el('div','muted','Documented methods in main tasks: '+job.core_documented_tasks.slice(0,3).join(' · ')));
      if((job.core_specializations_to_verify||[]).length)left.append(el('div','muted','Core specializations to verify: '+job.core_specializations_to_verify.slice(0,3).join(' · ')));
    }
    if((job.method_overlap||[]).length)left.append(el('div','muted','Documented method overlap: '+job.method_overlap.slice(0,3).join(' · ')));
    if((job.technical_gaps_to_verify||[]).length)left.append(el('div','muted','Experience to verify: '+job.technical_gaps_to_verify.slice(0,2).join(' · ')));
    if(job.technical_review==='Insufficient job details')left.append(el('div','muted','Full job requirements unavailable; no technical assessment.'));
    if((job.match_band==='Review first'||job.match_band==='Possible')&&job.triage_note)left.append(el('div','muted',job.triage_note));
    card.append(left);const a=el('a','', 'Official listing');a.href=job.url;a.target='_blank';a.rel='noopener noreferrer';card.append(a);ui.results.append(card);
  }
}
async function main(){try{
  const response=await fetch('./jobs.json',{cache:'no-store'});if(!response.ok)throw new Error('Cannot read jobs.json');
  data=await response.json();const jobs=data.jobs||[];ui.total.textContent=jobs.length;ui.priority.textContent=jobs.filter(j=>j.match_band==='Review first').length;ui.sources.textContent=(data.sources||[]).length;ui.updated.textContent=berlinDate(data.last_checked);ui.status.textContent=data.notice||'';
  const names=[...new Set(jobs.map(j=>j.company))].sort();for(const name of names){const opt=document.createElement('option');opt.value=name;opt.textContent=name;ui.company.append(opt)}
  for(const source of (data.sources||[])){const item=el('div');const mode=source.source_mode==='html_fallback'?` · ${source.details_extracted||0} full descriptions · ${source.title_only_count||0} title-only`:(source.source_mode==='html_detail'?` · ${source.details_extracted||0} full descriptions from job pages`:'');item.append(el('strong','',source.name),el('div',source.status==='ok'?'muted':'error',source.status==='ok'?`${source.count} tracked${mode} · Last checked ${berlinDate(source.last_checked)}`:`Error: ${source.error||'Unreachable'}`));ui.health.append(item)}
  if(!(data.sources||[]).length)ui.health.append(el('div','muted','No source checks yet. Run the monitoring workflow.'));
  for(const key of ['query','band','technicalBand','company','germanyOnly','degreeFocus'])ui[key].addEventListener('input',render);render();
}catch(err){ui.status.textContent=`Cannot load vacancy data: ${err.message}`;ui.results.append(el('p','muted','Check that a monitoring run has completed successfully.'))}}
main();
