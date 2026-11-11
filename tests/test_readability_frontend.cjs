'use strict';
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const source=fs.readFileSync(__dirname+'/../docs/app.js','utf8');
class Node {
  constructor(tag){this.tagName=tag;this.children=[];this.textContent='';this.value='all';this.checked=false;this.attrs={};}
  append(...items){this.children.push(...items)}
  replaceChildren(...items){this.children=[...items]}
  addEventListener(){}
}
const ids=['query','band','technicalBand','company','germanyOnly','degreeFocus','results','count','total','priority','sources','updated','health','status'];
const ui=Object.fromEntries(ids.map(id=>[id,new Node('div')]));ui.query.value='';ui.degreeFocus.checked=true;
const ctx={document:{getElementById(id){return ui[id]},createElement(tag){return new Node(tag)}},Intl,Date,console};
vm.createContext(ctx);vm.runInContext(source.replace(/\bmain\(\);\s*$/,''),ctx);
const j={company:'CMBlu Energy',title:'Developer — Battery Material Compounds',location:'Alzenau, Bavaria, Germany',country:'Germany',
 published_at:'2026-11-06T10:00:00Z',first_detected:'2026-11-10T10:00:00Z',at_startup:true,match_band:'Review first',description:'Formulation R&D',url:'https://example.org',hide_by_default:false,location_status:'germany',
 competency_counts:{technical:{matched:0,total:1,supported:[],verify:['Battery-cell electrochemistry']},method:{matched:2,total:3,supported:['DoE / experimental design','Laboratory synthesis scale-up'],verify:['Electrochemical testing']},general:{matched:1,total:1,supported:['Research project coordination'],verify:[]}},
 qualification_priority:{status:'parsed',explicit:[],preferred:[{name:'Battery-sector experience',documented:false}],learnable:[{name:'Electrochemical testing',documented:false}],listed:[{name:'DoE',documented:true}],experience_flags:[]},
 core_specializations_to_verify:['Battery electrochemistry and cells']};
vm.runInContext('data.jobs='+JSON.stringify([j])+';render()',ctx);
const card=ui.results.children[0],main=card.children[0];
const byTag=(n,t)=>[...(n.tagName===t?[n]:[]),...n.children.flatMap(x=>byTag(x,t))];
const flatten=n=>[n.textContent,...n.children.flatMap(flatten)].join(' ');
assert.match(flatten(card),/Alzenau, Bayern, Germany/);
const groups=byTag(main,'section');assert(groups.some(x=>flatten(x).includes('Documented experience')));
assert(groups.some(x=>flatten(x).includes('Needs verification')));
const evidenceLists=byTag(main,'ul');assert(evidenceLists.length>=3,'should contain bullet lists for evidence and qualification');
const details=byTag(main,'details');assert.equal(details.length,1,'one expandable qualification section');
const summary=byTag(details[0],'summary');assert.equal(summary.length,1);
assert.match(flatten(summary[0]),/▶/);
assert.match(flatten(summary[0]),/Qualification requirements/);
assert.match(flatten(summary[0]),/1 preferred/);
assert.match(flatten(details[0]),/Not in experience record/);
assert.match(flatten(details[0]),/Documented/);
assert.equal(byTag(main,'script').length,0,'do not inject scripts from source content');
assert.match(flatten(card),/Methods 2\/3/);
assert.match(flatten(card),/Technical 0\/1/);
console.log('PASS: structured bullets, disclosure arrow, grouped qualifications, scores, location');
