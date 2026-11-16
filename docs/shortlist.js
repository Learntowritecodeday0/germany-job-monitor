/* Germany Job Monitor: conservative, browser-side review queue.
   This file is intentionally independent of the source scanner and email alerts.
   It uses the employer's public job content and a small audited sample;
   it does NOT assert hiring eligibility or access private application history. */
(function(root, factory) {
  const api = factory();
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  if (root) root.JobShortlist = api;
})(typeof window === 'undefined' ? null : window, function() {
  'use strict';

  // Audited on the 12 Nov 2026 snapshot. Keys are public job-post identifiers.
  // These are review queues, not eligibility decisions or personal application history.
  const AUDITED = Object.freeze({
    'smartrecruiters:FischerGroup:744000159557829': ['review', 'Formulation R&D and analytical testing; verify polymer specialization and German requirement'],
    'pct_html:pct-chemie:/pct-chemie/karriere/offene-stellen/chemiker-/-naturwissenschaftler-m/w/d': ['review', 'Materials/additives development; verify cement chemistry, organic synthesis and German requirement'],
    'personio:emil-kiessling-gmbh:2849331': ['review', 'Emulsion development; verify cosmetic formulation and SPF-testing experience'],
    'greenhouse_eu:engcmbluenergyag:5020878101': ['review', 'Experimental formulation and DoE; battery electrochemistry remains a gap'],
    'pct_html:pct-chemie:/pct-chemie/karriere/offene-stellen/naturwissenschaftler-m/w/d-mit-ausgepraegter-technischer-affinitaet': ['secondary', 'Experimental materials testing; practical screed handling and German requirement need review'],
    'personio:rudolf:2805325': ['secondary', 'Chemical process optimization; verify industrial batch-production responsibilities'],
    'personio:blackwave:2871800': ['secondary', 'Laboratory/cleanliness work; verify aerospace-specific methods and German requirement'],
    'rss:tum-wissenschaftler:http://portal.mytum.de/jobs/wissenschaftler/NewsArticle_20261013_092729': ['details', 'Biopolymer/cellulose research; verify full duties and industry career relevance'],
    'personio:junglueck:760286': ['other', 'Senior cosmetics experience and native-level German requirement need closer review'],
    'personio:klb:2524785': ['other', 'Core specialty is industrial epoxy/polyurethane resin development'],
    'personio:blackwave:2657617': ['other', 'Core specialty is composite winding, not general DoE'],
    'ashby:blacksemiconductor:https://jobs.ashbyhq.com/blacksemiconductor/2a8897e7-bbb2-408f-ad16-136d2523017a': ['other', 'Routine instrument operation and tool maintenance require separate evidence'],
    'personio:proteros-biostructures-gmbh:1914202': ['other', 'Specialized HPLC/LC-MS protein analytics; advertisement also states no PhD'],
    'personio:dr-franz-koehler-chemie-gmbh:2845004': ['other', 'Vocational-level analytical role; primary methods differ'],
    'personio:planetafoods:2795212': ['other', 'Senior 24/7 food production ownership rather than laboratory scale-up'],
  });

  const hardTitle = /(?:\b(?:lagerist|lagerfachkraft|fachlagerist|lagerlogistik|warehouse|forklift|staplerfahrer|produktionshelfer|produktionsmitarbeiter|fertigungsmitarbeiter|verfahrensmechaniker|maschinenf[uü]hrer|maschinenbediener|anlagenf[uü]hrer|schichtf[uü]hrer|chemikant|facharbeiter|werkfeuerwehr|firefighter|verk[aä]ufer|assisten[zt]|sachbearbeiter|assistenz|büromanager|rezeption|mechatroniker|elektriker|elektroniker|instandhaltung|mechanical design|aircraft|avionics|fpga|embedded systems|backend engineer|python sdk|algorithms engineer)\b|\b(?:operator|production worker|plant operator)\b)/i;
  const training = /\b(?:masterarbeit|bachelorarbeit|abschlussarbeit|studienarbeit|thesis|werkstudent\w*|studentische\s+hilfskraft|praktikan\w*|internship|ausbildung|auszubild\w*|doktorand\w*|doctoral candidate|ph\.?d\.?\s+(?:student|candidate|position))\b/i;
  const incompatibleSpecialty = /\b(?:composite winding|fiber winding|fibre winding|layup engineering|aerospace structures|electric motor|rotor design|firmware|computational\s+materials?\s+scientist|dft\s+expert|reactive\s+transport\s+modell\w*|tritium|photonics circuit|semiconductor tool maintenance|wafer inspection|aircraft structures|spacecraft propulsion|mechanical systems|electronic architect|robotics navigation)\b/i;
  const technicalTitle = /(?:\b(?:chemist|chemiker(?:in)?|entwicklungschemiker|material(?:s)?\s+(?:scientist|developer|engineer)|materialwissenschaft\w*|werkstoffentwick\w*|surface\s+(?:scientist|chemistry)|r\s*&\s*d\s+(?:scientist|chemist)|anwendungschemiker|nanopartic\w*|nanopartik\w*|kolloid\w*|colloid\w*|aerogel\w*|formulier\w*|formulat\w*|dispers\w*|emulsion\w*|sol-gel|particle characterization|materialcharakteris\w*|produktentwickl\w*|process\s+development|prozessentwickl\w*|materialentwicklung|polymer scientist)\b|\b(?:laboratory|labor|research|scientist|entwickler|entwicklung|application scientist|anwendungstechniker|verfahrenstechniker|prozessingenieur)\b)/i;
  // Specific scientific duties required; generic words such as "process", "technology" or "materials" alone are insufficient.
  const coreChemistry = /\b(?:nanopartic\w*|nanopartik\w*|silica|siliciumdioxid|si[o0]2|sol[- ]?gel|aerogel\w*|colloid\w*|kolloid\w*|zellulose|cellulose|emulsion\w*|formul\w*|dispers\w*|suspension\w*|tenside\w*|surfactant\w*|oberfl[aä]chenchemie|surface functionaliz\w*|surface modification|materialcharakteris\w*|particle characteriz\w*|partikelsynthese|polymer synthesis|materials?\s+development|materialentwicklung|chemische\s+entwicklung)\b/i;
  const generalScientificRole = /(?:\bapplication\s+scientist\b|\br&d\s+(?:engineer|scientist)\b|\bresearch\s+engineer\b|\bentwicklungsingenieur\w*\b|\banwendungstechniker\w*\b|\banwendungsentwickl\w*\b|\bprozessingenieur\w*\b|\bprocess\s+development\s+engineer\b)/i;
  const experimentalDuty = /(?:\b(?:labor(?:atory)?(?:versuche|experiment|untersuchung|entwickl|test)|laboratory\s+(?:research|experiments?|development)|versuchsplanung|design\s+of\s+experiments?|\bdoe\b|dls|zetapotenzial|zeta potential|ftir|ft[- ]?ir|tga|partikelgr[oö]ße|partikelverteilung|rheolog\w*|produkten?twickl\w*|formulierung(?:sentwicklung)?|syntheseentwicklung|methodenentwicklung|method development|chemical characterization|material\s+characterization|materialcharakterisierung)\b)/i;
  const weakRole = /\b(?:senior|principal|director|head of|chief|leiter\w*|lead\s+(?:process|engineer|development)|vp\b)\b/i;
  const phdProhibited = /\b(?:keine\s+promotion|ohne\s+promotion|no\s+phd|no\s+ph\.d|phd\s+not\s+(?:eligible|accepted))\b/i;
  const operationHeavy = /\b(?:schichtdienst|wechselschicht|schichtbetrieb|schichtarbeit|bedienen\s+(?:und\s+)?(?:von\s+)?maschinen|wartung\s+und\s+instandhaltung|maintenance\s+of\s+equipment|f[uü]hrung\s+(?:von\s+)?(?:eines\s+)?produktionsteams)\b/i;

  function nonEmpty(s){return typeof s === 'string' ? s.trim() : '';}
  function hasChemistryInTitle(title){
    const role = /(?:chemiker|\bchemist\b|\bscientist\b|wissenschaftlich\w*\s+(?:mitarbeit|research)|entwickl\w*|developer|development|research|forscher|r&d|application|applikation|analyt\w*|charakteris\w*|labor\w*|engineer|ingenieur|technologe)/i;
    const domain = /(?:chem|material|werkstoff|surface|oberfl[aä]ch|formulier|formulat|emuls|dispers|nanop|particle|partikel|kolloid|colloid|polymer|silica|aerogel|sol[- ]?gel|cellulos|zellulos|biopolymer|additiv|coating|beschicht|rheolog|cosmetic|kosmetik|recycling)/i;
    return role.test(title) && domain.test(title);
  }
  // Hands-on formulations / synthesis / characterization are closer to the
  // documented work than generic DoE or laboratory scale-up. DoE alone is not
  // evidence of readiness for an unrelated production or sector-specific task.
  const directCoreTasks = new Set([
    'Nanoparticle and sol-gel synthesis',
    'Formulation and dispersion experiments',
    'Materials and particle characterization',
    'Surface functionalization and wettability'
  ]);

  function reviews(job) {
    const title = nonEmpty(job?.title);
    const description = nonEmpty(job?.description);
    const override = AUDITED[nonEmpty(job?.key)];
    // Apply fundamental exclusions BEFORE old manual-review overrides. An
    // inactive job or an outside-country posting must not re-enter the queue.
    if (job?.active === false || job?.location_status === 'outside')
      return {tier:'other',reason:'Inactive or outside the selected country',basis:'Source status'};
    if (job?.hide_by_default === true || ['training','unrelated','vocational'].includes(job?.career_track) || training.test(title) || hardTitle.test(title))
      return {tier:'other',reason:'Role family or career level is outside the selected search',basis:'Role classification'};
    if (phdProhibited.test(description))
      return {tier:'other',reason:'Advertised qualification conflicts with a completed PhD',basis:'Advertised qualification'};
    if (job?.education_review?.possible_overqualified === true && !/(?:r&d|forschung|entwicklung|development|scientist)/i.test(title))
      return {tier:'other',reason:'Primarily vocational qualification; career level may not align',basis:'Role classification'};
    if (incompatibleSpecialty.test(title))
      return {tier:'other',reason:'Different core industrial specialization',basis:'Role classification'};
    if (override && Number(job?.reopen_count||0)>0)
      return {tier:'details',reason:'Previously reviewed posting reappeared; recheck its complete requirements',basis:'Audited snapshot'};
    if (override) return {tier:override[0],reason:override[1],basis:'Audited snapshot'};

    const chemistryTitle = hasChemistryInTitle(title);
    const generalTitle = generalScientificRole.test(title);
    // Chemistry-adjacent adhesive testing is not evidence of direct
    // formulation/industrial rheology expertise. It merits a separate review
    // only when the verified daily duties include experimental testing.
    const adjacentTasks = Array.isArray(job?.core_adjacent_experimental_tasks) ?
      job.core_adjacent_experimental_tasks.filter(x => typeof x === 'string' && x.trim()) : [];
    const adjacentApplication = adjacentTasks.length > 0 && generalTitle;
    if (!chemistryTitle && !(generalTitle && coreChemistry.test(description) && experimentalDuty.test(description)) && !adjacentApplication)
      return {tier:'other',reason:'No clear chemical/materials R&D responsibilities',basis:'Job title and duties'};
    if (description.length < 150 || ['recent_title_only','api_list_only','html_fallback'].includes(job?.source_mode))
      return {tier:'details',reason:'Promising role title, but full responsibilities/requirements are missing',basis:'Source completeness'};
    if (weakRole.test(title))
      return {tier:'other',reason:'Senior/lead specialization requires substantial sector experience; review separately',basis:'Career level'};
    if (operationHeavy.test(description) && !experimentalDuty.test(description))
      return {tier:'other',reason:'Production/equipment operation appears to dominate daily work',basis:'Advertised duties'};

    const checks = requirementChecks(job);
    if (checks.essential.length || checks.highExperience)
      return {tier:'details',reason:'Explicit mandatory qualification or extensive experience needs verification',basis:'Advertised requirements'};

    if (adjacentApplication)
      return {tier:'details',reason:'Adhesive measurement or application testing is central, but specialized methods, customer scope and essential experience need verification',basis:'Adjacent experimental duties'};
    const skills = job?.competency_counts || {};
    const methodMatched = Number(skills.method?.matched || 0);
    const technicalMatched = Number(skills.technical?.matched || 0);
    const chemistryEvidence = coreChemistry.test(description);
    const experimentEvidence = experimentalDuty.test(description);
    const primaryTasks = Array.isArray(job?.core_documented_tasks) ?
      job.core_documented_tasks.filter(x => typeof x === 'string' && directCoreTasks.has(x)) : null;
    const taskGaps = checks.taskGaps;
    const structured = primaryTasks !== null && nonEmpty(job?.core_review_basis) !== '';
    if (structured) {
      // A primary industrial specialization is not made transferable by one
      // unrelated shared method. Examples: wafer fab + DoE; composite winding
      // + laboratory measurements. Send mixed cases for a manual requirements
      // review, not an automatic interview-readiness claim.
      if (taskGaps.length)
        return {tier:'details',reason:'Specialized daily duties require separate industry experience; shared laboratory methods are not sufficient evidence',basis:'Main responsibilities'};
      if (!primaryTasks.length)
        return {tier:'other',reason:'No documented primary chemistry, formulation, surface, or characterization work in daily duties',basis:'Main responsibilities'};
      if (checks.core.length && checks.noCoreCoverage)
        return {tier:'details',reason:'Core industry methods need verification despite matching scientific keywords',basis:'Core specialization'};
      if (job?.qualification_priority?.status === 'unavailable')
        return {tier:'details',reason:'Experimental duties overlap, but mandatory qualifications could not be extracted',basis:'Missing qualification detail'};
      if (primaryTasks.length >= 1 && (chemistryTitle || generalTitle)) {
        return {tier:'secondary',reason:taskGaps.length ?
          'Relevant experimental core duties; separate specialized industry tasks still need review' :
          'Relevant experimental core duties; verify mandatory experience and actual ownership',
          basis:'Primary scientific duties'};
      }
    }

    // Fallback for legacy postings without structured core-duty extraction.
    // This is deliberately narrower than matching title + one method keyword.
    if (checks.core.length && checks.noCoreCoverage)
      return {tier:'details',reason:'Unverified core specialization and no supported technical methods identified',basis:'Core specialization'};
    if (chemistryEvidence && experimentEvidence && (coreChemistry.test(title) || (methodMatched>0 && technicalMatched>0)))
      return {tier:'secondary',reason:'Potential laboratory overlap from available text; verify actual main tasks',basis:'Legacy text evidence'};
    return {tier:'other',reason:'Insufficient evidence of relevant daily scientific responsibilities',basis:'Main responsibilities'};
  }

  // Distinguish explicitly required expertise from preferences and skills
  // the employer allows a candidate to learn. Unrecorded != absent.
  function requirementChecks(job) {
    const q = job?.qualification_priority || {};
    const items = key => Array.isArray(q[key]) ? q[key] : [];
    const category = entry => ['Technical', 'Methods'].includes(entry?.category) ||
      (entry?.category === 'General' && [
        'Fluent professional German', 'Formal ISO / GMP / medical-device validation',
        'Senior people management'
      ].includes(entry.name));
    const notDocumented = entry => entry && entry.documented === false;
    const labels = group => [...new Set(items(group).filter(entry => category(entry) && notDocumented(entry))
      .map(entry => nonEmpty(entry.name)).filter(Boolean))].slice(0, 3);
    const experience = (Array.isArray(q.experience_flags) ? q.experience_flags : [])
      .filter(entry => entry?.kind === 'explicit minimum' && nonEmpty(entry.text))
      .map(entry => nonEmpty(entry.text)).slice(0, 2);
    const highExperience = experience.some(value => {
      const match = value.match(/(?:minimum(?:\s+of)?|at\s+least|mindestens)\s+(\d+)(?:\s*[-–]\s*\d+)?\+?\s*(?:years?|jahre[n]?)/i)
        || value.match(/\b(\d+)\s*\+\s*(?:years?|jahre[n]?)\b/i);
      return !!match && Number(match[1]) >= 5;
    });
    const core = Array.isArray(job?.core_specializations_to_verify) ?
      [...new Set(job.core_specializations_to_verify.filter(x => typeof x === 'string' && x.trim()))].slice(0, 2) : [];
    const taskGaps = Array.isArray(job?.core_task_specializations_to_verify) ?
      [...new Set(job.core_task_specializations_to_verify.filter(x => typeof x === 'string' && x.trim()))].slice(0, 3) : [];
    const counts = job?.competency_counts;
    const noCoreCoverage = !!(counts && counts.technical?.total > 0 && counts.method?.total > 0 &&
      counts.technical.matched === 0 && counts.method.matched === 0);
    return {
      essential: labels('explicit'),
      preferred: labels('preferred'),
      learnable: labels('learnable'),
      experience, highExperience, core, taskGaps, noCoreCoverage,
      basis: q.status === 'parsed' ? 'Advertised qualification wording (automated)' : 'Incomplete qualification extraction'
    };
  }

  function isShortlist(r){return r.tier==='review'||r.tier==='secondary'}
  const tiers={review:'Review soon',secondary:'Secondary review',details:'Needs requirements review',other:'Other / deprioritized'};
  const tierOrder={review:0,secondary:1,details:2,other:3};
  return Object.freeze({reviews,requirementChecks,isShortlist,tiers,tierOrder});
});
