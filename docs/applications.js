'use strict';
/* Personal application tracker for the public, static GitHub Pages dashboard.
   Never commit application records to docs/: localStorage remains the sole store. */
(() => {
  const KEY='germany-job-monitor:applications:v1';
  const STATUSES=['Applied','No response','Next step','Interview','Offer','Rejected','Withdrawn'];
  const $=id=>document.getElementById(id);
  const fields={company:'applicationCompany',title:'applicationTitle',location:'applicationLocation',url:'applicationUrl',
    posted_at:'applicationPosted',applied_at:'applicationApplied',response_at:'applicationResponse',
    status:'applicationOutcome',next_step:'applicationNextStep',follow_up_at:'applicationFollowUp',notes:'applicationNotes'};
  let editing=null;
  const text=(tag,content,className)=>{const n=document.createElement(tag);n.textContent=content??'';if(className)n.className=className;return n};
  function localToday(){const d=new Date();return [d.getFullYear(),String(d.getMonth()+1).padStart(2,'0'),String(d.getDate()).padStart(2,'0')].join('-')}
  function day(s){if(!s)return '';const m=String(s).match(/^(\d{4}-\d{2}-\d{2})/);return m?m[1]:''}
  function read(){try{const v=JSON.parse(localStorage.getItem(KEY)||'{}');return v?.version===1&&v.records&&!Array.isArray(v.records)&&typeof v.records==='object'?v.records:{}}catch(e){return {}}}
  function persist(records){try{localStorage.setItem(KEY,JSON.stringify({version:1,records}));return true}catch(e){$('appliedStatus').textContent='Saving failed: browser storage is unavailable or full. Export a backup.';return false}}
  function notify(){if(typeof window.JobApplicationsChanged==='function')window.JobApplicationsChanged()}
  function entries(){return Object.entries(read()).filter(([key,r])=>key&&r&&typeof r==='object'&&r.company&&r.title)}
  function safeLink(value){try{const u=new URL(String(value));return ['http:','https:'].includes(u.protocol)?u.href:''}catch(e){return ''}}
  function formatDate(v){const d=day(v);return d?d.split('-').reverse().join('.'):'—'}
  function setVisible(panel){$('vacanciesView').hidden=panel!=='vacancies';$('applicationsView').hidden=panel!=='applications';for(const [name,id] of [['vacancies','tabVacancies'],['applications','tabApplications']]){const selected=panel===name;$(id).classList.toggle('active',selected);$(id).setAttribute('aria-selected',String(selected))}}
  function hideEditor(){$('applicationEditor').hidden=true;editing=null;$('applicationForm').reset();$('applicationFormStatus').textContent=''}
  function openEditor(key){
    editing=key||null;$('applicationForm').reset();$('applicationFormStatus').textContent='';
    const old=editing?read()[editing]:null;
    $('applicationEditorTitle').textContent=old?'Edit application':'Add application';
    if(old){for(const [field,id] of Object.entries(fields))$(id).value=field.endsWith('_at')?day(old[field]):String(old[field]??'')}
    else{$('applicationApplied').value=localToday();$('applicationOutcome').value='Applied'}
    $('applicationEditor').hidden=false;setVisible('applications');$('applicationCompany').focus();
  }
  function collect(){
    const o={};for(const [key,id] of Object.entries(fields))o[key]=$(id).value.trim();
    if(!o.company||!o.title)throw new Error('Company and job title are required.');
    if(o.url&&!safeLink(o.url))throw new Error('Job URL must start with https:// or http://.');
    if(!STATUSES.includes(o.status))throw new Error('Invalid outcome.');
    for(const k of ['posted_at','applied_at','response_at','follow_up_at'])if(o[k]&&!/^\d{4}-\d{2}-\d{2}$/.test(o[k]))throw new Error('Invalid date: '+k);
    return o;
  }
  function save(e){
    e.preventDefault();
    try{
      const next=collect(),records=read();
      let key=editing;
      if(!key){key='manual:'+Date.now()+':'+Math.random().toString(36).slice(2,10)}
      const old=records[key]||{};
      records[key]={...old,...next,key,fingerprint:[next.company,next.title].map(s=>s.toLocaleLowerCase().replace(/[^\p{L}\p{N}]+/gu,' ').trim()).join('|')};
      if(!persist(records))return;
      hideEditor();refresh();notify();
    }catch(err){$('applicationFormStatus').textContent=err.message}
  }
  function remove(key){const all=read(),r=all[key];if(!r)return;
    if(!window.confirm('Delete application record for '+r.company+' — '+r.title+'?'))return;
    delete all[key];if(persist(all)){refresh();notify()}
  }
  function td(value){return text('td',value)}
  function refresh(){
    const all=entries(),records=all.map(([key,r])=>({key,...r}));
    $('appTabCount').textContent=records.length?'('+records.length+')':'';
    $('applicationTotal').textContent=records.length;
    $('applicationPending').textContent=records.filter(r=>['Applied','No response'].includes(r.status||'Applied')).length;
    $('applicationProgress').textContent=records.filter(r=>['Next step','Interview','Offer'].includes(r.status)).length;
    $('applicationRejected').textContent=records.filter(r=>r.status==='Rejected').length;
    const q=$('applicationSearch').value.trim().toLocaleLowerCase(),filter=$('applicationFilter').value,sort=$('applicationSort').value;
    const visible=records.filter(r=>(filter==='all'||(r.status||'Applied')===filter)&&(!q||[r.company,r.title,r.location,r.next_step,r.notes].join(' ').toLocaleLowerCase().includes(q)));
    visible.sort((a,b)=>sort==='company'?String(a.company).localeCompare(String(b.company)):sort==='oldest'?day(a.applied_at).localeCompare(day(b.applied_at)):day(b.applied_at).localeCompare(day(a.applied_at)));
    $('applicationRows').replaceChildren();
    $('applicationEmpty').hidden=visible.length>0;
    $('applicationEmpty').textContent=records.length?'No applications match these filters.':'No applications recorded yet. Use “Add application” or mark a vacancy as applied.';
    for(const r of visible){
      const tr=document.createElement('tr');
      const identity=document.createElement('td');identity.append(text('strong',r.company),text('div',r.title,'table-role'));
      const url=safeLink(r.url);if(url){const link=text('a','Job advertisement');link.href=url;link.target='_blank';link.rel='noopener noreferrer';identity.append(link)}
      tr.append(identity,td(r.location||'—'),td(formatDate(r.posted_at)),td(formatDate(r.applied_at)),td(formatDate(r.response_at)));
      tr.append(td(r.status||'Applied'));
      const next=document.createElement('td');next.append(text('span',r.next_step||'—'));
      if(r.follow_up_at)next.append(text('div','Follow-up: '+formatDate(r.follow_up_at),'table-role'));
      if(r.notes){const details=document.createElement('details');const sum=text('summary','Notes');details.append(sum,text('p',r.notes));next.append(details)}
      tr.append(next);
      const actions=document.createElement('td');const edit=text('button','Edit');edit.type='button';edit.addEventListener('click',()=>openEditor(r.key));
      const del=text('button','Delete','danger-button');del.type='button';del.addEventListener('click',()=>remove(r.key));actions.append(edit,del);tr.append(actions);
      $('applicationRows').append(tr);
    }
  }
  $('tabVacancies').addEventListener('click',()=>setVisible('vacancies'));
  $('tabApplications').addEventListener('click',()=>{refresh();setVisible('applications')});
  $('newApplication').addEventListener('click',()=>openEditor(null));
  $('cancelApplication').addEventListener('click',hideEditor);
  $('closeApplication').addEventListener('click',hideEditor);
  $('applicationForm').addEventListener('submit',save);
  for(const id of ['applicationSearch','applicationFilter','applicationSort'])$(id).addEventListener('input',refresh);
  window.addEventListener('storage',e=>{if(e.key===KEY){refresh();notify()}});
  window.JobApplications={refresh,openEditor};
  refresh();
})();