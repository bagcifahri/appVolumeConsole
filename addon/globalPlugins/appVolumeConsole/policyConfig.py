# Application Volume Console for NVDA
# Copyright (C) 2026 Fahri Bağcı
# This file is covered by the GNU General Public License, version 2.
# See the file COPYING.txt for more details.
# Per-application default audio endpoints.
# Windows has no public API for this; the Settings app ("App volume and device preferences")
# uses the undocumented IAudioPolicyConfigFactory WinRT factory, which is what this module calls.
# This module does not import any NVDA modules so it can be tested from plain Python.

import sys
from ctypes import POINTER, WINFUNCTYPE, WinDLL, byref, c_int, c_long, c_uint, c_void_p, cast, wstring_at
from ctypes.wintypes import LPCWSTR

from comtypes import GUID

from .coreAudio import FLOW_CAPTURE, ROLE_CONSOLE, ROLE_MULTIMEDIA

_combase = WinDLL("combase")
_combase.WindowsCreateString.argtypes = (LPCWSTR, c_uint, POINTER(c_void_p))
_combase.WindowsCreateString.restype = c_long
_combase.WindowsDeleteString.argtypes = (c_void_p,)
_combase.WindowsDeleteString.restype = c_long
_combase.WindowsGetStringRawBuffer.argtypes = (c_void_p, POINTER(c_uint))
_combase.WindowsGetStringRawBuffer.restype = c_void_p
_combase.RoGetActivationFactory.argtypes = (c_void_p, POINTER(GUID), POINTER(c_void_p))
_combase.RoGetActivationFactory.restype = c_long

# Windows 10 21H2 (build 21390) and later.
IID_AudioPolicyConfigFactory = GUID("{ab3d4648-e242-459f-b02f-541c70306324}")
# Earlier Windows 10 builds.
IID_AudioPolicyConfigFactoryDownlevel = GUID("{2a59116d-6c4f-45e0-a74f-707e3fef9258}")

_SLOT_RELEASE = 2
# Vtable slots: IUnknown (3) + IInspectable (3) + 19 methods we don't use.
_SLOT_SET_PERSISTED_DEFAULT_ENDPOINT = 25
_SLOT_GET_PERSISTED_DEFAULT_ENDPOINT = 26

_DEVICE_ID_PREFIX = "\\\\?\\SWD#MMDEVAPI#"
_RENDER_INTERFACE_SUFFIX = "#{e6327cad-dcec-4949-ae8a-991e976a79d2}"
_CAPTURE_INTERFACE_SUFFIX = "#{2eef81be-33fa-4800-9670-1cd474972c3f}"


class _HString:
	def __init__(self, text: str):
		self.handle = c_void_p()
		hr = _combase.WindowsCreateString(text, len(text), byref(self.handle))
		if hr < 0:
			raise OSError(hr, "WindowsCreateString failed")

	def __del__(self):
		if self.handle:
			_combase.WindowsDeleteString(self.handle)


def _packDeviceId(deviceId: str, flow: int) -> str:
	suffix = _CAPTURE_INTERFACE_SUFFIX if flow == FLOW_CAPTURE else _RENDER_INTERFACE_SUFFIX
	return f"{_DEVICE_ID_PREFIX}{deviceId}{suffix}"


def _unpackDeviceId(packed: str) -> str:
	if packed.startswith(_DEVICE_ID_PREFIX):
		packed = packed[len(_DEVICE_ID_PREFIX):]
	return packed.split("#", 1)[0]


class AudioPolicyConfig:
	def __init__(self):
		self._factory = None
		className = _HString("Windows.Media.Internal.AudioPolicyConfig")
		iids = [IID_AudioPolicyConfigFactory, IID_AudioPolicyConfigFactoryDownlevel]
		if sys.getwindowsversion().build < 21390:
			iids.reverse()
		for iid in iids:
			factory = c_void_p()
			hr = _combase.RoGetActivationFactory(className.handle, byref(iid), byref(factory))
			if hr >= 0 and factory:
				self._factory = factory
				break

	def release(self):
		if self._factory is not None:
			self._call(_SLOT_RELEASE, ())
			self._factory = None

	@property
	def available(self) -> bool:
		return self._factory is not None

	def _call(self, slot: int, argtypes: tuple, *args) -> int:
		vtable = cast(self._factory, POINTER(POINTER(c_void_p))).contents
		method = WINFUNCTYPE(c_long, c_void_p, *argtypes)(vtable[slot])
		return method(self._factory, *args)

	def getDefaultEndpoint(self, pid: int, flow: int) -> str:
		"""The MMDevice id an application is routed to, or an empty string when it follows the system default."""
		result = c_void_p()
		hr = self._call(
			_SLOT_GET_PERSISTED_DEFAULT_ENDPOINT,
			(c_uint, c_int, c_int, POINTER(c_void_p)),
			pid, flow, ROLE_MULTIMEDIA, byref(result),
		)
		if hr < 0 or not result:
			return ""
		try:
			length = c_uint()
			buf = _combase.WindowsGetStringRawBuffer(result, byref(length))
			packed = wstring_at(buf, length.value) if buf else ""
		finally:
			_combase.WindowsDeleteString(result)
		return _unpackDeviceId(packed)

	def setDefaultEndpoint(self, pid: int, flow: int, deviceId: str | None):
		"""Routes an application to a device; None makes it follow the system default again."""
		hstring = _HString(_packDeviceId(deviceId, flow)) if deviceId else None
		for role in (ROLE_CONSOLE, ROLE_MULTIMEDIA):
			hr = self._call(
				_SLOT_SET_PERSISTED_DEFAULT_ENDPOINT,
				(c_uint, c_int, c_int, c_void_p),
				pid, flow, role, hstring.handle if hstring else None,
			)
			if hr < 0:
				raise OSError(hr, "SetPersistedDefaultAudioEndpoint failed")
