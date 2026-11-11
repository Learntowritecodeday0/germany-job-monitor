'use strict';
const fs = require('node:fs'), vm = require('node:vm'), assert = require('node:assert/strict');
const app = fs.readFileSync(__dirname + '/../docs/app.js', 'utf8');
class N {
  constructor(tag){this.tagName=tag;this.children=[];this.textContent='';this.value='all';this.checked=false;this.attrs={};}
  append(...children){this.children.push(...children)}
  replaceChildren(...children){this.children=[...children]}
  addEventListener(){}
}
const ids=['query','band','technicalBand','company','germanyOnly','degreeFocus','results','count','total','priority','sources','updated','health','status'];
const controls=Object.fromEntries(ids.map(id=>[id,new N('div')]));
controls.query.value='';controls.degreeFocus.checked=true;
const context={document:{getElementById(id){return controls[id]},createElement(tag){return new N(tag)}}, console,Intl,Date};
vm.createContext(context);
vm.runInContext(app.replace(/\bmain\(\);\s*$/,''), context);
const record={company:'Black Semiconductor',title:'SEM Technician',location:'Aachen, Germany',country:'Germany',
  published_at:'2026-11-03T10:00:00Z',first_detected:'2026-11-10T10:00:00Z',at_startup:true,
  match_band:'Review first',description:'SEM and EDX',url:'https://example.com',hide_by_default:false,location_status:'germany',
  competency_counts:{technical:{matched:0,total:0,supported:[],verify:[]},method:{matched:2,total:3,supported:['SEM microscopy','EDS / EDX elemental analysis'],verify:['Focused ion beam (FIB)']},general:{matched:0,total:0,supported:[],verify:[]}},
  qualification_priority:{status:'parsed',explicit:[],preferred:[{name:'Focused ion beam (FIB)',documented:false}],
    learnable:[],listed:[{name:'SEM microscopy',documented:true}],experience_flags:[]},
  worksite_city:'Aachen',worksite_state:'Nordrhein-Westfalen',worksite_country:'Germany'};
vm.runInContext('data.jobs='+JSON.stringify([record])+'; render()',context);
const flatten=n=>[n.textContent,...n.children.flatMap(flatten)].join(' ');
const s=flatten(controls.results);
assert.match(s,/Requirement wording: 0 explicit · 1 preferred · 0 learnable · 1 unspecified/);
assert.match(s,/Focused ion beam \(FIB\)/);
assert.match(s,/Aachen, Nordrhein-Westfalen, Germany/);
const first=controls.results.children[0];
const details=first.children[0].children.filter(n=>n.tagName==='details');
assert.equal(details.length,1,'Qualification detail should be collapsible rather than expanding all cards');
console.log('Passed qualification priority frontend display checks');
