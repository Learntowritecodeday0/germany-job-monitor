'use strict';
/* Public employer research is separate from live job-monitoring sources.
   Personal interest statuses and notes remain browser-local. */
(function () {
  const STORAGE_KEY = 'germany-job-monitor:company-research:v1';
  const STATUSES = ['New', 'Researching', 'Monitor', 'Contact planned', 'Applied', 'Not pursuing'];

  function normalizeName(value) {
    return String(value || '').normalize('NFKD').replace(/[\u0300-\u036f]/g, '')
      .replace(/ß/g, 'ss').toLocaleLowerCase().replace(/&/g, ' and ')
      .replace(/\b(gmbh|gesellschaft|co|kg|ag|se|mbh|gbr)\b/g, ' ')
      .replace(/[^\p{L}\p{N}]+/gu, ' ').trim().replace(/\s+/g, ' ');
  }
  function matchesName(advertisedName, profile) {
    const actual = normalizeName(advertisedName);
    return !!actual && (profile.aliases || []).some(alias => normalizeName(alias) === actual);
  }
  function linkedJobs(profile, jobs) {
    return (jobs || []).filter(job => matchesName(job.company, profile));
  }
  function safeUrl(url) {
    try { const parsed = new URL(String(url || '')); return ['https:', 'http:'].includes(parsed.protocol) ? parsed.href : ''; }
    catch (_) { return ''; }
  }
  function coverage(profile, sources) {
    return (sources || []).find(source => matchesName(source.name, profile)) || null;
  }
  // The exported helpers also let regression tests verify matching without a browser.
  if (typeof module !== 'undefined' && module.exports) {
    module.exports = { normalizeName, matchesName, linkedJobs, coverage, safeUrl };
  }
  if (typeof document === 'undefined') return;

  const $ = id => document.getElementById(id);
  const ui = {
    view: $('companiesView'), results: $('companyResults'), message: $('companyMessage'),
    count: $('companyCount'), search: $('companySearch'), band: $('companyBand'),
    region: $('companyRegion'), segment: $('companySegment'), status: $('companyInterestFilter'),
    export: $('companyExport'), import: $('companyImport'), saved: $('companySaved')
  };
  if (!ui.view || !ui.results) return;
  let profiles = [];
  let snapshot = { jobs: [], sources: [], last_checked: '' };
  let jobDataError = false;
  let personal = loadPersonal();

  function node(tag, className, text) {
    const element = document.createElement(tag);
    if (className) element.className = className;
    if (text !== undefined) element.textContent = String(text);
    return element;
  }
  function appendText(parent, label, value, cls = '') {
    const line = node('p', 'company-detail-line ' + cls);
    line.append(node('strong', '', label + ' '), document.createTextNode(String(value || '—')));
    parent.append(line);
    return line;
  }
  function outbound(label, rawUrl) {
    const url = safeUrl(rawUrl);
    if (!url) return null;
    const a = node('a', 'company-link', label);
    a.href = url;
    a.target = '_blank';
    a.rel = 'noopener noreferrer';
    return a;
  }
  function loadPersonal() {
    try {
      const obj = JSON.parse(localStorage.getItem(STORAGE_KEY) || '{}');
      return obj.version === 1 && obj.records && typeof obj.records === 'object' && !Array.isArray(obj.records) ? obj.records : {};
    } catch (_) { return {}; }
  }
  function savePersonal(id, patch) {
    const prev = personal[id] || {};
    personal[id] = { interest: STATUSES.includes(patch.interest) ? patch.interest : (STATUSES.includes(prev.interest) ? prev.interest : 'New'),
      notes: typeof patch.notes === 'string' ? patch.notes.slice(0, 1500) : String(prev.notes || '').slice(0, 1500) };
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify({ version: 1, records: personal }));
      ui.saved.textContent = 'Saved locally in this browser.';
    } catch (_) { ui.saved.textContent = 'Browser storage failed. Export a backup.'; }
  }
  function interest(p) {
    return STATUSES.includes(personal[p.id]?.interest) ? personal[p.id].interest : 'New';
  }
  function addOptions(select, values) {
    for (const value of values) {
      const option = node('option', '', value);
      option.value = value;
      select.append(option);
    }
  }
  function populateFilters() {
    addOptions(ui.region, [...new Set(profiles.map(p => p.region))].sort());
    addOptions(ui.segment, [...new Set(profiles.map(p => p.segment))].sort());
  }
  function companyCard(profile) {
    const jobs = linkedJobs(profile, snapshot.jobs);
    const source = coverage(profile, snapshot.sources);
    const card = node('article', 'company-card');
    card.id = 'company-' + profile.id;
    const heading = node('div', 'company-top');
    const identity = node('div');
    identity.append(node('h3', '', profile.name), node('p', 'company-muted', [profile.city, profile.region].filter(Boolean).join(' · ')));
    const overlap = node('span', 'company-overlap ' + (profile.technical_overlap === 'High' ? 'top' : ''), profile.technical_overlap + ' technical overlap');
    heading.append(identity, overlap);
    card.append(heading);
    card.append(node('p', 'company-segment', profile.segment));
    card.append(node('p', 'company-focus', profile.focus));

    const badges = node('div', 'company-meta');
    const sourceLine = source
      ? (source.status === 'ok' ? 'Automated source: reporting' : 'Automated source: check error')
      : 'Manual careers check';
    badges.append(node('span', 'company-tag', sourceLine));
    badges.append(node('span', 'company-tag', jobs.length + ' linked post' + (jobs.length === 1 ? '' : 's') + ' in snapshot'));
    card.append(badges);

    const links = node('div', 'company-actions');
    for (const a of [outbound('Career page', profile.careers_url), outbound('Technical source', profile.source)]) {
      if (a) links.append(a);
    }
    card.append(links);

    const details = node('details', 'company-details');
    details.append(node('summary', '', 'Research, suitability and linked jobs'));
    const body = node('div', 'company-details-body');
    appendText(body, 'Research overlap:', profile.research_overlap);
    appendText(body, 'Screening gap:', profile.screening_gap);
    appendText(body, 'Possible job families (not vacancies):', (profile.roles || []).join(' · '));
    appendText(body, 'Recruitment route:', profile.application_channel || 'Not assessed');
    appendText(body, 'Research reviewed:', profile.research_updated || 'Not recorded');
    if (source) {
      appendText(body, 'Feed status:', source.status === 'ok' ? 'Successful check; results may be incomplete' : ('Source error; no absence-of-vacancies conclusion'));
    } else {
      appendText(body, 'Coverage:', 'Not in the automated sources; absence of linked posts does not mean no vacancies');
    }

    const jobsBox = node('section', 'company-linked-jobs');
    jobsBox.append(node('h4', '', 'Postings in the current monitor snapshot'));
    if (!jobs.length) {
      jobsBox.append(node('p', 'company-muted', source
        ? 'No postings matched this exact company identity in the current snapshot; check source status and official careers page.'
        : 'This employer is not individually monitored. Open the official careers page for current opportunities.'));
    } else {
      const list = node('ul', '');
      for (const job of jobs.slice(0, 12)) {
        const item = node('li', '');
        const link = outbound(job.title || 'Job advertisement', job.url);
        item.append(link || node('span', '', job.title || 'Untitled posting'));
        const location = job.location ? ' · ' + job.location : '';
        item.append(node('span', 'company-muted', location));
        list.append(item);
      }
      jobsBox.append(list);
      if (jobs.length > 12) jobsBox.append(node('p', 'company-muted', 'Showing 12 of ' + jobs.length + '. Use the Vacancies tab for the full source.'));
    }
    body.append(jobsBox);

    const privateBlock = node('div', 'company-personal');
    privateBlock.append(node('h4', '', 'Private research tracking (this browser only)'));
    const statusLabel = node('label', '', 'Interest status');
    const select = node('select', '');
    addOptions(select, STATUSES);
    select.value = interest(profile);
    select.setAttribute('aria-label', 'Interest status for ' + profile.name);
    select.addEventListener('change', () => savePersonal(profile.id, { interest: select.value }));
    statusLabel.append(select);
    const notesLabel = node('label', '', 'Research notes');
    const notes = node('textarea', '');
    notes.rows = 3;
    notes.maxLength = 1500;
    notes.placeholder = 'Department, contact approach, questions to investigate…';
    notes.value = String(personal[profile.id]?.notes || '');
    notes.addEventListener('change', () => savePersonal(profile.id, { notes: notes.value }));
    notesLabel.append(notes);
    const button = node('button', '', 'Save notes');
    button.type = 'button';
    button.addEventListener('click', () => savePersonal(profile.id, { notes: notes.value, interest: select.value }));
    privateBlock.append(statusLabel, notesLabel, button);
    body.append(privateBlock);
    details.append(body);
    card.append(details);
    return card;
  }
  function render() {
    const q = ui.search.value.trim().toLocaleLowerCase();
    const filtered = profiles.filter(p =>
      (ui.band.value === 'all' || p.technical_overlap === ui.band.value) &&
      (ui.region.value === 'all' || p.region === ui.region.value) &&
      (ui.segment.value === 'all' || p.segment === ui.segment.value) &&
      (ui.status.value === 'all' || interest(p) === ui.status.value) &&
      (!q || [p.name, p.city, p.region, p.segment, p.focus, p.research_overlap, ...(p.roles || [])].join(' ').toLocaleLowerCase().includes(q)));
    ui.results.replaceChildren(...filtered.map(companyCard));
    ui.count.textContent = filtered.length + ' of ' + profiles.length + ' employer profiles';
    if (!filtered.length) ui.results.append(node('p', 'company-muted', 'No companies match these filters.'));
  }
  function exportPersonal() {
    const payload = JSON.stringify({ version: 1, records: personal }, null, 2);
    const blob = new Blob([payload], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = 'company-research-personal.json';
    document.body.append(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(url);
    ui.saved.textContent = 'Local company notes exported. Store the file privately.';
  }
  async function importPersonal(file) {
    if (!file || file.size > 1048576) { ui.saved.textContent = 'Import failed: file missing or larger than 1 MB.'; return; }
    try {
      const incoming = JSON.parse(await file.text());
      if (incoming.version !== 1 || !incoming.records || typeof incoming.records !== 'object' || Array.isArray(incoming.records)) throw Error('Unsupported backup format.');
      let count = 0;
      const known = new Set(profiles.map(p => p.id));
      for (const [id, record] of Object.entries(incoming.records)) {
        if (!known.has(id) || !record || typeof record !== 'object') continue;
        const status = STATUSES.includes(record.interest) ? record.interest : 'New';
        personal[id] = { interest: status, notes: String(record.notes || '').slice(0, 1500) };
        count++;
      }
      localStorage.setItem(STORAGE_KEY, JSON.stringify({ version: 1, records: personal }));
      render();
      ui.saved.textContent = 'Imported ' + count + ' local company records.';
    } catch (error) { ui.saved.textContent = 'Import failed: ' + error.message; }
  }
  async function initialize() {
    try {
      const response = await fetch('./companies.json', { cache: 'no-store' });
      if (!response.ok) throw Error('Cannot load companies.json');
      const dataset = await response.json();
      if (dataset.version !== 1 || !Array.isArray(dataset.companies)) throw Error('Unexpected research-data format.');
      profiles = dataset.companies;
    } catch (error) {
      ui.message.textContent = 'Company profiles unavailable: ' + error.message;
      return;
    }
    try {
      const response = await fetch('./jobs.json', { cache: 'no-store' });
      if (!response.ok) throw Error('Cannot load jobs.json');
      const data = await response.json();
      snapshot = { jobs: data.jobs || [], sources: data.sources || [], last_checked: data.last_checked || '' };
    } catch (_) { jobDataError = true; }
    populateFilters();
    const monitored = profiles.filter(p => coverage(p, snapshot.sources)).length;
    ui.message.textContent = profiles.length + ' researched employer profiles. ' +
      monitored + ' have matching automated source status in the current snapshot. ' +
      (jobDataError ? 'Vacancy snapshot unavailable; job links cannot be displayed. ' :
        'Linked jobs reflect the latest monitor snapshot, not confirmed live vacancies. ') +
      'Technical overlap is not an employment probability. Locations refer to researched sites, not advertised worksites.';
    render();
    if (typeof window.dispatchEvent === 'function' && typeof Event === 'function') window.dispatchEvent(new Event('company-directory-ready'));
  }
  for (const control of [ui.search, ui.band, ui.region, ui.segment, ui.status]) control.addEventListener('input', render);
  ui.export.addEventListener('click', exportPersonal);
  ui.import.addEventListener('change', () => {
    const file = ui.import.files?.[0];
    importPersonal(file);
    ui.import.value = '';
  });
  window.CompanyDirectory = {
    refresh: render,
    hasCompany(name) { return profiles.some(profile => matchesName(name, profile)); },
    openByCompany(name) {
      const p = profiles.find(profile => matchesName(name, profile));
      if (!p) return false;
      $('tabCompanies').click();
      ui.search.value = '';
      for (const control of [ui.band, ui.region, ui.segment, ui.status]) control.value = 'all';
      render();
      const card = $('company-' + p.id);
      if (card) { card.querySelector('details')?.setAttribute('open', ''); card.scrollIntoView({ block: 'start' }); }
      return true;
    }
  };
  initialize();
})();
