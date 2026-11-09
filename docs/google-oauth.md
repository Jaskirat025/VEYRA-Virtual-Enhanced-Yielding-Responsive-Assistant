# Google access: Gmail locally, Calendar with OAuth

> **Status:** Gmail can use a Google App Password over IMAP/SMTP, with no OAuth client. Calendar and Gmail drafts still require an OAuth client. VEYRA never ships shared Google credentials; every user connects their own account.

## Gmail without OAuth

Google requires an explicit credential for mail access; an account name alone is not enough. For Gmail, VEYRA supports an App Password:

1. Open your Google Account security settings and enable **2-Step Verification**. App passwords are unavailable without it.
2. Open **Security → App passwords**, create one named `Veyra`, and copy the generated value.
3. In VEYRA, open **Settings → Accounts**.
4. Enter your Gmail address and the app password in the local Gmail fields, then choose **Save local Gmail**.
5. Send a test request such as “search my latest mail”. VEYRA uses IMAP and SMTP directly.

The app password is stored in **Windows Credential Manager**, not in `config.json`, and is never returned by the API. It is separate from your normal Google password; revoke it from the same Google page if you stop using VEYRA.

This local path supports:

- searching Gmail with Gmail's IMAP query syntax;
- reading a message by the id returned by search;
- sending plain-text mail, after the read-only setting is disabled and the action is confirmed.

It does **not** support Gmail drafts or Google Calendar. Those use OAuth, described below. If your Google Workspace administrator has disabled app passwords, use OAuth instead.

## Why Calendar and drafts need OAuth

Calendar data is not available through the Gmail app-password path. Draft creation is also outside the local IMAP flow. Both need a Google OAuth client that belongs to the user, so no shared secret is shipped in this repository.

The free tier is enough for personal use.

## Step 1 — Create a Google Cloud project

1. Open the Google Cloud Console and create a new project, for example `veyra-personal`.
2. Keep it selected for the rest of these steps.

## Step 2 — Enable the APIs

In **APIs & Services → Library**, enable:

- **Gmail API** (for OAuth Gmail drafts)
- **Google Calendar API**

Both are free at personal volumes.

## Step 3 — Configure the OAuth consent screen

1. Open **APIs & Services → OAuth consent screen**.
2. Choose **External** as the user type.
3. Fill in the app name (`Veyra`), your own support contact, and the developer contact. These are your details, not the project's.
4. Leave the app in **Testing** mode and add your own Google account under **Test users**. Testing mode is sufficient for personal use.
5. Add only the scopes VEYRA needs:

| Scope | Purpose | When |
| --- | --- | --- |
| `https://www.googleapis.com/auth/gmail.readonly` | search and read mail through OAuth | optional if local Gmail is used |
| `https://www.googleapis.com/auth/calendar.readonly` | list today's and ranged events | Calendar read-only |
| `https://www.googleapis.com/auth/gmail.compose` | create drafts | only if you enable drafts |
| `https://www.googleapis.com/auth/gmail.send` | send mail through OAuth | optional, write access |
| `https://www.googleapis.com/auth/calendar.events` | create events | optional, write access |

Start with the read-only scopes. Write scopes are unnecessary for reading and can be added later.

## Step 4 — Create the OAuth client

1. Open **APIs & Services → Credentials → Create credentials → OAuth client ID**.
2. Application type: **Desktop app**.
3. Name it `Veyra desktop`.
4. Create it, then download the JSON file.

Desktop clients use a loopback redirect, which is why VEYRA can complete the flow on `127.0.0.1` with a random port without a public HTTPS endpoint. Do not create a Web application client.

## Step 5 — Import the OAuth client into VEYRA

1. Open **Settings → Accounts → Google OAuth**.
2. Paste the downloaded client JSON and choose **Connect Google**.
3. VEYRA stores the client secret plus refresh token in **Windows Credential Manager**. The JSON file itself is never committed to the project.
4. Choose **Sign in** and complete the Google consent screen in your browser.
5. Grant the read-only scopes first. Write permissions are requested separately if you enable them.

Local Gmail and OAuth Gmail can coexist. When a local Gmail address and app password are configured, Gmail tools use the local path; Calendar and drafts still use OAuth.

## Notes and limitations

- **Testing mode refresh tokens expire after 7 days.** Google invalidates refresh tokens for external apps that are still in Testing. You will need to sign in again, or publish the app (which requires Google verification for sensitive scopes). For personal use the simplest option is to re-authorize when VEYRA reports an expired token.
- Unverified apps show a “Google hasn't verified this app” warning. Continue only because you created the client yourself.
- You can revoke access at any time from your Google account's third-party access page. Deleting the VEYRA entry there invalidates the stored token immediately.
- VEYRA requests no profile or drive scopes, and it does not upload mail content anywhere unless you explicitly send a request to an online model.
- Read-only mode is the default. `bozza_mail` is `SAFE` in the tool registry but still requires write access, while `invia_mail` and `crea_evento` are `CONFIRM`.

## Troubleshooting

| Symptom | Cause | Fix |
| --- | --- | --- |
| `access_denied` during consent | account not in Test users | add it under OAuth consent screen |
| `invalid_client` | wrong client type or imported file | recreate as a Desktop app client |
| Token expires weekly | app in Testing mode | re-authorize, or publish the app |
| `insufficient permissions` | write scope missing | re-run consent with the scope enabled |
| Redirect mismatch | Web client used instead of Desktop | create a Desktop client |
| `quota exceeded` | shared or heavily used project | create a dedicated project for VEYRA |
| App password rejected | 2-Step Verification or Workspace policy | enable 2-Step Verification, or use OAuth |
| Gmail login failed | wrong address or revoked app password | regenerate the app password in Google Account |

## Never do this

- Do not commit the downloaded JSON, a client secret, a refresh token, an app password or a screenshot containing them.
- Do not paste credentials into issues, pull requests or chat.
- Do not disable OAuth security settings to make the flow “simpler”.
- Do not use unofficial WhatsApp, Gmail or Google session-cookie automation.
