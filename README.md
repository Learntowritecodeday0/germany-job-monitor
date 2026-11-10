# Germany Job Monitor — starter project

An early-stage personal vacancy monitor for public German job postings. This is **not** an automated application system and **not** an AI hiring-fit assessment.

## What the starter does

- Checks four **example employers** in Germany using public Greenhouse EU and Ashby posting feeds.
- Runs a scheduled check six times a day using GitHub Actions (approximately every four hours; delays and missed runs are possible).
- Remembers when each job was **first detected**. It does not claim that this equals the original publication time.
- Excludes clearly non-German locations; flags uncertain or mixed locations for manual review.
- Gives approximate **keyword-based** review categories; always inspect essential requirements manually.
- Creates a public HTML dashboard showing open postings and links to the official listing.

**Important**: Network access to the four live feeds was not available in the file-generation environment. Source slugs were inferred from verified public career-page URLs, but initial live requests and response compatibility must still be checked in the deployed workflow logs.

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

Example: Copy an existing entry, replace the details, and commit the change. Check the next workflow run and source status. **Never assume a company supports a platform without verifying its official site.** Workday, Personio, and custom sites are not supported yet.

## Run on a computer (optional)

Needs Python 3.10+ and internet access:

```bash
python -m unittest discover -s tests -v
python monitor.py
python -m http.server 8000 --directory docs
```

Then visit `http://localhost:8000` in a browser. No third-party Python packages or AI API key are required.

## Privacy and limitations

- GitHub Pages sites are public, even when repository plans permit private source repositories. The demo only publishes vacancies that are already public. **Do not upload CVs, application notes, immigration status, or contact details.**
- GitHub Actions schedules can be delayed; public-repo schedules may be disabled after 60 days without activity. Check the workflow status periodically.
- The first successful scan creates a **baseline** of existing jobs. It cannot infer whether those listings are genuinely new. Later unseen jobs are detected as new.
- Source feeds can change without notice. Errors should never be interpreted as no vacancies.
- Job data might include an old open position or cross-border location; always inspect the original listing before applying.
- Keyword categories are not measured hiring probabilities. A role can be ranked high despite lacking a mandatory requirement.
- No email/Telegram alerts are included yet. Once the site successfully updates, notifications can be added through a separately configured channel (without exposing credentials in a public repo).
- If the monitoring process repeatedly fails, do not increase polling frequency or attempt to bypass anti-bot restrictions. Use employer-provided alerts or supported feeds.

## Authoritative references

- https://docs.greenhouse.io/job-board
- https://developers.ashbyhq.com/docs/public-job-posting-api
- https://docs.github.com/en/pages/getting-started-with-github-pages
- https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows
