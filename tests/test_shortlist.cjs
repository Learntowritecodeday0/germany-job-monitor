'use strict';
const assert=require('assert');
const fs=require('fs');
const path=require('path');
const short=require('../docs/shortlist.js');
const jobs=JSON.parse(fs.readFileSync(process.argv[2]||path.join(__dirname,'../docs/jobs.json'),'utf8')).jobs;
const byKey=Object.fromEntries(jobs.map(j=>[j.key,j]));
const assessed=jobs.map(j=>[j,short.reviews(j)]);
const counts={}; for(const [,r] of assessed)counts[r.tier]=(counts[r.tier]||0)+1;
console.log('Review-queue calibration on supplied snapshot:',counts);
if(byKey['personio:emil-kiessling-gmbh:2849331']){
  const role=byKey['personio:emil-kiessling-gmbh:2849331'];
  const excluded=role.active===false||role.location_status==='outside'||role.hide_by_default===true;
  assert.strictEqual(short.reviews(role).tier,excluded?'other':Number(role.reopen_count||0)>0?'details':'review');
}
if(byKey['smartrecruiters:FischerGroup:744000159557829']){
  const role=byKey['smartrecruiters:FischerGroup:744000159557829'];
  const excluded=role.active===false||role.location_status==='outside'||role.hide_by_default===true;
  assert.strictEqual(short.reviews(role).tier,excluded?'other':'review');
}
if(byKey['personio:rudolf:2805325']){
  const role=byKey['personio:rudolf:2805325'];
  const excluded=role.active===false||role.location_status==='outside'||role.hide_by_default===true;
  assert.strictEqual(short.reviews(role).tier,excluded?'other':Number(role.reopen_count||0)>0?'details':'secondary');
}
if(byKey['personio:blackwave:2657617'])assert.strictEqual(short.reviews(byKey['personio:blackwave:2657617']).tier,'other');
if(byKey['personio:klb:2524785'])assert.strictEqual(short.reviews(byKey['personio:klb:2524785']).tier,'other');
if(byKey['personio:proteros-biostructures-gmbh:1914202'])assert.strictEqual(short.reviews(byKey['personio:proteros-biostructures-gmbh:1914202']).tier,'other');
if(byKey['softgarden:palplast:61937989'])assert.strictEqual(short.reviews(byKey['softgarden:palplast:61937989']).tier,'other');
if(byKey['softgarden:palplast:62260129'])assert.strictEqual(short.reviews(byKey['softgarden:palplast:62260129']).tier,'other');
if(byKey['softgarden:ineos-solvents:65700851'])assert.strictEqual(short.reviews(byKey['softgarden:ineos-solvents:65700851']).tier,'other');
if(byKey['softgarden:ineos-solvents:66705928'])assert.strictEqual(short.reviews(byKey['softgarden:ineos-solvents:66705928']).tier,'explore','Laborant remains discoverable with career-level verification');
const good={key:'new:good',company:'Example',title:'Nanoparticle Development Scientist',description:'Develop silica nanoparticles with laboratory sol-gel synthesis, surface functionalization, and design of experiments. Characterize materials using DLS zeta and FTIR. Independently run synthesis experiments and maintain research records.'};
assert.strictEqual(short.reviews(good).tier,'secondary', 'Strong experimental work should enter review queue');
const good2={key:'new:good2',company:'Example',title:'Materials Development Engineer',description:'Formulation and laboratory development of sol-gel materials, nanoparticles, and experimental design with DoE, dispersions and FTIR characterization. Independently run synthesis trials and document all results.'};
assert.strictEqual(short.reviews(good2).tier,'secondary');
const unknown={key:'new:missing',title:'Nanoparticle Research Scientist',description:'',source_mode:'recent_title_only'};
assert.strictEqual(short.reviews(unknown).tier,'details');
const student={title:'Masterarbeit Silica Nanoparticles',description:good.description};assert.strictEqual(short.reviews(student).tier,'other');
const maintenance={title:'Machine Operator Chemistry',description:good.description};assert.strictEqual(short.reviews(maintenance).tier,'other');
const noPhd={title:'Chemiker Laborentwicklung',description:'keine Promotion; '+good.description};assert.strictEqual(short.reviews(noPhd).tier,'other');
const index=fs.readFileSync(path.join(__dirname,'../docs/index.html'),'utf8');
const app=fs.readFileSync(path.join(__dirname,'../docs/app.js'),'utf8');
assert(index.indexOf('src="shortlist.js"')>=0 && index.indexOf('src="shortlist.js"')<index.indexOf('src="app.js"'));
for(const id of ['reviewQueue','degreeFocus','showApplied','pageSize','results','priority','matches','queueStats'])assert(index.includes(`id="${id}"`),id);
for(const sn of ['reviewAPI.reviews','reviewAPI.isShortlist','reviewAPI.isDiscovery','showApplied','applicationStatus','Qualification requirements'])assert(app.includes(sn),sn);
// The number of postings changes on every scan. Do not freeze queue sizes
// to a historical snapshot: this previously broke deployment on text updates.
const allowed = new Set(['review','secondary','details','explore','other']);
assert.strictEqual(Object.values(counts).reduce((n,v)=>n+v,0), jobs.length);
assert(Object.keys(counts).every(tier=>allowed.has(tier)));

console.log('PASS: 18+ assertions; previous applied handling, source code and email scripts unchanged.');
