'use strict';
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const directory=require('../docs/companies.js');
const atlas=require('../docs/companies.json');
const root=path.join(__dirname,'..');

assert.equal(atlas.version,1);
assert.equal(atlas.companies.length,34,'The industry atlas should provide all 34 researched profiles');
assert.equal(new Set(atlas.companies.map(p=>p.id)).size,34,'Stable company IDs must be unique');
for(const profile of atlas.companies){
  for(const field of ['id','name','city','region','segment','focus','research_overlap','screening_gap','technical_overlap','source'])
    assert.equal(typeof profile[field],'string',profile.id+' missing '+field);
  assert(profile.aliases.length>=1,profile.id+' missing monitored-name aliases');
  assert(profile.roles.length>=1,profile.id+' missing job search families');
  assert(directory.safeUrl(profile.source).startsWith('https://'),profile.id+' needs an official HTTPS research source');
  if(profile.careers_url)assert(directory.safeUrl(profile.careers_url).startsWith('https://'));
  assert(['High','Medium–High','Medium'].includes(profile.technical_overlap));
}
const byId=id=>atlas.companies.find(p=>p.id===id);
assert(directory.matchesName('Evonik Industries GmbH',byId('evonik')));
assert(directory.matchesName('MÜNZING CHEMIE GmbH',byId('muenzing')));
assert(directory.matchesName('Chemiewerk Bad Köstritz GmbH',byId('cwk')));
assert(directory.matchesName('Fraunhofer ISC',byId('fraunhofer-isc')));
assert(!directory.matchesName('WACKER Neuson',byId('wacker')),'Avoid confusing Wacker Chemie with Wacker Neuson');
assert(!directory.matchesName('Fraunhofer IWS',byId('fraunhofer-isc')),'Do not link unrelated Fraunhofer institutes');
assert(!directory.matchesName('Heraeus Precious Metals',byId('heraeus')),'Business units must remain distinct');
const jobs=[
  {company:'Evonik Industries',title:'Development Chemist',url:'https://example.org/one'},
  {company:'WACKER Neuson',title:'Equipment Engineer',url:'https://example.org/two'},
  {company:'Evonik',title:'Lab Technician',url:'https://example.org/three'}
];
assert.equal(directory.linkedJobs(byId('evonik'),jobs).length,2);
assert.equal(directory.linkedJobs(byId('wacker'),jobs).length,0);
assert.equal(directory.coverage(byId('evonik'),[{name:'Evonik Industries',status:'ok'}]).status,'ok');
assert.equal(directory.coverage(byId('cwk'),[{name:'Evonik Industries',status:'ok'}]),null);
assert.equal(directory.safeUrl('javascript:alert(1)'),'');
const html=fs.readFileSync(root+'/docs/index.html','utf8');
const app=fs.readFileSync(root+'/docs/applications.js','utf8');
const jobsJs=fs.readFileSync(root+'/docs/app.js','utf8');
assert.match(html,/id="tabCompanies"/);
assert.match(html,/id="companiesView"/);
assert.match(html,/src="companies.js"/);
assert.match(html,/href="companies.css"/);
assert.match(html,/id="companySearch"/);
assert.match(app,/companiesView/);
assert.match(jobsJs,/CompanyDirectory.openByCompany/);
assert.match(app,/germany-job-monitor:applications:v1/,'Original application store must be retained');
assert.match(fs.readFileSync(root+'/docs/companies.js','utf8'),/germany-job-monitor:company-research:v1/);
console.log('PASS: 34 researched employers, safe exact matching, data integrity, independent company tab');
