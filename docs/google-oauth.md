# Creating your own Google credentials

> **Status:** the Gmail and Calendar tools are implemented; they stay disabled until a user connects an account. VEYRA never ships a Google OAuth client: every user creates their own, so no client secret lives in this repository.

## Why you need to do this yourself

Google requires an OAuth client for any application that reads Gmail or Calendar data. Shipping a shared client would mean publishing a secret that identifies the project, and every install would share quotas and consent status. A personal client keeps your data under your own Google Cloud project and your own control.

The free tier is enough for personal use.

## Step 1 — Create a Google Cloud project

1. Open the Google Cloud Console and create a new project, for example `veyra-personal`.
2. Keep it selected for the rest of these steps.

## Step 2 — Enable the APIs

In **APIs & Services → Library**, enable:

- **Gmail API**
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
| `https://www.googleapis.com/auth/gmail.readonly` | search and read mail | read-only default |
| `https://www.googleapis.com/auth/calendar.readonly` | list today's and ranged events | read-only default |
| `https://www.googleapis.com/auth/gmail.compose` | create drafts | only if you enable drafts |
| `https://www.googleapis.com/auth/gmail.send` | send mail | optional, write access |
| `https://www.googleapis.com/auth/calendar.events` | create events | optional, write access |

Start with the two read-only scopes. Write scopes are unnecessary for reading and can be added later.

## Step 4 — Create the OAuth client

1. Open **APIs & Services → Credentials → Create credentials → OAuth client ID**.
2. Application type: **Desktop app**.
3. Name it `Veyra desktop`.
4. Create it, then download the JSON file.

Desktop clients use a loopback redirect, which is why VEYRA can complete the flow on `127.0.0.1` with a random port without a public HTTPS endpoint. Do not create a Web application client.

## Step 5 — Import the client into VEYRA

1. Open **Settings → Accounts → Google**.
2. Choose **Import client JSON** and select the file you downloaded.
3. VEYRA stores the client ID in its configuration and the client secret plus refresh token in **Windows Credential Manager**. The JSON file itself is copied into `%APPDATA%\Veyra\credentials\` with access limited to your Windows account, and it is never committed to the project.
4. Choose **Sign in** and complete the Google consent screen in your browser.
5. Grant the read-only scopes first. Write permissions are requested separately if you enable them.

## Notes and limitations

- **Testing mode refresh tokens expire after 7 days.** Google invalidates refresh tokens for external apps that are still in Testing. You will need to sign in again, or publish the app (which requires Google verification for sensitive scopes). For personal use the simplest option is to re-authorize when VEYRA reports an expired token.
- Unverified apps show a “Google hasn't verified this app” warning. Continue only because you created the client yourself.
- You can revoke access at any time from your Google account's third-party access page. Deleting the VEYRA entry there invalidates the stored token immediately.
- VEYRA requests no profile or drive scopes, and it does not upload mail content anywhere unless you explicitly send a request to an online model.
- Read-only mode is the default. `bozza_mail` is `SAFE`, while `invia_mail` and `crea_evento` are `CONFIRM` and require write scopes.

## Troubleshooting

| Symptom | Cause | Fix |
| --- | --- | --- |
| `access_denied` during consent | account not in Test users | add it under OAuth consent screen |
| `invalid_client` | wrong client type or imported file | recreate as a Desktop app client |
| Token expires weekly | app in Testing mode | re-authorize, or publish the app |
| `insufficient permissions` | write scope missing | re-run consent with the scope enabled |
| Redirect mismatch | Web client used instead of Desktop | create a Desktop client |
| `quota exceeded` | shared or heavily used project | create a dedicated project for VEYRA |

## Never do this

- Do not commit the downloaded JSON, a client secret, a refresh token or a screenshot containing them.
- Do not paste credentials into issues, pull requests or chat.
- Do not disable OAuth security settings to make the flow “simpler”.
