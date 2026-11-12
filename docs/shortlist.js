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
  const generalScientificRole = /(?:\bapplication\s+scientist\b|\br&d\s+(?:engineer|scientist)\b|\bresearch\s+engineer\b|\bentwicklungsingenieur\w*\b|\banwendungstechniker\w*\b|\bprozessingenieur\w*\b|\bprocess\s+development\s+engineer\b)/i;
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
  function reviews(job) {
    const title = nonEmpty(job?.title);
    const description = nonEmpty(job?.description);
    const key = nonEmpty(job?.key);
    const override = AUDITED[key];
    if (override && Number(job?.reopen_count||0)>0) return {tier:'details',reason:'Previously reviewed posting reappeared; recheck its complete requirements',basis:'Audited snapshot'};
    if (override) return {tier:override[0],reason:override[1],basis:'Audited snapshot'};
    if (job?.active === false || job?.location_status === 'outside')return {tier:'other',reason:'Inactive or outside the selected country',basis:'Rule-based'};
    if (job?.hide_by_default === true || ['training','unrelated','vocational'].includes(job?.career_track) || training.test(title) || hardTitle.test(title)) {
      return {tier:'other',reason:'Role family or career level is outside the selected search',basis:'Rule-based'};
    }
    if (phdProhibited.test(description))return {tier:'other',reason:'Advertised qualification conflicts with a completed PhD',basis:'Rule-based'};
    if (job?.education_review?.possible_overqualified === true && !/(?:r&d|forschung|entwicklung|development|scientist)/i.test(title)){
      return {tier:'other',reason:'Primarily vocational qualification; career level may not align',basis:'Rule-based'};
    }
    if (incompatibleSpecialty.test(title))return {tier:'other',reason:'Different core industrial specialization',basis:'Rule-based'};
    if (!hasChemistryInTitle(title) && !(generalScientificRole.test(title) && coreChemistry.test(description) && experimentalDuty.test(description)))return {tier:'other',reason:'No clear chemical/materials R&D responsibilities',basis:'Rule-based'};
    if (description.length < 150 || ['recent_title_only','api_list_only','html_fallback'].includes(job?.source_mode)){
      return {tier:'details',reason:'Promising role title, but full responsibilities/requirements are missing',basis:'Rule-based'};
    }
    if (weakRole.test(title))return {tier:'other',reason:'Senior/lead specialization requires a separate essential-experience check',basis:'Rule-based'};
    if (operationHeavy.test(description) && !experimentalDuty.test(description))return {tier:'other',reason:'Production/equipment operation appears to dominate daily work',basis:'Rule-based'};
    const skills=job?.competency_counts || {};
    const methodMatched=Number(skills.method?.matched || 0);
    const technicalMatched=Number(skills.technical?.matched || 0);
    const titleMatch=coreChemistry.test(title);
    const chemistryEvidence=coreChemistry.test(description);
    const experimentEvidence=experimentalDuty.test(description);
    if (titleMatch && (methodMatched>0 || technicalMatched>0 || (chemistryEvidence&&experimentEvidence))){
      return {tier:'secondary',reason:'Potential experimental chemistry/materials overlap; verify the primary duties and mandatory experience',basis:'Rule-based'};
    }
    if (chemistryEvidence && experimentEvidence && (methodMatched>0 || technicalMatched>0)){
      return {tier:'secondary',reason:'Experimental duties overlap; role title is less specific',basis:'Rule-based'};
    }
    return {tier:'other',reason:'Insufficient evidence of relevant daily scientific responsibilities',basis:'Rule-based'};
  }

  function isShortlist(r){return r.tier==='review'||r.tier==='secondary'}
  const tiers={review:'Review soon',secondary:'Secondary review',details:'Needs description review',other:'Other / deprioritized'};
  const tierOrder={review:0,secondary:1,details:2,other:3};
  return Object.freeze({reviews,isShortlist,tiers,tierOrder});
});
