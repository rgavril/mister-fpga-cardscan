#!/usr/bin/python

# TODO:
#  - When game is loaded from MLG, use the core name from mlg
#  - When core is loaded, don't save the version after underscore
#  - When core is loaded and not matched, use names.txt to resolve

import os
import sys
import glob
import xml.etree.ElementTree as ET
import subprocess
import logging
import time

OUTPUT_FILE="/tmp/LOADED"

def file_content(filename):
	if not os.path.isfile(filename):
		logging.warning(f"File does not exist : {filename}")
		return ""

	with open(filename) as f:
		return f.readline()

def rom_from_mgl(mglFilePath):
	logging.debug("Started MGL Parsing")

	root = ET.parse(mglFilePath)
	rbfNode = root.find('rbf')
	fileNode = root.find('file')

	if fileNode is not None and 'path' in fileNode.attrib:
		logging.debug("Parsing from file node : " + fileNode.get('path'))
		romFile = find_file("/" + fileNode.get('path'))
		logging.debug(f"Parsing from file completed : {romFile}")
		return romFile

	elif rbfNode is not None:
		logging.debug(f"Parsing from rbf node : {rbfNode.text}")
		romFile = find_file(rbfNode.text)
		logging.debug(f"Parsing from rbf completed : {romFile}")
		return romFile

	logging.warning("Parsing the mgl file failed!")
	return 

def find_file(match):
	logging.debug(f"Started File Finding : {match}")
	romPath = os.path.abspath(f"/media/fat/{match}")

	if os.path.isfile(romPath):
		logging.debug(f"Matched to : {romPath}")
		return romPath

	# If the file is within a zip
	if ".zip/" in romPath:
		logging.debug(f"Matched to : {romPath}")
		return romPath

	# Check if the file is missing an extension
	romPathFull=glob.glob(glob.escape(romPath)+".*")
	if romPathFull and os.path.isfile(romPathFull[0]):
		logging.debug(f"Matched to : {romPathFull[0]}")
		return romPathFull[0]

	# Check if the file is a core with missing version info
	romPathFull=glob.glob(glob.escape(romPath)+"_*.rbf")
	if romPathFull and os.path.isfile(romPathFull[0]):
		logging.debug(f"Matched to : {romPathFull[0]}")
		return romPathFull[0]

	logging.warning(f"Match not found!")
	return

def update_loaded_with(CORENAME, romPath):
	content = ""
	if romPath.endswith(".rbf"):
		content = f"Core|{romPath}"
	elif romPath.endswith(".mra"):
		content = f"Arcade|{romPath}"
	else:
		content = f"{CORENAME}|{romPath}"

	logging.info(f"WRITING : {content}")

	if content != file_content(OUTPUT_FILE):
		with open(OUTPUT_FILE, "w") as f:
			f.write(content)


def main():
	logging.info("Game watch process started")
	
	oldSTARTPATH = file_content("/tmp/STARTPATH")
	oldCURRENTPATH = file_content("/tmp/CURRENTPATH")

	while 1:
		subprocess.run(("/usr/bin/inotifywait", "-e","MODIFY", "/tmp/FILESELECT"), capture_output=True)
		if file_content("/tmp/FILESELECT") != "selected":
			continue

		time.sleep(1)
		FULLPATH = file_content("/tmp/FULLPATH")
		CURRENTPATH = file_content("/tmp/CURRENTPATH")
		STARTPATH = file_content("/tmp/STARTPATH")
		CORENAME = file_content("/tmp/CORENAME")

		logging.debug("-- START --")
		logging.debug(f"FULLPATH = {FULLPATH}")
		logging.debug(f"CURRENTPATH = {CURRENTPATH}")
		logging.debug(f"STARTPATH = {STARTPATH}")
		logging.debug(f"CORENAME = {CORENAME}")

		romPath = ""
		if STARTPATH != oldSTARTPATH: # Loaded a new Core
			logging.info(f"A core file was loaded ({STARTPATH})")
			romPath = STARTPATH
		elif CURRENTPATH != oldCURRENTPATH: # Loaded a new File
			logging.info(f"A rom file was loded ({CURRENTPATH})")
			romPath = find_file(f"{FULLPATH}/{CURRENTPATH}")

		if romPath and romPath.endswith('.mgl'):
			romPath = rom_from_mgl(romPath)

		if romPath:
			logging.debug(f"Will try to save : {romPath}")			
			update_loaded_with(CORENAME, romPath)
		else:
			logging.debug(f"Cannot resolve loaded game.")

		logging.debug("-- END --")
		oldCURRENTPATH = CURRENTPATH
		oldSTARTPATH = STARTPATH


#logging.basicConfig(format='%(asctime)s %(levelname)s : %(message)s', level=logging.DEBUG, datefmt='%Y-%m-%d %H:%M:%S', filename="/var/log/gamewatch.log")
logging.basicConfig(format='%(asctime)s %(levelname)s : %(message)s', level=logging.DEBUG, datefmt='%Y-%m-%d %H:%M:%S')
if __name__ == "__main__":
    main()
