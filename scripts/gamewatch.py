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

def wait_until_game_loaded():
	""" Wait until mister sends a file selected event """

	while True:
		# We can't use the inotify in python so we fallback to the inotifywait
		subprocess.run(("/usr/bin/inotifywait", "-e","MODIFY", "/tmp/FILESELECT"), capture_output=True)

		# Check the contents of the file and exit when "selected" is found in the file
		if file_content("/tmp/FILESELECT") == "selected":
			return

def main():
	logging.info("Game watch process started")
	
	oldSTARTPATH = file_content("/tmp/STARTPATH")
	oldCURRENTPATH = file_content("/tmp/CURRENTPATH")

	while True:
		logging.info('Waiting for a file selected event.')
		wait_until_game_loaded()

		FULLPATH    = file_content("/tmp/FULLPATH")
		CURRENTPATH = file_content("/tmp/CURRENTPATH")
		STARTPATH   = file_content("/tmp/STARTPATH")
		CORENAME    = file_content("/tmp/CORENAME")

		if STARTPATH != oldSTARTPATH:
			logging.info(f"Change in STARTPATH detected : {STARTPATH}")
			loaded_file = STARTPATH
		elif CURRENTPATH != oldCURRENTPATH:
			logging.info(f"Change in CURRENTPATH detected : {CURRENTPATH}")
			loaded_file = CURRENTPATH
		else:
			logging.debug("Change not detected, ignoring event.")
			continue

		logging.debug(f"/tmp/FULLPATH    : {FULLPATH}")
		logging.debug(f"/tmp/CURRENTPATH : {CURRENTPATH}")
		logging.debug(f"/tmp/STARTPATH   : {STARTPATH}")
		logging.debug(f"/tmp/CORENAME    : {CORENAME}")

		if not os.path.isfile(loaded_file):
			logging.info(f"Tyring to locate '{loaded_file}' in '{FULLPATH}'")
			found_file = find_file(FULLPATH+"/"+loaded_file)
			if found_file:
				logging.info(f"Located '{loaded_file}'' : {found_file}")
				loaded_file = found_file
			else:
				logging.warning(f"Failed to locate '{loaded_file}'")
				continue

		if loaded_file.endswith('.mgl'):
			logging.info("Detected MLG, trying to extract the rom loaded.")
			found_file = rom_from_mgl(loaded_file)
			if found_file:
				logging.info(f"Detected {found_file} from mgl.")
				loaded_file = found_file
			else:
				logging.warning(f"Failed to detect file from mlg.")
				continue;


		if loaded_file:
			logging.debug(f"Will try to save : {loaded_file}")			
			update_loaded_with(CORENAME, loaded_file)
		else:
			logging.debug(f"Cannot resolve loaded game.")

		oldCURRENTPATH = CURRENTPATH
		oldSTARTPATH = STARTPATH


#logging.basicConfig(format='%(asctime)s %(levelname)s : %(message)s', level=logging.DEBUG, datefmt='%Y-%m-%d %H:%M:%S', filename="/var/log/gamewatch.log")
logging.basicConfig(format='%(asctime)s %(levelname)s : %(message)s', level=logging.DEBUG, datefmt='%Y-%m-%d %H:%M:%S')
if __name__ == "__main__":
    main()
