# AI Chat Client

A Kivy Android app that chats with GitHub Copilot models. GitHub
device-flow auth, streaming responses, dark theme, persistent history.

## Files
    main.py                          Full Kivy app
    buildozer.spec                   Android build config (API 33, arm64-v8a)
    .github/workflows/build-apk.yml  GitHub Actions build pipeline
    INSTALL.txt                      Manual Termux build notes (alternative)

## Build the APK with GitHub Actions (recommended)

1. Create a new GitHub repo (private or public).
2. Push this directory to it:

       cd ~/ai-chat-client
       git init -b main
       git add .
       git commit -m "Initial AI Chat Client"
       git remote add origin git@github.com:<you>/<repo>.git
       git push -u origin main

3. Open the repo on github.com → **Actions** tab. The workflow
   "Build Android APK" runs automatically on every push, and can also
   be triggered manually via **Run workflow**.

4. When the run finishes (~15-25 min on the first build, ~5 min after
   caches warm up), open the run and download the
   `aichatclient-debug-apk` artifact from the bottom of the page.

5. Unzip and sideload the APK on your phone.

To attach the APK directly to a GitHub Release, just publish a release
on the repo — the workflow uploads `bin/*.apk` as a release asset.

## Auth flow inside the app

- First launch shows the GitHub device-auth screen.
- Tap **Start GitHub Login** → an 8-character user code appears.
- On any device open https://github.com/login/device, enter the code,
  approve.
- The app polls GitHub, saves the token to
  `~/.ai_chat_client/token.json` (chmod 600 on Linux), then opens the
  chat screen.
- Chat history persists in `~/.ai_chat_client/history.json`.
- Switch models via the spinner in the top bar.

## Models

The 5 model strings in `MODELS` (top of `main.py`) are sent verbatim as
the OpenAI `model` field. If your Copilot account doesn't have access to
one of them you'll get a 400 — swap the string for one you do have
(`gpt-4o`, `claude-3.5-sonnet`, etc.).
