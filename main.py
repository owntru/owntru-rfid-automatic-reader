"""
NFC Card Scanner -> Sends card UID to your laptop
--------------------------------------------------
A minimal Kivy app for Android that:
1. Listens for NFC tag/card scans while the app is open (foreground dispatch)
2. Reads the card's UID
3. Sends it via HTTP POST to your laptop's nfc_listener.py

Build this into an APK with Buildozer (see buildozer.spec + build instructions).
"""

from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.clock import mainthread
import threading
import urllib.request
import json

from jnius import autoclass
from android import activity

PythonActivity = autoclass('org.kivy.android.PythonActivity')
NfcAdapter = autoclass('android.nfc.NfcAdapter')
PendingIntent = autoclass('android.app.PendingIntent')
Intent = autoclass('android.content.Intent')

DEFAULT_URL = "http://192.168.1.42:5005"  # <-- change to your laptop's IP


class NFCApp(App):
    def build(self):
        self.status_label = Label(text="Ready. Tap a card to scan.", font_size=20)
        self.ip_input = TextInput(text=DEFAULT_URL, multiline=False,
                                   size_hint_y=None, height=50)
        layout = BoxLayout(orientation='vertical', padding=20, spacing=15)
        layout.add_widget(Label(text="Laptop address:", size_hint_y=None, height=30))
        layout.add_widget(self.ip_input)
        layout.add_widget(self.status_label)
        return layout

    def on_start(self):
        activity.bind(on_new_intent=self.on_new_intent)
        self.enable_nfc_dispatch()

    def on_resume(self):
        self.enable_nfc_dispatch()

    def enable_nfc_dispatch(self):
        current_activity = PythonActivity.mActivity
        nfc_adapter = NfcAdapter.getDefaultAdapter(current_activity)
        if nfc_adapter is None:
            self.status_label.text = "NFC not available on this device."
            return
        intent = Intent(current_activity, current_activity.getClass())
        intent.addFlags(Intent.FLAG_ACTIVITY_SINGLE_TOP)
        pending_intent = PendingIntent.getActivity(
            current_activity, 0, intent, PendingIntent.FLAG_MUTABLE
        )
        nfc_adapter.enableForegroundDispatch(current_activity, pending_intent, None, None)

    def on_new_intent(self, intent):
        action = intent.getAction()
        if action in (NfcAdapter.ACTION_TAG_DISCOVERED,
                      NfcAdapter.ACTION_TECH_DISCOVERED,
                      NfcAdapter.ACTION_NDEF_DISCOVERED):
            tag = intent.getParcelableExtra(NfcAdapter.EXTRA_TAG)
            uid_bytes = tag.getId()
            uid_hex = ''.join('%02X' % (b & 0xFF) for b in uid_bytes)
            self.status_label.text = f"Scanned: {uid_hex}"
            threading.Thread(target=self.send_to_laptop, args=(uid_hex,)).start()

    def send_to_laptop(self, card_id):
        url = self.ip_input.text.strip()
        try:
            data = json.dumps({"id": card_id}).encode('utf-8')
            req = urllib.request.Request(
                url, data=data, headers={'Content-Type': 'application/json'}
            )
            urllib.request.urlopen(req, timeout=5)
            self.update_status(f"Sent: {card_id}")
        except Exception as e:
            self.update_status(f"Error sending: {e}")

    @mainthread
    def update_status(self, text):
        self.status_label.text = text


if __name__ == '__main__':
    NFCApp().run()
