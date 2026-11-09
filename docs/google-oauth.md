# Google sign-in, Gmail and Calendar

> **Status:** VEYRA ships a project-owned Google Desktop OAuth client. Users choose **Settings → Accounts → Sign in with Google** and consent in the browser; they do not create an API key, an OAuth client or a JSON file. The refresh token stays in Windows Credential Manager. Current tools cover Gmail and Calendar. Other Google services and third-party apps are separate integrations, described below.

## What the user does

1. Install VEYRA and open **Settings → Accounts**.
2. Leave write access disabled for read-only use, or enable it to allow Gmail drafts/sending and Calendar event creation.
3. Choose **Sign in with Google**.
4. Complete Google's consent screen in the default browser. VEYRA listens only on a random loopback port for the callback.
5. Return to VEYRA. The account is connected when the app reports success.

No cloud relay is involved: the local FastAPI backend on `127.0.0.1` completes the loopback flow. The OAuth client identifies the VEYRA application; each user still consents separately, and their access can be revoked at any time from the Google account's third-party access page.

The write checkbox requests the write scopes during sign-in. Change it and sign in again to change the granted scopes. The separate Google read-only setting controls whether the tools are allowed to perform write actions.

## What is covered

| Area | Read | Create/write | Authentication |
| --- | --- | --- | --- |
| Gmail | Search and read messages | Drafts and send | Google OAuth with the project client |
| Calendar | Today and date-range events | Create events | Google OAuth with the project client |
| Gmail fallback | Search and read over IMAP | Send over SMTP | Google App Password |
| Calendar fallback | Today and date-range events | Not available | Secret iCal URL (read-only) |

The local Gmail and iCal paths are optional. When configured, Gmail tools prefer the local account and Calendar reads prefer the iCal feed. OAuth is still required for Gmail drafts, Gmail send through the API path and Calendar creation.

## What one Google login does not cover

- **Other Google services are not enabled by this release.** Drive, Contacts, Tasks, Docs and Sheets need their own scopes and tool implementations. They are not silently requested by the Gmail/Calendar consent.
- **Third-party apps have their own authorization.** A Google login cannot grant access to Slack, Notion, Outlook, Dropbox or any other provider. Each provider needs a separate OAuth app, scopes and consent screen. There is no universal "all apps" login.
- **No one-click login can create a server-side private tunnel to Google.** The local loopback backend is the broker; the user's Google account remains protected by Google's consent and token rules.

Adding a provider later means adding its scopes, tools and tests one at a time; it must not be simulated by reusing Google credentials.

## For maintainers: create the project client

The client must belong to the VEYRA project, not to each user. Create it once, then inject it into release builds.

### 1. Create a Google Cloud project

1. Open the Google Cloud Console and create a project, for example `veyra-app`.
2. Keep it selected for the remaining steps.

### 2. Enable the APIs

In **APIs & Services → Library**, enable:

- **Gmail API**
- **Google Calendar API**

### 3. Configure the OAuth consent screen

1. Open **APIs & Services → OAuth consent screen**.
2. Choose **External**.
3. Set the app name (`VEYRA`), a support contact and a developer contact.
4. Add the scopes in the table below.
5. While testing, add test accounts under **Test users**. Testing mode is limited to 100 users and refresh tokens expire after 7 days.

### 4. Create the OAuth client

1. Open **APIs & Services → Credentials → Create credentials → OAuth client ID**.
2. Choose **Desktop app**.
3. Name it `VEYRA desktop` and create it.
4. Download the JSON only to inject it into the build; do not commit it.

Desktop clients use a loopback redirect, so no public HTTPS callback is required.

### 5. Scopes

| Scope | Purpose | Sensitivity |
| --- | --- | --- |
| `https://www.googleapis.com/auth/gmail.readonly` | Search and read mail | Restricted |
| `https://www.googleapis.com/auth/calendar.readonly` | Read events | Sensitive |
| `https://www.googleapis.com/auth/gmail.compose` | Create drafts | Restricted |
| `https://www.googleapis.com/auth/gmail.send` | Send mail | Restricted |
| `https://www.googleapis.com/auth/calendar.events` | Create events | Sensitive |

Request only the scopes the shipped tools use. Do not add Drive, Contacts or Tasks scopes until their tools exist; Google's scope-minimization policy expects the consent to match the functionality.

### 6. Inject the client at build time

Local development: set these in the environment used to start the backend (the shell or your launcher):

```dotenv
VEYRA_GOOGLE_CLIENT_ID=000000000000-example.apps.googleusercontent.com
VEYRA_GOOGLE_CLIENT_SECRET=example-not-a-real-secret
```

The values above are fake placeholders. Do not commit real values; `.env` and `backend/google_client.json` are git-ignored. Without them and without a local client file, the button reports that sign-in is not configured.

Release builds use repository secrets named `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET`. The Windows workflow writes `backend/google_client.json` from those secrets, then packages it into the PyInstaller sidecar with `--add-data`. The generated file is git-ignored and must never be committed. If either secret is missing, the release build fails instead of shipping a broken sign-in button.

The OAuth client is shared by all installs of the VEYRA build. It does not contain user tokens and does not grant access without each user's consent.

### 7. Verification and release limits

- **Gmail uses restricted scopes.** A public app that uses Gmail requires Google OAuth verification and an annual CASA security assessment. Budget for this before distributing broadly.
- **Calendar uses sensitive scopes.** Verification is required for public distribution as well.
- In **Testing** mode the app is limited to 100 users and refresh tokens expire after 7 days. Re-authenticate when VEYRA reports an expired token.
- An unverified app shows Google's "Google hasn't verified this app" warning. Users should continue only if they trust the build.
- Google may require a privacy policy, homepage and domain ownership verification during review.

## Security model

- The OAuth client and user refresh tokens are not in `config.json`; tokens are stored in Windows Credential Manager.
- The local backend binds to `127.0.0.1`, uses a per-run session token and never exposes the OAuth callback to the network.
- A Desktop client secret is extractable from any desktop binary; it identifies the application, not the user, and is not a substitute for user consent. Keeping it out of the repository and injecting it at build time avoids publishing it in source and CI logs.
- The generated `backend/google_client.json` and all `.env` files are git-ignored. Do not paste real values into issues, pull requests, screenshots or chat.

## Optional local fallbacks

### Gmail App Password

1. Enable **2-Step Verification** in the Google Account.
2. Open **Security → App passwords**, create one named `Veyra` and copy it.
3. In VEYRA, open **Settings → Accounts**, enter the Gmail address and app password, then choose **Save local Gmail**.

The app password is stored in Credential Manager and is never returned by the API. It supports IMAP search/read and SMTP send, but not drafts. Workspace administrators can disable app passwords; use Google sign-in in that case.

### Read-only Calendar iCal URL

1. In Google Calendar, open **Settings → Settings for my calendars**, select the calendar and open **Integrate calendar**.
2. Copy the **Secret address in iCal format**.
3. Paste it into **Settings → Accounts → Calendar secret iCal URL** and choose **Save calendar URL**.

The URL is a bearer secret stored in Credential Manager. VEYRA fetches it over HTTPS only, rejects redirects, limits the response size and never returns the URL from the API. It supports today and ranged reads, recurring events and exceptions, but cannot create or change events. Save an empty URL to remove it.

## Troubleshooting

| Symptom | Cause | Fix |
| --- | --- | --- |
| "Google sign-in is not configured in this build" | release secrets missing, or local environment not set | set `GOOGLE_CLIENT_ID`/`GOOGLE_CLIENT_SECRET` for the release, or the `VEYRA_*` values locally |
| `access_denied` during consent | account is not a test user while the consent screen is in Testing | add the account under **Test users**, or publish the app |
| `invalid_client` | wrong client type or wrong client values | recreate a **Desktop app** client and inject its values again |
| `redirect_uri_mismatch` | a Web client was used | use a Desktop client; the loopback port is chosen automatically |
| `insufficient permissions` | read-only sign-in, then a write action | enable write access and sign in again |
| Token stops working after a week | app is in Testing | sign in again, or complete verification and publish |
| Gmail tools use the wrong path | a local Gmail address is also configured | clear the local Gmail address/app password to force OAuth, or keep the local path intentionally |
| Calendar create fails | only the read-only iCal URL is configured | connect Google with write access; iCal cannot write |
| `quota exceeded` | shared or heavily used Google Cloud project | use the VEYRA project's quota responsibly, or request an increase |

## Never do this

- Do not commit a client JSON, client secret, refresh token, app password, secret iCal URL or screenshot containing one.
- Do not paste credentials into issues, pull requests or chat.
- Do not disable OAuth security settings to make the flow simpler.
- Do not automate Google session cookies or use an unofficial Gmail/Calendar client.
- Do not request scopes that no shipped tool uses.
