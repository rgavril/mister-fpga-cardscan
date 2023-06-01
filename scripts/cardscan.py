#!/usr/bin/python

import os
import sys
import getopt
import time
import configparser
import logging

MGL_TEMP_FILE = "/tmp/cardscan.mgl"
CONFIG_FILE = "/media/fat/cardscan.ini"
LOADED_FILE = "/tmp/LOADED"
DEFAULT_SERIAL_PORT = "/dev/ttyUSB0"
DEFAULT_SERIAL_SPEED = "9600"
#logging.basicConfig(format='%(asctime)s %(levelname)s : %(message)s', level=logging.DEBUG, datefmt='%Y-%m-%d %H:%M:%S', filename="/var/log/cardscan.log")
logging.basicConfig(format='%(asctime)s %(levelname)s : %(message)s', level=logging.DEBUG, datefmt='%Y-%m-%d %H:%M:%S')

def read_config():
	config = configparser.ConfigParser()
	config.read(CONFIG_FILE)
	return config

def save_config(config):
	with open(CONFIG_FILE, "w") as file:
		config.write(file)

def setup_config_file():
	config = read_config()

	if not config.has_section('SERIAL'):
		config.add_section('SERIAL')

	if not config.has_option('SERIAL', 'port'):
		config.set('SERIAL', 'port', DEFAULT_SERIAL_PORT)

	if not config.has_option('SERIAL', 'speed'):
		config.set('SERIAL', 'speed', DEFAULT_SERIAL_SPEED)

	if not config.has_section('CARDS'):
		config.add_section('CARDS')

	save_config(config)

def setup_serial_port():
	config = read_config()

	port = config.get('SERIAL', 'port')
	speed = config.get('SERIAL', 'speed')

	os.system(f'stty -F {port} speed {speed} -raw -echo > /dev/null')

	serialPort = open(port, "r")
	logging.info(f"Connected to serial port {port} baud rate {speed}.")
	return serialPort

def countinous_readline(file):
	while True:
		line = file.readline()
		if not line:
			time.sleep(0.1)
			continue
		yield line

def send_mister_cmd(cmd):
	logging.info(f"Mister command {cmd}")
	# os.system('echo \"{cmd}\" > /dev/MiSTer_cmd 2>/dev/null')
	with open("/dev/MiSTer_cmd", "w") as cmdFile:
		cmdFile.write(cmd)

def read_active_game():
	try:
		f = open(LOADED_FILE)
		contents = f.read()
		return contents
	except FileNotFoundError:
		logging.warning(f"Error reading {LOADED_FILE}")
		return None

def make_mgl(rbf, delay, type, index, path):
	mgl = '<mistergamedescription>\n\t<rbf>{}</rbf>\n\t<file delay="{}" type="{}" index="{}" path="{}"/>\n</mistergamedescription>'

	file = open(MGL_TEMP_FILE, "w")
	file.write(mgl.format(rbf, delay, type, index, path))
	file.close()
	return 

def load_game(game):
	if not "|" in game :
		logging.warning(f"Invalid format for game : {game}")
		return 

	index = game.index("|")
	filetype = game[:index].strip()
	filename = game[index+1:].strip()

	if filetype == "RBF" or filetype == "MRA" or filetype == "MGL":
		send_mister_cmd(f'load_core {filename}')
	elif filetype == "NES":
		make_mgl("_Console/NES", 1, "f", 0, "../../../.."+filename)
		send_mister_cmd(f'load_core {MGL_TEMP_FILE}')
	else:
		logging.warning(f"Invalid file type detected : {filetype}")

##
## Continously reads the serial port and performs actions based
## on the id that is received by it.
##
def serial_main_loop():
	logging.info(f"Serial port process started.")
	config = read_config()
	serial = setup_serial_port()
	
	for line in countinous_readline(serial):
		# Skip all lines that don't start with a '['
		if not line.startswith('['):
			continue;

		# Remove formatting data to get the card id
		cardID = line.strip("[]\n");
		logging.info(f'Card reader detected the card with #{cardID}.')

		# Re-read the config file
		config = read_config()

		# If the card was not game associated, write a empty value
		if not config.has_option('CARDS', cardID) :
			config.set('CARDS', cardID, "")
			save_config(config)

		# Read the game associated with the card
		cardGame = config.get('CARDS', cardID).strip('"')

		# Bail out if no game is associated with the card
		if cardGame == "":
			logging.warning(f'Card #{cardID} is not associated to any game.')
			continue
		else:
			logging.info(f'Card #{cardID} is associated to "{cardGame}".')

		# Skip realoadin if the game / card did not change
		activeGame = read_active_game()
		if activeGame == cardGame:
			logging.info(f'Game "{cardGame}" already running.')
			continue

		# Tell MiSTer to load the associated game
		load_game(cardGame)

def display_help():
	print(f"Usage : {sys.argv[0]} [OPTIONS]")
	print("Listen to RFID reader and launch games.")
	print("")
	print("-h, --help   display this help and exit")
	print("-d, --daemon run the application in daemon mode")

def daemonize():
	fpid = os.fork()
	if fpid!=0:
		sys.exit(0)

def main():
	argumentList = sys.argv[1:]
	try:
		arguments, values = getopt.getopt(argumentList, 'hdo:', ["help", "daemon", "output"])
		for currentArgument, currentValue in arguments:
			if currentArgument in ("-h", "--help"):
				display_help()
				sys.exit(0)
			elif currentArgument in ("-d", "--daemon"):
				print("Starting in daemon mode.")
				daemonize()
	except getopt.GetoptError as err:
		print (str(err))

	setup_config_file()
	serial_main_loop()

if __name__ == "__main__":
    main()
