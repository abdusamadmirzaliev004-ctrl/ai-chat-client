"""
AI Chat Client - Kivy Android App
GitHub Copilot powered chat using device auth flow.
"""
import os
import json
import time
import threading
from urllib import request as urlrequest
from urllib import error as urlerror

from kivy.app import App
from kivy.clock import Clock, mainthread
from kivy.core.window import Window
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.scrollview import ScrollView
from kivy.uix.spinner import Spinner
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.graphics import Color, Rectangle, RoundedRectangle
from kivy.properties import StringProperty, ListProperty
from kivy.metrics import dp


# ---------- Theme ----------
BG          = (0x08/255, 0x0a/255, 0x0f/255, 1)
ACCENT      = (0x00/255, 0xd4/255, 0xff/255, 1)
USER_BUBBLE = (0x10/255, 0x2a/255, 0x3a/255, 1)
AI_BUBBLE   = (0x14/255, 0x18/255, 0x22/255, 1)
TEXT_FG     = (0.92, 0.95, 0.98, 1)
MUTED       = (0.55, 0.62, 0.72, 1)
TOPBAR      = (0x0c/255, 0x10/255, 0x18/255, 1)

MODELS = [
    "claude-opus-4.7",
    "claude-sonnet-4.6",
    "gpt-5.5",
    "gpt-5.4",
    "gemini-3.1-pro-preview",
]

# GitHub Copilot client_id (the same one used by the official VS Code Copilot extension)
GITHUB_CLIENT_ID = "Iv1.b507a08c87ecfe98"
DEVICE_CODE_URL  = "https://github.com/login/device/code"
ACCESS_TOKEN_URL = "https://github.com/login/oauth/access_token"
COPILOT_TOKEN_URL = "https://api.github.com/copilot_internal/v2/token"
COMPLETIONS_URL  = "https://api.githubcopilot.com/chat/completions"

APP_DIR = os.path.expanduser("~/.ai_chat_client")
os.makedirs(APP_DIR, exist_ok=True)
TOKEN_FILE   = os.path.join(APP_DIR, "token.json")
HISTORY_FILE = os.path.join(APP_DIR, "history.json")


# ---------- HTTP helpers (stdlib only, no external deps) ----------
def http_post_json(url, data, headers=None, timeout=30):
    body = json.dumps(data).encode("utf-8")
    h = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "User-Agent": "AIChatClient/1.0",
    }
    if headers:
        h.update(headers)
    req = urlrequest.Request(url, data=body, headers=h, method="POST")
    try:
        with urlrequest.urlopen(req, timeout=timeout) as r:
            raw = r.read().decode("utf-8", "replace")
            try:
                return r.status, json.loads(raw)
            except Exception:
                return r.status, {"_raw": raw}
    except urlerror.HTTPError as e:
        raw = e.read().decode("utf-8", "replace")
        try:
            return e.code, json.loads(raw)
        except Exception:
            return e.code, {"_raw": raw, "error": str(e)}
    except Exception as e:
        return 0, {"error": str(e)}


def http_post_form(url, data, headers=None, timeout=30):
    from urllib.parse import urlencode
    body = urlencode(data).encode("utf-8")
    h = {
        "Accept": "application/json",
        "Content-Type": "application/x-www-form-urlencoded",
        "User-Agent": "AIChatClient/1.0",
    }
    if headers:
        h.update(headers)
    req = urlrequest.Request(url, data=body, headers=h, method="POST")
    try:
        with urlrequest.urlopen(req, timeout=timeout) as r:
            raw = r.read().decode("utf-8", "replace")
            try:
                return r.status, json.loads(raw)
            except Exception:
                return r.status, {"_raw": raw}
    except urlerror.HTTPError as e:
        raw = e.read().decode("utf-8", "replace")
        try:
            return e.code, json.loads(raw)
        except Exception:
            return e.code, {"_raw": raw}
    except Exception as e:
        return 0, {"error": str(e)}


def http_get(url, headers=None, timeout=30):
    h = {"User-Agent": "AIChatClient/1.0", "Accept": "application/json"}
    if headers:
        h.update(headers)
    req = urlrequest.Request(url, headers=h, method="GET")
    try:
        with urlrequest.urlopen(req, timeout=timeout) as r:
            raw = r.read().decode("utf-8", "replace")
            try:
                return r.status, json.loads(raw)
            except Exception:
                return r.status, {"_raw": raw}
    except urlerror.HTTPError as e:
        raw = e.read().decode("utf-8", "replace")
        try:
            return e.code, json.loads(raw)
        except Exception:
            return e.code, {"_raw": raw}
    except Exception as e:
        return 0, {"error": str(e)}


# ---------- Token storage ----------
def save_gh_token(token):
    with open(TOKEN_FILE, "w") as f:
        json.dump({"github_token": token}, f)
    try:
        os.chmod(TOKEN_FILE, 0o600)
    except Exception:
        pass


def load_gh_token():
    if not os.path.exists(TOKEN_FILE):
        return None
    try:
        with open(TOKEN_FILE) as f:
            return json.load(f).get("github_token")
    except Exception:
        return None


def load_history():
    if not os.path.exists(HISTORY_FILE):
        return []
    try:
        with open(HISTORY_FILE) as f:
            return json.load(f)
    except Exception:
        return []


def save_history(msgs):
    try:
        with open(HISTORY_FILE, "w") as f:
            json.dump(msgs, f, indent=2)
    except Exception:
        pass


# ---------- Copilot token cache ----------
class CopilotSession:
    """Exchanges a GitHub OAuth token for a short-lived Copilot bearer."""
    def __init__(self, gh_token):
        self.gh_token = gh_token
        self.cp_token = None
        self.cp_expires = 0

    def get_token(self):
        now = int(time.time())
        if self.cp_token and now < self.cp_expires - 60:
            return self.cp_token
        status, data = http_get(COPILOT_TOKEN_URL, headers={
            "Authorization": f"token {self.gh_token}",
            "Editor-Version": "vscode/1.95.0",
            "Editor-Plugin-Version": "copilot-chat/0.22.0",
        })
        if status == 200 and "token" in data:
            self.cp_token = data["token"]
            self.cp_expires = int(data.get("expires_at", now + 1500))
            return self.cp_token
        raise RuntimeError(f"Copilot token exchange failed: {status} {data}")


# ---------- UI primitives ----------
class BgBox(BoxLayout):
    bg_color = ListProperty(BG)
    radius = ListProperty([0, 0, 0, 0])

    def __init__(self, **kw):
        super().__init__(**kw)
        with self.canvas.before:
            self._col = Color(*self.bg_color)
            self._rect = RoundedRectangle(pos=self.pos, size=self.size, radius=self.radius)
        self.bind(pos=self._sync, size=self._sync, bg_color=self._sync_color, radius=self._sync_radius)

    def _sync(self, *a):
        self._rect.pos = self.pos
        self._rect.size = self.size

    def _sync_color(self, *a):
        self._col.rgba = self.bg_color

    def _sync_radius(self, *a):
        self._rect.radius = self.radius


class ChatBubble(BgBox):
    def __init__(self, text, role="user", **kw):
        is_user = (role == "user")
        kw.setdefault("orientation", "vertical")
        kw.setdefault("padding", [dp(12), dp(8), dp(12), dp(8)])
        kw.setdefault("size_hint_y", None)
        kw.setdefault("size_hint_x", 0.88)
        super().__init__(**kw)
        self.bg_color = USER_BUBBLE if is_user else AI_BUBBLE
        self.radius = [dp(12)] * 4
        font_name = "RobotoMono-Regular" if not is_user else "Roboto"
        # Try monospace for AI; fall back gracefully if unavailable
        lbl = Label(
            text=text,
            color=TEXT_FG,
            halign="left",
            valign="top",
            markup=False,
            size_hint_y=None,
            font_size="14sp",
        )
        # Set monospace font for AI; ignore if font missing
        if not is_user:
            try:
                lbl.font_name = "RobotoMono-Regular"
            except Exception:
                pass
        self.lbl = lbl
        self.add_widget(lbl)
        self.bind(width=self._on_width)
        lbl.bind(texture_size=self._on_tex)

    def _on_width(self, *_):
        self.lbl.text_size = (self.width - dp(24), None)

    def _on_tex(self, *_):
        self.lbl.height = self.lbl.texture_size[1]
        self.height = self.lbl.height + dp(16)


class BubbleRow(BoxLayout):
    def __init__(self, bubble, role="user", **kw):
        super().__init__(orientation="horizontal", size_hint_y=None,
                         padding=[dp(8), dp(4), dp(8), dp(4)], **kw)
        if role == "user":
            self.add_widget(BoxLayout(size_hint_x=0.12))
            self.add_widget(bubble)
        else:
            self.add_widget(bubble)
            self.add_widget(BoxLayout(size_hint_x=0.12))
        bubble.bind(height=self._sync_h)
        Clock.schedule_once(lambda *_: self._sync_h(), 0)

    def _sync_h(self, *_):
        self.height = max(c.height for c in self.children) + dp(8)


# ---------- Auth screen ----------
class AuthScreen(Screen):
    status_text = StringProperty("Sign in with GitHub to begin.")
    code_text   = StringProperty("")
    url_text    = StringProperty("")

    def __init__(self, **kw):
        super().__init__(**kw)
        root = BgBox(orientation="vertical", padding=dp(20), spacing=dp(14))
        root.bg_color = BG

        title = Label(text="AI Chat Client", color=ACCENT,
                      font_size="26sp", bold=True, size_hint_y=None, height=dp(50))
        sub = Label(text="GitHub Copilot Chat", color=MUTED,
                    font_size="14sp", size_hint_y=None, height=dp(24))

        self.status_lbl = Label(text=self.status_text, color=TEXT_FG,
                                font_size="14sp", size_hint_y=None, height=dp(40),
                                halign="center", valign="middle")
        self.status_lbl.bind(size=lambda i, v: setattr(i, "text_size", v))

        self.code_lbl = Label(text="", color=ACCENT, font_size="34sp", bold=True,
                              size_hint_y=None, height=dp(70))
        self.url_lbl = Label(text="", color=TEXT_FG, font_size="16sp",
                             size_hint_y=None, height=dp(40))

        self.btn = Button(text="Start GitHub Login", size_hint_y=None,
                          height=dp(56), background_normal="",
                          background_color=ACCENT, color=(0, 0, 0, 1),
                          font_size="16sp", bold=True)
        self.btn.bind(on_release=self.start_auth)

        self.copy_btn = Button(text="Copy Code", size_hint_y=None, height=dp(44),
                               background_normal="", background_color=(0.1, 0.15, 0.2, 1),
                               color=ACCENT, font_size="14sp", disabled=True)
        self.copy_btn.bind(on_release=self.copy_code)

        root.add_widget(title)
        root.add_widget(sub)
        root.add_widget(BoxLayout(size_hint_y=None, height=dp(20)))
        root.add_widget(self.status_lbl)
        root.add_widget(self.code_lbl)
        root.add_widget(self.url_lbl)
        root.add_widget(self.copy_btn)
        root.add_widget(BoxLayout())
        root.add_widget(self.btn)
        self.add_widget(root)

    def copy_code(self, *_):
        try:
            from kivy.core.clipboard import Clipboard
            Clipboard.copy(self.code_lbl.text)
            self.status_lbl.text = "Code copied to clipboard."
        except Exception:
            pass

    def start_auth(self, *_):
        self.btn.disabled = True
        self.btn.text = "Waiting for authorization..."
        self.status_lbl.text = "Requesting device code..."
        threading.Thread(target=self._auth_worker, daemon=True).start()

    @mainthread
    def _set_codes(self, code, url, msg):
        self.code_lbl.text = code
        self.url_lbl.text = url
        self.status_lbl.text = msg
        self.copy_btn.disabled = False

    @mainthread
    def _set_status(self, msg):
        self.status_lbl.text = msg

    @mainthread
    def _on_success(self, token):
        save_gh_token(token)
        app = App.get_running_app()
        app.gh_token = token
        app.copilot = CopilotSession(token)
        self.status_lbl.text = "Authorized. Loading chat..."
        Clock.schedule_once(lambda *_: setattr(app.sm, "current", "chat"), 0.4)

    @mainthread
    def _on_fail(self, msg):
        self.status_lbl.text = "Failed: " + msg
        self.btn.disabled = False
        self.btn.text = "Retry GitHub Login"

    def _auth_worker(self):
        status, data = http_post_form(DEVICE_CODE_URL, {
            "client_id": GITHUB_CLIENT_ID,
            "scope": "read:user",
        })
        if status != 200 or "device_code" not in data:
            self._on_fail(f"device code request: {status} {data}")
            return
        device_code = data["device_code"]
        user_code   = data["user_code"]
        verify_url  = data.get("verification_uri", "https://github.com/login/device")
        interval    = int(data.get("interval", 5))
        expires_in  = int(data.get("expires_in", 900))

        self._set_codes(user_code, verify_url,
                        f"Open the URL on any device, enter the code, and approve.")

        deadline = time.time() + expires_in
        while time.time() < deadline:
            time.sleep(interval)
            s, d = http_post_form(ACCESS_TOKEN_URL, {
                "client_id": GITHUB_CLIENT_ID,
                "device_code": device_code,
                "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
            })
            if s == 200 and "access_token" in d:
                self._on_success(d["access_token"])
                return
            err = d.get("error") if isinstance(d, dict) else None
            if err == "authorization_pending":
                continue
            if err == "slow_down":
                interval += 5
                continue
            if err in ("expired_token", "access_denied"):
                self._on_fail(err)
                return
            # Unknown error — keep polling but surface message
            if err:
                self._set_status(f"Polling... ({err})")
        self._on_fail("device code expired")


# ---------- Chat screen ----------
class ChatScreen(Screen):
    def __init__(self, **kw):
        super().__init__(**kw)
        self.current_model = MODELS[0]
        self.messages = load_history()  # [{"role":"user"/"assistant","content":...}]
        self.busy = False

        root = BgBox(orientation="vertical")
        root.bg_color = BG

        # Top bar
        topbar = BgBox(orientation="horizontal", size_hint_y=None, height=dp(56),
                       padding=[dp(12), dp(6), dp(12), dp(6)], spacing=dp(8))
        topbar.bg_color = TOPBAR
        title = Label(text="AI Chat", color=ACCENT, font_size="18sp",
                      bold=True, size_hint_x=None, width=dp(110), halign="left",
                      valign="middle")
        title.bind(size=lambda i, v: setattr(i, "text_size", v))
        self.spinner = Spinner(
            text=self.current_model, values=MODELS,
            size_hint_x=1, background_normal="",
            background_color=(0.08, 0.12, 0.18, 1), color=TEXT_FG,
            font_size="13sp",
        )
        self.spinner.bind(text=self._on_model_change)
        clear_btn = Button(text="Clear", size_hint_x=None, width=dp(70),
                           background_normal="", background_color=(0.15, 0.1, 0.12, 1),
                           color=(1, 0.6, 0.6, 1), font_size="13sp")
        clear_btn.bind(on_release=self.clear_chat)
        topbar.add_widget(title)
        topbar.add_widget(self.spinner)
        topbar.add_widget(clear_btn)

        # Chat scroll
        self.scroll = ScrollView(size_hint=(1, 1), bar_width=dp(3),
                                 bar_color=ACCENT, bar_inactive_color=(0, 0.5, 0.7, 0.4))
        self.chat_box = BoxLayout(orientation="vertical", size_hint_y=None,
                                  spacing=dp(4), padding=[0, dp(8), 0, dp(8)])
        self.chat_box.bind(minimum_height=self.chat_box.setter("height"))
        self.scroll.add_widget(self.chat_box)

        # Input bar
        inputbar = BgBox(orientation="horizontal", size_hint_y=None, height=dp(64),
                         padding=[dp(8), dp(8), dp(8), dp(8)], spacing=dp(6))
        inputbar.bg_color = TOPBAR
        self.input = TextInput(
            hint_text="Type a message...",
            multiline=False,
            background_color=(0.06, 0.09, 0.13, 1),
            foreground_color=TEXT_FG,
            cursor_color=ACCENT,
            hint_text_color=MUTED,
            font_size="15sp",
            padding=[dp(10), dp(12), dp(10), dp(10)],
        )
        self.input.bind(on_text_validate=self._on_send)
        self.send_btn = Button(text="Send", size_hint_x=None, width=dp(80),
                               background_normal="", background_color=ACCENT,
                               color=(0, 0, 0, 1), bold=True, font_size="15sp")
        self.send_btn.bind(on_release=self._on_send)
        inputbar.add_widget(self.input)
        inputbar.add_widget(self.send_btn)

        root.add_widget(topbar)
        root.add_widget(self.scroll)
        root.add_widget(inputbar)
        self.add_widget(root)

        # Render any saved history
        for m in self.messages:
            self._add_bubble(m.get("content", ""), m.get("role", "user"))

    def _on_model_change(self, _spin, value):
        self.current_model = value

    def clear_chat(self, *_):
        self.messages = []
        save_history(self.messages)
        self.chat_box.clear_widgets()

    def _add_bubble(self, text, role):
        bubble = ChatBubble(text=text, role=role)
        row = BubbleRow(bubble, role=role)
        self.chat_box.add_widget(row)
        Clock.schedule_once(lambda *_: setattr(self.scroll, "scroll_y", 0), 0.05)
        return bubble

    def _on_send(self, *_):
        if self.busy:
            return
        text = self.input.text.strip()
        if not text:
            return
        self.input.text = ""
        self.messages.append({"role": "user", "content": text})
        save_history(self.messages)
        self._add_bubble(text, "user")

        # Add placeholder AI bubble
        ai_bubble = self._add_bubble("…", "assistant")
        self.busy = True
        self.send_btn.disabled = True
        threading.Thread(
            target=self._chat_worker,
            args=(list(self.messages), self.current_model, ai_bubble),
            daemon=True,
        ).start()

    @mainthread
    def _update_bubble(self, bubble, text):
        bubble.lbl.text = text
        bubble._on_width()

    @mainthread
    def _finish(self, bubble, text, ok):
        bubble.lbl.text = text
        bubble._on_width()
        if ok:
            self.messages.append({"role": "assistant", "content": text})
            save_history(self.messages)
        self.busy = False
        self.send_btn.disabled = False
        Clock.schedule_once(lambda *_: setattr(self.scroll, "scroll_y", 0), 0.1)

    def _chat_worker(self, msgs, model, bubble):
        app = App.get_running_app()
        try:
            cp_token = app.copilot.get_token()
        except Exception as e:
            self._finish(bubble, f"[auth error] {e}", False)
            return

        # Build OpenAI-compatible payload
        payload = {
            "model": model,
            "messages": msgs,
            "stream": True,
            "temperature": 0.7,
            "n": 1,
        }
        body = json.dumps(payload).encode("utf-8")
        headers = {
            "Authorization": f"Bearer {cp_token}",
            "Content-Type": "application/json",
            "Accept": "text/event-stream",
            "User-Agent": "AIChatClient/1.0",
            "Editor-Version": "vscode/1.95.0",
            "Editor-Plugin-Version": "copilot-chat/0.22.0",
            "Copilot-Integration-Id": "vscode-chat",
            "Openai-Intent": "conversation-panel",
        }
        req = urlrequest.Request(COMPLETIONS_URL, data=body, headers=headers, method="POST")
        try:
            resp = urlrequest.urlopen(req, timeout=120)
        except urlerror.HTTPError as e:
            raw = e.read().decode("utf-8", "replace")
            self._finish(bubble, f"[http {e.code}] {raw[:500]}", False)
            return
        except Exception as e:
            self._finish(bubble, f"[network error] {e}", False)
            return

        ctype = resp.headers.get("Content-Type", "")
        accumulated = ""

        if "text/event-stream" in ctype or "stream" in ctype:
            # SSE streaming parse
            buf = b""
            try:
                while True:
                    chunk = resp.read(1024)
                    if not chunk:
                        break
                    buf += chunk
                    while b"\n" in buf:
                        line, buf = buf.split(b"\n", 1)
                        line = line.strip()
                        if not line or not line.startswith(b"data:"):
                            continue
                        data = line[5:].strip()
                        if data == b"[DONE]":
                            break
                        try:
                            obj = json.loads(data.decode("utf-8", "replace"))
                        except Exception:
                            continue
                        try:
                            delta = obj["choices"][0].get("delta", {})
                            piece = delta.get("content") or ""
                            if piece:
                                accumulated += piece
                                self._update_bubble(bubble, accumulated)
                        except Exception:
                            pass
            except Exception as e:
                if not accumulated:
                    self._finish(bubble, f"[stream error] {e}", False)
                    return
        else:
            try:
                raw = resp.read().decode("utf-8", "replace")
                obj = json.loads(raw)
                accumulated = obj["choices"][0]["message"]["content"]
            except Exception as e:
                self._finish(bubble, f"[parse error] {e}", False)
                return

        if not accumulated:
            accumulated = "[empty response]"
        self._finish(bubble, accumulated, True)


# ---------- App ----------
class AIChatApp(App):
    title = "AI Chat Client"

    def build(self):
        Window.clearcolor = BG
        self.gh_token = load_gh_token()
        self.copilot = CopilotSession(self.gh_token) if self.gh_token else None

        self.sm = ScreenManager()
        self.sm.add_widget(AuthScreen(name="auth"))
        self.sm.add_widget(ChatScreen(name="chat"))
        self.sm.current = "chat" if self.gh_token else "auth"
        return self.sm


if __name__ == "__main__":
    AIChatApp().run()
