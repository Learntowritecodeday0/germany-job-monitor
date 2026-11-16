'use strict';
/* Broad discovery deliberately preserves uncertainty, not a hiring fit score. */
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const api=require('../docs/shortlist.js');

const scienceText='Your Tasks: Design and document materials experiments in the laboratory, '+
  'compare measured particle properties and validate experimental protocols with microscopy. '+
  'Your Profile: Degree in materials science or chemistry, strong documentation skills.';
function job(extra={}) {
  return {key:'test:unknown',company:'Example',title:'Materials Scientist',
    description:scienceText,active:true,hide_by_default:false,
    location_status:'germany',career_track:'professional_or_unknown',
    core_documented_tasks:[],core_task_specializations_to_verify:[],
    core_review_basis:'Tasks and listed qualifications; rule-based manual screening',
    qualification_priority:{status:'parsed',explicit:[],preferred:[],learnable:[],
      listed:[],experience_flags:[]},...extra};
}
const review=extra=>api.reviews(job(extra));
assert.equal(review({}).tier,'explore','A materials title with unrecognized specific tasks should remain discoverable');
assert.equal(review({core_documented_tasks:['Materials and particle characterization']}).tier,'secondary');
assert.equal(review({title:'Senior Chemist Adhesives'}).tier,'explore','senior role visible but not in direct shortlist');
assert.equal(review({title:'Lab Technician - Mechatronics and Prototyping'}).tier,'other','unrelated mechatronics excluded');
assert.equal(review({title:'Requirements Engineer Analytics'}).tier,'other','analytics IT requirements are not chemical analysis');
assert.equal(review({title:'Team Lead/Director Chemistry, Manufacturing and Controls'}).tier,'other','non-laboratory executive role excluded');
assert.equal(review({title:'Manager Product Development Power Module Materials'}).tier,'other','management title alone not sufficient');
assert.equal(review({title:'Ausbildung zum Chemielaboranten',career_track:'training',hide_by_default:true}).tier,'other');
assert.equal(review({title:'Chemielaborant/CTA für analytische Methodenentwicklung',
 career_track:'vocational',hide_by_default:true}).tier,'explore','technical lab position visible for qualification review');
assert.equal(review({title:'Chemielaborant/CTA für analytische Methodenentwicklung',
 career_track:'vocational',hide_by_default:true,active:false}).tier,'other');
assert.equal(review({title:'Senior Chemist Adhesives',location_status:'outside'}).tier,'other');
assert.equal(review({title:'Backend Software Engineer for Materials'}).tier,'other');
assert.equal(review({title:'Materials Scientist',description:'Your Tasks: Coordinate factory equipment maintenance and production shifts in manufacturing operations, oversee daily equipment uptime, organize repair work and manage the maintenance schedule. Your Profile: Management experience and industrial maintenance supervision required.'}).tier,'other');
assert.equal(review({title:'Materials Scientist',description:'keine Promotion; '+scienceText}).tier,'other');
const sem=job({key:'ashby:blacksemiconductor:https://jobs.ashbyhq.com/blacksemiconductor/2a8897e7-bbb2-408f-ad16-136d2523017a',
 title:'SEM Technician (f/m/d)'});
assert.equal(api.reviews(sem).tier,'details','SEM characterization requires check of independent tool work');
assert.equal(api.isDiscovery(api.reviews(sem)),true);
assert.equal(api.isShortlist(api.reviews(sem)),false);
assert.equal(api.isDiscovery(review({})),true);
assert.equal(api.isShortlist(review({})),false);
const index=fs.readFileSync(path.join(__dirname,'../docs/index.html'),'utf8');
const app=fs.readFileSync(path.join(__dirname,'../docs/app.js'),'utf8');
assert(index.includes('<option value="matches" selected>'),'Broad matches should be default');
assert(index.includes('value="shortlist"'),'Strict shortlist remains available');
assert(index.includes('value="explore"'),'Related roles available separately');
assert(index.includes('id="matches"'),'Broad candidate count shown');
assert(app.includes('visibleUnderPreference'),'Lab technicians can be explored under relevant categories');
assert(app.includes('reviewAPI.isDiscovery'),'The combined queue must use discovery selection');
const raw=JSON.parse(fs.readFileSync(path.join(__dirname,'../docs/jobs.json'),'utf8')).jobs;
const candidates=raw.map(j=>api.reviews(j));
const count=candidates.filter(r=>api.isDiscovery(r)).length;
const strict=candidates.filter(r=>api.isShortlist(r)).length;
assert(count>=strict,'discovery cannot be narrower than direct shortlist');
if(raw.length>500)assert(count>strict,'in a broad snapshot, discovery must reveal more than strict roles');

// Regression cases: laboratory titles and duties missing from earlier discovery.
const wetLab = 'Your tasks: Perform wet chemistry analysis and independent laboratory testing, '+
  'prepare buffer solutions and document analytical measurements. Your profile: Chemistry training.';
assert.equal(review({title:'Mitarbeiter (m/w/d) Analytik',description:wetLab}).tier,'explore',
  'Analytical laboratory staff must be discoverable without a Chemist title');
assert.equal(review({title:'Chemisch Technischer Assistent (m/w/d) in Teilzeit',
  description:'Laboranalytik und Qualitätskontrolle von Proben in einem R&D-Labor.'}).tier,'explore',
  'Chemically trained assistants belong in laboratory career-level review');
assert.equal(review({title:'Lab Assistant Packaging Testing (m/w/d)',
  description:'Laboratory testing and analytical sample preparation under a quality system.'}).tier,'explore',
  'Testing-focused laboratory assistants should not disappear from discovery');
assert.equal(review({title:'R&D & Scale-up Food Scientist [m/f/d]',description:''}).tier,'explore',
  'Relevant food formulation and scale-up scientist titles should be visible with missing details');
assert.equal(review({title:'Process Development Engineer',description:
  'Your tasks: Perform laboratory tests and method development for chemical formulations and particle properties. '+
  'Your profile: Engineering degree and industrial experience.',core_documented_tasks:[]}).tier,'explore',
  'Scientific duties may warrant review even when task parser misses unfamiliar descriptions');
assert.equal(review({title:'Mitarbeiter (m/w/d) im Einkauf',description:wetLab}).tier,'other',
  'Purchasing staff must not be promoted by laboratory words in the advert');
assert.equal(review({title:'Technische Assistenz Geschäftsführung',description:wetLab}).tier,'other',
  'Administrative assistants remain outside the scientific search');
assert.equal(review({title:'Research Associate',description:'We offer a chemistry laboratory and technical training.',core_documented_tasks:[]}).tier,'other',
  'Chemistry mentioned only as workplace context is not enough without hands-on duties');
assert.equal(review({title:'R&D & Scale-up Food Scientist [m/f/d]',career_track:'training',description:''}).tier,'other',
  'Training roles remain excluded even when scientific title vocabulary overlaps');

const actualHeraeus=raw.find(j=>j.company.startsWith('Heraeus')&&j.title==='Mitarbeiter (m/w/d) Analytik');
if(actualHeraeus)assert.equal(api.reviews(actualHeraeus).tier,'explore',
  'Verified analytical work at Heraeus must not be invisible');
const actualDye=raw.find(j=>j.company==='DyeMansion'&&j.title.startsWith('Chemisch Technischer Assistent'));
if(actualDye)assert.equal(api.reviews(actualDye).tier,'explore',
  'Verified technical assistant role at DyeMansion must not be invisible');

console.log('PASS: broad discovery vs strict shortlist, exclusions, vocational jobs, historical SEM audit, UI');
