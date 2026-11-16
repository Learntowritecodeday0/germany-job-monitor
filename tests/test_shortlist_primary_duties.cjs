'use strict';
/* Regression checks for primary-duty / transferability screening.
 * These fixtures are illustrative job descriptions, not a claim about a
 * real employer or an automatic assessment of eligibility.
 */
const assert = require('node:assert/strict');
const shortlist = require('../docs/shortlist.js');

const parsed = {
  status: 'parsed', explicit: [], preferred: [], learnable: [],
  listed: [], experience_flags: []
};
const baseDesc = 'Your tasks: Develop experimental nanoparticle formulations, characterize particle size using DLS and optimize the synthesis in the laboratory using DoE. Your profile: Degree in chemistry and relevant research experience. Benefits and professional training opportunities.';
function job(extra = {}) {
  return {
    key:'synthetic:role', company:'Example',
    title:'Materials Development Scientist',
    description:baseDesc,
    active:true, hide_by_default:false, location_status:'germany',
    core_review:'Several core methods overlap',
    core_review_basis:'Tasks and listed qualifications; rule-based manual screening',
    core_documented_tasks:['Formulation and dispersion experiments','Materials and particle characterization'],
    core_task_specializations_to_verify:[],
    core_specializations_to_verify:[],
    competency_counts:{
      technical:{matched:1,total:1}, method:{matched:2,total:2},
      general:{matched:1,total:1}
    },
    qualification_priority:structuredClone(parsed),
    ...extra
  };
}
const check = (expected, fields, why) =>
  assert.equal(shortlist.reviews(job(fields)).tier, expected, why);

// Central hands-on chemistry remains on the secondary list, not inflated to
// a hiring recommendation or a numerical match score.
check('secondary', {}, 'Direct formulation and characterization duties should be visible');

// Keywords in a profile are not equivalent to primary responsibilities.
check('explore', {
  core_documented_tasks:[],
  core_review:'Core technical fit unclear',
}, 'A materials-science title without detected core duties belongs in discovery, not the direct shortlist');

// A generic optimization tool does not compensate for a new industry process.
check('details', {
  core_documented_tasks:['Design of experiments and experimental optimization'],
  core_task_specializations_to_verify:['Semiconductor fabrication'],
  core_specializations_to_verify:['Semiconductor fabrication'],
}, 'Wafer processing as core work requires a sector assessment');
check('details', {
  core_documented_tasks:['Formulation and dispersion experiments'],
  core_task_specializations_to_verify:['Battery electrochemistry and cells'],
  core_specializations_to_verify:['Battery electrochemistry and cells']
}, 'Mixed battery-cell core duties deserve a separate verification');

check('details', {
  core_documented_tasks:['Formulation and dispersion experiments','Materials and particle characterization'],
  core_task_specializations_to_verify:['Semiconductor fabrication'],
  core_specializations_to_verify:['Semiconductor fabrication']
}, 'Several transferable laboratory methods still do not establish wafer-fabrication readiness');

// Preferred battery specialization should not be misread as mandatory.
check('secondary', {
  core_specializations_to_verify:['Battery electrochemistry and cells'],
  qualification_priority:{
    ...structuredClone(parsed),
    preferred:[{name:'Battery-cell electrochemistry',category:'Technical',documented:false}]
  }
}, 'Preferred skills alone must not trigger the essential-requirement gate');

check('details', {
  title:'Prozessingenieur Fließverhalten (w/m/d)',
  description:'Your Tasks: Carry out adhesive flow measurement experiments, validate new measurement methods and simulate adhesive rheology. Your Skills: CFD or materials engineering experience, very good German and English.',
  core_documented_tasks:[],
  core_adjacent_experimental_tasks:['Adhesive application and flow testing'],
  core_task_specializations_to_verify:['Mechanical design and CAD'],
}, 'Adjacent experimental adhesive rheology must enter requirements review, not a direct shortlist');
check('details', {
  title:'Ingenieur Anwendungsentwicklung Optical Packaging (w/m/d)',
  description:'Your Tasks: Plan Testreihen zur Bewertung der Klebstoffeignung, beraten Kunden und optimieren die Klebstoffanwendung mit dem Labor. Your Skills: Optik oder Werkstoffwissenschaften, deutsche Sprachkenntnisse.',
  core_documented_tasks:[],
  core_adjacent_experimental_tasks:['Adhesive application and flow testing'],
}, 'Experimental adhesive application testing needs a specialist review');
check('other', {
  title:'Financial Controller',
  core_documented_tasks:[],
  core_adjacent_experimental_tasks:['Adhesive application and flow testing']
}, 'Adjacent activity evidence does not promote unrelated job families');
check('other', {
  title:'Prozessingenieur Fließverhalten (w/m/d)',
  core_documented_tasks:[],
  core_adjacent_experimental_tasks:[]
}, 'Subject words in an advert are insufficient without actual daily experimental work');

// Known hard requirements, including sector-specific standards and language,
// should be reviewed, but not interpreted as proven ineligibility.
for(const name of ['Battery-cell electrochemistry','Industrial semiconductor fabrication']){
  check('details', {
    qualification_priority:{
      ...structuredClone(parsed),
      explicit:[{name,category:'Technical',documented:false}]
    }
  }, 'Explicit mandatory domain requirement needs review: '+name);
}
for(const name of ['Fluent professional German','Formal ISO / GMP / medical-device validation']){
  check('details', {
    qualification_priority:{
      ...structuredClone(parsed),
      explicit:[{name,category:'General',documented:false}]
    }
  }, 'Explicit screening or regulated qualification needs review: '+name);
}

check('details', {
  qualification_priority:{
    ...structuredClone(parsed),
    experience_flags:[{kind:'explicit minimum',text:'5+ years of hands-on industrial materials development experience required'}]
  }
}, 'Five-plus years of explicitly required industrial experience deserves review');
check('secondary', {
  qualification_priority:{
    ...structuredClone(parsed),
    experience_flags:[{kind:'explicit minimum',text:'2+ years of laboratory development experience required'}]
  }
}, 'A smaller explicit threshold is not automatically a five-year hard-gap gate');

// Documentation cannot assert requirements when job details are unavailable.
check('details', {
  qualification_priority:{...structuredClone(parsed),status:'unavailable'}
}, 'Missing identifiable qualifications should not receive automatic priority');
check('details', {
  description:'',source_mode:'recent_title_only',
  core_review:'Insufficient role details',core_documented_tasks:[]
}, 'Title-only scientific roles belong in the details queue');

check('other', {description:'Your tasks: Coordinate factory equipment maintenance, plan production shifts and supervise machine operators on the shop floor. Your profile: Experience with manufacturing operations and mechanical maintenance is required.',core_documented_tasks:[]},
  'Production-operation focus should not be promoted');
check('other', {title:'Masterarbeit – Silica Nanoparticles'}, 'Training position stays outside the search');
check('other', {title:'Senior Mechanical Design Engineer'}, 'Unrelated senior mechanical role stays outside search');

// Manual audits must not override later basic disqualifying status information.
const reviewed = 'smartrecruiters:FischerGroup:744000159557829';
const audited = job({key:reviewed,title:'Chemiker (m/w/d) Produktentwicklung'});
assert.equal(shortlist.reviews(audited).tier,'review');
assert.equal(shortlist.reviews({...audited,active:false}).tier,'other');
assert.equal(shortlist.reviews({...audited,location_status:'outside'}).tier,'other');
assert.equal(shortlist.reviews({...audited,hide_by_default:true}).tier,'other');
assert.equal(shortlist.reviews({...audited,reopen_count:1}).tier,'details');

// Legacy records without the newer core structure still have a conservative path.
const legacy = {
  key:'legacy',title:'Nanoparticle Development Scientist',
  description:'Develop silica nanoparticles with laboratory sol-gel synthesis, surface functionalization, and design of experiments. Characterize materials using DLS zeta and FTIR. Independently run synthesis experiments and maintain research records.'
};
assert.equal(shortlist.reviews(legacy).tier,'secondary');
assert.ok(shortlist.requirementChecks(job({
  core_task_specializations_to_verify:['Semiconductor fabrication']
})).taskGaps.includes('Semiconductor fabrication'));

console.log('PASS: central scientific duties, specialist gaps, qualification priority, legacy records, audited state');
