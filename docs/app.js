'use strict';
const ui = Object.fromEntries(['query','band','technicalBand','company','germanyOnly','degreeFocus','results','count','total','priority','sources','updated','health','status'].map(id=>[id, document.getElementById(id)]));
let data = {jobs:[],sources:[]};
const berlinDate = s => {if(!s) return 'Not yet';const d=new Date(s);return Number.isNaN(+d)?'Unknown':new Intl.DateTimeFormat('en-GB',{timeZone:'Europe/Berlin',day:'2-digit',month:'short',hour:'2-digit',minute:'2-digit'}).format(d)};
const hoursSince = s => s ? (Date.now()-new Date(s).getTime())/36e5 : Infinity;
const sortWeight = { 'Review first':0, 'Possible':1, 'Low':2, 'Not target':3 };
function el(tag, className, text){let a=document.createElement(tag);if(className)a.className=className;if(text!==undefined)a.textContent=String(text);return a}
function chip(text, cls=''){return el('span','chip '+cls,text)}

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
    return techOk&&(company==='all'||company===j.company)&&(band==='all'||band===j.match_band)&&(!ui.germanyOnly.checked||j.location_status==='germany')&&(!ui.degreeFocus.checked||!j.hide_by_default)&&(!search||hay.includes(search));
  });
  const sourceDate=j=>(j.at_startup?(j.published_at||j.first_detected):(j.first_detected||j.published_at)||'');
  jobs.sort((a,b)=>(sortWeight[a.match_band]??9)-(sortWeight[b.match_band]??9)||sourceDate(b).localeCompare(sourceDate(a)));
  ui.results.replaceChildren();const hidden = ui.degreeFocus.checked ? data.jobs.filter(j=>j.hide_by_default).length : 0;ui.count.textContent=`${jobs.length} shown${hidden ? ` · ${hidden} filtered by preference` : ''}`;
  if(!jobs.length){ui.results.append(el('p','muted','No positions match these filters. Try changing the filter or checking source health.'));return;}
  for(const job of jobs){
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
    left.append(tags);
    if(!job.at_startup&&hoursSince(job.first_detected)>=0&&hoursSince(job.first_detected)<24){
      left.append(el('div','muted','First detected within the last 24 hours'));
    }
    if(job.location_status!=='germany')left.append(el('div','muted','Worksite country requires verification'));
    if(job.source_mode==='html_fallback')left.append(el('div','muted','Title-only source; full requirements unavailable'));
    if(job.hide_by_default)left.append(el('div','muted','Outside selected job families (hidden by default)'));
    for(const flag of (job.screening_flags||[]).filter(s=>!s.startsWith('Title-only')).slice(0,3)){
      left.append(el('div','muted','Review flag: '+flag));
    }
    if(score){
      for(const [key,label] of [['technical','Technical'],['method','Methods'],['general','General']]){
        const c=score[key];
        if(c?.supported?.length)left.append(el('div','muted',`${label} documented: ${c.supported.slice(0,4).join(' · ')}`));
        if(c?.verify?.length)left.append(el('div','muted',`${label} to verify: ${c.verify.slice(0,4).join(' · ')}`));
      }
    }else{
      left.append(el('div','muted','Detailed criteria unavailable: no evidence counts calculated'));
    }
    const priorityReview=job.qualification_priority;
    if(priorityReview?.status==='parsed'){
      const groups=[['explicit','Explicit requirement wording'],
        ['preferred','Preferred qualifications'],
        ['learnable','Employer allows learning'],
        ['listed','Listed qualifications — priority unspecified']];
      const explicitCount=(priorityReview.explicit||[]).length+(priorityReview.experience_flags||[]).length;
      const totalDetected=groups.reduce((n,[key])=>n+(priorityReview[key]||[]).length,0)+(priorityReview.experience_flags||[]).length;
      const details=el('details','requirement-review');
      details.append(el('summary','',`Requirement wording: ${explicitCount} explicit · ${(priorityReview.preferred||[]).length} preferred · ${(priorityReview.learnable||[]).length} learnable · ${(priorityReview.listed||[]).length} unspecified`));
      if(!totalDetected){details.append(el('div','muted','No recognized requirement categories; verify the full job advertisement.'));}
      for(const [key,label] of groups){
        const items=priorityReview[key]||[];
        if(items.length){
          const summary=items.map(item=>`${item.name} (${item.documented?'documented':'not documented in current experience record'})`).join(' · ');
          details.append(el('div','muted',`${label}: ${summary}`));
        }
      }
      for(const flag of (priorityReview.experience_flags||[]).slice(0,3)){
        details.append(el('div','muted',`Explicit experience threshold — verify: ${flag.text}`));
      }
      left.append(details);
    }else if(priorityReview?.status==='unavailable'){
      left.append(el('div','muted','Qualification wording: insufficient description'));
    }
    if((job.core_specializations_to_verify||[]).length){
      left.append(el('div','muted','Core specialization gaps to verify: '+job.core_specializations_to_verify.slice(0,3).join(' · ')));
    }
    if((job.match_band==='Review first'||job.match_band==='Possible')&&job.triage_note){
      left.append(el('div','muted',job.triage_note));
    }
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
