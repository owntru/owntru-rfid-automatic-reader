from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.scrollview import ScrollView
from kivy.clock import mainthread
from kivy.core.window import Window
import threading
import urllib.request
import json
import time
import traceback

from jnius import autoclass, cast
from android import activity

PythonActivity = autoclass('org.kivy.android.PythonActivity')
NfcAdapter = autoclass('android.nfc.NfcAdapter')
PendingIntent = autoclass('android.app.PendingIntent')
Intent = autoclass('android.content.Intent')
Tag = autoclass('android.nfc.Tag')

DEFAULT_URL = "http://192.168.1.42:5005"  # <-- change to your laptop's IP


class NFCApp(App):
    def build(self):
        self.status_label = Label(text="Ready. Tap a card to scan.", font_size=20,
                                   size_hint_y=None, height=50)
        self.ip_input = TextInput(text=DEFAULT_URL, multiline=False,
                                   size_hint_y=None, height=50)

        self.log_label = Label(text="", font_size=13, size_hint_y=None,
                                halign="left", valign="top")
        self.log_label.bind(width=lambda *_: self.log_label.setter('text_size')(
            self.log_label, (self.log_label.width, None)))
        self.log_label.bind(texture_size=lambda *_: setattr(
            self.log_label, 'height', self.log_label.texture_size[1]))

        self.scroll = ScrollView(size_hint=(1, 1))
        self.scroll.add_widget(self.log_label)

        layout = BoxLayout(orientation='vertical', padding=15, spacing=10)
        layout.add_widget(Label(text="Laptop address:", size_hint_y=None, height=25))
        layout.add_widget(self.ip_input)
        layout.add_widget(self.status_label)
        layout.add_widget(Label(text="Debug log:", size_hint_y=None, height=25))
        layout.add_widget(self.scroll)

        self.log_lines = []
        return layout

    def log(self, msg):
        timestamp = time.strftime('%H:%M:%S')
        line = f"[{timestamp}] {msg}"
        print(line)  # also visible in adb logcat if connected
        self.log_lines.append(line)
        # keep last 200 lines so it doesn't grow forever
        self.log_lines = self.log_lines[-200:]
        self._refresh_log()

    @mainthread
    def _refresh_log(self):
        self.log_label.text = "\n".join(self.log_lines)
        # auto-scroll to bottom
        self.scroll.scroll_y = 0

    def on_start(self):
        self.log("App started.")
        try:
            activity.bind(on_new_intent=self.on_new_intent)
            self.log("Bound on_new_intent listener.")
        except Exception as e:
            self.log(f"ERROR binding on_new_intent: {e}")
        self.enable_nfc_dispatch()

    def on_resume(self):
        self.log("App resumed, re-enabling NFC dispatch.")
        self.enable_nfc_dispatch()

    def on_pause(self):
        self.log("App paused.")
        return True

    def enable_nfc_dispatch(self):
        try:
            current_activity = PythonActivity.mActivity
            nfc_adapter = NfcAdapter.getDefaultAdapter(current_activity)
            if nfc_adapter is None:
                self.log("NFC not available on this device.")
                return
            if not nfc_adapter.isEnabled():
                self.log("WARNING: NFC adapter exists but is turned OFF in system settings.")
            intent = Intent(current_activity, current_activity.getClass())
            intent.addFlags(Intent.FLAG_ACTIVITY_SINGLE_TOP)
            pending_intent = PendingIntent.getActivity(
                current_activity, 0, intent, PendingIntent.FLAG_MUTABLE
            )
            nfc_adapter.enableForegroundDispatch(current_activity, pending_intent, None, None)
            self.log("NFC foreground dispatch ENABLED. Ready to scan.")
        except Exception as e:
            self.log(f"ERROR enabling NFC dispatch: {e}")
            self.log(traceback.format_exc()[-300:])

    def on_new_intent(self, intent):
        try:
            action = intent.getAction()
            self.log(f"Intent received! Action: {action}")
            if action in (NfcAdapter.ACTION_TAG_DISCOVERED,
                          NfcAdapter.ACTION_TECH_DISCOVERED,
                          NfcAdapter.ACTION_NDEF_DISCOVERED):
                tag_parcelable = intent.getParcelableExtra(NfcAdapter.EXTRA_TAG)
                if tag_parcelable is None:
                    self.log("Tag object was None.")
                    return
                tag = cast(Tag, tag_parcelable)
                uid_bytes = tag.getId()
                uid_hex = ''.join('%02X' % (b & 0xFF) for b in uid_bytes)
                self.log(f"Card UID read: {uid_hex}")
                self.status_label.text = f"Scanned: {uid_hex}"
                threading.Thread(target=self.send_to_laptop, args=(uid_hex,)).start()
            else:
                self.log("Intent action was not an NFC discovery action.")
        except Exception as e:
            self.log(f"ERROR in on_new_intent: {e}")
            self.log(traceback.format_exc()[-300:])

    def send_to_laptop(self, card_id):
        url = self.ip_input.text.strip()
        self.log(f"Sending to {url} ...")
        try:
            data = json.dumps({"id": card_id}).encode('utf-8')
            req = urllib.request.Request(
                url, data=data, headers={'Content-Type': 'application/json'}
            )
            resp = urllib.request.urlopen(req, timeout=5)
            self.log(f"Server responded: {resp.status}")
            self.update_status(f"Sent: {card_id}")
        except Exception as e:
            self.log(f"ERROR sending to laptop: {e}")
            self.update_status(f"Error sending: {e}")

    @mainthread
    def update_status(self, text):
        self.status_label.text = text


if __name__ == '__main__':
    NFCApp().run()
