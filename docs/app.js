'use strict';
const ui = Object.fromEntries(['query','band','technicalBand','company','germanyOnly','degreeFocus','results','count','total','priority','sources','updated','health','status','showApplied','exportApplied','importApplied','appliedStatus','pageSize','pageInfo','prevPage','nextPage'].map(id=>[id, document.getElementById(id)]));
let data = {jobs:[],sources:[]};
const berlinDate = s => {if(!s) return 'Not yet';const d=new Date(s);return Number.isNaN(+d)?'Unknown':new Intl.DateTimeFormat('en-GB',{timeZone:'Europe/Berlin',day:'2-digit',month:'short',hour:'2-digit',minute:'2-digit'}).format(d)};
const hoursSince = s => s ? (Date.now()-new Date(s).getTime())/36e5 : Infinity;
const sortWeight = { 'Review first':0, 'Possible':1, 'Low':2, 'Not target':3 };
// Browser-only application history. The public Pages website has no authenticated
// database: use Export/Import to carry marks between browsers or devices.
const HISTORY_KEY='germany-job-monitor:applications:v1';
let appliedRecords={};
let pageNumber=1;
function canStore(){try{return typeof localStorage!=='undefined'}catch(e){return false}}
function restoreHistory(){
  if(!canStore())return {};
  try{
    const obj=JSON.parse(localStorage.getItem(HISTORY_KEY)||'{}');
    return obj&&typeof obj==='object'&&obj.version===1&&obj.records&&typeof obj.records==='object'&&!Array.isArray(obj.records)?obj.records:{};
  }catch(e){return {}}
}
function saveHistory(){
  if(!canStore()){ui.appliedStatus.textContent='Browser storage unavailable. Application history will not persist; export a backup.';return;}
  try{localStorage.setItem(HISTORY_KEY,JSON.stringify({version:1,records:appliedRecords}));}
  catch(e){ui.appliedStatus.textContent='Could not save application marks. Browser storage may be disabled.';}
}
function compactTitle(s){return String(s||'').toLocaleLowerCase().replace(/\((?:m\/w\/d|w\/m\/d|f\/m\/d|m\/f\/d|all genders?)\)/g,'').replace(/[^\p{L}\p{N}]+/gu,' ').trim()}
function fingerprint(j){return compactTitle(j.company)+'|'+compactTitle(j.title)}
function findPriorApplication(job){
  const direct=appliedRecords[job.key];
  if(direct)return {record:direct,direct:true};
  const fp=fingerprint(job);
  const matches=Object.values(appliedRecords).filter(r=>r&&r.fingerprint===fp&&r.key!==job.key);
  matches.sort((a,b)=>String(b.applied_at||'').localeCompare(String(a.applied_at||'')));
  return matches.length?{record:matches[0],direct:false}:null;
}
function dateAfter(a,b){return a&&b&&Number.isFinite(Date.parse(a))&&Number.isFinite(Date.parse(b))&&Date.parse(a)>Date.parse(b)}
function applicationStatus(job){
  const ref=findPriorApplication(job);
  if(!ref)return {applied:false,repost:false,reason:''};
  const r=ref.record;
  if(!ref.direct){
    return {applied:false,repost:dateAfter(job.first_detected,r.applied_at),reason:'Similar title previously applied; verify whether this is a repost or another opening'};
  }
  if(dateAfter(job.reopened_at,r.applied_at))return {applied:true,repost:true,reason:'This listing disappeared and later reappeared after the recorded application'};
  if(dateAfter(job.published_at,r.applied_at))return {applied:true,repost:true,reason:'Advertised publication date is later than the recorded application — verify reposting'};
  return {applied:true,repost:false,reason:'Applied on '+new Date(r.applied_at).toLocaleDateString('en-GB')};
}
function markApplied(job){
  appliedRecords[String(job.key)]={key:String(job.key),company:String(job.company||''),title:String(job.title||''),
    fingerprint:fingerprint(job),applied_at:new Date().toISOString(),url:String(job.url||'')};
  saveHistory();render();
}
function unmarkApplied(job){delete appliedRecords[String(job.key)];saveHistory();render();}
function exportHistory(){
  const text=JSON.stringify({version:1,exported_at:new Date().toISOString(),records:appliedRecords},null,2);
  const blob=new Blob([text],{type:'application/json'});const href=URL.createObjectURL(blob);
  const a=document.createElement('a');a.href=href;a.download='germany-job-monitor-applications.json';document.body.append(a);a.click();a.remove();
  setTimeout(()=>URL.revokeObjectURL(href),1000);
}
async function importHistory(file){
  if(!file)return;
  if(file.size>2_000_000){ui.appliedStatus.textContent='Import rejected: file exceeds 2 MB.';return;}
  try{
    const obj=JSON.parse(await file.text());
    if(obj.version!==1||!obj.records||typeof obj.records!=='object'||Array.isArray(obj.records))throw new Error('Unexpected export format');
    const incoming=Object.entries(obj.records);
    if(incoming.length>5000)throw new Error('Too many records');
    let n=0;
    for(const [key,r] of incoming){
      if(!key||key.length>512||!r||r.key!==key||typeof r.title!=='string'||typeof r.company!=='string'||!Number.isFinite(Date.parse(r.applied_at)))continue;
      appliedRecords[key]={key,company:r.company.slice(0,250),title:r.title.slice(0,500),fingerprint:fingerprint(r),
        applied_at:r.applied_at,url:typeof r.url==='string'?r.url.slice(0,1500):''};n++;
    }
    saveHistory();render();ui.appliedStatus.textContent=`Imported ${n} application records. Stored locally in this browser.`;
  }catch(e){ui.appliedStatus.textContent='Import failed: '+e.message;}
}

function el(tag, className, text){let a=document.createElement(tag);if(className)a.className=className;if(text!==undefined)a.textContent=String(text);return a}
function chip(text, cls=''){return el('span','chip '+cls,text)}

// Card sections use structured text nodes instead of injecting employer content as HTML.
function evidenceSection(title, items, type='evidence'){
  if(!items.length)return null;
  const section=el('section','evidence-section '+type);
  section.append(el('h3','evidence-heading',title));
  const list=el('ul','evidence-list');
  for(const item of items){
    const li=el('li','evidence-item');
    if(item.label)li.append(el('strong','evidence-label',item.label+': '));
    li.append(el('span','',item.text));
    list.append(li);
  }
  section.append(list);
  return section;
}
function appendQualificationGroup(parent, title, items){
  if(!items.length)return;
  const section=el('section','qualification-group');
  section.append(el('h4','qualification-group-title',title));
  const list=el('ul','qualification-list');
  for(const item of items){
    const li=el('li','qualification-item');
    li.append(el('span','qualification-name',item.name));
    li.append(el('span',item.documented?'evidence-status documented':'evidence-status unverified',item.documented?'Documented':'Not in experience record'));
    list.append(li);
  }
  section.append(list);
  parent.append(section);
}

// Fallback for deployments where the job snapshot lacks the newer worksite_* fields.
// Use the vacancy's advertised location; never infer a worksite from employer HQ.
const FALLBACK_CITY_REGIONS = [["Brandenburg an der Havel","Brandenburg","Germany"],["Inning am Ammersee","Bayern","Germany"],["Wasserburg am Inn","Bayern","Germany"],["Frankfurt am Main","Hessen","Germany"],["Unterschleißheim","Bayern","Germany"],["Oberpfaffenhofen","Bayern","Germany"],["Fürstenfeldbruck","Bayern","Germany"],["Oberschleißheim","Bayern","Germany"],["Friedrichshafen","Baden-Württemberg","Germany"],["Kaiserslautern","Rheinland-Pfalz","Germany"],["Aschaffenburg","Bayern","Germany"],["Braunschweig","Niedersachsen","Germany"],["Ludwigshafen","Rheinland-Pfalz","Germany"],["Fort Collins","Colorado","United States"],["Martinsried","Bayern","Germany"],["Taufkirchen","Bayern","Germany"],["Schweinfurt","Bayern","Germany"],["Rüsselsheim","Hessen","Germany"],["Bremerhaven","Bremen","Germany"],["Saarbrücken","Saarland","Germany"],["Gräfelfing","Bayern","Germany"],["Geretsried","Bayern","Germany"],["Regensburg","Bayern","Germany"],["Burghausen","Bayern","Germany"],["Wasserburg","Bayern","Germany"],["Ingolstadt","Bayern","Germany"],["Kaufbeuren","Bayern","Germany"],["Heidelberg","Baden-Württemberg","Germany"],["Oberkochen","Baden-Württemberg","Germany"],["Reutlingen","Baden-Württemberg","Germany"],["Ravensburg","Baden-Württemberg","Germany"],["Düsseldorf","Nordrhein-Westfalen","Germany"],["Leverkusen","Nordrhein-Westfalen","Germany"],["Hildesheim","Niedersachsen","Germany"],["Greifswald","Mecklenburg-Vorpommern","Germany"],["Zoetermeer","Zuid-Holland","Netherlands"],["Germering","Bayern","Germany"],["Karlsfeld","Bayern","Germany"],["Starnberg","Bayern","Germany"],["Nuremberg","Bayern","Germany"],["Memmingen","Bayern","Germany"],["Landsberg","Bayern","Germany"],["Stuttgart","Baden-Württemberg","Germany"],["Karlsruhe","Baden-Württemberg","Germany"],["Esslingen","Baden-Württemberg","Germany"],["Heilbronn","Baden-Württemberg","Germany"],["Pforzheim","Baden-Württemberg","Germany"],["Frankfurt","Hessen","Germany"],["Darmstadt","Hessen","Germany"],["Wiesbaden","Hessen","Germany"],["Bielefeld","Nordrhein-Westfalen","Germany"],["Paderborn","Nordrhein-Westfalen","Germany"],["Magdeburg","Sachsen-Anhalt","Germany"],["Osnabrück","Niedersachsen","Germany"],["Göttingen","Niedersachsen","Germany"],["Wolfsburg","Niedersachsen","Germany"],["Oldenburg","Niedersachsen","Germany"],["Flensburg","Schleswig-Holstein","Germany"],["Amsterdam","Noord-Holland","Netherlands"],["Innsbruck","Tirol","Austria"],["Garching","Bayern","Germany"],["Puchheim","Bayern","Germany"],["Freising","Bayern","Germany"],["Wessling","Bayern","Germany"],["Penzberg","Bayern","Germany"],["Würzburg","Bayern","Germany"],["Erlangen","Bayern","Germany"],["Nürnberg","Bayern","Germany"],["Augsburg","Bayern","Germany"],["Bayreuth","Bayern","Germany"],["Emmering","Bayern","Germany"],["Freiburg","Baden-Württemberg","Germany"],["Tübingen","Baden-Württemberg","Germany"],["Konstanz","Baden-Württemberg","Germany"],["Mannheim","Baden-Württemberg","Germany"],["Kronberg","Hessen","Germany"],["Dortmund","Nordrhein-Westfalen","Germany"],["Duisburg","Nordrhein-Westfalen","Germany"],["Freiberg","Sachsen","Germany"],["Chemnitz","Sachsen","Germany"],["Hannover","Niedersachsen","Germany"],["Schwerin","Mecklenburg-Vorpommern","Germany"],["Shanghai","Shanghai","China"],["München","Bayern","Germany"],["Planegg","Bayern","Germany"],["Neuried","Bayern","Germany"],["Maisach","Bayern","Germany"],["Weßling","Bayern","Germany"],["Gauting","Bayern","Germany"],["Alzenau","Bayern","Germany"],["Eresing","Bayern","Germany"],["Marburg","Hessen","Germany"],["Giessen","Hessen","Germany"],["Cologne","Nordrhein-Westfalen","Germany"],["Schwelm","Nordrhein-Westfalen","Germany"],["Münster","Nordrhein-Westfalen","Germany"],["Krefeld","Nordrhein-Westfalen","Germany"],["Dresden","Sachsen","Germany"],["Leipzig","Sachsen","Germany"],["Zwickau","Sachsen","Germany"],["Görlitz","Sachsen","Germany"],["Möckern","Sachsen-Anhalt","Germany"],["Hamburg","Hamburg","Germany"],["Koblenz","Rheinland-Pfalz","Germany"],["Rostock","Mecklenburg-Vorpommern","Germany"],["Potsdam","Brandenburg","Germany"],["Cottbus","Brandenburg","Germany"],["Homburg","Saarland","Germany"],["Toronto","Ontario","Canada"],["Coimbra","Coimbra","Portugal"],["Munich","Bayern","Germany"],["Coburg","Bayern","Germany"],["Singen","Baden-Württemberg","Germany"],["Kassel","Hessen","Germany"],["Gießen","Hessen","Germany"],["Aachen","Nordrhein-Westfalen","Germany"],["Bochum","Nordrhein-Westfalen","Germany"],["Plauen","Sachsen","Germany"],["Dessau","Sachsen-Anhalt","Germany"],["Berlin","Berlin","Germany"],["Bremen","Bremen","Germany"],["Lübeck","Schleswig-Holstein","Germany"],["Erfurt","Thüringen","Germany"],["Weimar","Thüringen","Germany"],["Vienna","Wien","Austria"],["Zurich","Zürich","Switzerland"],["Zürich","Zürich","Switzerland"],["London","England","United Kingdom"],["Warsaw","Mazowieckie","Poland"],["Pilsen","Plzeňský kraj","Czechia"],["Ningbo","Zhejiang","China"],["Hanau","Hessen","Germany"],["Fulda","Hessen","Germany"],["Essen","Nordrhein-Westfalen","Germany"],["Halle","Sachsen-Anhalt","Germany"],["Mainz","Rheinland-Pfalz","Germany"],["Trier","Rheinland-Pfalz","Germany"],["Delft","Zuid-Holland","Netherlands"],["Paris","Île-de-France","France"],["Plzeň","Plzeňský kraj","Czechia"],["Haar","Bayern","Germany"],["Köln","Nordrhein-Westfalen","Germany"],["Bonn","Nordrhein-Westfalen","Germany"],["Kiel","Schleswig-Holstein","Germany"],["Jena","Thüringen","Germany"],["Gera","Thüringen","Germany"],["Wien","Wien","Austria"],["Ulm","Baden-Württemberg","Germany"]];
const FALLBACK_STATE_NAMES = {"Bayern":["Bavaria","Bayern"],"Baden-Württemberg":["Baden-Württemberg","Baden-Wuerttemberg","Baden Wurttemberg"],"Hessen":["Hesse","Hessen"],"Nordrhein-Westfalen":["North Rhine-Westphalia","Nordrhein-Westfalen","NRW"],"Sachsen":["Saxony","Sachsen"],"Sachsen-Anhalt":["Saxony-Anhalt","Sachsen-Anhalt"],"Niedersachsen":["Lower Saxony","Niedersachsen"],"Rheinland-Pfalz":["Rhineland-Palatinate","Rheinland-Pfalz"],"Thüringen":["Thuringia","Thüringen"],"Brandenburg":["Brandenburg"],"Schleswig-Holstein":["Schleswig-Holstein"],"Berlin":["Berlin"],"Hamburg":["Hamburg"],"Bremen":["Bremen"]};
const FALLBACK_COUNTRIES = {"Germany":["Germany","Deutschland","DEU"],"Netherlands":["Netherlands","Nederland"],"United States":["United States","USA","U.S.A."],"Austria":["Austria","Österreich"],"Switzerland":["Switzerland","Schweiz"],"France":["France"],"United Kingdom":["United Kingdom","UK"],"Belgium":["Belgium"],"Canada":["Canada"],"Poland":["Poland"],"Portugal":["Portugal"],"Czechia":["Czech Republic","Czechia","Tschechien"],"India":["India"],"China":["China"]};
function hasLocationTerm(haystack, term){
  const n=String(haystack||'').normalize('NFC');
  const t=String(term||'').normalize('NFC');
  const escaped=t.replace(/[.*+?^${}()|[\]\\]/g,'\\$&');
  return new RegExp('(^|[^\\p{L}\\p{N}])'+escaped+'(?=$|[^\\p{L}\\p{N}])','iu').test(n);
}
function inferCountry(raw){
  const text=String(raw||'');
  if(/^(DE|DEU)$/i.test(text.trim()))return 'Germany';
  if(/^(NL)$/i.test(text.trim()))return 'Netherlands';
  for(const [country,aliases] of Object.entries(FALLBACK_COUNTRIES)){
    if(aliases.some(a=>hasLocationTerm(text,a)))return country;
  }
  return null;
}
function inferSite(raw,hint){
  const text=String(raw||'').trim();
  for(const [city,state,country] of FALLBACK_CITY_REGIONS){
    if(hasLocationTerm(text,city))return {city,state,country,text};
  }
  const country=inferCountry(text)||hint||null;
  let state=null;
  if(country==='Germany'){
    for(const [region,aliases] of Object.entries(FALLBACK_STATE_NAMES)){
      if(aliases.some(a=>hasLocationTerm(text,a))){state=region;break;}
    }
  }
  return {city:null,state,country,text};
}
function inferLocationForDisplay(job){
  const raw=String(job.location||'').trim();
  const countryHint=inferCountry(job.country||'');
  const parts=raw?raw.split(/\s*;\s*|\s+\|\s+|\s+\/\s+/).map(s=>s.trim()).filter(Boolean):[''];
  const sites=parts.map(s=>inferSite(s,countryHint));
  const multi=sites.length>1;
  const countries=[...new Set(sites.map(s=>s.country).filter(Boolean))].sort();
  const inferred={city:multi?null:sites[0].city,state:multi?null:sites[0].state,country:multi?(countries.join(' / ')||null):sites[0].country,sites,multiple:multi,note:multi?'Multiple advertised locations; confirm the actual worksite':(sites[0].city?'':'City not confirmed from the advertised location'),raw,fromFallback:true};
  const serverSites=Array.isArray(job.worksite_sites)?job.worksite_sites:[];
  const serverHasValues=Boolean(job.worksite_city||job.worksite_state||job.worksite_country||serverSites.some(s=>s.city||s.state||s.country));
  if(!serverHasValues)return inferred;
  return {
    city:job.worksite_city||inferred.city,
    state:job.worksite_state||inferred.state,
    country:job.worksite_country||inferred.country,
    sites:serverSites.length?serverSites:inferred.sites,
    multiple:job.worksite_multiple===true||inferred.multiple,
    note:job.worksite_note||inferred.note,
    raw,fromFallback:false
  };
}

function render(){
  const search=ui.query.value.trim().toLocaleLowerCase(); const company=ui.company.value;const band=ui.band.value;const technicalBand=ui.technicalBand.value;
  const jobs=data.jobs.filter(j=>{
    const scores=j.competency_counts;
    const evidence=(scores?Object.values(scores).flatMap(x=>[...(x.supported||[]),...(x.verify||[])]):[]);
    const hay=[j.company,j.title,j.location,j.description,...evidence,j.worksite_city||'',j.worksite_state||'',j.worksite_country||''].join(' ').toLocaleLowerCase();
    const techOk=technicalBand==='all'||(technicalBand==='some'&&scores&&scores.technical.matched>0)||(technicalBand==='none'&&scores&&scores.technical.matched===0)||(technicalBand==='unknown'&&!scores);
    const app=applicationStatus(j);
    const appliedVisible=ui.showApplied?.checked||!app.applied||app.repost;
    return appliedVisible&&techOk&&(company==='all'||company===j.company)&&(band==='all'||band===j.match_band)&&(!ui.germanyOnly.checked||j.location_status==='germany')&&(!ui.degreeFocus.checked||!j.hide_by_default)&&(!search||hay.includes(search));
  });
  const sourceDate=j=>(j.at_startup?(j.published_at||j.first_detected):(j.first_detected||j.published_at)||'');
  jobs.sort((a,b)=>Number(applicationStatus(b).repost)-Number(applicationStatus(a).repost)||(sortWeight[a.match_band]??9)-(sortWeight[b.match_band]??9)||sourceDate(b).localeCompare(sourceDate(a)));
  ui.results.replaceChildren();const hidden = ui.degreeFocus.checked ? data.jobs.filter(j=>j.hide_by_default).length : 0;
  const perPage=Number(ui.pageSize?.value)||50;const pages=Math.max(1,Math.ceil(jobs.length/perPage));pageNumber=Math.min(Math.max(1,pageNumber),pages);
  ui.count.textContent=`${jobs.length} matching${hidden ? ` · ${hidden} filtered by preference` : ''}`;
  if(ui.pageInfo)ui.pageInfo.textContent=`Page ${pageNumber} of ${pages} · ${jobs.length?((pageNumber-1)*perPage+1):0}–${Math.min(pageNumber*perPage,jobs.length)} of ${jobs.length}`;
  if(ui.prevPage)ui.prevPage.disabled=pageNumber<=1;if(ui.nextPage)ui.nextPage.disabled=pageNumber>=pages;
  if(!jobs.length){ui.results.append(el('p','muted','No positions match these filters. Try changing the filter or checking source health.'));return;}
  for(const job of jobs.slice((pageNumber-1)*perPage,pageNumber*perPage)){
    const card=el('article','job');const left=el('div');left.append(el('div','company',job.company),el('strong','',job.title));
    const worksite=inferLocationForDisplay(job);
    const place=(value)=>value||'Not specified';
    const locationText=worksite.multiple?
      ('Multiple worksites'+(worksite.country?' — '+worksite.country:'')):
      ([worksite.city,worksite.state,worksite.country].filter(Boolean).join(', ') || 'Location not specified');
    left.append(el('div','meta',locationText));
    if(worksite.multiple && worksite.sites.length){
      left.append(el('div','muted','Advertised worksites: '+worksite.sites.map(p=>`${p.city||'City unspecified'}, ${p.state||'State unspecified'}, ${p.country||'Country unspecified'}`).join(' ; ')));
    } else if(!worksite.city && worksite.raw){
      left.append(el('div','muted','Location as advertised: '+worksite.raw));
    } else if(worksite.note && !worksite.city){left.append(el('div','muted',worksite.note));}
    left.append(el('div','meta',`Source date ${berlinDate(job.published_at)} · First detected ${berlinDate(job.first_detected)}`));
    const tags=el('div','chips');
    const cls=job.match_band==='Review first'?'strong':job.match_band==='Possible'?'possible':'low';
    tags.append(chip(job.match_band,cls));
    const score=job.competency_counts;
    for(const [key,label] of [['technical','Technical'],['method','Methods'],['general','General']]){
      const cat=score?.[key];
      tags.append(chip(`${label} ${!cat?'?':cat.total?`${cat.matched}/${cat.total}`:'—'}`,cat&&cat.total&&cat.matched===cat.total?'strong':cat&&cat.matched>0?'possible':'low'));
    }
    const edu=job.education_review;
    if(edu?.possible_overqualified) tags.append(chip('Possible overqualified','possible'));
    const applied=applicationStatus(job);
    if(applied.repost)tags.append(chip('Previously applied · check repost','possible'));
    else if(applied.applied)tags.append(chip('Applied','low'));
    left.append(tags);
    if(applied.repost)left.append(el('p','repost-note',applied.reason));
    const notices=[];
    if(!job.at_startup&&hoursSince(job.first_detected)>=0&&hoursSince(job.first_detected)<24){
      notices.push({label:'New detection',text:'First detected within the last 24 hours'});
    }
    if(job.location_status!=='germany')notices.push({label:'Location',text:'Worksite country requires verification'});
    if(job.source_mode==='html_fallback')notices.push({label:'Source',text:'Title-only listing; full requirements unavailable'});
    if(job.hide_by_default)notices.push({label:'Role family',text:'Outside selected job families (hidden by default)'});
    for(const flag of (job.screening_flags||[]).filter(s=>!s.startsWith('Title-only')).slice(0,3)){
      notices.push({label:'Review flag',text:flag});
    }

    const supported=[];
    const verify=[];
    if(score){
      for(const [key,label] of [['technical','Technical'],['method','Methods'],['general','General']]){
        const c=score[key];
        if(c?.supported?.length)supported.push({label,text:c.supported.slice(0,4).join(' · ')});
        if(c?.verify?.length)verify.push({label,text:c.verify.slice(0,4).join(' · ')});
      }
    }else{
      notices.push({label:'Technical evidence',text:'Detailed criteria unavailable; no counts calculated'});
    }
    // Core specialization gaps often restate the technical category. Do not duplicate them.
    if((job.core_specializations_to_verify||[]).length && !score?.technical?.verify?.length){
      verify.push({label:'Core specialization',text:job.core_specializations_to_verify.slice(0,3).join(' · ')});
    }
    const evidence=evidenceSection('Documented experience',supported,'supported');
    if(evidence)left.append(evidence);
    const concerns=evidenceSection('Needs verification',verify,'verify');
    if(concerns)left.append(concerns);
    const notes=evidenceSection('Other review notes',notices,'notes');
    if(notes)left.append(notes);

    const priorityReview=job.qualification_priority;
    if(priorityReview?.status==='parsed'){
      const groups=[['explicit','Explicit requirements'],['preferred','Preferred qualifications'],
        ['learnable','Employer allows learning'],['listed','Listed — priority unspecified']];
      const expFlags=priorityReview.experience_flags||[];
      const explicitCount=(priorityReview.explicit||[]).length+expFlags.length;
      const totalDetected=groups.reduce((n,[key])=>n+(priorityReview[key]||[]).length,0)+expFlags.length;
      const details=el('details','requirement-review');
      const summary=el('summary','requirement-toggle');
      const chevron=el('span','requirement-chevron');chevron.append(el('span','requirement-chevron-icon','▶'));summary.append(chevron);
      const summaryText=el('span','requirement-text');
      summaryText.append(el('strong','requirement-label','Qualification requirements'));
      const hasEducation=edu?.status==='identified';
      summaryText.append(el('span','requirement-counts',`${hasEducation?'Education specified · ':''}${explicitCount} explicit · ${(priorityReview.preferred||[]).length} preferred · ${(priorityReview.learnable||[]).length} learnable · ${(priorityReview.listed||[]).length} unspecified`));
      summary.append(summaryText);
      details.append(summary);
      const body=el('div','requirement-body');
      // Education comes before technical, method, and general qualifications.
      // When a job states only experience, no artificial education row is shown.
      if(hasEducation){
        const section=el('section','qualification-group education-group');
        section.append(el('h4','qualification-group-title','Education / Studium & Ausbildung'));
        const list=el('ul','qualification-list');
        if(edu.minimum_evidence){
          const li=el('li','qualification-item');
          li.append(el('strong','',`Advertised education: ${edu.minimum_level || 'Level not determined'}. `));
          li.append(el('span','',edu.minimum_evidence));
          list.append(li);
        }
        if(edu.preferred_evidence){
          const li=el('li','qualification-item');
          li.append(el('strong','',`Preferred: ${edu.preferred_level || 'Level not determined'}. `));
          li.append(el('span','',edu.preferred_evidence));
          list.append(li);
        }
        for(const alternative of (edu.alternative_routes||[]).slice(0,2))list.append(el('li','qualification-item',alternative));
        if(edu.possible_overqualified){
          const li=el('li','qualification-item');
          li.append(el('strong','possible-overqualified','Possible overqualified — '));
          li.append(el('span','', 'Only a vocational qualification is identified. This may be a career-level mismatch, not an automatic rejection.'));
          list.append(li);
        }
        section.append(list);body.append(section);
      }
      if(!totalDetected&&!hasEducation)body.append(el('p','muted','No requirement categories recognized. Check the official advertisement.'));
      for(const [key,label] of groups)appendQualificationGroup(body,label,priorityReview[key]||[]);
      if(expFlags.length){
        const section=el('section','qualification-group');
        section.append(el('h4','qualification-group-title','Explicit experience thresholds'));
        const list=el('ul','qualification-list');
        for(const flag of expFlags.slice(0,3))list.append(el('li','qualification-item',flag.text));
        section.append(list);body.append(section);
      }
      body.append(el('p','requirement-caveat','“Not in experience record” does not establish that a skill is absent. Always verify the employer’s complete requirements.'));
      details.append(body);
      left.append(details);
    }else if(priorityReview?.status==='unavailable'){
      left.append(el('p','muted','Qualification details are unavailable; check the official advertisement.'));
    }
    if(!supported.length&&!verify.length&&(job.match_band==='Review first'||job.match_band==='Possible')&&job.triage_note){
      left.append(el('p','muted',job.triage_note));
    }
    card.append(left);
    const actions=el('div','job-actions');
    const a=el('a','', 'Official listing');a.href=job.url;a.target='_blank';a.rel='noopener noreferrer';actions.append(a);
    const applyButton=el('button','applied-button',applied.applied?(applied.repost?'Mark reapplied':'Undo applied mark'):(applied.repost?'Mark applied again':'Mark applied'));
    applyButton.type='button';applyButton.addEventListener('click',()=>{
      if(applied.applied&&!applied.repost)unmarkApplied(job);else markApplied(job);
    });
    actions.append(applyButton);card.append(actions);ui.results.append(card);
  }
}
async function main(){try{
  const response=await fetch('./jobs.json',{cache:'no-store'});if(!response.ok)throw new Error('Cannot read jobs.json');
  data=await response.json();const jobs=data.jobs||[];ui.total.textContent=jobs.length;ui.priority.textContent=jobs.filter(j=>j.match_band==='Review first').length;ui.sources.textContent=(data.sources||[]).length;ui.updated.textContent=berlinDate(data.last_checked);ui.status.textContent=data.notice||'';
  const names=[...new Set(jobs.map(j=>j.company))].sort();for(const name of names){const opt=document.createElement('option');opt.value=name;opt.textContent=name;ui.company.append(opt)}
  for(const source of (data.sources||[])){const item=el('div');const mode=source.source_mode==='public_rss_fallback'?' · official public RSS fallback':(source.source_mode==='html_fallback'?` · ${source.details_extracted||0} full descriptions · ${source.title_only_count||0} title-only`:(source.source_mode==='html_detail'?` · ${source.details_extracted||0} full descriptions from job pages`:''));item.append(el('strong','',source.name),el('div',source.status==='ok'?'muted':'error',source.status==='ok'?`${source.count} tracked${mode} · Last checked ${berlinDate(source.last_checked)}`:`Error: ${source.error||'Unreachable'}`));ui.health.append(item)}
  if(!(data.sources||[]).length)ui.health.append(el('div','muted','No source checks yet. Run the monitoring workflow.'));
  for(const key of ['query','band','technicalBand','company','germanyOnly','degreeFocus','showApplied','pageSize'])ui[key].addEventListener('input',()=>{pageNumber=1;render()});
  ui.prevPage.addEventListener('click',()=>{pageNumber=Math.max(1,pageNumber-1);render();ui.pageInfo.scrollIntoView({block:'nearest'});});
  ui.nextPage.addEventListener('click',()=>{pageNumber+=1;render();ui.pageInfo.scrollIntoView({block:'nearest'});});
  ui.exportApplied.addEventListener('click',exportHistory);
  ui.importApplied.addEventListener('change',async()=>{await importHistory(ui.importApplied.files?.[0]);ui.importApplied.value='';});
  appliedRecords=restoreHistory();
  if(!canStore())ui.appliedStatus.textContent='Browser storage is disabled; application marks may not persist.';
  render();
}catch(err){ui.status.textContent=`Cannot load vacancy data: ${err.message}`;ui.results.append(el('p','muted','Check that a monitoring run has completed successfully.'))}}
main();
