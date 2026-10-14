"""Builds appVolumeConsole-<version>.nvda-addon from the addon folder.

Compiles every locale/*/LC_MESSAGES/nvda.po to nvda.mo first, so no gettext tools are needed.
Usage: python build.py
"""

import ast
import os
import struct
import zipfile

ROOT = os.path.dirname(os.path.abspath(__file__))
ADDON_DIR = os.path.join(ROOT, "addon")


def parsePo(path: str) -> dict[str, str]:
	messages = {}
	msgid = msgstr = None
	section = None

	def flush():
		if msgid is not None and msgstr:
			messages[msgid] = msgstr

	with open(path, encoding="utf-8") as f:
		for line in f:
			line = line.strip()
			if not line or line.startswith("#"):
				continue
			if line.startswith("msgid "):
				flush()
				msgid, msgstr, section = ast.literal_eval(line[6:]), None, "id"
			elif line.startswith("msgstr "):
				msgstr, section = ast.literal_eval(line[7:]), "str"
			elif line.startswith('"'):
				if section == "id":
					msgid += ast.literal_eval(line)
				else:
					msgstr += ast.literal_eval(line)
	flush()
	return messages


def writeMo(messages: dict[str, str], path: str):
	keys = sorted(messages)
	ids = [k.encode("utf-8") for k in keys]
	strs = [messages[k].encode("utf-8") for k in keys]
	headerSize = 7 * 4
	idsTableOffset = headerSize
	strsTableOffset = idsTableOffset + len(keys) * 8
	dataOffset = strsTableOffset + len(keys) * 8
	idsTable, strsTable, data = [], [], b""
	for s in ids:
		idsTable.append((len(s), dataOffset + len(data)))
		data += s + b"\0"
	for s in strs:
		strsTable.append((len(s), dataOffset + len(data)))
		data += s + b"\0"
	out = struct.pack("<7I", 0x950412DE, 0, len(keys), idsTableOffset, strsTableOffset, 0, 0)
	out += b"".join(struct.pack("<2I", *entry) for entry in idsTable)
	out += b"".join(struct.pack("<2I", *entry) for entry in strsTable)
	out += data
	with open(path, "wb") as f:
		f.write(out)


def readManifestValue(key: str) -> str:
	with open(os.path.join(ADDON_DIR, "manifest.ini"), encoding="utf-8") as f:
		for line in f:
			name, sep, value = line.partition("=")
			if sep and name.strip() == key:
				return value.strip().strip('"')
	raise KeyError(key)


def main():
	localeDir = os.path.join(ADDON_DIR, "locale")
	for lang in os.listdir(localeDir):
		po = os.path.join(localeDir, lang, "LC_MESSAGES", "nvda.po")
		if os.path.isfile(po):
			writeMo(parsePo(po), po[:-3] + ".mo")
	name = readManifestValue("name")
	version = readManifestValue("version")
	target = os.path.join(ROOT, f"{name}-{version}.nvda-addon")
	with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as z:
		# The license lives at the repository root so GitHub detects it.
		z.write(os.path.join(ROOT, "COPYING.txt"), "COPYING.txt")
		for folder, dirs, files in os.walk(ADDON_DIR):
			dirs[:] = [d for d in dirs if d != "__pycache__"]
			for file in files:
				if file.endswith((".po", ".pyc")):
					continue
				full = os.path.join(folder, file)
				z.write(full, os.path.relpath(full, ADDON_DIR))
	print(target)


if __name__ == "__main__":
	main()
