#!/usr/bin/python

# TODO:
#  - When core is loaded, don't save the version after underscore
#  - When core is loaded and not matched, use names.txt to resolve
#  - When neogeo rom is loaed, look it up in the romsets.xml file

import os
import sys
import glob
import xml.etree.ElementTree as ET
import subprocess
import logging
import time

OUTPUT_FILE="/tmp/LOADED"

class MGLParser:
	def __init__(self, filename):
		self.root = ET.parse(filename)

	def get_rom(self):
		node_file = self.root.find('file')
		
		if node_file is None:
			raise Exception("MLG is missing the <file> node.")
			return

		if 'path' not in node_file.attrib:
			raise Exception("MLG is missing 'path' attribute for the <file> node.")
			return

		return node_file.get('path');

	def get_core(self):
		node_rbf = self.root.find('rbf')
		
		if node_rbf is None:
			raise Exception("MLG is missing the <rbf> node.")
			return

		return node_rbf.text

def file_content(filename):
	if not os.path.isfile(filename):
		logging.warning(f"File does not exist : {filename}")
		return ""

	with open(filename) as f:
		return f.readline()

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

def update_loaded_with(content):
	logging.info(f"************************************")
	logging.info(f"{content}")
	logging.info(f"************************************")

	if content != file_content(OUTPUT_FILE):
		with open(OUTPUT_FILE, "w") as f:
			f.write(content)

def translate_neogeo(altname):
	return altname

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
			if "games/NEOGEO" in FULLPATH:
				loaded_file = translate_neogeo(loaded_file)

			logging.info(f"Tyring to locate '{loaded_file}' in '{FULLPATH}'")
			found_file = find_file(FULLPATH+"/"+loaded_file)
			if found_file:
				logging.info(f"Located '{loaded_file}'' : {found_file}")
				loaded_file = found_file
			else:
				logging.warning(f"Failed to locate '{loaded_file}'")
				continue

		if loaded_file.endswith('.mgl'):
			logging.info("A MLG was loaded, tyring to parse it.")
			try:
				mgl_parser = MGLParser(loaded_file)
			except Exception as error:
				loggin.warning(f"Cannot load MLG : {error}")
				continue

			try:
				core = mgl_parser.get_core()
			except Exception as error:
				loggin.warning(f"Cannot extract core from MLG : {error}")
				continue

			try:
				rom = mgl_parser.get_rom()
			except Exception as warning:
				logging.warning(f"Canot extract rom from MLG : {warning}")
				rom = None

			logging.debug(f"CORE: {core}")
			logging.debug(f"ROM : {rom}")
			
			if rom is not None:
				rom = find_file(rom)
				core = os.path.basename(core) 
				update_loaded_with(f"{core}|{rom}")

			else:
				core = find_file(core)
				update_loaded_with(f"RBF|{core}")
		
		elif loaded_file.endswith('.rbf'):
			update_loaded_with(f"RBF|{loaded_file}")

		elif loaded_file.endswith('.mra'):
			update_loaded_with(f"MRA|{loaded_file}")

		else:
			update_loaded_with(f"{CORENAME}|{loaded_file}")

		oldCURRENTPATH = CURRENTPATH
		oldSTARTPATH = STARTPATH


#logging.basicConfig(format='%(asctime)s %(levelname)s : %(message)s', level=logging.DEBUG, datefmt='%Y-%m-%d %H:%M:%S', filename="/var/log/gamewatch.log")
logging.basicConfig(format='%(asctime)s %(levelname)s : %(message)s', level=logging.DEBUG, datefmt='%Y-%m-%d %H:%M:%S')
if __name__ == "__main__":
    main()
