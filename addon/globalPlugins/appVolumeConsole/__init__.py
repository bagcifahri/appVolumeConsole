# Application Volume Console for NVDA
# Copyright (C) 2026 Fahri Bağcı
# This file is covered by the GNU General Public License, version 2.
# See the file COPYING.txt for more details.
# NVDA+Windows+S opens a command layer for controlling the volume, mute state
# and input/output devices of applications that are playing audio.

import functools

import addonHandler
import api
import config
import globalPluginHandler
import gui
import tones
import ui
import wx
from comtypes import COMError
from gui import guiHelper, nvdaControls
from gui.settingsDialogs import NVDASettingsDialog, SettingsPanel
from keyboardHandler import KeyboardInputGesture
from logHandler import log
from scriptHandler import script

from . import coreAudio
from .coreAudio import FLOW_CAPTURE, FLOW_RENDER
from .policyConfig import AudioPolicyConfig

addonHandler.initTranslation()

CONF_SECTION = "appVolumeConsole"
START_FOCUSED = "focused"
START_FIRST = "first"

config.conf.spec[CONF_SECTION] = {
	"startPosition": f'option("{START_FOCUSED}", "{START_FIRST}", default="{START_FOCUSED}")',
	"volumeStep": "integer(default=5, min=1, max=25)",
}


def _reportErrors(func):
	"""Speaks an error instead of failing silently when Windows refuses an audio operation."""

	@functools.wraps(func)
	def wrapper(self, gesture):
		try:
			return func(self, gesture)
		except (COMError, OSError):
			log.error("Application Volume Console: audio operation failed", exc_info=True)
			# Translators: Reported when an audio operation fails.
			ui.message(_("Could not access the audio settings"))

	return wrapper


class AppVolumeConsolePanel(SettingsPanel):
	# Translators: Title of the settings panel.
	title = _("Application Volume Console")

	def makeSettings(self, settingsSizer):
		helper = guiHelper.BoxSizerHelper(self, sizer=settingsSizer)
		conf = config.conf[CONF_SECTION]
		self._startValues = [START_FOCUSED, START_FIRST]
		startLabels = [
			# Translators: Option for where the console starts.
			_("The application in focus"),
			# Translators: Option for where the console starts.
			_("The first application in the list"),
		]
		self.startPosition = helper.addLabeledControl(
			# Translators: Label of the start position choice in settings.
			_("When the console opens, &start from:"),
			wx.Choice,
			choices=startLabels,
		)
		self.startPosition.SetSelection(self._startValues.index(conf["startPosition"]))
		self.volumeStep = helper.addLabeledControl(
			# Translators: Label of the volume step setting.
			_("Volume &step (percent):"),
			nvdaControls.SelectOnFocusSpinCtrl,
			min=1,
			max=25,
			initial=conf["volumeStep"],
		)

	def onSave(self):
		conf = config.conf[CONF_SECTION]
		conf["startPosition"] = self._startValues[self.startPosition.GetSelection()]
		conf["volumeStep"] = self.volumeStep.GetValue()


class GlobalPlugin(globalPluginHandler.GlobalPlugin):
	# Translators: Category of the add-on's commands in the Input Gestures dialog.
	scriptCategory = _("Application Volume Console")

	_layerGestures = {
		"kb:leftArrow": "previousApp",
		"kb:rightArrow": "nextApp",
		"kb:home": "firstApp",
		"kb:end": "lastApp",
		"kb:upArrow": "volumeUp",
		"kb:downArrow": "volumeDown",
		"kb:m": "toggleMute",
		"kb:control+upArrow": "previousInputDevice",
		"kb:control+downArrow": "nextInputDevice",
		"kb:alt+upArrow": "previousOutputDevice",
		"kb:alt+downArrow": "nextOutputDevice",
		"kb:space": "reportCurrent",
		"kb:f1": "layerHelp",
		"kb:escape": "closeLayer",
	}

	def __init__(self):
		super().__init__()
		self._layerActive = False
		self._apps: list[coreAudio.AudioApp] = []
		self._index = 0
		# The focused application, kept in the list even when it has no audio session yet.
		self._focusedApp: coreAudio.AudioApp | None = None
		self._policy: AudioPolicyConfig | None = None
		NVDASettingsDialog.categoryClasses.append(AppVolumeConsolePanel)

	def terminate(self):
		self._exitLayer()
		if self._policy is not None:
			self._policy.release()
			self._policy = None
		try:
			NVDASettingsDialog.categoryClasses.remove(AppVolumeConsolePanel)
		except ValueError:
			pass
		super().terminate()

	# Layer handling

	def getScript(self, gesture):
		scriptFunc = super().getScript(gesture)
		if (
			self._layerActive
			and scriptFunc is None
			and isinstance(gesture, KeyboardInputGesture)
			and not gesture.isModifier
		):
			return self.script_unknownLayerKey
		return scriptFunc

	def event_foreground(self, obj, nextHandler):
		# Another window came to the front (Start menu, mouse click, notification...):
		# leave the layer so the arrow keys work in that window again.
		if self._layerActive:
			self._exitLayer()
			tones.beep(150, 80)
		nextHandler()

	def _enterLayer(self):
		self._layerActive = True
		self.bindGestures(self._layerGestures)

	def _exitLayer(self):
		if not self._layerActive:
			return
		self._layerActive = False
		for gestureId in self._layerGestures:
			try:
				self.removeGestureBinding(gestureId)
			except LookupError:
				pass
		self._apps = []
		self._focusedApp = None

	@script(
		# Translators: Description of the command that opens the console.
		description=_("Opens the application volume console"),
		gesture="kb:NVDA+windows+s",
	)
	@_reportErrors
	def script_openConsole(self, gesture):
		if self._layerActive:
			self._exitLayer()
			# Translators: Reported when the console is closed.
			ui.message(_("Volume console closed"))
			return
		self._focusedApp = self._getForegroundApp()
		self._apps = []
		self._index = 0
		self._refresh()
		if not self._apps:
			# Translators: Reported when no application is playing audio.
			ui.message(_("No applications with audio"))
			return
		self._index = 0
		if config.conf[CONF_SECTION]["startPosition"] == START_FOCUSED and self._focusedApp:
			for i, app in enumerate(self._apps):
				if app.key == self._focusedApp.key:
					self._index = i
					break
		self._enterLayer()
		# Translators: Announced when the console opens, followed by the current application.
		ui.message(_("Volume console") + ", " + self._describe(self._current()))

	def script_closeLayer(self, gesture):
		self._exitLayer()
		# Translators: Reported when the console is closed.
		ui.message(_("Volume console closed"))

	def script_unknownLayerKey(self, gesture):
		self._exitLayer()
		tones.beep(150, 80)

	def script_layerHelp(self, gesture):
		ui.message(
			# Translators: Help for the console's command layer.
			_(
				"Left and right arrows: choose application. "
				"Home and end: first and last application. "
				"Up and down arrows: change volume. "
				"M: mute or unmute. "
				"Alt with up and down arrows: change output device. "
				"Control with up and down arrows: change input device. "
				"Space: report the current application. "
				"Escape: close the console.",
			),
		)

	# Application list

	def _getForegroundApp(self) -> coreAudio.AudioApp | None:
		obj = api.getForegroundObject()
		pid = getattr(obj, "processID", 0) if obj else 0
		path = coreAudio.getProcessImagePath(pid)
		if not path:
			return None
		app = coreAudio.AudioApp(path.lower(), coreAudio.getAppName(path))
		app.pids.append(pid)
		return app

	def _refresh(self) -> bool:
		"""Re-reads the session list, keeping the current application selected.
		Returns False if the previously selected application has disappeared.
		"""
		currentKey = self._apps[self._index].key if self._apps else None
		# Translators: Name of the Windows system sounds entry.
		apps = coreAudio.getAudioApps(_("System sounds"))
		focused = self._focusedApp
		if focused and coreAudio.getProcessImagePath(focused.pids[0]) is None:
			# The focused application was closed while the console was open.
			focused = self._focusedApp = None
		if focused and all(app.key != focused.key for app in apps):
			apps = coreAudio.sortApps(apps + [focused])
		self._apps = apps
		for i, app in enumerate(apps):
			if app.key == currentKey:
				self._index = i
				return True
		self._index = max(0, min(self._index, len(apps) - 1))
		return currentKey is None

	def _current(self) -> coreAudio.AudioApp | None:
		if not self._apps:
			return None
		return self._apps[self._index]

	def _currentOrReport(self) -> coreAudio.AudioApp | None:
		"""The selected application, or None (after telling the user why) if no action should be taken."""
		stillThere = self._refresh()
		app = self._current()
		if app is None:
			# Translators: Reported when no application is playing audio.
			ui.message(_("No applications with audio"))
			return None
		if not stillThere:
			# Don't change a different application than the one the user selected.
			# Translators: Reported when the selected application was closed, followed by the new selection.
			ui.message(_("The application was closed") + ", " + self._describe(app))
			return None
		return app

	def _moveTo(self, index: int):
		self._refresh()
		if not self._apps:
			# Translators: Reported when no application is playing audio.
			ui.message(_("No applications with audio"))
			return
		if index < 0 or index >= len(self._apps):
			tones.beep(250, 40)
		else:
			self._index = index
		ui.message(self._describe(self._current()))

	@_reportErrors
	def script_previousApp(self, gesture):
		self._moveTo(self._index - 1)

	@_reportErrors
	def script_nextApp(self, gesture):
		self._moveTo(self._index + 1)

	@_reportErrors
	def script_firstApp(self, gesture):
		self._moveTo(0)

	@_reportErrors
	def script_lastApp(self, gesture):
		self._refresh()
		self._moveTo(len(self._apps) - 1)

	@_reportErrors
	def script_reportCurrent(self, gesture):
		app = self._currentOrReport()
		if app:
			ui.message(self._describe(app))

	# Descriptions

	def _volumeText(self, app: coreAudio.AudioApp) -> str:
		if not app.hasSessions:
			# Translators: Reported for an application that is not using audio right now.
			return _("no audio session")
		if app.isMuted():
			# Translators: Reported for a muted application.
			return _("muted")
		# Translators: Volume of an application, e.g. "volume 80%".
		return _("volume {value}%").format(value=round(app.getVolume() * 100))

	def _getPolicy(self) -> AudioPolicyConfig:
		if self._policy is None:
			self._policy = AudioPolicyConfig()
		return self._policy

	def _deviceLabel(self, deviceId: str | None, flow: int, devices: list[coreAudio.AudioDevice]) -> str:
		if not deviceId:
			default = coreAudio.getDefaultDevice(flow)
			if default is None:
				# Translators: The system default device when no device is available.
				return _("default")
			# Translators: The system default device, e.g. "default (Speakers)".
			return _("default ({device})").format(device=default.name)
		for device in devices:
			if device.id == deviceId:
				return device.name
		# Translators: A device that is no longer connected.
		return _("disconnected device")

	def _appDeviceId(self, app: coreAudio.AudioApp, flow: int) -> str:
		policy = self._getPolicy()
		if app.isSystem or not app.pids or not policy.available:
			return ""
		return policy.getDefaultEndpoint(app.pids[0], flow)

	def _deviceText(self, app: coreAudio.AudioApp, flow: int) -> str:
		devices = coreAudio.listDevices(flow)
		return self._deviceLabel(self._appDeviceId(app, flow), flow, devices)

	def _describe(self, app: coreAudio.AudioApp) -> str:
		return ", ".join((
			app.name,
			self._volumeText(app),
			# Translators: The output device of an application.
			_("output: {device}").format(device=self._deviceText(app, FLOW_RENDER)),
			# Translators: The input device of an application.
			_("input: {device}").format(device=self._deviceText(app, FLOW_CAPTURE)),
		))

	# Volume and mute

	def _changeVolume(self, direction: int):
		app = self._currentOrReport()
		if app is None:
			return
		if not app.hasSessions:
			# Translators: Reported when the volume of an application without audio cannot be changed.
			ui.message(_("This application is not using audio right now"))
			return
		step = config.conf[CONF_SECTION]["volumeStep"]
		current = round(app.getVolume() * 100)
		if direction > 0:
			new = (current // step + 1) * step
		else:
			new = ((current + step - 1) // step - 1) * step
		new = max(0, min(100, new))
		app.setVolume(new / 100)
		if app.isMuted():
			app.setMute(False)
		# Translators: A volume level, e.g. "80%".
		ui.message(_("{value}%").format(value=new))

	@_reportErrors
	def script_volumeUp(self, gesture):
		self._changeVolume(1)

	@_reportErrors
	def script_volumeDown(self, gesture):
		self._changeVolume(-1)

	@_reportErrors
	def script_toggleMute(self, gesture):
		app = self._currentOrReport()
		if app is None:
			return
		if not app.hasSessions:
			# Translators: Reported when the volume of an application without audio cannot be changed.
			ui.message(_("This application is not using audio right now"))
			return
		mute = not app.isMuted()
		app.setMute(mute)
		# Translators: Reported when an application is muted or unmuted.
		ui.message(_("muted") if mute else _("unmuted"))

	# Devices

	def _cycleDevice(self, flow: int, direction: int):
		app = self._currentOrReport()
		if app is None:
			return
		if app.isSystem:
			# Translators: Reported when trying to change the device of system sounds.
			ui.message(_("The device of system sounds follows the Windows default device"))
			return
		policy = self._getPolicy()
		if not policy.available:
			# Translators: Reported when Windows does not support per-application devices.
			ui.message(_("This version of Windows does not support choosing a device per application"))
			return
		devices = coreAudio.listDevices(flow)
		options: list[str | None] = [None] + [device.id for device in devices]
		current = policy.getDefaultEndpoint(app.pids[0], flow) or None
		index = options.index(current) if current in options else 0
		newId = options[(index + direction) % len(options)]
		for pid in app.pids:
			policy.setDefaultEndpoint(pid, flow, newId)
		label = self._deviceLabel(newId, flow, devices)
		if flow == FLOW_RENDER:
			# Translators: Reported after changing the output device.
			ui.message(_("output: {device}").format(device=label))
		else:
			# Translators: Reported after changing the input device.
			ui.message(_("input: {device}").format(device=label))

	@_reportErrors
	def script_previousInputDevice(self, gesture):
		self._cycleDevice(FLOW_CAPTURE, -1)

	@_reportErrors
	def script_nextInputDevice(self, gesture):
		self._cycleDevice(FLOW_CAPTURE, 1)

	@_reportErrors
	def script_previousOutputDevice(self, gesture):
		self._cycleDevice(FLOW_RENDER, -1)

	@_reportErrors
	def script_nextOutputDevice(self, gesture):
		self._cycleDevice(FLOW_RENDER, 1)
