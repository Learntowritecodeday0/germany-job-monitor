'use strict';
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const app=fs.readFileSync(__dirname+'/../docs/app.js','utf8');
class N {
 constructor(tag){this.tagName=tag;this.children=[];this.textContent='';this.value='all';this.checked=false;this.attrs={};}
 append(...children){this.children.push(...children)}
 replaceChildren(...children){this.children=[...children]}
 addEventListener(){}
}
const ids=['query','band','technicalBand','company','germanyOnly','degreeFocus','results','count','total','priority','sources','updated','health','status'];
const controls=Object.fromEntries(ids.map(id=>[id,new N('div')]));
controls.query.value='';controls.germanyOnly.checked=false;controls.degreeFocus.checked=true;
const context={document:{getElementById(id){return controls[id]},createElement(tag){return new N(tag)}},console,Intl,Date};
vm.createContext(context);
vm.runInContext(app.replace(/\bmain\(\);\s*$/,''),context);
const example={key:'x',company:'CMBlu Energy',title:'Battery Material Compounds',location:'Alzenau, Bavaria, Germany',country:'Germany',
 published_at:'2026-11-06T10:00:00Z',first_detected:'2026-11-10T12:00:00Z',at_startup:true,match_band:'Review first',
 description:'battery DoE',url:'https://example.com',hide_by_default:false,location_status:'germany',
 competency_counts:{technical:{matched:0,total:1,supported:[],verify:['Battery-cell electrochemistry']},
 method:{matched:2,total:3,supported:['DoE','Scale-up'],verify:['Electrochemical testing']},
 general:{matched:1,total:2,supported:['Teamwork'],verify:['Formal certification']}},
 worksite_city:'Alzenau',worksite_state:'Bayern',worksite_country:'Germany'};
vm.runInContext('data.jobs='+JSON.stringify([example])+'; render()',context);
const flatten=(n)=>[n.textContent,...n.children.flatMap(flatten)].join(' ');
let html=flatten(controls.results);
assert.match(html,/Alzenau, Bayern, Germany/);
assert.doesNotMatch(html,/City:|State:|Country:/);
assert.match(html,/Technical 0\/1/);
assert.match(html,/Methods 2\/3/);
assert.match(html,/General 1\/2/);
assert.match(html,/Technical to verify: Battery-cell electrochemistry/);
const hidden={...example,key:'y',title:'Senior Python SDK Engineer',hide_by_default:true};
vm.runInContext('data.jobs='+JSON.stringify([example,hidden])+'; render()',context);
assert.equal(controls.results.children.length,1);
controls.technicalBand.value='none';vm.runInContext('render()',context);assert.equal(controls.results.children.length,1);
controls.technicalBand.value='some';vm.runInContext('render()',context);assert.equal(controls.results.children.filter(n=>n.tagName==='article').length,0);
controls.technicalBand.value='all';
const noDetected={...example, key:'z', competency_counts:{...example.competency_counts,technical:{matched:0,total:0,supported:[],verify:[]}}};
vm.runInContext('data.jobs='+JSON.stringify([noDetected])+'; render()',context);
html=flatten(controls.results);
assert.match(html,/Technical —/);
assert.doesNotMatch(html,/Technical 0\/0/);
console.log('Passed frontend card/filter checks including undefined 0/0 display');
