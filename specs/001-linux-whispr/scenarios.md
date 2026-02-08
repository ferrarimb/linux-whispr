# Scenarios — LinuxWhispr

## Scenario 1: First-Time Setup

**Actor**: New user installing LinuxWhispr for the first time.

### Steps
1. User installs via `pip install linux-whispr` or downloads AppImage.
2. User runs `linux-whispr` for the first time.
3. First-run wizard appears:
   a. **Welcome screen**: brief explanation of what LinuxWhispr does.
   b. **Microphone test**: user speaks, app shows audio level to confirm mic works.
   c. **Model selection**: user picks a Whisper model (default: `base` recommended, with size/speed trade-off explained).
   d. **Model download**: progress bar shows download (base model ~150MB).
   e. **Hotkey configuration**: user can accept defaults or customize.
   f. **Quick test**: user dictates a test phrase, sees it transcribed — confirms everything works.
4. Setup complete. App minimizes to system tray. Hotkey is active.

### Expected Outcome
- User is dictating within 5 minutes of installation.
- No terminal commands needed after initial install.

---

## Scenario 2: Basic Dictation in a Browser

**Actor**: User writing an email in Gmail (Firefox/Chrome).

### Steps
1. User clicks in Gmail compose field.
2. User presses `F12` (default hotkey).
3. Floating overlay appears with pulsing red recording indicator.
4. User speaks: "Hi Maria, thanks for sending over the project proposal. I've reviewed it and I think we should move forward with option B. Let me know when you're free to discuss. Best, João."
5. User presses `F12` again to stop.
6. Overlay shows processing spinner (< 2 seconds).
7. Refined text appears in the Gmail compose field:

   > Hi Maria,
   >
   > Thanks for sending over the project proposal. I've reviewed it and I think we should move forward with option B. Let me know when you're free to discuss.
   >
   > Best,
   > João

8. Overlay briefly shows green checkmark, then returns to idle.

### Expected Outcome
- Text is properly formatted for email context (greeting, paragraphs, sign-off).
- Proper nouns ("Maria", "João") correctly capitalized.
- No filler words in output.

---

## Scenario 3: Dictating Code Comments in VS Code

**Actor**: Developer writing code documentation.

### Steps
1. User is in VS Code, cursor on a blank line above a function.
2. User presses `F12`.
3. User speaks: "This function takes a list of user objects and returns a dictionary mapping user IDs to their email addresses. It raises a ValueError if any user object is missing the email field."
4. User presses `F12`.
5. Text appears at cursor:

   ```
   # This function takes a list of user objects and returns a dictionary
   # mapping user IDs to their email addresses. It raises a ValueError
   # if any user object is missing the email field.
   ```

### Expected Outcome
- AI detects VS Code context and formats as code comment.
- Technical terms ("ValueError", "dictionary", "user IDs") handled correctly.
- Proper line wrapping for code comment style.

---

## Scenario 4: Self-Correction During Dictation

**Actor**: User dictating a message who changes their mind mid-sentence.

### Steps
1. User presses hotkey, speaks: "Let's schedule the meeting for Tuesday at 2 PM... actually no, make it Wednesday at 3 PM."
2. User stops recording.
3. AI refinement understands the self-correction.
4. Output: "Let's schedule the meeting for Wednesday at 3 PM."

### Expected Outcome
- Only the corrected version appears.
- Self-correction phrases ("actually no", "I mean", "wait", "no wait") are recognized and handled.

---

## Scenario 5: Command Mode — Text Transformation

**Actor**: User who wants to improve already-written text.

### Steps
1. User selects a paragraph of text in LibreOffice Writer.
2. User presses `Ctrl+Shift+H` (Command Mode hotkey).
3. Overlay shows blue Command Mode indicator.
4. User speaks: "Make this more concise and professional."
5. User stops recording.
6. LinuxWhispr reads the selected text from clipboard.
7. AI processes the command + selected text.
8. Selected text is replaced with the improved version.

### Expected Outcome
- Original text selection is replaced, not appended.
- Transformation matches the spoken instruction.
- Original text is saved in history for undo reference.

---

## Scenario 6: Command Mode — Text Generation

**Actor**: User who wants AI to write something from scratch.

### Steps
1. User clicks in a Slack message box.
2. User presses `Ctrl+Shift+H`.
3. User speaks: "Write a short message thanking the team for their hard work on the release and suggesting we celebrate on Friday."
4. AI generates the text and injects it.

### Expected Outcome
- Generated text matches the casual tone of Slack context.
- Message is concise and appropriate.

---

## Scenario 7: Snippet Expansion

**Actor**: Power user with configured snippets.

### Steps
1. User has configured snippet: trigger "my email" → "joao.ferrai@example.com"
2. User presses hotkey, speaks: "Please send the invoice to my email."
3. Output: "Please send the invoice to joao.ferrai@example.com."

### Expected Outcome
- Trigger phrase is replaced with expanded text seamlessly.
- Rest of the sentence is preserved.

---

## Scenario 8: Whisper Mode in Quiet Environment

**Actor**: User in a library or open office who needs to dictate quietly.

### Steps
1. User enables Whisper Mode via tray menu.
2. Overlay shows whisper indicator (dimmed microphone icon).
3. User presses hotkey, whispers: "Remind me to call the dentist tomorrow at 10 AM."
4. Microphone gain is boosted, VAD sensitivity is increased.
5. Transcription succeeds despite low input volume.

### Expected Outcome
- Low-volume speech is captured accurately.
- No significantly degraded accuracy compared to normal volume.

---

## Scenario 9: Multi-Language Dictation

**Actor**: Bilingual user who switches between Portuguese and English.

### Steps
1. User has language set to "auto" (default).
2. User presses hotkey, speaks in Portuguese: "Preciso enviar o relatório até sexta-feira."
3. Whisper auto-detects Portuguese.
4. Output: "Preciso enviar o relatório até sexta-feira."
5. Later, user speaks in English: "The quarterly report is ready for review."
6. Whisper auto-detects English.
7. Output: "The quarterly report is ready for review."

### Expected Outcome
- Language is detected per-utterance automatically.
- Accented characters (é, á, ã) are handled correctly.
- No manual language switching needed.

---

## Scenario 10: Network Failure with Cloud Backend

**Actor**: User configured with Groq cloud STT who loses internet.

### Steps
1. User presses hotkey, speaks, stops recording.
2. Cloud API call fails (network timeout).
3. LinuxWhispr detects failure, shows error notification: "Cloud transcription failed. Falling back to local model."
4. If local model is available: automatically retries with local faster-whisper.
5. If no local model: shows notification "No local model available. Please check your connection or download a local model in Settings."
6. Audio is saved temporarily for retry.

### Expected Outcome
- No audio data is lost.
- Graceful fallback when possible.
- Clear error message when fallback isn't possible.

---

## Scenario 11: Custom Dictionary for Technical Terms

**Actor**: Developer working on a project with specialized terminology.

### Steps
1. User adds to custom dictionary: "Kubernetes", "kubectl", "etcd", "CRD", "LinuxWhispr"
2. User dictates: "We need to deploy the new CRD using kubectl and verify the etcd cluster is healthy."
3. Without dictionary, Whisper might produce: "We need to deploy the new CRT using cube control and verify the ETCD cluster is healthy."
4. With dictionary, Whisper correctly produces: "We need to deploy the new CRD using kubectl and verify the etcd cluster is healthy."

### Expected Outcome
- Technical terms from dictionary are recognized with significantly higher accuracy.
- Dictionary is loaded as Whisper `initial_prompt` context.

---

## Scenario 12: Long Dictation Session (Brain Dump)

**Actor**: User doing a long-form brain dump to an AI assistant (e.g., Claude chat).

### Steps
1. User clicks in Claude's chat input in browser.
2. User presses hotkey, speaks for 4 minutes continuously about a complex topic.
3. At 5:30, overlay shows subtle warning: "30 seconds remaining."
4. User wraps up and stops at 5:45.
5. Large audio file is transcribed (may take 5-10 seconds on CPU).
6. AI refinement structures the rambling thoughts into coherent paragraphs.
7. Refined text is injected into the chat input.

### Expected Outcome
- Full recording is captured without truncation.
- Long transcription is handled without memory issues.
- AI refinement adds significant value for rambling input.

---

## Scenario 13: Wayland + GNOME Desktop

**Actor**: Ubuntu 24.04 user with default GNOME Wayland session.

### Steps
1. User installs LinuxWhispr.
2. App detects Wayland session, uses D-Bus GlobalShortcuts portal for hotkey.
3. App detects wtype is installed, uses it for text injection.
4. User presses hotkey, dictates, text appears in GNOME Text Editor.
5. Overlay renders as GTK4 Layer Shell surface (always on top, non-focusable).
6. System tray uses SNI protocol, appears in GNOME's tray area.

### Expected Outcome
- Full functionality on Wayland without XWayland fallback.
- No "this app needs X11" warnings.
- Native look and feel with libadwaita.

---

## Scenario 14: X11 + i3 Window Manager

**Actor**: Arch Linux user with i3 window manager on X11.

### Steps
1. User installs via AUR.
2. App detects X11 session, uses XGrabKey for hotkey.
3. App detects xdotool, uses it for text injection.
4. Overlay renders as override-redirect X11 window (always on top).
5. User dictates in Alacritty terminal — text appears at cursor.

### Expected Outcome
- Works correctly in tiling WM environment.
- Overlay doesn't cause i3 to tile it as a window.
- Text injection works in terminal emulators.

---

## Scenario 15: Viewing and Searching History

**Actor**: User who wants to find something they dictated last week.

### Steps
1. User opens Settings from tray menu.
2. Navigates to History tab.
3. Searches "project proposal".
4. Finds the email dictation from Scenario 2.
5. Clicks "Copy" to get the text again.
6. Optionally clicks "Delete" to remove the entry.

### Expected Outcome
- Fast full-text search across all transcriptions.
- Clear display of timestamp, app context, word count.
- Easy copy-to-clipboard and delete actions.
