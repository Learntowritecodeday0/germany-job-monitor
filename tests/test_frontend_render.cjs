'use strict';
const fs=require('fs'),vm=require('vm'),assert=require('assert');
const source=fs.readFileSync(__dirname+'/../docs/app.js','utf8');
const shortlist=require('../docs/shortlist.js');
const snapshot=JSON.parse(fs.readFileSync(process.argv[2]||require('path').join(__dirname,'../docs/jobs.json'),'utf8'));
const keys=['smartrecruiters:FischerGroup:744000159557829','personio:emil-kiessling-gmbh:2849331','personio:rudolf:2805325',
  'ashby:blacksemiconductor:https://jobs.ashbyhq.com/blacksemiconductor/2a8897e7-bbb2-408f-ad16-136d2523017a','softgarden:palplast:62260129'];
class Node {
  constructor(tag='div'){this.tagName=tag;this.children=[];this.textContent='';this.value='all';this.checked=false;this.disabled=false;this.style={};this.attrs={};}
  append(...items){this.children.push(...items)} replaceChildren(...items){this.children=[...items]} addEventListener(){} scrollIntoView(){}
}
const ids=['query','band','reviewQueue','technicalBand','company','germanyOnly','degreeFocus','results','count','total','priority','sources','updated','health','status','showApplied','exportApplied','importApplied','appliedStatus','pageSize','pageInfo','prevPage','nextPage'];
const ui=Object.fromEntries(ids.map(id=>[id,new Node()]));
ui.query.value='';ui.reviewQueue.value='shortlist';ui.degreeFocus.checked=true;ui.pageSize.value='50';
const ctx={document:{getElementById(id){return ui[id]},createElement(tag){return new Node(tag)}},window:{JobShortlist:shortlist},Intl,Date,console};
vm.createContext(ctx);
vm.runInContext(source.replace(/\bmain\(\);\s*$/,''),ctx);
const fixtures=keys.map(k=>snapshot.jobs.find(j=>j.key===k));
assert(fixtures.every(Boolean),'Fixture keys must exist in the uploaded snapshot');
vm.runInContext('data.jobs='+JSON.stringify(fixtures)+';render()',ctx);
const flatten=n=>[n.textContent,...n.children.flatMap(flatten)].join(' ');
assert.strictEqual(ui.results.children.length,3,'Two audited priority roles and RUDOLF, not SEM or warehouse role');
assert.match(flatten(ui.results),/fischer Group/);
assert.doesNotMatch(flatten(ui.results),/SEM Technician/);
assert.match(flatten(ui.results),/Review note/);
assert.match(ui.count.textContent,/in priority shortlist/);
ui.reviewQueue.value='other';
vm.runInContext('render()',ctx);
assert.strictEqual(ui.results.children.length,2,'Other queue contains the legacy misclassified SEM and warehouse roles');
ui.degreeFocus.checked=false;
vm.runInContext('render()',ctx);
assert.strictEqual(ui.results.children.length,2,'Other queue remains accessible with preference filter disabled');
ui.reviewQueue.value='all';
vm.runInContext('render()',ctx);
assert.strictEqual(ui.results.children.length,5,'All queue shows every fixture when preferences disabled');
console.log('PASS: shortlist rendering, qualification panels preserved, legacy preferences, all-jobs override');
