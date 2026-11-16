# Germany Job Monitor

A public vacancy monitor for scientific, chemical and materials-related positions in Germany, with a browser-local application history. This is **not** an automated application system or a verified hiring-fit assessment.

## What the monitor does

- Tracks a growing list of 62 configured official recruitment sources, including Greenhouse, Ashby, Personio, Softgarden, SmartRecruiters and selected public career pages. Some sources can fail or have limited search coverage; always inspect **Source status**.
- Runs a scheduled check six times a day using GitHub Actions (approximately every four hours; delays and missed runs are possible).
- Remembers when each job was **first detected**. It does not claim that this equals the original publication time.
- Excludes clearly non-German locations; flags uncertain or mixed locations for manual review.
- Uses a two-stage browser view: **Matches to investigate (broad)** is the default discovery queue; **Direct shortlist (strict)** separately highlights documented experimental overlap. The broad queue includes related chemistry/materials lab technicians, analytical development, senior/stretched specialties and incomplete-description leads for manual review. These labels do not imply eligibility or interview likelihood.
- Retains keyword categories only as a separate search signal. The **Direct shortlist** requires evidence of central experimental duties (e.g. formulation, nanoparticle synthesis, surface chemistry or materials characterization), rather than a familiar instrument name mentioned anywhere in the advertisement.
- Sends otherwise relevant roles to **Needs requirements review** when critical industry-specific daily tasks, undocumented explicit qualifications, substantial required experience, or unavailable qualifications require verification. Preferred or explicitly learnable skills do not automatically exclude a role.
- Also flags **adjacent application-testing roles** when an explicit tasks section pairs adhesive/material subjects with experimental measurements or trials. These go to requirements review rather than being counted as directly documented formulation expertise. Ambiguous experience clauses such as “minimum 3–5 years … desirable” are displayed for review, not automatically treated as mandatory.
- Uses **Review soon** for a small historical manual audit, **Secondary review** for evidence-based automatic suggestions, and keeps **Other / deprioritized** vacancies searchable. These are review queues, not a hiring-fit probability or an eligibility decision.
- Creates a public HTML dashboard with links to official job postings and a separate manual employer watchlist.
- Includes an **Applications** tab for locally stored application dates, outcomes, responses, notes and follow-ups. JSON export/import is available; records do not sync between browsers automatically.
- Offers **System (default), Light and Dark** appearance choices. System follows the device/browser theme; manual choices remain in this browser.

**Important:** A configured source is not a guarantee of working live coverage. Check the latest GitHub Actions workflow and website source-health report before relying on a new source.

## Setup: first time (beginner-friendly)

1. Sign in or create a GitHub account: https://github.com/signup . Do **not** share your password or login tokens in chat.
2. Create a new repository named `germany-job-monitor`. Select **Public**, and do not initialize it with a README (this download already includes one). The public site must not contain private career documents or personal data.
3. Download this ZIP and extract it. Upload **the contents** of the extracted folder (including `.github`) into the repository. Check that the file `.github/workflows/monitor.yml` is present in the repository. Commit the upload.
4. Go to the repository's **Settings → Pages → Build and deployment**. Set **Source = GitHub Actions**.
5. Go to **Actions → Check German career pages → Run workflow**, choose the main branch, and run it. Allow the workflow to complete. If a step fails, open the run log and inspect the error. The four live connections must be verified here.
6. After a successful Pages deployment, the link should look like `https://YOUR_GITHUB_USERNAME.github.io/germany-job-monitor/`. Replace the username with the actual account username; no domain purchase is required.
7. Return to this conversation with the **public repository URL** (not a password). Further companies can be added and errors corrected.

GitHub may show an extra confirmation for enabling Actions or Pages. Pages and Actions permissions/policies may differ by account or organization.

## Add or remove companies

Open `config/companies.json` and edit the list. Each entry needs the official name, `platform`, `slug`, and public career URL. Supported platforms:

- `greenhouse_eu` — job board like `https://job-boards.eu.greenhouse.io/COMPANY`
- `greenhouse` — `https://job-boards.greenhouse.io/COMPANY`
- `ashby` — `https://jobs.ashbyhq.com/COMPANY`
- `personio` — an employer's official Personio board and its public feed or job-list HTML
- `softgarden` — an employer's official `jobs.feed.json` public DataFeed
- `smartrecruiters` — official public SmartRecruiters posting API
- `workday_limited` — a verified employer-linked public Workday careers board, with bounded 20-job pages. This uses the public listing endpoint, not a private HR API; source errors are displayed and the scan may omit older jobs.
- Selected source-specific limited-window HTML readers, defined in `monitor.py`

Example: Copy an existing entry, replace the details, and commit the change. Check the next workflow run and source status. **Never assume a company supports a platform without verifying its official site.** Workday has a limited, employer-specific reader for DELO; it is not a universal connector or a guarantee that other Workday boards accept requests. Other custom public sources use dedicated, limited-scope adapters.

## Run on a computer (optional)

Needs Python 3.10+ and internet access:

```bash
python -m unittest discover -s tests -v
python monitor.py
python -m http.server 8000 --directory docs
```

Then visit `http://localhost:8000` in a browser. No third-party Python packages or AI API key are required.

## Privacy and limitations

- GitHub Pages sites are public, even when repository plans permit private source repositories. The monitor publishes vacancies that are already public. **Do not commit CVs, application notes, immigration status, or contact details.** The Applications tab stores records only in the browser; export backups privately.
- GitHub Actions schedules can be delayed; public-repo schedules may be disabled after 60 days without activity. Check the workflow status periodically.
- The first successful scan of a source creates a **baseline** of existing jobs. It cannot infer whether those listings are genuinely new. Later unseen jobs are detected as new.
- Source feeds can change without notice. Errors should never be interpreted as no vacancies.
- **62 configured sources is not comprehensive coverage of Germany's chemistry sector.** Important large employers (BASF, Henkel, Covestro, Clariant, SCHOTT, LANXESS, WACKER, BYK and Evonik) are linked under the manual watchlist but are not counted as automated vacancy sources. Partial-window sources and public feeds lacking full job descriptions can miss relevant roles. For limited-window sources, jobs disappearing from the latest pages do not prove that they closed.
- Job data might include an old open position or cross-border location; always inspect the original listing before applying.
- Keyword categories are not measured hiring probabilities. A role can be ranked high despite lacking a mandatory requirement.
- Email alerts are supported through private GitHub Actions secrets, when configured. No email credentials belong in public repository files.
- If the monitoring process repeatedly fails, do not increase polling frequency or attempt to bypass anti-bot restrictions. Use employer-provided alerts or supported feeds.

## Authoritative references

- https://docs.greenhouse.io/job-board
- https://developers.ashbyhq.com/docs/public-job-posting-api
- https://docs.github.com/en/pages/getting-started-with-github-pages
- https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows
