#!/usr/bin/python

# TODO:
#  - When core is loaded, don't save the version after underscore
#  - Lookup mlg aliases in names.txt, aparenty they also match agains that

import os
import sys
import glob
import xml.etree.ElementTree as ET
import subprocess
import logging
import time

OUTPUT_FILE="/tmp/LOADED"
# logging.basicConfig(format='%(asctime)s %(levelname)s : %(message)s', level=logging.DEBUG, datefmt='%Y-%m-%d %H:%M:%S', filename="/var/log/gamewatch.log")
logging.basicConfig(format='%(asctime)s %(levelname)s : %(message)s', level=logging.DEBUG, datefmt='%Y-%m-%d %H:%M:%S')


def get_rbf_from_mgl(mgl_filename):
	# Try to load MGL file for parsing
	try:
		root = ET.parse(mgl_filename)
	except Exception as error:
		logging.error(f"Error parsing MLG : {error}")
		return None

	# Find the <rbf /> node in the mgl
	node_rbf = root.find('rbf')
	if node_rbf is None:
		logging.warning(f"MLG is missing the <rbf> entry.")
		return None

	# Return whatever is written inside the <rbf /> node
	return node_rbf.text


def get_file_path_from_mgl(mgl_filename):
	# Try to load MGL file for parsing
	try:
		root = ET.parse(mgl_filename)
	except Exception as error:
		logging.error(f"Error parsing MLG : {error}")
		return None

	# Find the <file /> node in the mgl
	file = root.find('file')
	if file is None:
		# Sometimes the <file /> node is missing, which is normal as there
		# are mgl files that only load cores.
		logging.warning(f"MLG is missing the <file /> entry.")
		return None

	# The path attribute shuld not be missing from the <file /> node afaik
	if 'path' not in file.attrib:
		logging.error("MLG is missing the 'path' attribute for the <file /> node.")
		return None

	# Return the path attrinute of the file node
	return file.get('path');


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
			break

	# Debugging to see what was the content of the files
	logging.debug(f"/tmp/FULLPATH    : " + read_file_contents("/tmp/FULLPATH"))
	logging.debug(f"/tmp/CURRENTPATH : " + read_file_contents("/tmp/CURRENTPATH"))
	logging.debug(f"/tmp/STARTPATH   : " + read_file_contents("/tmp/STARTPATH"))
	logging.debug(f"/tmp/CORENAME    : " + read_file_contents("/tmp/CORENAME"))


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

	while True:
		# Wait until mister changes the contents of /tmp/FILESELECT to "selected"
		logging.info("Waiting for MiSTer to write 'selected' in /tmp/FILESELECT.")
		wait_mister_file_selection();

		# Check if mister also reported a change in the seleted/loaded file
		selected_file = get_mister_file_selection()
		logging.info(f"Reported as loaded : {selected_file}")
		if selected_file is None:
			continue;

		# Try to backtrace the mister selection to an actual file
		fullpath = read_file_contents("/tmp/FULLPATH")
		loaded_file = find_matching_file(selected_file, fullpath)
		logging.info(f"Matched to file : {loaded_file}")

		# If we could not match it to a file, stop doing anyting
		if loaded_file is None :
			logging.warning(f"Failed to find a file matching {selected_file} in {fullpath}")
			continue;

		# If the loaded file is actually a MGL we need to see what was actually loaded
		# by looking within the file.
		if loaded_file.endswith('.mgl'):
			# Tyring ro read the core loeaded trough the MGL 
			core = get_rbf_from_mgl(loaded_file)
			rom  = get_file_path_from_mgl(loaded_file)

			logging.info(f"MGL is running the rbf : {core}")
			logging.info(f"MLG is loading the rom : {rom}")
			
			# If a rom was loaded, create a entry for it
			if rom is not None:
				rom  = os.path.abspath(f"/media/fat/{rom}")
				core = os.path.basename(core) 
				update_loaded_with(f"{core}|{rom}")
			# If a rom was not loaded, we probably need to load the core
			elif core is not None:
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
			core = read_file_contents("/tmp/CORENAME")
			update_loaded_with(f"{core}|{loaded_file}")

if __name__ == "__main__":
    main()
