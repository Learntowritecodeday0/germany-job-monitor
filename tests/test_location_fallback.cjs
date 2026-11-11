const fs=require('fs'), vm=require('vm'), assert=require('node:assert/strict');
const app=fs.readFileSync(__dirname+'/../docs/app.js','utf8');
const code=app.slice(app.indexOf('// Fallback for deployments'),app.indexOf('function render(){'));
const ctx={};vm.createContext(ctx);vm.runInContext(code,ctx);
const infer=j=>JSON.parse(JSON.stringify(vm.runInContext('inferLocationForDisplay('+JSON.stringify(j)+')',ctx)));
const tests=[
  [{location:'Alzenau, Bavaria, Germany',country:'Germany'},['Alzenau','Bayern','Germany']],
  [{location:'Aachen, Germany',country:'Germany'},['Aachen','Nordrhein-Westfalen','Germany']],
  [{location:'Munich HQ',country:'Germany'},['Munich','Bayern','Germany']],
  [{location:'Zwickau',country:'Germany'},['Zwickau','Sachsen','Germany']],
  [{location:'Ulm',country:''},['Ulm','Baden-Württemberg','Germany']],
  [{location:'Essen, Germany',country:''},['Essen','Nordrhein-Westfalen','Germany']],
  [{location:'Hessen, Deutschland',country:''},[null,'Hessen','Germany']],
  [{location:'EDMO Manufacturing & Testing Facility',country:'Germany'},[null,null,'Germany']],
  [{location:'',country:''},[null,null,null]]
];
for(const [j,values] of tests){const x=infer(j);assert.deepEqual([x.city,x.state,x.country],values,'For '+j.location)}
const multi=infer({location:'Munich HQ; Delft',country:'Germany'});
assert.equal(multi.multiple,true);assert.equal(multi.country,'Germany / Netherlands');
assert.deepEqual(multi.sites.map(x=>x.city),['Munich','Delft']);
const old=infer({location:'Alzenau, Bavaria, Germany',country:'Germany',worksite_city:'Alzenau',worksite_state:'Bayern',worksite_country:'Germany'});
assert.equal(old.fromFallback,false);
const missing=infer({location:'Alzenau, Bavaria, Germany',country:'Germany'});
assert.equal(missing.fromFallback,true);
console.log('Passed 12 frontend location fallback tests');
