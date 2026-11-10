# Proactive mode

VEYRA can speak first after a period without interaction. It is an optional,
local-only check-in, not an always-listening assistant.

## Enable it

1. Open **Settings → Proactive mode**.
2. Enable **Let VEYRA speak first**.
3. Choose the idle interval, from 5 to 240 minutes. The default is 30 minutes.
4. Save the settings.

The setting is off by default. VEYRA only starts a check-in after a real
conversation exists; it does not greet an empty session.

## What it can do

- After the idle interval, VEYRA asks the **local model** for one short
  sentence based on the recent conversation and the current local time.
- If the model has nothing genuinely useful to say, it replies `[SILENT]` and
  nothing is shown or spoken.
- The message appears in the normal chat transcript and is spoken only when
  **Speak answers aloud** is enabled.
- When a timer or alarm expires, VEYRA shows the normal reminder and also
  speaks it aloud if voice replies are enabled.

## What it cannot do

Proactive turns are deliberately restricted:

- no tool calls, including files, apps or custom APIs;
- no external model or network request;
- no microphone recording and no background listening;
- no automatic action, confirmation dialog or change to the computer;
- no reading of files or external services. It only sees the recent local chat
  history.

A proactive message cannot claim that VEYRA checked an external service. The
prompt says this explicitly, and the mode receives no tool schemas.

## Privacy and control

- The mode uses the local model through the bundled runtime. If it is unavailable, the check-in
  is skipped silently.
- Chat history stays in the local SQLite database; it is not sent anywhere by
  proactive mode.
- Turn the setting off at any time. The next session stops scheduling
  check-ins; an in-flight check-in is cancelled when the user sends a message
  or starts listening.
- The interval is a minimum idle time, not a guarantee that VEYRA will speak.
  The model is allowed to stay silent.

## Limits

This is a first, safe step towards a film-style assistant. It does not make
VEYRA omnipresent: it does not listen continuously, monitor the screen, or
act on its own. Those capabilities would need separate permissions and
security review. For now, proactive mode only starts a brief conversation and
announces due timers.
