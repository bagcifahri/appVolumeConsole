# Application Volume Console for NVDA
# Copyright (C) 2026 Fahri Bağcı
# This file is covered by the GNU General Public License, version 2.
# See the file COPYING.txt for more details.
# Minimal Windows Core Audio bindings: audio endpoints and per-application audio sessions.
# This module does not import any NVDA modules so it can be tested from plain Python.

import os
from ctypes import (
	HRESULT,
	POINTER,
	Structure,
	Union,
	WinDLL,
	byref,
	c_float,
	c_int,
	c_ubyte,
	c_ushort,
	c_void_p,
	create_unicode_buffer,
	wstring_at,
)
from ctypes.wintypes import BOOL, DWORD, HANDLE, LPCWSTR, LPWSTR, UINT, WORD

from comtypes import CLSCTX_ALL, COMMETHOD, GUID, IUnknown, CoCreateInstance, COMError

# EDataFlow
FLOW_RENDER = 0
FLOW_CAPTURE = 1
# ERole
ROLE_CONSOLE = 0
ROLE_MULTIMEDIA = 1
DEVICE_STATE_ACTIVE = 0x1
STGM_READ = 0
VT_LPWSTR = 31
# AudioSessionState
SESSION_STATE_EXPIRED = 2


class PROPERTYKEY(Structure):
	_fields_ = [("fmtid", GUID), ("pid", DWORD)]


class _PropVariantValue(Union):
	# Padded so the structure is large enough on both 32 and 64 bit.
	_fields_ = [("pwszVal", c_void_p), ("_pad", c_ubyte * 16)]


class PROPVARIANT(Structure):
	_fields_ = [
		("vt", c_ushort),
		("reserved1", WORD),
		("reserved2", WORD),
		("reserved3", WORD),
		("value", _PropVariantValue),
	]


PKEY_Device_FriendlyName = PROPERTYKEY(GUID("{a45c254e-df1c-4efd-8020-67d146a850e0}"), 14)


class IPropertyStore(IUnknown):
	_iid_ = GUID("{886D8EEB-8CF2-4446-8D02-CDBA1DBDCF99}")
	_methods_ = (
		COMMETHOD([], HRESULT, "GetCount", (["out"], POINTER(DWORD), "cProps")),
		COMMETHOD([], HRESULT, "GetAt", (["in"], DWORD, "iProp"), (["out"], POINTER(PROPERTYKEY), "pkey")),
		COMMETHOD(
			[], HRESULT, "GetValue",
			(["in"], POINTER(PROPERTYKEY), "key"),
			(["out"], POINTER(PROPVARIANT), "pv"),
		),
		COMMETHOD(
			[], HRESULT, "SetValue",
			(["in"], POINTER(PROPERTYKEY), "key"),
			(["in"], POINTER(PROPVARIANT), "propvar"),
		),
		COMMETHOD([], HRESULT, "Commit"),
	)


class IMMDevice(IUnknown):
	_iid_ = GUID("{D666063F-1587-4E43-81F1-B948E807363F}")
	_methods_ = (
		COMMETHOD(
			[], HRESULT, "Activate",
			(["in"], POINTER(GUID), "iid"),
			(["in"], DWORD, "dwClsCtx"),
			(["in"], c_void_p, "pActivationParams"),
			(["out"], POINTER(POINTER(IUnknown)), "ppInterface"),
		),
		COMMETHOD(
			[], HRESULT, "OpenPropertyStore",
			(["in"], DWORD, "stgmAccess"),
			(["out"], POINTER(POINTER(IPropertyStore)), "ppProperties"),
		),
		COMMETHOD([], HRESULT, "GetId", (["out"], POINTER(c_void_p), "ppstrId")),
		COMMETHOD([], HRESULT, "GetState", (["out"], POINTER(DWORD), "pdwState")),
	)


class IMMDeviceCollection(IUnknown):
	_iid_ = GUID("{0BD7A1BE-7A1A-44DB-8397-CC5392387B5E}")
	_methods_ = (
		COMMETHOD([], HRESULT, "GetCount", (["out"], POINTER(UINT), "pcDevices")),
		COMMETHOD([], HRESULT, "Item", (["in"], UINT, "nDevice"), (["out"], POINTER(POINTER(IMMDevice)), "ppDevice")),
	)


class IMMDeviceEnumerator(IUnknown):
	_iid_ = GUID("{A95664D2-9614-4F35-A746-DE8DB63617E6}")
	_methods_ = (
		COMMETHOD(
			[], HRESULT, "EnumAudioEndpoints",
			(["in"], c_int, "dataFlow"),
			(["in"], DWORD, "dwStateMask"),
			(["out"], POINTER(POINTER(IMMDeviceCollection)), "ppDevices"),
		),
		COMMETHOD(
			[], HRESULT, "GetDefaultAudioEndpoint",
			(["in"], c_int, "dataFlow"),
			(["in"], c_int, "role"),
			(["out"], POINTER(POINTER(IMMDevice)), "ppEndpoint"),
		),
		COMMETHOD([], HRESULT, "GetDevice", (["in"], LPCWSTR, "pwstrId"), (["out"], POINTER(POINTER(IMMDevice)), "ppDevice")),
		COMMETHOD([], HRESULT, "RegisterEndpointNotificationCallback", (["in"], c_void_p, "pClient")),
		COMMETHOD([], HRESULT, "UnregisterEndpointNotificationCallback", (["in"], c_void_p, "pClient")),
	)


CLSID_MMDeviceEnumerator = GUID("{BCDE0395-E52F-467C-8E3D-C4579291692E}")


class ISimpleAudioVolume(IUnknown):
	_iid_ = GUID("{87CE5498-68D6-44E5-9215-6DA47EF883D8}")
	_methods_ = (
		COMMETHOD([], HRESULT, "SetMasterVolume", (["in"], c_float, "fLevel"), (["in"], POINTER(GUID), "EventContext")),
		COMMETHOD([], HRESULT, "GetMasterVolume", (["out"], POINTER(c_float), "pfLevel")),
		COMMETHOD([], HRESULT, "SetMute", (["in"], BOOL, "bMute"), (["in"], POINTER(GUID), "EventContext")),
		COMMETHOD([], HRESULT, "GetMute", (["out"], POINTER(BOOL), "pbMute")),
	)


class IAudioSessionControl(IUnknown):
	_iid_ = GUID("{F4B1A599-7266-4319-A8CA-E70ACB11E8CD}")
	_methods_ = (
		COMMETHOD([], HRESULT, "GetState", (["out"], POINTER(c_int), "pRetVal")),
		COMMETHOD([], HRESULT, "GetDisplayName", (["out"], POINTER(c_void_p), "pRetVal")),
		COMMETHOD([], HRESULT, "SetDisplayName", (["in"], LPCWSTR, "Value"), (["in"], POINTER(GUID), "EventContext")),
		COMMETHOD([], HRESULT, "GetIconPath", (["out"], POINTER(c_void_p), "pRetVal")),
		COMMETHOD([], HRESULT, "SetIconPath", (["in"], LPCWSTR, "Value"), (["in"], POINTER(GUID), "EventContext")),
		COMMETHOD([], HRESULT, "GetGroupingParam", (["out"], POINTER(GUID), "pRetVal")),
		COMMETHOD([], HRESULT, "SetGroupingParam", (["in"], POINTER(GUID), "Override"), (["in"], POINTER(GUID), "EventContext")),
		COMMETHOD([], HRESULT, "RegisterAudioSessionNotification", (["in"], c_void_p, "NewNotifications")),
		COMMETHOD([], HRESULT, "UnregisterAudioSessionNotification", (["in"], c_void_p, "NewNotifications")),
	)


class IAudioSessionControl2(IAudioSessionControl):
	_iid_ = GUID("{BFB7FF88-7239-4FC9-8FA2-07C950BE9C6D}")
	_methods_ = (
		COMMETHOD([], HRESULT, "GetSessionIdentifier", (["out"], POINTER(c_void_p), "pRetVal")),
		COMMETHOD([], HRESULT, "GetSessionInstanceIdentifier", (["out"], POINTER(c_void_p), "pRetVal")),
		COMMETHOD([], HRESULT, "GetProcessId", (["out"], POINTER(DWORD), "pRetVal")),
		COMMETHOD([], HRESULT, "IsSystemSoundsSession"),
		COMMETHOD([], HRESULT, "SetDuckingPreference", (["in"], BOOL, "optOut")),
	)


class IAudioSessionEnumerator(IUnknown):
	_iid_ = GUID("{E2F5BB11-0570-40CA-ACDD-3AA01277DEE8}")
	_methods_ = (
		COMMETHOD([], HRESULT, "GetCount", (["out"], POINTER(c_int), "SessionCount")),
		COMMETHOD(
			[], HRESULT, "GetSession",
			(["in"], c_int, "SessionCount"),
			(["out"], POINTER(POINTER(IAudioSessionControl)), "Session"),
		),
	)


class IAudioSessionManager(IUnknown):
	_iid_ = GUID("{BFA971F1-4D5E-40BB-935E-967039BFBEE4}")
	_methods_ = (
		COMMETHOD(
			[], HRESULT, "GetAudioSessionControl",
			(["in"], POINTER(GUID), "AudioSessionGuid"),
			(["in"], DWORD, "StreamFlags"),
			(["out"], POINTER(POINTER(IAudioSessionControl)), "SessionControl"),
		),
		COMMETHOD(
			[], HRESULT, "GetSimpleAudioVolume",
			(["in"], POINTER(GUID), "AudioSessionGuid"),
			(["in"], DWORD, "StreamFlags"),
			(["out"], POINTER(POINTER(ISimpleAudioVolume)), "AudioVolume"),
		),
	)


class IAudioSessionManager2(IAudioSessionManager):
	_iid_ = GUID("{77AA99A0-1BD6-484F-8BC7-2C654C9A9B6F}")
	_methods_ = (
		COMMETHOD([], HRESULT, "GetSessionEnumerator", (["out"], POINTER(POINTER(IAudioSessionEnumerator)), "SessionEnum")),
		COMMETHOD([], HRESULT, "RegisterSessionNotification", (["in"], c_void_p, "SessionNotification")),
		COMMETHOD([], HRESULT, "UnregisterSessionNotification", (["in"], c_void_p, "SessionNotification")),
		COMMETHOD([], HRESULT, "RegisterDuckNotification", (["in"], LPCWSTR, "sessionID"), (["in"], c_void_p, "duckNotification")),
		COMMETHOD([], HRESULT, "UnregisterDuckNotification", (["in"], c_void_p, "duckNotification")),
	)


_ole32 = WinDLL("ole32")
_ole32.CoTaskMemFree.argtypes = (c_void_p,)
_ole32.CoTaskMemFree.restype = None
_ole32.PropVariantClear.argtypes = (POINTER(PROPVARIANT),)
_ole32.PropVariantClear.restype = HRESULT

_kernel32 = WinDLL("kernel32")
_kernel32.OpenProcess.argtypes = (DWORD, BOOL, DWORD)
_kernel32.OpenProcess.restype = HANDLE
_kernel32.QueryFullProcessImageNameW.argtypes = (HANDLE, DWORD, LPWSTR, POINTER(DWORD))
_kernel32.QueryFullProcessImageNameW.restype = BOOL
_kernel32.CloseHandle.argtypes = (HANDLE,)
_kernel32.CloseHandle.restype = BOOL

_version = WinDLL("version")
_version.GetFileVersionInfoSizeW.argtypes = (LPCWSTR, POINTER(DWORD))
_version.GetFileVersionInfoSizeW.restype = DWORD
_version.GetFileVersionInfoW.argtypes = (LPCWSTR, DWORD, DWORD, c_void_p)
_version.GetFileVersionInfoW.restype = BOOL
_version.VerQueryValueW.argtypes = (c_void_p, LPCWSTR, POINTER(c_void_p), POINTER(UINT))
_version.VerQueryValueW.restype = BOOL

PROCESS_QUERY_LIMITED_INFORMATION = 0x1000


def _takeCoTaskString(ptr) -> str:
	"""Reads a string allocated with CoTaskMemAlloc and frees it."""
	if not ptr:
		return ""
	try:
		return wstring_at(ptr)
	finally:
		_ole32.CoTaskMemFree(ptr)


def getProcessImagePath(pid: int) -> str | None:
	"""Returns the full executable path of a process, or None if it is not running or not accessible."""
	if not pid:
		return None
	handle = _kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
	if not handle:
		return None
	try:
		size = DWORD(1024)
		buf = create_unicode_buffer(size.value)
		if not _kernel32.QueryFullProcessImageNameW(handle, 0, buf, byref(size)):
			return None
		return buf.value
	finally:
		_kernel32.CloseHandle(handle)


_descriptionCache: dict[str, str] = {}


def getFileDescription(path: str) -> str:
	"""Returns the FileDescription from an executable's version resource, or an empty string."""
	key = path.lower()
	if key in _descriptionCache:
		return _descriptionCache[key]
	description = ""
	try:
		size = _version.GetFileVersionInfoSizeW(path, None)
		if size:
			data = create_unicode_buffer(size)
			if _version.GetFileVersionInfoW(path, 0, size, data):
				translations = []
				ptr = c_void_p()
				length = UINT()
				if _version.VerQueryValueW(data, "\\VarFileInfo\\Translation", byref(ptr), byref(length)) and ptr:
					words = (c_ushort * (length.value // 2)).from_address(ptr.value)
					for i in range(0, len(words) - 1, 2):
						translations.append("%04x%04x" % (words[i], words[i + 1]))
				translations.extend(("040904b0", "040904e4", "041f04b0"))
				for translation in translations:
					if _version.VerQueryValueW(
						data,
						f"\\StringFileInfo\\{translation}\\FileDescription",
						byref(ptr),
						byref(length),
					) and ptr and length.value > 1:
						description = wstring_at(ptr.value, length.value).rstrip("\0").strip()
						if description:
							break
	except OSError:
		description = ""
	_descriptionCache[key] = description
	return description


def getAppName(path: str) -> str:
	"""A user friendly name for an executable."""
	if os.path.basename(path).lower() in ("nvda.exe", "nvda_uiaccess.exe", "nvda_nouiaccess.exe"):
		return "NVDA"
	return getFileDescription(path) or os.path.splitext(os.path.basename(path))[0]


class AudioDevice:
	def __init__(self, deviceId: str, name: str):
		self.id = deviceId
		self.name = name

	def __repr__(self):
		return f"AudioDevice({self.name!r}, {self.id!r})"


def _getEnumerator():
	return CoCreateInstance(CLSID_MMDeviceEnumerator, IMMDeviceEnumerator, CLSCTX_ALL)


def _deviceFromCom(device) -> AudioDevice:
	deviceId = _takeCoTaskString(device.GetId())
	name = ""
	try:
		store = device.OpenPropertyStore(STGM_READ)
		value = store.GetValue(byref(PKEY_Device_FriendlyName))
		try:
			if value.vt == VT_LPWSTR and value.value.pwszVal:
				name = wstring_at(value.value.pwszVal)
		finally:
			_ole32.PropVariantClear(byref(value))
	except COMError:
		pass
	return AudioDevice(deviceId, name or deviceId)


def _iterComDevices(enumerator, flow: int):
	collection = enumerator.EnumAudioEndpoints(flow, DEVICE_STATE_ACTIVE)
	for i in range(collection.GetCount()):
		yield collection.Item(i)


def listDevices(flow: int) -> list[AudioDevice]:
	"""Active endpoints for the given data flow (FLOW_RENDER or FLOW_CAPTURE)."""
	enumerator = _getEnumerator()
	return [_deviceFromCom(d) for d in _iterComDevices(enumerator, flow)]


def getDefaultDevice(flow: int) -> AudioDevice | None:
	try:
		device = _getEnumerator().GetDefaultAudioEndpoint(flow, ROLE_MULTIMEDIA)
	except COMError:
		return None
	return _deviceFromCom(device)


class AudioApp:
	"""One application, possibly with several processes and several audio sessions."""

	def __init__(self, key: str, name: str, isSystem: bool = False):
		self.key = key
		self.name = name
		self.isSystem = isSystem
		self.pids: list[int] = []
		self.sessions: list = []  # ISimpleAudioVolume pointers

	def __repr__(self):
		return f"AudioApp({self.name!r}, pids={self.pids}, sessions={len(self.sessions)})"

	@property
	def hasSessions(self) -> bool:
		return bool(self.sessions)

	def getVolume(self) -> float:
		return self.sessions[0].GetMasterVolume()

	def setVolume(self, level: float):
		level = min(1.0, max(0.0, level))
		for session in self.sessions:
			session.SetMasterVolume(level, None)

	def isMuted(self) -> bool:
		return all(session.GetMute() for session in self.sessions)

	def setMute(self, mute: bool):
		for session in self.sessions:
			session.SetMute(mute, None)


def getAudioApps(systemSoundsName: str = "System sounds") -> list[AudioApp]:
	"""Applications that currently own an audio session on any active output device, sorted by name."""
	apps: dict[str, AudioApp] = {}
	enumerator = _getEnumerator()
	for device in _iterComDevices(enumerator, FLOW_RENDER):
		try:
			manager = device.Activate(IAudioSessionManager2._iid_, CLSCTX_ALL, None)
			manager = manager.QueryInterface(IAudioSessionManager2)
			sessionEnum = manager.GetSessionEnumerator()
			count = sessionEnum.GetCount()
		except COMError:
			continue
		for i in range(count):
			try:
				control = sessionEnum.GetSession(i).QueryInterface(IAudioSessionControl2)
				if control.GetState() == SESSION_STATE_EXPIRED:
					continue
				pid = control.GetProcessId()
				volume = control.QueryInterface(ISimpleAudioVolume)
			except COMError:
				continue
			if pid == 0:
				key = "#system"
				app = apps.get(key)
				if app is None:
					app = apps[key] = AudioApp(key, systemSoundsName, isSystem=True)
			else:
				path = getProcessImagePath(pid)
				if not path:
					# The process has exited but its session has not expired yet.
					continue
				key = path.lower()
				app = apps.get(key)
				if app is None:
					app = apps[key] = AudioApp(key, getAppName(path))
			if pid not in app.pids:
				app.pids.append(pid)
			app.sessions.append(volume)
	return sortApps(list(apps.values()))


def sortApps(apps: list[AudioApp]) -> list[AudioApp]:
	return sorted(apps, key=lambda app: (app.isSystem, app.name.casefold()))
