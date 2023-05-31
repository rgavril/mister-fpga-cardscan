#!/usr/bin/python

# TODO:
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

def read_file_contents(file_path):
	try:
		with open(file_path) as f:
			contents = f.read()
		return contents
	except FileNotFoundError:
		logging.warning(f"File '{file_path}' not found.")
	except IOError:
		logging.warning(f"Error reading file '{file_path}'.")
	return None


def find_neogeo_romset_with_altname(altname):
	try:
		root = ET.parse("/media/fat/games/NeoGeo/romsets.xml")
	except Exception as error:
		logging.warning("Cannot find parse xml : /media/fat/games/NeoGeo/romsets.xml")
		return
	
	for romset in root.findall('romset'):
		if romset.get('altname') == altname:
			return romset.get('name')
	return

def update_loaded_with(content):
	if content != read_file_contents(OUTPUT_FILE):
		with open(OUTPUT_FILE, "w") as f:
			f.write(content)
	logging.info(f"************************************")
	logging.info(f"{content}")
	logging.info(f"************************************")	

def wait_until_game_loaded():
	while True:
		# Wait until mister modified /tmp/FILESELECTED
		subprocess.run(("/usr/bin/inotifywait", "-e","MODIFY", "/tmp/FILESELECT"), capture_output=True)
		
		# Retur if was modified because of a file selected event
		if read_file_contents("/tmp/FILESELECT") == "selected":
			return

def find_matching_file(loaded_file, prefix=""):
	# Check if the loaded file is actually a file
	if os.path.isfile(f"/media/fat/{prefix}/{loaded_file}"):
		return os.path.abspath(f"/media/fat/{prefix}/{loaded_file}")

	# Check if the loaded file is within a zip, nothing to much we can do then
	if prefix.endswith(".zip"):
		return os.path.abspath(f"/media/fat/{prefix}/{loaded_file}")

	# Check if the loaded file is missing the file extension
	matched_files = glob.glob(glob.escape(f"/media/fat/{prefix}/{loaded_file}")+".*")
	if len(matched_files) >= 1:
		return os.path.abspath(matched_files[0])

	# Check if the loaded file is a rbd missing the versioning string
	matched_files = glob.glob(glob.escape(f"/media/fat/{prefix}/{loaded_file}")+"_*.rbf")
	if len(matched_files) >= 1:
		return os.path.abspath(matched_files[0])

	# Check if the loaded file is a neogeo altname
	neogeo_romset = find_neogeo_romset_with_altname(loaded_file)
	if neogeo_romset is not None:
		if os.path.exists(f"/media/fat/{prefix}/{neogeo_romset}"):
			return os.path.abspath(f"/media/fat/{prefix}/{neogeo_romset}")
		if os.path.isfile(f"/media/fat/{prefix}/{neogeo_romset}.zip"):
			return os.path.abspath(f"/media/fat/{prefix}/{neogeo_romset}.zip")

	return None



def main():
	logging.info("Game watch process started")
	
	old_STARTPATH = read_file_contents("/tmp/STARTPATH")
	old_CURRENTPATH = read_file_contents("/tmp/CURRENTPATH")

	while True:
		logging.info('Waiting for a file selected event.')
		wait_until_game_loaded()

		FULLPATH    = read_file_contents("/tmp/FULLPATH")
		CURRENTPATH = read_file_contents("/tmp/CURRENTPATH")
		STARTPATH   = read_file_contents("/tmp/STARTPATH")
		CORENAME    = read_file_contents("/tmp/CORENAME")

		if STARTPATH != old_STARTPATH:
			logging.info(f"Change in STARTPATH detected : {STARTPATH}")
			loaded_file = STARTPATH
		elif CURRENTPATH != old_CURRENTPATH:
			logging.info(f"Change in CURRENTPATH detected : {CURRENTPATH}")
			loaded_file = CURRENTPATH
		else:
			logging.debug("Change not detected, ignoring event.")
			continue

		old_CURRENTPATH = CURRENTPATH
		old_STARTPATH = STARTPATH

		logging.debug(f"/tmp/FULLPATH    : {FULLPATH}")
		logging.debug(f"/tmp/CURRENTPATH : {CURRENTPATH}")
		logging.debug(f"/tmp/STARTPATH   : {STARTPATH}")
		logging.debug(f"/tmp/CORENAME    : {CORENAME}")

		if not os.path.isfile(loaded_file):
			matching_file = find_matching_file(loaded_file, FULLPATH)
			if matching_file is None :
				logging.warning(f"Failed to find a file matching {loaded_file}")
				continue;
			loaded_file = matching_file

		logging.debug(f"Loaded file is {loaded_file}")

		if loaded_file.endswith('.mgl'):
			logging.info("A MLG was loaded, tyring to parse it.")
			try:
				mgl_parser = MGLParser(loaded_file)
			except Exception as error:
				logging.warning(f"Cannot load MLG : {error}")
				continue

			try:
				core = mgl_parser.get_core()
			except Exception as error:
				logging.warning(f"Cannot extract core from MLG : {error}")
				continue

			try:
				rom = mgl_parser.get_rom()
			except Exception as warning:
				logging.warning(f"Canot extract rom from MLG : {warning}")
				rom = None

			logging.debug(f"CORE: {core}")
			logging.debug(f"ROM : {rom}")
			
			if rom is not None:
				rom = find_matching_file(rom)
				core = os.path.basename(core) 
				update_loaded_with(f"{core}|{rom}")

			else:
				core = find_matching_file(core)
				update_loaded_with(f"RBF|{core}")
		
		elif loaded_file.endswith('.rbf'):
			update_loaded_with(f"RBF|{loaded_file}")

		elif loaded_file.endswith('.mra'):
			update_loaded_with(f"MRA|{loaded_file}")

		else:
			update_loaded_with(f"{CORENAME}|{loaded_file}")

# logging.basicConfig(format='%(asctime)s %(levelname)s : %(message)s', level=logging.DEBUG, datefmt='%Y-%m-%d %H:%M:%S', filename="/var/log/gamewatch.log")
logging.basicConfig(format='%(asctime)s %(levelname)s : %(message)s', level=logging.DEBUG, datefmt='%Y-%m-%d %H:%M:%S')
if __name__ == "__main__":
    main()
