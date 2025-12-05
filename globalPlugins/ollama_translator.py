import os
import socket
import globalVars
import globalPluginHandler
import scriptHandler
import ui
import wx
import gui.settingsDialogs
import json
import urllib.request
import threading
import api
import textInfos
import languageHandler
from logHandler import log

# Localization
TRANS = {
    "en": {
        "title": "Ollama Translator",
        "ollama_url": "Ollama URL:",
        "model": "Model:",
        "source_lang": "Source Language:",
        "target_lang": "Target Language:",
        "shortcut": "Translate Shortcut:",
        "shortcut_start": "Start Marker Shortcut:",
        "shortcut_end": "End Marker & Translate Shortcut:",
        "source_text": "Source Text:",
        "translation": "Translation:",
        "translate": "Translate",
        "close": "Close",
        "translating": "Translating...",
        "no_text": "No text found to translate.",
        "success": "Translation successful.",
        "failed": "Translation failed: Empty response.",
        "error": "Error: {}",
        "settings_registered": "Settings panel registered.",
        "menu_added": "Added to Tools menu.",
        "menu_removed": "Removed from Tools menu.",
        "menu_item": "Ollama Translator...",
        "menu_desc": "Open Ollama Translator",
        "settings_menu": "Settings...",
        "settings_desc": "Configure Ollama Translator",
        "documentation": "Documentation...",
        "doc_desc": "Open Documentation",
        "start_marker_set": "Start marker set.",
        "no_start_marker": "No start marker set. Please set start marker first.",
        "marker_error": "Error creating text range. Markers must be in the same object.",
        "timeout_title": "Timeout Error",
        "timeout_message": "Translation timed out. Do you want to retry?",
        "progress_started": "Translation started...",
        "progress_update": "Translating... ({} chars)"
    },
    "tr": {
        "title": "Ollama Çevirici",
        "ollama_url": "Ollama URL:",
        "model": "Model:",
        "source_lang": "Kaynak Dil:",
        "target_lang": "Hedef Dil:",
        "shortcut": "Çeviri Kısayolu:",
        "shortcut_start": "Başlangıç İşaretçisi Kısayolu:",
        "shortcut_end": "Bitiş İşaretçisi ve Çevir Kısayolu:",
        "source_text": "Kaynak Metin:",
        "translation": "Çeviri:",
        "translate": "Çevir",
        "close": "Kapat",
        "translating": "Çevriliyor...",
        "no_text": "Çevrilecek metin bulunamadı.",
        "success": "Çeviri başarılı.",
        "failed": "Çeviri başarısız: Boş yanıt.",
        "error": "Hata: {}",
        "settings_registered": "Ayarlar paneli kaydedildi.",
        "menu_added": "Araçlar menüsüne eklendi.",
        "menu_removed": "Araçlar menüsünden kaldırıldı.",
        "menu_item": "Ollama Çevirici...",
        "menu_desc": "Ollama Çevirici'yi Aç",
        "settings_menu": "Ayarlar...",
        "settings_desc": "Ollama Çevirici Ayarlarını Yapılandır",
        "documentation": "Dokümantasyon...",
        "doc_desc": "Dokümantasyonu Aç",
        "start_marker_set": "Başlangıç işaretçisi ayarlandı.",
        "no_start_marker": "Başlangıç işaretçisi ayarlanmadı. Lütfen önce başlangıç işaretçisini ayarlayın.",
        "marker_error": "Metin aralığı oluşturulurken hata. İşaretçiler aynı nesne üzerinde olmalıdır.",
        "timeout_title": "Zaman Aşımı Hatası",
        "timeout_message": "Çeviri zaman aşımına uğradı. Tekrar denemek ister misiniz?",
        "progress_started": "Çeviri başladı...",
        "progress_update": "Çevriliyor... ({} karakter)"
    }
}

def _(key):
    lang = languageHandler.getLanguage()
    if lang.startswith("tr"):
        return TRANS["tr"].get(key, TRANS["en"].get(key, key))
    return TRANS["en"].get(key, key)

# Configuration defaults
DEFAULT_CONFIG = {
    "ollama_url": "http://localhost:11434/api/generate",
    "model": "llama3",
    "source_lang": "Auto",
    "target_lang": "English",
    "shortcut": "kb:NVDA+shift+t",
    "shortcut_start": "kb:NVDA+shift+k",
    "shortcut_end": "kb:NVDA+shift+l"
}

CONFIG_FILE = os.path.join(globalVars.appArgs.configPath, "ollamaTranslator.json")

# Supported Languages
LANGUAGES = [
    "English", "Turkish", "Spanish", "French", "German", 
    "Italian", "Portuguese", "Russian", "Chinese", "Japanese", 
    "Korean", "Arabic", "Hindi", "Dutch", "Polish", 
    "Swedish", "Norwegian", "Danish", "Finnish", "Greek"
]

class SettingsPanel(gui.settingsDialogs.SettingsPanel):
    title = _("title")

    def makeSettings(self, settingsSizer):
        sHelper = gui.guiHelper.BoxSizerHelper(self, sizer=settingsSizer)
        
        # Ollama URL
        self.ollamaUrl = sHelper.addLabeledControl(_("ollama_url"), wx.TextCtrl)
        self.ollamaUrl.Value = GlobalPlugin.config.get("ollama_url", DEFAULT_CONFIG["ollama_url"])
        
        # Model (Dropdown)
        models = self.fetch_models(self.ollamaUrl.Value)
        self.model = sHelper.addLabeledControl(_("model"), wx.Choice, choices=models)
        current_model = GlobalPlugin.config.get("model", DEFAULT_CONFIG["model"])
        if current_model in models:
            self.model.SetStringSelection(current_model)
        elif models:
            self.model.SetSelection(0)
        else:
            self.model.Append(current_model)
            self.model.SetStringSelection(current_model)
        
        # Source Language
        source_choices = ["Auto"] + LANGUAGES
        self.sourceLang = sHelper.addLabeledControl(_("source_lang"), wx.Choice, choices=source_choices)
        current_source = GlobalPlugin.config.get("source_lang", DEFAULT_CONFIG["source_lang"])
        if current_source in source_choices:
            self.sourceLang.SetStringSelection(current_source)
        else:
            self.sourceLang.SetSelection(0)
        
        # Target Language
        self.targetLang = sHelper.addLabeledControl(_("target_lang"), wx.Choice, choices=LANGUAGES)
        current_target = GlobalPlugin.config.get("target_lang", DEFAULT_CONFIG["target_lang"])
        if current_target in LANGUAGES:
            self.targetLang.SetStringSelection(current_target)
        else:
            self.targetLang.SetSelection(0)

        # Shortcuts
        self.shortcut = sHelper.addLabeledControl(_("shortcut"), wx.TextCtrl)
        self.shortcut.Value = GlobalPlugin.config.get("shortcut", DEFAULT_CONFIG["shortcut"])

        self.shortcutStart = sHelper.addLabeledControl(_("shortcut_start"), wx.TextCtrl)
        self.shortcutStart.Value = GlobalPlugin.config.get("shortcut_start", DEFAULT_CONFIG["shortcut_start"])

        self.shortcutEnd = sHelper.addLabeledControl(_("shortcut_end"), wx.TextCtrl)
        self.shortcutEnd.Value = GlobalPlugin.config.get("shortcut_end", DEFAULT_CONFIG["shortcut_end"])

    def fetch_models(self, base_url):
        # Construct tags URL from generate URL (assuming standard Ollama structure)
        # base_url is like http://localhost:11434/api/generate
        # we want http://localhost:11434/api/tags
        try:
            if "/api/generate" in base_url:
                tags_url = base_url.replace("/api/generate", "/api/tags")
            else:
                # Fallback assumption
                tags_url = "http://localhost:11434/api/tags"
            
            with urllib.request.urlopen(tags_url, timeout=2) as response:
                data = json.loads(response.read().decode('utf-8'))
                # data['models'] is a list of dicts: [{'name': 'llama3:latest', ...}, ...]
                return [m['name'] for m in data.get('models', [])]
        except Exception as e:
            log.error(f"Ollama Translator: Failed to fetch models: {e}")
            return []

    def onSave(self):
        GlobalPlugin.config["ollama_url"] = self.ollamaUrl.Value
        GlobalPlugin.config["model"] = self.model.GetStringSelection()
        GlobalPlugin.config["source_lang"] = self.sourceLang.GetStringSelection()
        GlobalPlugin.config["target_lang"] = self.targetLang.GetStringSelection()
        
        old_shortcut = GlobalPlugin.config.get("shortcut")
        new_shortcut = self.shortcut.Value
        GlobalPlugin.config["shortcut"] = new_shortcut

        old_start = GlobalPlugin.config.get("shortcut_start")
        new_start = self.shortcutStart.Value
        GlobalPlugin.config["shortcut_start"] = new_start

        old_end = GlobalPlugin.config.get("shortcut_end")
        new_end = self.shortcutEnd.Value
        GlobalPlugin.config["shortcut_end"] = new_end
        
        GlobalPlugin.saveSettings()
        
        # Update gestures if changed
        if old_shortcut != new_shortcut:
            GlobalPlugin.updateGesture(old_shortcut, new_shortcut, "translate")
        if old_start != new_start:
            GlobalPlugin.updateGesture(old_start, new_start, "markStart")
        if old_end != new_end:
            GlobalPlugin.updateGesture(old_end, new_end, "markEndAndTranslate")

class GlobalPlugin(globalPluginHandler.GlobalPlugin):
    config = DEFAULT_CONFIG.copy()
    _instance = None
    start_marker = None

    def __init__(self):
        super(GlobalPlugin, self).__init__()
        GlobalPlugin._instance = self
        log.info("Ollama Translator: Initializing GlobalPlugin...")
        self.loadSettings()
        
        # Register Settings Panel
        try:
            if hasattr(gui.settingsDialogs.NVDASettingsDialog, "categoryClasses"):
                gui.settingsDialogs.NVDASettingsDialog.categoryClasses.append(SettingsPanel)
            elif hasattr(gui.settingsDialogs.NVDASettingsDialog, "categoryToPanels"):
                gui.settingsDialogs.NVDASettingsDialog.categoryToPanels.setdefault(_("title"), []).append(SettingsPanel)
            log.info(_("settings_registered"))
        except Exception as e:
            log.error(f"Ollama Translator: Failed to register settings panel: {e}")

        # Add to Tools Menu via CallAfter to ensure GUI is ready
        wx.CallAfter(self.createMenu)

        # Bind initial gestures
        self.bindConfiguredGestures()

    def bindConfiguredGestures(self):
        # Helper to bind all configured gestures
        for key, script in [
            ("shortcut", "translate"),
            ("shortcut_start", "markStart"),
            ("shortcut_end", "markEndAndTranslate")
        ]:
            shortcut = self.config.get(key, DEFAULT_CONFIG[key])
            if shortcut:
                try:
                    self.bindGesture(shortcut, script)
                except Exception as e:
                    log.error(f"Ollama Translator: Failed to bind {key}: {e}")

    def createMenu(self):
        try:
            self.toolsMenu = gui.mainFrame.sysTrayIcon.toolsMenu
            self.ollamaMenu = wx.Menu()
            
            # Translate Item
            self.translateItem = self.ollamaMenu.Append(wx.ID_ANY, _("translate"), _("menu_desc"))
            gui.mainFrame.sysTrayIcon.Bind(wx.EVT_MENU, self.onShowDialog, id=self.translateItem.GetId())
            
            # Settings Item
            self.settingsItem = self.ollamaMenu.Append(wx.ID_ANY, _("settings_menu"), _("settings_desc"))
            gui.mainFrame.sysTrayIcon.Bind(wx.EVT_MENU, self.onSettings, id=self.settingsItem.GetId())
            
            # Documentation Item
            self.docItem = self.ollamaMenu.Append(wx.ID_ANY, _("documentation"), _("doc_desc"))
            gui.mainFrame.sysTrayIcon.Bind(wx.EVT_MENU, self.onDocumentation, id=self.docItem.GetId())
            
            # Append Submenu to Tools
            self.menuItem = self.toolsMenu.AppendSubMenu(self.ollamaMenu, _("title"), _("menu_desc"))
            
            log.info(_("menu_added"))
        except Exception as e:
            log.error(f"Ollama Translator: Failed to add to Tools menu: {e}")

    def onSettings(self, event):
        # Open NVDA Settings Dialog focused on our panel
        try:
            gui.mainFrame.prePopup()
            d = gui.settingsDialogs.NVDASettingsDialog(gui.mainFrame, SettingsPanel)
            d.Show()
            gui.mainFrame.postPopup()
        except Exception as e:
            log.error(f"Ollama Translator: Failed to open settings: {e}")
            # Fallback
            try:
                gui.mainFrame.onSettingsCommand(None)
            except:
                pass

    def onDocumentation(self, event):
        try:
            # Determine language
            lang = languageHandler.getLanguage()
            if lang.startswith("tr"):
                lang_code = "tr"
            else:
                lang_code = "en"

            # Path construction: .../addon/doc/{lang}/readme.html
            # __file__ is .../addon/globalPlugins/ollama_translator.py
            # We need to go up two levels to get to addon root, then into doc/{lang}
            
            base_dir = os.path.dirname(os.path.dirname(__file__))
            doc_path = os.path.join(base_dir, "doc", lang_code, "readme.html")
            
            if os.path.exists(doc_path):
                os.startfile(doc_path)
            else:
                # Fallback to English if specific lang not found
                doc_path_en = os.path.join(base_dir, "doc", "en", "readme.html")
                if os.path.exists(doc_path_en):
                    os.startfile(doc_path_en)
                else:
                    # Fallback for dev environment or different structure
                    # Try sibling of globalPlugins
                    doc_path_dev = os.path.join(os.path.dirname(__file__), "..", "doc", lang_code, "readme.html")
                    if os.path.exists(doc_path_dev):
                         os.startfile(doc_path_dev)
                    else:
                        ui.message("Documentation file not found.")
        except Exception as e:
            log.error(f"Ollama Translator: Failed to open documentation: {e}")
            ui.message(f"Error opening documentation: {e}")

    @classmethod
    def updateGesture(cls, old_gesture, new_gesture, script_name):
        if cls._instance:
            try:
                # Unbind old gesture if it exists
                if old_gesture:
                    try:
                        cls._instance.removeGestureBinding(old_gesture)
                        log.info(f"Ollama Translator: Unbound old shortcut {old_gesture} for {script_name}")
                    except LookupError:
                        pass # Gesture wasn't bound
                    except Exception as e:
                        log.warning(f"Ollama Translator: Failed to unbind old shortcut: {e}")

                # Bind new gesture
                if new_gesture:
                    cls._instance.bindGesture(new_gesture, script_name)
                    log.info(f"Ollama Translator: Bound new shortcut {new_gesture} for {script_name}")
            except Exception as e:
                log.error(f"Ollama Translator: Failed to update shortcut: {e}")
                ui.message(f"Error updating shortcut: {e}")

    def terminate(self):
        super(GlobalPlugin, self).terminate()
        try:
            if hasattr(gui.settingsDialogs.NVDASettingsDialog, "categoryClasses"):
                if SettingsPanel in gui.settingsDialogs.NVDASettingsDialog.categoryClasses:
                    gui.settingsDialogs.NVDASettingsDialog.categoryClasses.remove(SettingsPanel)
            elif hasattr(gui.settingsDialogs.NVDASettingsDialog, "categoryToPanels"):
                panels = gui.settingsDialogs.NVDASettingsDialog.categoryToPanels.get(_("title"))
                if panels and SettingsPanel in panels:
                    panels.remove(SettingsPanel)
        except Exception as e:
            log.error(f"Ollama Translator: Failed to unregister settings panel: {e}")

        try:
            if self.menuItem:
                self.toolsMenu.Remove(self.menuItem)
                log.info(_("menu_removed"))
        except Exception as e:
            log.error(f"Ollama Translator: Failed to remove from Tools menu: {e}")

    def onShowDialog(self, event):
        gui.mainFrame.prePopup()
        d = TranslationDialog(gui.mainFrame)
        d.Show()
        gui.mainFrame.postPopup()

    @classmethod
    def loadSettings(cls):
        try:
            with open(CONFIG_FILE, "r") as f:
                cls.config.update(json.load(f))
            log.info("Ollama Translator: Settings loaded.")
        except (FileNotFoundError, json.JSONDecodeError):
            log.info("Ollama Translator: No settings file found or invalid, using defaults.")
        except Exception as e:
            log.error(f"Ollama Translator: Error loading settings: {e}")

    @classmethod
    def saveSettings(cls):
        try:
            with open(CONFIG_FILE, "w") as f:
                json.dump(cls.config, f, indent=4)
            log.info("Ollama Translator: Settings saved.")
        except Exception as e:
            log.error(f"Error saving settings: {e}")

    def script_markStart(self, gesture):
        # Use focus object (and treeInterceptor if available) to support Browse Mode documents
        obj = api.getFocusObject()
        treeInterceptor = obj.treeInterceptor
        if treeInterceptor and hasattr(treeInterceptor, "TextInfo") and not treeInterceptor.passThrough:
            obj = treeInterceptor
            
        try:
            self.start_marker = obj.makeTextInfo(textInfos.POSITION_CARET)
            # Also store the object to ensure we are marking on the same object
            self.start_marker_obj = obj
            ui.message(_("start_marker_set"))
        except Exception as e:
            log.error(f"Ollama Translator: Failed to set start marker: {e}")
            ui.message("Failed to set start marker.")

    def script_markEndAndTranslate(self, gesture):
        if not self.start_marker:
            ui.message(_("no_start_marker"))
            return

        # Use focus object (and treeInterceptor if available)
        obj = api.getFocusObject()
        treeInterceptor = obj.treeInterceptor
        if treeInterceptor and hasattr(treeInterceptor, "TextInfo") and not treeInterceptor.passThrough:
            obj = treeInterceptor

        if obj != self.start_marker_obj:
            # Fallback: Check if they belong to the same context
            is_same_context = False
            
            # Check if obj is inside the start_marker_obj (which is a treeInterceptor)
            if hasattr(obj, "treeInterceptor") and obj.treeInterceptor == self.start_marker_obj:
                is_same_context = True
            
            # Check if start_marker_obj is inside obj's treeInterceptor (unlikely but possible if roles reversed)
            elif hasattr(self.start_marker_obj, "treeInterceptor") and self.start_marker_obj.treeInterceptor == obj:
                 is_same_context = True
                 
            # Check if both share the same treeInterceptor
            elif getattr(obj, "treeInterceptor", None) and \
                 getattr(obj, "treeInterceptor", None) == getattr(self.start_marker_obj, "treeInterceptor", None):
                 is_same_context = True

            if is_same_context:
                obj = self.start_marker_obj
            else:
                ui.message(_("marker_error"))
                return

        try:
            end_marker = obj.makeTextInfo(textInfos.POSITION_CARET)
            
            # Create a range from start to end
            # We assume start_marker is before end_marker, but we should handle both
            # copy start marker to avoid modifying the stored one
            range_info = self.start_marker.copy()
            
            # Set the end of range_info to the end of end_marker
            # This works even if end_marker is before start_marker (it flips?)
            # Actually setEndPoint might fail if order is wrong or just set it.
            # Usually we want to ensure start is before end.
            
            # Check order
            if range_info.compareEndPoints(end_marker, "startToStart") > 0:
                # start_marker is AFTER end_marker. Swap?
                # We can't easily swap TextInfos of different times if they are just markers.
                # But we can create a new range from end_marker to start_marker.
                range_info = end_marker.copy()
                range_info.setEndPoint(self.start_marker, "endToEnd")
            else:
                range_info.setEndPoint(end_marker, "endToEnd")
            
            # Extract text safely using chunks
            text = ""
            try:
                for chunk in range_info.getTextInChunks(textInfos.UNIT_PARAGRAPH):
                    text += chunk
                    if len(text) > 5000:
                        text = text[:5000]
                        break
            except Exception as e:
                # Fallback to simple .text if chunks fail
                log.warning(f"Ollama Translator: getTextInChunks failed, falling back to .text: {e}")
                text = range_info.text

            if not text or not text.strip():
                ui.message(_("no_text"))
                return
            
            # Limit text length just in case fallback was used
            if len(text) > 5000:
                text = text[:5000]

            ui.message(_("translating"))
            threading.Thread(target=self.translateText, args=(text,)).start()
            
            # Reset marker
            self.start_marker = None
            self.start_marker_obj = None

        except Exception as e:
            log.error(f"Ollama Translator: Failed to process end marker: {e}")
            ui.message(_("error").format(e))

    def script_translate(self, gesture):
        log.info("Ollama Translator: Translation triggered.")
        obj = api.getFocusObject()
        treeInterceptor = obj.treeInterceptor
        if treeInterceptor and hasattr(treeInterceptor, "TextInfo") and not treeInterceptor.passThrough:
            obj = treeInterceptor

        # 1. Try to get selected text (User's primary workflow)
        info = None
        try:
            info = obj.makeTextInfo(textInfos.POSITION_SELECTION)
        except (RuntimeError, NotImplementedError):
            info = None

        # 2. If no selection, try to get text from the focus object (Fallback)
        if not info or info.isCollapsed:
            try:
                info = obj.makeTextInfo(textInfos.POSITION_ALL)
            except (RuntimeError, NotImplementedError):
                info = None

        # 3. If still no text, try navigator object
        if not info or not info.text:
            obj = api.getNavigatorObject()
            try:
                info = obj.makeTextInfo(textInfos.POSITION_ALL)
            except (RuntimeError, NotImplementedError):
                info = None

        if not info or not info.text:
            ui.message(_("no_text"))
            return

        text = info.text
        # Limit text length to avoid accidental huge translations if falling back to ALL
        if len(text) > 5000:
            ui.message("Text too long to translate (limit 5000 chars). Please select a smaller chunk.")
            return

        ui.message(_("translating"))
        threading.Thread(target=self.translateText, args=(text,)).start()

    def translateText(self, text, callback=None):
        url = self.config.get("ollama_url", DEFAULT_CONFIG["ollama_url"])
        model = self.config.get("model", DEFAULT_CONFIG["model"])
        source = self.config.get("source_lang", DEFAULT_CONFIG["source_lang"])
        target = self.config.get("target_lang", DEFAULT_CONFIG["target_lang"])

        prompt = f"Translate the following text from {source} to {target}. Only output the translation, nothing else. Text: {text}"
        
        data = {
            "model": model,
            "prompt": prompt,
            "stream": True
        }

        try:
            req = urllib.request.Request(url, data=json.dumps(data).encode('utf-8'), headers={'Content-Type': 'application/json'})
            # Set timeout to 30 seconds
            with urllib.request.urlopen(req, timeout=30) as response:
                full_translation = ""
                count = 0
                
                # Notify start
                if callback:
                    wx.CallAfter(callback, _("progress_started"))
                
                for line in response:
                    if line:
                        try:
                            json_line = json.loads(line.decode('utf-8'))
                            chunk = json_line.get("response", "")
                            full_translation += chunk
                            count += len(chunk)
                            
                            # Update progress periodically (e.g. every 50 chars or so to avoid spamming UI)
                            # For screen readers, too many updates are bad. Let's update only if callback is present (dialog open)
                            # and maybe not too often.
                            if callback and count % 50 == 0:
                                wx.CallAfter(callback, _("progress_update").format(count))
                                
                            if json_line.get("done", False):
                                break
                        except json.JSONDecodeError:
                            continue

                if full_translation.strip():
                    if callback:
                        wx.CallAfter(callback, full_translation.strip())
                    else:
                        wx.CallAfter(ui.browseableMessage, full_translation.strip(), _("title"))
                else:
                    msg = _("failed")
                    if callback:
                        wx.CallAfter(callback, msg)
                    else:
                        ui.message(msg)

        except (urllib.error.URLError, socket.timeout) as e:
            log.error(f"Translation timeout or network error: {e}")
            
            def ask_retry():
                dlg = wx.MessageDialog(None, _("timeout_message"), _("timeout_title"), wx.YES_NO | wx.ICON_WARNING)
                if dlg.ShowModal() == wx.ID_YES:
                    threading.Thread(target=self.translateText, args=(text, callback)).start()
                dlg.Destroy()
            
            wx.CallAfter(ask_retry)

        except Exception as e:
            log.error(f"Translation error: {e}")
            msg = _("error").format(e)
            if callback:
                wx.CallAfter(callback, msg)
            else:
                ui.message(msg)

    __gestures = {
        "kb:NVDA+shift+t": "translate",
        "kb:NVDA+shift+k": "markStart",
        "kb:NVDA+shift+l": "markEndAndTranslate"
    }

class TranslationDialog(wx.Dialog):
    def __init__(self, parent):
        super(TranslationDialog, self).__init__(parent, title=_("title"), size=(500, 400))
        
        mainSizer = wx.BoxSizer(wx.VERTICAL)
        
        # Source Text
        mainSizer.Add(wx.StaticText(self, label=_("source_text")), 0, wx.ALL, 5)
        self.sourceText = wx.TextCtrl(self, style=wx.TE_MULTILINE)
        mainSizer.Add(self.sourceText, 1, wx.EXPAND | wx.ALL, 5)
        
        # Target Text
        mainSizer.Add(wx.StaticText(self, label=_("translation")), 0, wx.ALL, 5)
        self.targetText = wx.TextCtrl(self, style=wx.TE_MULTILINE | wx.TE_READONLY)
        mainSizer.Add(self.targetText, 1, wx.EXPAND | wx.ALL, 5)
        
        # Buttons
        btnSizer = wx.BoxSizer(wx.HORIZONTAL)
        self.translateBtn = wx.Button(self, label=_("translate"))
        self.translateBtn.Bind(wx.EVT_BUTTON, self.onTranslate)
        btnSizer.Add(self.translateBtn, 0, wx.ALL, 5)
        
        self.closeBtn = wx.Button(self, wx.ID_CLOSE, label=_("close"))
        self.closeBtn.Bind(wx.EVT_BUTTON, self.onClose)
        btnSizer.Add(self.closeBtn, 0, wx.ALL, 5)
        
        mainSizer.Add(btnSizer, 0, wx.ALIGN_CENTER | wx.ALL, 5)
        
        self.SetSizer(mainSizer)
        self.Center()

    def onTranslate(self, event):
        text = self.sourceText.GetValue()
        if not text:
            return
        
        self.targetText.SetValue(_("translating"))
        # Use the global plugin instance to translate
        if GlobalPlugin._instance:
            threading.Thread(target=GlobalPlugin._instance.translateText, args=(text, self.targetText.SetValue)).start()

    def onClose(self, event):
        self.Destroy()
