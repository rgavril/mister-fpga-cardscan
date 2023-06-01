#!/usr/bin/python

# TODO:
#  - When core is loaded, don't save the version after underscore

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

def find_rbf_with_alias(alias):
	try:
		file = open("/media/fat/names.txt")
	except FileNotFoundError as error:
		logging.debug("File '/media/fat/names.txt' not found.")
		return None
	except IOError as error:
		logging.debug("Error reading file '/media/fat/names.txt'.")
		return None

	for line in file:
		if not ":" in line:
			continue		
		index = line.index(':')
		core_name  = line[:index].strip()
		core_alias = line[index+1:].strip()
		if core_alias == alias:
			return core_name

	return None

def update_loaded_with(content):
	if content != read_file_contents(OUTPUT_FILE):
		with open(OUTPUT_FILE, "w") as f:
			f.write(content)
	logging.info(f"************************************")
	logging.info(f"{content}")
	logging.info(f"************************************")	


def wait_mister_file_selection():
	while True:
		# Wait until mister modifies /tmp/FILESELECTED
		# NOTE: Need to use external inotifywait as the 
		#       python library is missing on mister.
		subprocess.run(("/usr/bin/inotifywait", "-e","MODIFY", "/tmp/FILESELECT"), capture_output=True)

		# Return only on a file selected event
		if read_file_contents("/tmp/FILESELECT") == "selected":
			return

def get_mister_file_selection():
	# Read the current values of misters's CURRENTPATH and STARTPATH
	# files as one of them hold the current selection.
	currentpath = read_file_contents("/tmp/CURRENTPATH")
	startpath   = read_file_contents("/tmp/STARTPATH")

	# First checking if STARTPATH content changed. 
	# It usually changes when a core, mlg or mra was loaded.
	if get_mister_file_selection.startpath_old != startpath:
		selection = startpath

	# Second check if CURRENTPATH content changed.
	# It usually changes when a rom was loaded.
	elif get_mister_file_selection.currentpath_old != currentpath:	
		selection = currentpath

	# If none of the files changed, we can't figure out what was selected.
	# Is very common for mister to send selected events without something 
	# actualy changing.
	else:
		selection = None
	
	# Save the current values so we can compare against them the next time
	get_mister_file_selection.startpath_old = startpath
	get_mister_file_selection.currentpath_old = currentpath

	return selection
get_mister_file_selection.startpath_old = ""
get_mister_file_selection.currentpath_old = ""


def find_matching_file(loaded_file, prefix=""):
	# Check if the loaded fine is actually a file
	if os.path.isfile(loaded_file):
		return os.path.abspath(loaded_file)

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

	# Check if the loaded file is a names.txt alias of a core
	rbf = find_rbf_with_alias(loaded_file)
	if rbf is not None:
		matched_files = glob.glob(glob.escape(f"/media/fat/{prefix}/{rbf}")+"_*.rbf")
		if len(matched_files) >= 1:
			return os.path.abspath(matched_files[0])

	return None


def main():
	logging.info("Game watch process started")
	
	# # Save current value ot STARTPATH and CURRENTPATH so we can
	# # test which one has changed, later when a game/core is loaded.
	# # At least one of them changes and will give us a hint on what was loaded.
	# old_STARTPATH = read_file_contents("/tmp/STARTPATH")
	# old_CURRENTPATH = read_file_contents("/tmp/CURRENTPATH")

	while True:
		# Wait until mister changes the contents of /tmp/FILESELECT to "selected"
		logging.info("Waiting for a file selected event.")
		wait_mister_file_selection();

		# Wait for selected file
		selected_file = get_mister_file_selection()
		if selected_file is None:
			logging.info("Selection is not valid, false event.")
			continue;

		# Read what mister wrote in the information files
		FULLPATH    = read_file_contents("/tmp/FULLPATH")
		CURRENTPATH = read_file_contents("/tmp/CURRENTPATH")
		STARTPATH   = read_file_contents("/tmp/STARTPATH")
		CORENAME    = read_file_contents("/tmp/CORENAME")

		# Debugging to see what was the content of the files
		logging.debug(f"/tmp/FULLPATH    : {FULLPATH}")
		logging.debug(f"/tmp/CURRENTPATH : {CURRENTPATH}")
		logging.debug(f"/tmp/STARTPATH   : {STARTPATH}")
		logging.debug(f"/tmp/CORENAME    : {CORENAME}")

		# Try to backtrace the mister selection to an actual file
		loaded_file = find_matching_file(selected_file, FULLPATH)

		# If we could not match it to a file, stop doing anyting
		if loaded_file is None :
			logging.warning(f"Failed to find a file matching {selected_file}")
			continue;

		# Debuging to see what file we detected
		logging.debug(f"Loaded file is {loaded_file}")

		# If the loaded file is actually a MGL we need to see what was actually loaded
		# by looking within the file.
		if loaded_file.endswith('.mgl'):
			logging.info("A MLG was loaded, tyring to parse it.")
			try:
				mgl_parser = MGLParser(loaded_file)
			# If we cannot open MGL, there is nothing else to do
			except Exception as error:
				logging.warning(f"Cannot load MLG : {error}")
				continue

			# Tyring ro read the core loeaded trough the MGL 
			try:
				core = mgl_parser.get_core()
			# A MGL without a core (rbf) is impossible afaik, so we're out
			except Exception as error:
				logging.warning(f"Cannot extract core from MGL : {error}")
				continue

			# Trying to read the rom loaded trought the MGL
			try:
				rom = mgl_parser.get_rom()
			# Is possible to not read a rom if the MGL is loading only the rbf
			except Exception as warning:
				logging.info(f"Canot extract rom from MGL : {warning}")
				rom = None

			# Do some debugging to figure out what we got
			logging.debug(f"CORE: {core}")
			logging.debug(f"ROM : {rom}")
			
			# If a rom was loaded, create a entry for it
			if rom is not None:
				rom = find_matching_file(rom)
				core = os.path.basename(core) 
				update_loaded_with(f"{core}|{rom}")
			# If a rom was not loaded, we probably need to load the core
			else:
				core = find_matching_file(core)
				update_loaded_with(f"RBF|{core}")
		
		# If the file loaded was not a MLG (Shortcut) but a RBF (Core)
		elif loaded_file.endswith('.rbf'):
			update_loaded_with(f"RBF|{loaded_file}")

		# If the file loaded ir a MRA (Arcade Shortcut)
		elif loaded_file.endswith('.mra'):
			update_loaded_with(f"MRA|{loaded_file}")

		# If is not a MRA, RBF or MGL than it must be a ROM
		else:
			update_loaded_with(f"{CORENAME}|{loaded_file}")

# logging.basicConfig(format='%(asctime)s %(levelname)s : %(message)s', level=logging.DEBUG, datefmt='%Y-%m-%d %H:%M:%S', filename="/var/log/gamewatch.log")
logging.basicConfig(format='%(asctime)s %(levelname)s : %(message)s', level=logging.DEBUG, datefmt='%Y-%m-%d %H:%M:%S')
if __name__ == "__main__":
    main()
