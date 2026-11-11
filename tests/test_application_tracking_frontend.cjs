'use strict';
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const source=fs.readFileSync(__dirname+'/../docs/app.js','utf8').replace(/\bmain\(\);\s*$/,'');
class Node{
 constructor(tag){this.tagName=tag;this.children=[];this.textContent='';this.value='all';this.checked=false;this.listeners={};this.disabled=false;this.type='';this.className='';}
 append(...c){this.children.push(...c)} replaceChildren(...c){this.children=[...c]}
 addEventListener(name,fn){this.listeners[name]=fn} click(){this.listeners.click?.()}
}
const ids=['query','band','technicalBand','company','germanyOnly','degreeFocus','results','count','total','priority','sources','updated','health','status','showApplied','exportApplied','importApplied','appliedStatus','pageSize','pageInfo','prevPage','nextPage'];
const ui=Object.fromEntries(ids.map(id=>[id,new Node('div')]));ui.query.value='';ui.pageSize.value='50';ui.degreeFocus.checked=true;
const storage=new Map();const localStorage={getItem:k=>storage.has(k)?storage.get(k):null,setItem:(k,v)=>storage.set(k,v)};
const ctx={document:{getElementById:id=>ui[id],createElement:tag=>new Node(tag)},Intl,Date,console,localStorage};
vm.createContext(ctx);vm.runInContext(source,ctx);
function make(i){return {key:'job'+i,company:'Lab '+i,title:'Materials Scientist '+i,description:'silica laboratory synthesis',location:'Munich',country:'Germany',match_band:'Possible',hide_by_default:false,location_status:'germany',url:'https://example.org/'+i,first_detected:'2026-11-10T10:00:00+00:00'};}
const all=Array.from({length:121},(_,i)=>make(i));
vm.runInContext('data.jobs='+JSON.stringify(all)+';render()',ctx);
assert.equal(ui.results.children.length,50);assert.match(ui.pageInfo.textContent,/Page 1 of 3/);
vm.runInContext('pageNumber=2;render()',ctx);assert.equal(ui.results.children.length,50);
vm.runInContext('pageNumber=3;render()',ctx);assert.equal(ui.results.children.length,21);
vm.runInContext('pageNumber=1;render()',ctx);
const first=ui.results.children[0]; const actions=first.children[1];assert.equal(actions.children.length,2);
actions.children[1].click();assert.equal(ui.results.children.length,50);assert(storage.size>0); // job hidden, next fills page
assert.match(ui.pageInfo.textContent,/120/);
ui.showApplied.checked=true;vm.runInContext('render()',ctx);assert.match(ui.pageInfo.textContent,/121/);
// A successful backend scan later explicitly marks the same posting as reopened.
const j=Object.assign({},all[0],{reopened_at:'2026-11-12T10:00:00+00:00'});
vm.runInContext('data.jobs[0]='+JSON.stringify(j)+';render()',ctx);
const flatten=n=>[n.textContent,...n.children.flatMap(flatten)].join(' ');
assert.match(flatten(ui.results),/Previously applied/);
ui.showApplied.checked=false;vm.runInContext('render()',ctx);
assert.match(flatten(ui.results),/Previously applied/);
console.log('PASS: 50-item pagination, applied tracking and reappearance');
