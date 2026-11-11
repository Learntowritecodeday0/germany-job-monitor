'use strict';
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const source=fs.readFileSync(__dirname+'/../docs/app.js','utf8');
class Node {constructor(tag){this.tagName=tag;this.children=[];this.textContent='';this.value='all';this.checked=false;}
append(...items){this.children.push(...items)}replaceChildren(...items){this.children=[...items]}addEventListener(){}}
const ids=['query','band','technicalBand','company','germanyOnly','degreeFocus','results','count','total','priority','sources','updated','health','status'];
const ui=Object.fromEntries(ids.map(id=>[id,new Node('div')]));ui.query.value='';
const ctx={document:{getElementById(id){return ui[id]},createElement(tag){return new Node(tag)}},Intl,Date,console};
vm.createContext(ctx);vm.runInContext(source.replace(/\bmain\(\);\s*$/,''),ctx);
function flatten(n){return [n.textContent,...n.children.flatMap(flatten)].join(' ')}
function byTag(n,t){return [...(n.tagName===t?[n]:[]),...n.children.flatMap(x=>byTag(x,t))]}
const j={company:'Example',title:'Materials scientist',location:'Munich, Germany',match_band:'Possible',at_startup:true,location_status:'germany',description:'test description',url:'https://example.com',
  competency_counts:{technical:{matched:0,total:1,supported:[],verify:['battery chemistry']},method:{matched:1,total:1,supported:['DoE'],verify:[]},general:{matched:0,total:0,supported:[],verify:[]}},
  qualification_priority:{status:'parsed',explicit:[],preferred:[],learnable:[],listed:[],experience_flags:[]},
  education_review:{status:'identified',minimum_level:'Bachelor',minimum_evidence:'Bachelor degree in materials science',preferred_level:'PhD / Promotion',preferred_evidence:'Promotion von Vorteil',alternative_routes:[],possible_overqualified:false}};
vm.runInContext('data.jobs='+JSON.stringify([j])+';render()',ctx);
const card=ui.results.children[0],details=byTag(card,'details')[0];
assert(details,'qualification section');
const body=byTag(details,'div').find(x=>x.className==='requirement-body');
assert(body,'requirement body');
const sections=body.children.filter(x=>x.tagName==='section');
assert(sections[0].className.includes('education-group'),'education first');
assert.match(flatten(sections[0]),/Bachelor/);assert.match(flatten(sections[0]),/PhD/);
// Overqualification only as a warning and never an automatic exclusion.
j.education_review={status:'identified',minimum_level:'Vocational training / Ausbildung',minimum_evidence:'Abgeschlossene Ausbildung als Chemielaborant',preferred_level:null,preferred_evidence:null,alternative_routes:[],possible_overqualified:true};
vm.runInContext('data.jobs='+JSON.stringify([j])+';render()',ctx);
assert.match(flatten(ui.results.children[0]),/Possible overqualified/);
// No degree requirement: omit education section altogether.
j.education_review={status:'not_specified'};
vm.runInContext('data.jobs='+JSON.stringify([j])+';render()',ctx);
assert(!flatten(ui.results.children[0]).includes('Education \/ Studium'),'missing education must not be inferred');
console.log('PASS: education first, optional preferred degree, possible overqualification and absent-degree handling');
