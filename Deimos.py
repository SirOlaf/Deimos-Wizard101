import asyncio
import traceback

import requests
import wizwalker
from wizwalker import Keycode, HotkeyListener, ModifierKeys, utils, XYZ
from wizwalker.client_handler import ClientHandler, Client
from wizwalker.extensions.scripting import teleport_to_friend_from_list
from wizwalker.combat import CombatMember
import os
import time
import sys
import subprocess
from loguru import logger
import datetime
from configparser import ConfigParser
import statistics
import re
from pypresence import AioPresence
from src.drop_logger import logging_loop
from src.combat import Fighter
from src.teleport_math import navmap_tp, calc_Distance
# from src.questing import Quester
from src.questing_new import Quester
from src.sigil import Sigil
from src.utils import is_visible_by_path, is_free, auto_potions, auto_potions_force_buy, to_world, collect_wisps, collect_wisps_with_limit
from src.paths import advance_dialog_path, decline_quest_path
import PySimpleGUI as gui
import pyperclip
from src.sprinty_client import SprintyClient
from src.gui_inputs import param_input
from wizwalker.extensions.wizsprinter.wiz_navigator import toZoneDisplayName, toZone
from typing import List, Tuple


tool_version = '3.6.0'
tool_name = 'Deimos'
repo_name = tool_name + '-Wizard101'
branch = 'master'

type_format_dict = {
"char": "<c",
"signed char": "<b",
"unsigned char": "<B",
"bool": "?",
"short": "<h",
"unsigned short": "<H",
"int": "<i",
"unsigned int": "<I",
"long": "<l",
"unsigned long": "<L",
"long long": "<q",
"unsigned long long": "<Q",
"float": "<f",
"double": "<d",
}


def remove_if_exists(file_name : str, sleep_after : float = 0.1):
	if os.path.exists(file_name):
		os.remove(file_name)
		time.sleep(sleep_after)


def download_file(url: str, file_name : str, delete_previous: bool = False, debug : str = True):
	if delete_previous:
		remove_if_exists(file_name)
	if debug:
		print(f'Downloading {file_name}...')
	with requests.get(url, stream=True) as r:
		with open(file_name, 'wb') as f:
			for chunk in r.iter_content(chunk_size=128000):
				f.write(chunk)


# reading hotkeys from config
parser = ConfigParser()


def read_config(config_name : str):
	parser.read(config_name)

	# Settings
	global auto_updating
	global speed_multiplier
	global wiz_path
	global use_potions
	global rpc_status
	global drop_status
	auto_updating = parser.getboolean('settings', 'auto_updating', fallback=True)
	speed_multiplier = parser.getfloat('settings', 'speed_multiplier', fallback=5.0)
	wiz_path = parser.get('settings', 'wiz_path', fallback=None)
	use_potions = parser.get('settings', 'use_potions', fallback=True)
	rpc_status = parser.getboolean('settings', 'rich_presence', fallback=True)
	drop_status = parser.getboolean('settings', 'drop_logging', fallback=True)

	# Hotkeys
	global x_press_key
	global sync_locations_key
	global quest_teleport_key
	global mass_quest_teleport_key
	global toggle_speed_key
	global friend_teleport_key
	global kill_tool_key
	global toggle_auto_combat_key
	global toggle_auto_dialogue_key
	global toggle_auto_sigil_key
	global toggle_freecam_key
	global toggle_auto_questing_key
	x_press_key = parser.get('hotkeys', 'x_press', fallback='X')
	sync_locations_key = parser.get('hotkeys', 'sync_client_locations', fallback='F8')
	quest_teleport_key = parser.get('hotkeys', 'quest_teleport', fallback='F7')
	mass_quest_teleport_key = parser.get('hotkeys', 'mass_quest_teleport', fallback='F6')
	toggle_speed_key = parser.get('hotkeys', 'toggle_speed_multiplier', fallback='F5')
	friend_teleport_key = parser.get('hotkeys', 'friend_teleport', fallback='EIGHT')
	kill_tool_key = parser.get('hotkeys', 'kill_tool', fallback='F9')
	toggle_auto_combat_key = parser.get('hotkeys', 'toggle_auto_combat', fallback='NINE')
	toggle_auto_dialogue_key = parser.get('hotkeys', 'toggle_auto_dialogue', fallback='F4')
	toggle_auto_sigil_key = parser.get('hotkeys', 'toggle_auto_sigil', fallback='F2')
	toggle_freecam_key = parser.get('hotkeys', 'toggle_freecam', fallback='F1')
	toggle_auto_questing_key = parser.get('hotkeys', 'toggle_auto_questing', fallback='F3')

	# GUI Settings
	global show_gui
	global gui_on_top
	global gui_theme
	global gui_text_color
	global gui_button_color
	show_gui = parser.getboolean('gui', 'show_gui', fallback=True)
	gui_on_top = parser.getboolean('gui', 'on_top', fallback=True)
	gui_theme = parser.get('gui', 'theme', fallback='Black')
	gui_text_color = parser.get('gui', 'text_color', fallback='white')
	gui_button_color = parser.get('gui', 'button_color', fallback='#4a019e')

	# Auto Sigil Settings
	global use_team_up
	global buy_potions
	global client_to_follow
	use_team_up = parser.getboolean('sigil', 'use_team_up', fallback=False)
	buy_potions = parser.getboolean('settings', 'buy_potions', fallback=True)
	client_to_follow = parser.get('sigil', 'client_to_follow', fallback=None)

	# Auto Questing Settings
	global client_to_boost
	global questing_friend_tp
	client_to_boost = parser.get('questing', 'client_to_boost', fallback=None)
	questing_friend_tp = parser.getboolean('questing', 'friend_teleport', fallback=False)

while True:
	if not os.path.exists(f'{tool_name}-config.ini'):
		download_file(f'https://raw.githubusercontent.com/Slackaduts/{repo_name}/{branch}/{tool_name}-config.ini', f'{tool_name}-config.ini')
	time.sleep(0.1)
	# try:
	read_config(f'{tool_name}-config.ini')
	break
	# except:
	# 	logger.critical('Error found in the config. Redownloading the config to prevent further issues.')
	# 	# sg.Popup(f'{tool_name} Error', 'Error found in the config. Redownloading the config to prevent further issues.', non_blocking=True)
	# 	os.remove(f'{tool_name}-config.ini')
	# 	time.sleep(0.1)
	# else:
	# 	break


speed_status = False
combat_status = False
dialogue_status = False
sigil_status = False
freecam_status = False
hotkey_status = False
questing_status = False
tool_status = True

hotkeys_blocked = False

sigil_leader_pid: int = None
questing_leader_pid: int = None

def file_len(filepath):
	# return the number of lines in a file
	f = open(filepath, "r")
	return len(f.readlines())


def read_webpage(url):
	# return a list of lines from a hosted file
	try:
		response = requests.get(url, allow_redirects=True)
		page_text = response.text
		line_list = page_text.splitlines()
	except:
		return []
	else:
		return line_list


def generate_timestamp():
	# generates a timestamp and makes the symbols filename-friendly
	time = str(datetime.datetime.now())
	time_list = time.split('.')
	time_stamp = str(time_list[0])
	time_stamp = time_stamp.replace('/', '-').replace(':', '-')
	return time_stamp


def config_update():
	config_url = f'https://raw.githubusercontent.com/Slackaduts/{repo_name}/{branch}/{tool_name}-config.ini'

	if not os.path.exists(f'{tool_name}-config.ini'):
		download_file(url=config_url, file_name=f'{tool_name}-config.ini')
		time.sleep(0.1)

	if not os.path.exists(f'README.txt'):
		download_file(f'https://raw.githubusercontent.com/Slackaduts/{repo_name}/{branch}/README.txt', 'README.txt')

	download_file(url=config_url, file_name=f'{tool_name}-Testconfig.ini', delete_previous=True, debug=False)
	time.sleep(0.1)

	comparison_parser = ConfigParser()
	comparison_parser.read(f'{tool_name}-Testconfig.ini')
	comparison_sections = comparison_parser.sections()
	for i in comparison_sections:
		if not parser.has_section(i):
			print(f'Config file lacks section "{i}", adding it.')
			parser.add_section(i)

		comparison_options = comparison_parser.options(i)
		for b in comparison_options:
			if not parser.has_option(i, b):
				print(f'Config file section "{i}" lacks option "{b}", adding it and its default value.')
				parser.set(i, b, str(comparison_parser.get(i, b)))

	sections = parser.sections()
	for i in sections:
		if not comparison_parser.has_section(i):
			print(f'Config file has erroneous section "{i}", removing it.')
			parser.remove_section(i)

		options = parser.options(i)
		for b in options:
			if not comparison_parser.has_option(i, b):
				print(f'Config file section "{i}" has erroneous option "{b}", removing it.')
				parser.remove_option(i, b)

	with open(f'{tool_name}-config.ini', 'w') as new_config:
		parser.write(new_config)
	remove_if_exists(f'{tool_name}-Testconfig.ini')
	time.sleep(0.1)
	read_config(f'{tool_name}-config.ini')
	print('\n')


def run_updater():
	download_file(url=f"https://raw.githubusercontent.com/Slackaduts/{repo_name}/{branch}/{tool_name}Updater.exe", file_name=f'{tool_name}Updater.exe', delete_previous=True)
	time.sleep(0.1)
	subprocess.Popen(f'{tool_name}Updater.exe')
	sys.exit()


def get_latest_version():
	update_server = None

	try:
		update_server = read_webpage(f"https://raw.githubusercontent.com/Slackaduts/{repo_name}/{branch}/LatestVersion.txt")
	except:
		time.sleep(0.1)

	if len(update_server) >= 1:
		return update_server[0]
	else:
		return None


def is_version_greater(version: str, comparison_version: str) -> bool:
	# Compares the semantic version of two inputted versions and returns True if the first is greater
	version_list = version.split('.')
	comparison_version_list = comparison_version.split('.')

	for i, v in enumerate(version_list):
		current_v = int(v)
		current_comparison_v = int(comparison_version_list[i])
		if current_v > current_comparison_v:
			return True
		elif current_v < current_comparison_v:
			return False

	return False


def auto_update(latest_version: str = get_latest_version()):
	remove_if_exists(f'{tool_name}-copy.exe')
	remove_if_exists(f'{tool_name}Updater.exe')
	time.sleep(0.1)
	if auto_updating:
		if is_version_greater(latest_version, tool_version):
			run_updater()


def hotkey_button(name: str, auto_size: bool = False, text_color: str = gui_text_color, button_color: str = gui_button_color):
	return gui.Button(name, button_color=(text_color, button_color), auto_size_button=auto_size)


async def wait_for_not_blocked():
	while hotkeys_blocked:
		await asyncio.sleep(0.01)


async def mass_key_press(foreground_client : Client, background_clients : list[Client], pressed_key_name: str, key, duration : float = 0.1, debug : bool = False):
	# sends a given keystroke to all clients, handles foreground client seperately
	if debug and foreground_client:
		key_name = str(key)
		key_name = key_name.replace('Keycode.', '')
		logger.debug(f'{pressed_key_name} key pressed, sending {key_name} key press to all clients.')
	await asyncio.gather(*[p.send_key(key=key, seconds=duration) for p in background_clients])
	# only send foreground key press if there is a client in foreground
	if foreground_client:
		await foreground_client.send_key(key=key, seconds=duration)


async def sync_camera(client: Client, xyz: XYZ = None, yaw: float = None):
	# Teleports the freecam to a specified position, yaw, etc.
	if not xyz:
		xyz = await client.body.position()

	if not yaw:
		yaw = await client.body.yaw()

	xyz.z += 200

	camera = await client.game_client.free_camera_controller()
	await camera.write_position(xyz)
	await camera.write_yaw(yaw)


async def xyz_sync(foreground_client : Client, background_clients : list[Client], turn_after : bool = True, debug : bool = False):
	# syncs client XYZ up with the one in foreground, doesn't work across zones or realms
	if background_clients:
		if debug:
			logger.debug(f'{sync_locations_key} key pressed, syncing client locations.')
		if foreground_client:
			xyz = await foreground_client.body.position()
		else:
			first_background_client = background_clients[0]
			xyz = await first_background_client.body.position()

		await asyncio.gather(*[p.teleport(xyz) for p in background_clients])
		if turn_after:
			await asyncio.gather(*[p.send_key(key=Keycode.A, seconds=0.1) for p in background_clients])
			await asyncio.gather(*[p.send_key(key=Keycode.D, seconds=0.1) for p in background_clients])
		await asyncio.sleep(0.3)


async def navmap_teleport(foreground_client : wizwalker.Client, background_clients : list[Client], mass_teleport: bool = False, debug : bool = False, xyz: XYZ = None):
	# teleports foreground client or all clients using the navmap.
	# nested function that allows for the gathering of the teleports for each client
	async def client_navmap_teleport(client: Client, xyz: XYZ = None):
		if not xyz:
			xyz = await client.quest_position.position()
		await navmap_tp(client, xyz)
		# except:
		# 	# skips teleport if there's no navmap, this should just switch to auto adjusting teleport
		# 	logger.error(f'{client.title} encountered an error during navmap tp, most likely the navmap for the zone did not exist. Skipping teleport.')

	if debug:
		if mass_teleport:
			logger.debug(f'{mass_quest_teleport_key} key pressed, teleporting all clients to quests.')
		else:
			logger.debug(f'{quest_teleport_key} key pressed, teleporting client {foreground_client.title} to quest.')
	clients_to_port = []
	if foreground_client:
		clients_to_port.append(foreground_client)
	if mass_teleport:
		for b in background_clients:
			clients_to_port.append(b)
		# decide which client's quest XYZ to obey. Chooses the most common Quest XYZ across all clients, if there is none and all clients are in the same zone then it obeys the foreground client. If the zone differs, each client obeys their own quest XYZ.
		list_modes = statistics.multimode([await c.quest_position.position() for c in clients_to_port])
		zone_names = [await p.zone_name() for p in clients_to_port]
		if len(list_modes) == 1:
			xyz = list_modes[0]
		else:
			if zone_names.count(zone_names[0]) == len(zone_names):
				if foreground_client:
					xyz = await foreground_client.quest_position.position()

	# if mass teleport is off and no client is selected, this will default to p1
	if len(clients_to_port) == 0:
		if background_clients:
			clients_to_port.append(background_clients[0])

	# all clients teleport at the same time
	await asyncio.gather(*[client_navmap_teleport(p, xyz) for p in clients_to_port])


async def toggle_speed(debug : bool = False):
	# toggles a bool for the speed multiplier. Speed multiplier task handles the actual logic, this just enables/disables it.
	global speed_status
	speed_status ^= True
	if debug:
		if speed_status:
			logger.debug(f'{toggle_speed_key} key pressed, enabling speed multiplier.')
		else:
			logger.debug(f'{toggle_speed_key} key pressed, disabling speed multiplier.')


async def friend_teleport_sync(clients : list[wizwalker.Client], debug: bool):
	# uses the util for porting to friend via the friends list. Sends every client to p1. I really don't like this function, or this code, but it works and people want it so I have to have it in here sadly. Might rewrite it someday.
	if debug:
		logger.debug(f'{friend_teleport_key} key pressed, friend teleporting all clients to p1.')
	child_clients = clients[1:]
	try:
		await asyncio.gather(*[p.mouse_handler.activate_mouseless() for p in child_clients])
		for p in child_clients:
			p.mouseless_status = True
	except:
		await asyncio.sleep(0)
	await asyncio.sleep(0.25)
	try:
		[await teleport_to_friend_from_list(client=p, icon_list=1, icon_index=50) for p in child_clients]
	except:
		await asyncio.sleep(0)
	try:
		await asyncio.gather(*[p.mouse_handler.deactivate_mouseless() for p in child_clients])
		for p in child_clients:
			p.mouseless_status = True
	except:
		await asyncio.sleep(0)


async def kill_tool(debug: bool):
	# raises KeyboardInterrupt, forcing the tool to exit.
	if debug:
		logger.debug(f'{kill_tool_key} key pressed, killing {tool_name}.')
	await asyncio.sleep(0)
	await asyncio.sleep(0)
	raise KeyboardInterrupt


async def toggle_combat(debug: bool):
	global combat_status
	combat_status ^= True
	if debug:
		if combat_status:
			logger.debug(f'{toggle_auto_combat_key} key pressed, enabling auto combat.')
		else:
			logger.debug(f'{toggle_auto_combat_key} key pressed, disabling auto combat.')


async def toggle_dialogue(debug: bool):
	# automatically clicks through dialogue, and rejects sidequests.
	global dialogue_status
	dialogue_status ^= True
	if debug:
		if dialogue_status:
			logger.debug(f'{toggle_auto_dialogue_key} key pressed, enabling auto dialogue.')
		else:
			logger.debug(f'{toggle_auto_dialogue_key} key pressed, disabling auto dialogue.')


async def toggle_questing(debug: bool):
	# toggles auto questing
	global questing_status
	global sigil_status
	questing_status ^= True
	if debug:
		if questing_status:
			logger.debug(f'{toggle_auto_questing_key} key pressed, enabling auto questing.')
			sigil_status = False
		else:
			logger.debug(f'{toggle_auto_questing_key} key pressed, disabling auto questing.')


async def toggle_sigil(debug: bool):
	# toggles auto sigil
	global sigil_status
	global questing_status
	sigil_status ^= True
	if debug:
		if sigil_status:
			logger.debug(f'{toggle_auto_sigil_key} key pressed, enabling auto sigil.')
			questing_status = False
		else:
			logger.debug(f'{toggle_auto_sigil_key} key pressed, disabling auto sigil.')


@logger.catch()
async def main():
	global tool_status
	listener = HotkeyListener()
	foreground_client = None
	background_clients = []
	await asyncio.sleep(0)
	listener.start()

	async def tool_finish():
		if speed_status:
			await asyncio.gather(*[p.client_object.write_speed_multiplier(client_speeds[p]) for p in walker.clients])

		for p in walker.clients:
			p.title = 'Wizard101'
			if await p.game_client.is_freecam():
				await p.camera_elastic()
			else:
				camera = await p.game_client.elastic_camera_controller()
				client_object = await p.body.parent_client_object()
				await camera.write_attached_client_object(client_object)
				await camera.write_check_collisions(True)
				await camera.write_distance_target(300.0)
				await camera.write_distance(300.0)
				await camera.write_min_distance(150.0)
				await camera.write_max_distance(450.0)
				await camera.write_zoom_resolution(150.0)

			try:
				await p.mouse_handler.deactivate_mouseless()
				p.mouseless_status = False
			except:
				await asyncio.sleep(0)

		logger.remove(current_log)
		await listener.clear()
		for p in walker.clients:
			try:
				await p.close()
			except:
				pass
		# await walker.close()
		await asyncio.sleep(0)
		global tool_status
		tool_status = False


	async def x_press_hotkey():
		await wait_for_not_blocked()
		await mass_key_press(foreground_client, background_clients, x_press_key, Keycode.X, duration=0.1, debug=True)


	async def xyz_sync_hotkey():
		await wait_for_not_blocked()
		await xyz_sync(foreground_client, background_clients, turn_after=True, debug=True)


	async def navmap_teleport_hotkey():
		await wait_for_not_blocked()
		if not freecam_status:
			await navmap_teleport(foreground_client, background_clients, mass_teleport=False, debug=True)


	async def mass_navmap_teleport_hotkey():
		await wait_for_not_blocked()
		if not freecam_status:
			await navmap_teleport(foreground_client, background_clients, mass_teleport=True, debug=True)


	async def toggle_speed_hotkey():
		await wait_for_not_blocked()
		if not freecam_status:
			await toggle_speed(debug=True)


	async def friend_teleport_sync_hotkey():
		await wait_for_not_blocked()
		if not freecam_status:
			await friend_teleport_sync(walker.clients, debug=True)


	async def kill_tool_hotkey():
		await wait_for_not_blocked()
		await kill_tool(debug=True)


	async def toggle_combat_hotkey():
		await wait_for_not_blocked()
		if not freecam_status:
			for p in walker.clients:
				p.combat_status ^= True
			await toggle_combat(debug=True)


	async def toggle_dialogue_hotkey():
		await wait_for_not_blocked()
		if not freecam_status:
			await toggle_dialogue(debug=True)


	async def toggle_sigil_hotkey():
		await wait_for_not_blocked()
		if not freecam_status:
			for p in walker.clients:
				p.sigil_status ^= True
				if p.sigil_status:
					p.questing_status = False
			await toggle_sigil(debug=True)


	async def toggle_freecam_hotkey(debug: bool = True):
		await wait_for_not_blocked()
		global freecam_status
		if foreground_client:
			if await is_free(foreground_client):
				if await foreground_client.game_client.is_freecam():
					if debug:
						logger.debug(f'{toggle_freecam_key} key pressed, disabling freecam.')
					await foreground_client.camera_elastic()
					freecam_status = False
				else:
					if debug:
						logger.debug(f'{toggle_freecam_key} key pressed, enabling freecam.')
					freecam_status = True
					await sync_camera(foreground_client)
					await foreground_client.camera_freecam()


	async def tp_to_freecam_hotkey():
		await wait_for_not_blocked()
		if foreground_client:
			logger.debug(f'Shift + {toggle_freecam_key} key pressed, teleporting foreground client to freecam position.')
			if await foreground_client.game_client.is_freecam():
				camera = await foreground_client.game_client.free_camera_controller()
				camera_pos = await camera.position()
				await foreground_client.teleport(camera_pos, wait_on_inuse=True, purge_on_after_unuser_fixer=True)
				await toggle_freecam_hotkey(False)


	async def toggle_questing_hotkey():
		await wait_for_not_blocked()
		if not freecam_status:
			for p in walker.clients:
				p.questing_status ^= True
				if p.questing_status:
					p.sigil_status = False
			await toggle_questing(debug=True)


	async def enable_hotkeys(exclude_freecam: bool = False, debug: bool = False):
		# adds every hotkey
		global hotkey_status
		if not hotkey_status:
			if debug:
				logger.debug('Client selected, starting hotkey listener.')
			await listener.add_hotkey(Keycode[x_press_key], x_press_hotkey, modifiers=ModifierKeys.NOREPEAT)
			# await listener.add_hotkey(Keycode[space_press_key], space_press_hotkey, modifiers=ModifierKeys.NOREPEAT)
			await listener.add_hotkey(Keycode[sync_locations_key], xyz_sync_hotkey, modifiers=ModifierKeys.NOREPEAT)
			await listener.add_hotkey(Keycode[quest_teleport_key], navmap_teleport_hotkey, modifiers=ModifierKeys.NOREPEAT)
			await listener.add_hotkey(Keycode[mass_quest_teleport_key], mass_navmap_teleport_hotkey, modifiers=ModifierKeys.NOREPEAT)
			await listener.add_hotkey(Keycode[toggle_speed_key], toggle_speed_hotkey, modifiers=ModifierKeys.NOREPEAT)
			await listener.add_hotkey(Keycode[friend_teleport_key], friend_teleport_sync_hotkey, modifiers=ModifierKeys.NOREPEAT)
			await listener.add_hotkey(Keycode[toggle_auto_combat_key], toggle_combat_hotkey, modifiers=ModifierKeys.NOREPEAT)
			await listener.add_hotkey(Keycode[toggle_auto_dialogue_key], toggle_dialogue_hotkey, modifiers=ModifierKeys.NOREPEAT)
			await listener.add_hotkey(Keycode[toggle_auto_sigil_key], toggle_sigil_hotkey, modifiers=ModifierKeys.NOREPEAT)
			if not exclude_freecam:
				await listener.add_hotkey(Keycode[toggle_freecam_key], toggle_freecam_hotkey, modifiers=ModifierKeys.NOREPEAT)
				await listener.add_hotkey(Keycode[toggle_freecam_key], tp_to_freecam_hotkey, modifiers=ModifierKeys.SHIFT | ModifierKeys.NOREPEAT)
			await listener.add_hotkey(Keycode[toggle_auto_questing_key], toggle_questing_hotkey, modifiers=ModifierKeys.NOREPEAT)
			hotkey_status = True


	async def disable_hotkeys(exclude_freecam: bool = False, debug: bool = False, exclude_kill: bool = True):
		# removes every hotkey
		global hotkey_status
		if hotkey_status:
			if debug:
				logger.debug('Client not selected, stopping hotkey listener.')
			await listener.remove_hotkey(Keycode[x_press_key], modifiers=ModifierKeys.NOREPEAT)
			# await listener.remove_hotkey(Keycode[space_press_key], modifiers=ModifierKeys.NOREPEAT)
			await listener.remove_hotkey(Keycode[sync_locations_key], modifiers=ModifierKeys.NOREPEAT)
			await listener.remove_hotkey(Keycode[quest_teleport_key], modifiers=ModifierKeys.NOREPEAT)
			await listener.remove_hotkey(Keycode[mass_quest_teleport_key], modifiers=ModifierKeys.NOREPEAT)
			await listener.remove_hotkey(Keycode[toggle_speed_key], modifiers=ModifierKeys.NOREPEAT)
			await listener.remove_hotkey(Keycode[friend_teleport_key], modifiers=ModifierKeys.NOREPEAT)
			if not exclude_kill:
				await listener.remove_hotkey(Keycode[kill_tool_key], modifiers=ModifierKeys.NOREPEAT)
			await listener.remove_hotkey(Keycode[toggle_auto_combat_key], modifiers=ModifierKeys.NOREPEAT)
			await listener.remove_hotkey(Keycode[toggle_auto_dialogue_key], modifiers=ModifierKeys.NOREPEAT)
			await listener.remove_hotkey(Keycode[toggle_auto_sigil_key], modifiers=ModifierKeys.NOREPEAT)
			if not exclude_freecam:
				await listener.remove_hotkey(Keycode[toggle_freecam_key], modifiers=ModifierKeys.NOREPEAT)
				await listener.remove_hotkey(Keycode[toggle_freecam_key], modifiers=ModifierKeys.SHIFT | ModifierKeys.NOREPEAT)
			await listener.remove_hotkey(Keycode[toggle_auto_questing_key], modifiers=ModifierKeys.NOREPEAT)
			hotkey_status = False


	async def foreground_client_switching():
		await asyncio.sleep(2)
		# enable hotkeys if a client is selected, disable if none are
		while True:
			await asyncio.sleep(0.1)
			foreground_client_list = [c for c in walker.clients if c.is_foreground]
			if foreground_client_list:
				await enable_hotkeys(debug = True)
			else:
				await disable_hotkeys(debug = True)


	async def assign_foreground_clients():
		# assigns the foreground client and a list of background clients
		nonlocal foreground_client
		nonlocal background_clients
		while True:
			foreground_client_list = [c for c in walker.clients if c.is_foreground]
			# print(foreground_client_list)
			if len(foreground_client_list) > 0:
				foreground_client = foreground_client_list[0]
			else:
				# foreground_client = None
				pass
			background_clients = [c for c in walker.clients if not c.is_foreground and c != foreground_client]
			await asyncio.sleep(0.1)


	async def speed_switching():
		# handles updating the speed multiplier if a zone or realm change happens
		nonlocal client_speeds
		for c in walker.clients:
			client_speeds[c] = await c.client_object.speed_multiplier()
		modified_speed = (int(speed_multiplier) - 1) * 100
		while True:
			await asyncio.sleep(0.1)
			# if speed multiplier is enabled, rewrite the multiplier value if the speed changes. If speed mult is disabled, rewrite the original untouched speed multiplier only if it equals the multiplier speed
			if not freecam_status:
				if speed_status:
					await asyncio.sleep(0.1)
					await asyncio.sleep(0.1)
					for c in walker.clients:
						if speed_status and await c.client_object.speed_multiplier() != modified_speed:
							await c.client_object.write_speed_multiplier(modified_speed)
				else:
					for c in walker.clients:
						if await c.client_object.speed_multiplier() == modified_speed:
							await c.client_object.write_speed_multiplier(client_speeds[c])


	async def is_client_in_combat_loop():
		async def async_in_combat(client: Client):
			# battle = Fighter(client)
			# while True:
			# 	if await battle.is_fighting():
			# 		client.in_combat = True
			# 	else:
			# 		client.in_combat = False
			# 	await asyncio.sleep(0.1)
			while True:
				if not freecam_status:
					client.in_combat = await client.in_battle()
				await asyncio.sleep(0.1)

		await asyncio.gather(*[async_in_combat(p) for p in walker.clients])


	async def combat_loop():
		logger.catch()
		# waits for combat for every client and handles them seperately.
		async def async_combat(client: Client):
			while True:
				await asyncio.sleep(1)
				if client in walker.clients and not freecam_status:
					while ((not client.in_combat) or not combat_status) and client in walker.clients:
						await asyncio.sleep(1)

					if client.in_combat and combat_status and client in walker.clients:
						logger.debug(f'Client {client.title} in combat, handling combat.')

						# ORIGINAL CODE
						battle = Fighter(client, walker.clients)
						await battle.wait_for_combat()

		await asyncio.gather(*[async_combat(p) for p in walker.clients])


	async def dialogue_loop():
		# auto advances dialogue for every client, individually and concurrently
		async def async_dialogue(client: Client):
			while True:
				if dialogue_status and not freecam_status:
					if await is_visible_by_path(client, advance_dialog_path):
						if await is_visible_by_path(client, decline_quest_path):
							await client.send_key(key=Keycode.ESC)
							await asyncio.sleep(0.1)
							await client.send_key(key=Keycode.ESC)
						else:
							await client.send_key(key=Keycode.SPACEBAR)
				await asyncio.sleep(0.1)

		await asyncio.gather(*[async_dialogue(p) for p in walker.clients])

	# logger.catch()
	async def questing_loop():
		# Auto questing on a per client basis.
		# TODO: Team logic for auto questing, absolutely no clue how I'll handle this, so this is either a notfaj or future slack problem
		async def async_questing(client: Client):
			while True:
				await asyncio.sleep(1)

				if client in walker.clients and questing_status:
					if questing_leader_pid is not None:
						if client.process_id == questing_leader_pid:
							# if follow leader is off, quest on all clients, passing through only the leader
							logger.debug(f'Client {client.title} - Handling questing.')
							questing = Quester(client, walker.clients, questing_leader_pid)
							await questing.auto_quest_leader(questing_friend_tp)
					else:
						# if follow leader is off, quest on all clients, passing through only the leader
						logger.debug(f'Client {client.title} - Handling questing.')
						questing = Quester(client, walker.clients, None)
						await questing.auto_quest()

					# TODO: Put SlackQuester's loop function here
		await asyncio.gather(*[async_questing(p) for p in walker.clients])

	async def nearest_duel_circle_distance_and_xyz(sprinter: SprintyClient):
		min_distance = None
		circle_xyz = None

		try:
			entities = await sprinter.get_base_entity_list()
		except ValueError:
			return None, None

		for entity in entities:
			try:
				entity_name = await entity.object_name()
			except wizwalker.MemoryReadError:
				entity_name = ''

			if entity_name == 'Duel Circle':
				entity_pos = await entity.location()
				distance = calc_Distance(entity_pos, await sprinter.client.body.position())

				if min_distance is None:
					min_distance = distance
					circle_xyz = entity_pos
				elif distance < min_distance:
					min_distance = distance
					circle_xyz = entity_pos
				# print('distance to duel circle: ', distance)

		return min_distance, circle_xyz

	async def is_duel_circle_joinable(p: Client):
		sprinter = SprintyClient(p)
		await asyncio.sleep(7)
		just_entered_combat = False

		distance, duel_circle_xyz = await nearest_duel_circle_distance_and_xyz(sprinter)
		# if after 7 seconds we are not in a battle position, we either teleported while invincible or teleported to a non-joinable fight
		if distance is not None:
			if not (590 < distance < 610):
				logger.debug('Bad teleport.  Returning ' + p.title + ' to safe location.')
				if p.original_location_before_combat is not None:
					await p.teleport(p.original_location_before_combat)
					p.original_location_before_combat = None
				else:
					position = await p.body.position()
					await p.teleport(XYZ(position.x, position.y, position.z - 350))

				p.entity_detect_combat_status = False

				return False

			return True
		else:
			return False

	async def entity_detect_combat_loop():
		async def detect_combat(p: Client):
			sprinter = SprintyClient(p)

			other_clients = []
			for c in walker.clients:
				if c != p:
					other_clients.append(c)

			safe_distance = 620
			just_left_combat = False
			just_entered_combat = False
			try:
				while True:
					await asyncio.sleep(0.2)
					if p.questing_status:
						distance, duel_circle_xyz = await nearest_duel_circle_distance_and_xyz(sprinter)

						if distance is None:
							if p.entity_detect_combat_status:
								just_left_combat = True
							else:
								p.entity_detect_combat_status = False

						# When fully in combat (once running animation occurs and selection phase begins) clients in any battle order are ~600 away from the center of the duel circle
						# extra leeway on this allows clients to teleport more quickly to ensure that they arrive before the selection phase even starts
						elif distance < safe_distance:
							# if not p.combat_status and p.entity_detect_combat_status:
							# 	just_left_combat = True
							# else:
								if not p.entity_detect_combat_status:
									just_entered_combat = True

								p.entity_detect_combat_status = True

								original_client_locations = dict()
								all_fighting_clients = [p]

								# don't teleport clients to duel circles that are closed off, and don't teleport clients if they are in separate instances
								if p.duel_circle_joinable and not p.in_solo_zone:
									helper_clients = []
									for c in other_clients:
										if await is_free(c) and not c.entity_detect_combat_status and not c.invincible_combat_timer:
											# player_distance = calc_Distance(await c.body.position(), await p.body.position())
											# print('player distance between [', c.title, '] and [', p.title, '] is: ', player_distance)

											if await c.zone_name() == await p.zone_name():
												if not c.entity_detect_combat_status:
													c.original_location_before_combat = await c.body.position()
													original_client_locations.update({c: await c.body.position()})
													if c not in helper_clients:
														helper_clients.append(c)
														all_fighting_clients.append(c)

													if not c.entity_detect_combat_status:
														logger.debug('Combat detected from client ' + p.title + ' - teleporting client ' + c.title)
														await c.teleport(duel_circle_xyz)
														just_entered_combat = True

									if len(helper_clients) > 0:
										check_duel_circle_joinable = [asyncio.create_task(is_duel_circle_joinable(helper)) for helper in helper_clients]
										done, pending = await asyncio.wait(check_duel_circle_joinable)

										is_circle_joinable = True
										for d in done:
											is_circle_joinable = d.result()

										if not is_circle_joinable:
											p.duel_circle_joinable = False
											logger.debug('Client ' + p.title + ' - ' + 'Duel circle not joinable - teleports halted.')

								# if not all(await asyncio.gather(*[is_duel_circle_joinable(helper) for helper in helper_clients]):
								#	print('a')

								# if len(helping_clients) > 0:
								# prevent additional unnecessary teleports by giving helper clients a chance to mark themselves as in combat
								if just_entered_combat:
									await asyncio.sleep(8)
									just_entered_combat = False

								original_client_locations = dict()
								helper_clients = []


						else:
							if p.entity_detect_combat_status:
								just_left_combat = True
							else:
								p.entity_detect_combat_status = False

						if just_left_combat and await is_free(p):
							# collect wisps, up to a certain number
							await collect_wisps_with_limit(p, limit=2)
							await asyncio.sleep(.3)

							# return helper clients to their previous safe location

							if p.original_location_before_combat is not None:
								logger.debug('Client ' + p.title + ' - ' + 'Returning to safe location.')
								try:
									await p.teleport(p.original_location_before_combat)
								except ValueError:
									print(traceback.print_exc())
									p.original_location_before_combat = None

							just_left_combat = False

							# Mark wizard as invincible, as clients can get stuck standing in the middle of another client's battle circle due to teleporting while invincibile
							logger.debug('Client ' + p.title + ' - ' + 'Battle teleports off while invulnerable')
							p.invincible_combat_timer = True
							p.entity_detect_combat_status = False
							p.duel_circle_joinable = True

							# Timer seems to be about 6.5 seconds to become draggable again
							await asyncio.sleep(6.5)
							logger.debug('Client ' + p.title + ' - ' + 'Battle teleports re-enabled')
							p.invincible_combat_timer = False
			except:
				print(traceback.print_exc())

		await asyncio.gather(*[detect_combat(p) for p in walker.clients])


	async def sigil_loop():
		# Auto sigil on a per client basis.
		async def async_sigil(client: Client):
			while True:
				await asyncio.sleep(1)
				if client in walker.clients and client.sigil_status and not freecam_status:
					sigil = Sigil(client, walker.clients, sigil_leader_pid)
					await sigil.wait_for_sigil()

		await asyncio.gather(*[async_sigil(p) for p in walker.clients])


	async def anti_afk_loop():
		# anti AFK implementation on a per client basis.
		async def async_anti_afk(client: Client):
			# await client.root_window.debug_print_ui_tree()
			# print(await client.body.position())
			while True:
				await asyncio.sleep(0.1)
				if not freecam_status:
					client_xyz = await client.body.position()
					await asyncio.sleep(350)
					client_xyz_2 = await client.body.position()
					distance_moved = calc_Distance(client_xyz, client_xyz_2)
					if distance_moved < 5.0 and not await client.in_battle():
						logger.debug(f"Client {client.title} - AFK client detected, moving slightly.")
						await client.send_key(key=Keycode.A)
						await asyncio.sleep(0.1)
						await client.send_key(key=Keycode.D)

		await asyncio.gather(*[async_anti_afk(p) for p in walker.clients])


	async def handle_gui():
		if show_gui:
			await create_gui()
		else:
			while True:
				await asyncio.sleep(1)


	async def create_gui():
		gui.theme(gui_theme)

		toggles = ['Speedhack', 'Combat', 'Dialogue', 'Sigil', 'Questing']
		hotkeys = ['Quest TP', 'Freecam', 'Freecam TP']
		mass_hotkeys = ['Mass TP', 'XYZ Sync', 'X Press']
		toggles_layout = [[hotkey_button(name), gui.Text(f'Disabled', key=f'{name}Status', auto_size_text=False, size=(7, 1), text_color=gui_text_color)] for name in toggles]
		framed_toggles_layout = gui.Frame('Toggles', toggles_layout, title_color=gui_text_color)
		hotkeys_layout = [[hotkey_button(name)] for name in hotkeys]
		framed_hotkeys_layout = gui.Frame('Hotkeys', hotkeys_layout, title_color=gui_text_color)
		mass_hotkeys_layout = [[hotkey_button(name)] for name in mass_hotkeys]
		framed_mass_hotkeys_layout = gui.Frame('Mass Hotkeys', mass_hotkeys_layout, title_color=gui_text_color)

		client_title = gui.Text('Client: ', key='Title', text_color=gui_text_color)

		x_pos = gui.Text('x: ', key='x', auto_size_text=False, text_color=gui_text_color)
		y_pos = gui.Text('y: ', key='y', auto_size_text=False, text_color=gui_text_color)
		z_pos = gui.Text('z: ', key='z', auto_size_text=False, text_color=gui_text_color)
		yaw = gui.Text('Yaw: ', key='Yaw', auto_size_text=False, text_color=gui_text_color)

		zone_info = gui.Text('Zone: ', key='Zone', auto_size_text=False, size=(62, 1), text_color=gui_text_color)

		copy_pos = hotkey_button('Copy Position')
		copy_zone = hotkey_button('Copy Zone')
		copy_yaw = hotkey_button('Copy Yaw')

		client_info_layout = [
			[client_title],
			[zone_info],
			[x_pos],
			[y_pos],
			[z_pos],
			[yaw]
		]

		utils_layout = [
			[copy_zone],
			[copy_pos],
			[copy_yaw]
		]

		framed_utils_layout = gui.Frame('Utils', utils_layout, title_color=gui_text_color)

		custom_tp_layout = [
			[gui.Text('The utils shown below are for advanced users and no support will be provided on them.', text_color=gui_text_color)],
			[gui.Text('X:', text_color=gui_text_color), gui.InputText(size=(8, 1)), gui.Text('Y:', text_color=gui_text_color), gui.InputText(size=(8, 1)), gui.Text('Z:', text_color=gui_text_color), gui.InputText(size=(8, 1)), gui.Text('Yaw: ', text_color=gui_text_color), gui.InputText(size=(8, 1)), hotkey_button('Custom TP')],
			[gui.Text('Entity Name:', text_color=gui_text_color), gui.InputText(size=(43, 1)), hotkey_button('Entity TP')]
		]

		framed_custom_tp_layout = gui.Frame('TP Utils', custom_tp_layout, title_color=gui_text_color)

		dev_utils_layout = [
			[gui.Text('The utils shown below are for advanced users and no support will be provided on them.', text_color=gui_text_color)],
			[hotkey_button('Copy Entity List', True), hotkey_button('Copy Camera Position', True), hotkey_button('Copy Camera Rotation', True), hotkey_button('Print UI Tree', True)],
			[gui.Text('Zone Name:', text_color=gui_text_color), gui.InputText(size=(29, 1)), hotkey_button('Go To Zone'), hotkey_button('Mass Go To Zone', True)],
			[gui.Text('World Name:', text_color=gui_text_color), gui.Combo(['WizardCity', 'Krokotopia', 'Marleybone', 'MooShu', 'DragonSpire', 'Grizzleheim', 'Celestia', 'Wysteria', 'Zafaria', 'Avalon', 'Azteca', 'Khrysalis', 'Polaris', 'Mirage', 'Empyrea', 'Karamelle', 'Lemuria'], text_color=gui_text_color, size=(27, 1)), hotkey_button('Go To World', True), hotkey_button('Mass Go To World', True)],
			[hotkey_button('Go To Bazaar', True), hotkey_button('Mass Go To Bazaar', True), hotkey_button('Refill Potions', True), hotkey_button('Mass Refill Potions', True)]
		]

		framed_dev_utils_layout = gui.Frame('Dev Utils', dev_utils_layout, title_color=gui_text_color)

		camera_controls_layout = [
			[gui.Text('The utils shown below are for advanced users and no support will be provided on them.', text_color=gui_text_color)],
			[gui.Text('X:', text_color=gui_text_color), gui.InputText(size=(12, 1)), gui.Text('Y:', text_color=gui_text_color), gui.InputText(size=(12, 1)), gui.Text('Z:', text_color=gui_text_color), gui.InputText(size=(11, 1)), hotkey_button('Set Camera Position', True)],
			[gui.Text('Yaw:', text_color=gui_text_color), gui.InputText(size=(16, 1)), gui.Text('Roll:', text_color=gui_text_color), gui.InputText(size=(16, 1)), gui.Text('Pitch:', text_color=gui_text_color), gui.InputText(size=(15, 1))],
			[gui.Text('Entity:', text_color=gui_text_color), gui.InputText(size=(25, 1)), hotkey_button('Anchor', text_color=gui_text_color), hotkey_button('Toggle Camera Collision', True)],
			[gui.Text('Distance:', text_color=gui_text_color), gui.InputText(size=(10, 1)), gui.Text('Min:', text_color=gui_text_color), gui.InputText(size=(10, 1)), gui.Text('Max:', text_color=gui_text_color), gui.InputText(size=(11, 1)), hotkey_button('Set Distance', True)]
		]

		framed_camera_controls_layout = gui.Frame('Camera Controls', camera_controls_layout, title_color=gui_text_color)

		tabs = [
			[
				gui.Tab('Hotkeys', [[framed_toggles_layout, framed_hotkeys_layout, framed_mass_hotkeys_layout, framed_utils_layout]], title_color=gui_text_color),
				gui.Tab('Camera Utils', [[framed_camera_controls_layout]], title_color=gui_text_color),
				gui.Tab('Dev Utils', [[framed_custom_tp_layout], [framed_dev_utils_layout]], title_color=gui_text_color)
			]
		]

		layout = [
			[gui.TabGroup(tabs)],
			[client_info_layout]
		]

		window = gui.Window(title= f'{tool_name} GUI v{tool_version}', layout= layout, keep_on_top=gui_on_top, finalize=True)

		global hotkeys_blocked
		while True:
			hotkeys_blocked = True
			event, inputs = window.read(timeout=0.25)
			hotkeys_blocked = False

			if foreground_client:
				current_zone = await foreground_client.zone_name()
				current_pos = await foreground_client.body.position()
				current_yaw = await foreground_client.body.yaw()

				window['Title'].update(f'Client: {foreground_client.title}')
				window['Zone'].update(f'Zone: {current_zone}')
				window['x'].update(f'X: {current_pos.x}')
				window['y'].update(f'Y: {current_pos.y}')
				window['z'].update(f'Z: {current_pos.z}')
				window['Yaw'].update(f'Yaw: {current_yaw}')

			match event:
				case gui.WINDOW_CLOSED:
					await kill_tool(False)

				case gui.WINDOW_CLOSE_ATTEMPTED_EVENT:
					await kill_tool(False)

				case 'Speedhack':
					await toggle_speed_hotkey()

				case 'Combat':
					await toggle_combat_hotkey()

				case 'Dialogue':
					await toggle_dialogue_hotkey()

				case 'Sigil':
					await toggle_sigil_hotkey()

				case 'Questing':
					await toggle_questing_hotkey()

				case 'Quest TP':
					await navmap_teleport_hotkey()

				case 'Mass TP':
					await mass_navmap_teleport_hotkey()

				case 'Freecam':
					await toggle_freecam_hotkey()

				case 'Freecam TP':
					await tp_to_freecam_hotkey()

				case 'XYZ Sync':
					await xyz_sync_hotkey()

				case 'X Press':
					await x_press_hotkey()

				case 'Copy Zone':
					logger.debug('Copied Zone')
					pyperclip.copy(current_zone)

				case 'Copy Position':
					logger.debug('Copied Position')
					pyperclip.copy(f'XYZ(x={current_pos.x}, y={current_pos.y}, z={current_pos.z})')

				case 'Copy Yaw':
					logger.debug('Copied Yaw')
					pyperclip.copy(current_yaw)

				case 'Custom TP':
					# Teleports to custom XYZ or adding/subtracting from it, same with the yaw (Character rotation)
					tp_inputs = [inputs[i] for i in range(4)]
					if any(tp_inputs) and foreground_client:
						x_input = inputs[0]
						y_input = inputs[1]
						z_input = inputs[2]
						yaw_input = inputs[3]

						x_input = param_input(inputs[0], current_pos.x)
						y_input = param_input(inputs[1], current_pos.y)
						z_input = param_input(inputs[2], current_pos.z)
						yaw_input = param_input(inputs[3], current_yaw)

						custom_xyz = XYZ(x=x_input, y=y_input, z=z_input)
						logger.debug(f'Teleporting client {foreground_client.title} to {custom_xyz}, yaw= {yaw_input}')
						await foreground_client.teleport(custom_xyz)
						await foreground_client.body.write_yaw(yaw_input)

				case 'Entity TP':
					# Teleports to closest entity with vague name, using WizSprinter
					if foreground_client and inputs[4]:
						sprinter = SprintyClient(foreground_client)
						entities = await sprinter.get_base_entities_with_vague_name(inputs[4])
						if entities:
							entity = await sprinter.find_closest_of_entities(entities)
							entity_pos = await entity.location()
							await foreground_client.teleport(entity_pos)

				case 'Set Camera Position':
					camera_inputs = [inputs[i] for i in range(10)][-6:]
					if any(camera_inputs) and foreground_client:
						if not freecam_status:
							await toggle_freecam_hotkey()

						# camera = await foreground_client.game_client.free_camera_controller()
						camera = await foreground_client.game_client.selected_camera_controller()
						camera_pos = await camera.position()
						camera_yaw = await camera.yaw()
						camera_roll = await camera.roll()
						camera_pitch = await camera.pitch()

						x_input = inputs[5]
						y_input = inputs[6]
						z_input = inputs[7]
						yaw_input = inputs[8]
						roll_input = inputs[9]
						pitch_input = inputs[10]

						x_input = param_input(inputs[5], camera_pos.x)
						y_input = param_input(inputs[6], camera_pos.y)
						z_input = param_input(inputs[7], camera_pos.z)
						yaw_input = param_input(inputs[8], camera_yaw)
						roll_input = param_input(inputs[9], camera_roll)
						pitch_input = param_input(inputs[10], camera_pitch)

						input_pos = XYZ(x_input, y_input, z_input)
						logger.debug(f'Teleporting Camera to {input_pos}, yaw={yaw_input}, roll={roll_input}, pitch={pitch_input}')
						await camera.write_position(input_pos)
						await camera.write_yaw(yaw_input)
						await camera.write_roll(roll_input)
						await camera.write_pitch(pitch_input)

				case 'Anchor':
					if inputs[11] and foreground_client:
						if freecam_status:
							await toggle_freecam_hotkey()

						camera = await foreground_client.game_client.elastic_camera_controller()

						sprinter = SprintyClient(foreground_client)
						entities = await sprinter.get_base_entities_with_vague_name(inputs[11])
						entity_pos: XYZ = None
						if entities:
							entity = await sprinter.find_closest_of_entities(entities)
							entity_name = await entity.object_name()
							logger.debug(f'Anchoring camera to entity {entity_name}')
							await camera.write_attached_client_object(entity)

				case 'Set Distance':
					distance_inputs = [inputs[i] for i in range(15)][-3:]
					if any(distance_inputs) and foreground_client:
						camera = await foreground_client.game_client.elastic_camera_controller()
						current_zoom = await camera.distance()
						current_min = await camera.min_distance()
						current_max = await camera.max_distance()
						distance_input = param_input(inputs[12], current_zoom)
						min_input = param_input(inputs[13], current_min)
						max_input = param_input(inputs[14], current_max)
						logger.debug(f'Setting camera distance to {distance_input}, min={min_input}, max={max_input}')

						if inputs[12]:
							await camera.write_distance_target(distance_input)
							await camera.write_distance(distance_input)
						if inputs[13]:
							await camera.write_min_distance(min_input)
							await camera.write_zoom_resolution(min_input)
						if inputs[14]:
							await camera.write_max_distance(max_input)


				case 'Toggle Camera Collisions':
					if foreground_client:
						camera = await foreground_client.game_client.elastic_camera_controller()

						collision_status = await camera.check_collisions()
						collision_status ^= True

						logger.debug(f'Camera Collisions {bool_to_string(collision_status)}')
						await camera.write_check_collisions(collision_status)

				case 'Copy Entity List':
					if foreground_client:
						logger.debug('Copied Entity List')
						sprinter = SprintyClient(foreground_client)
						entities = await sprinter.get_base_entity_list()
						entities_info = ''
						for entity in entities:
							entity_pos = await entity.location()
							entity_name = await entity.object_name()
							entities_info += f'{entity_name}, XYZ(x={entity_pos.x}, y={entity_pos.y}, z={entity_pos.z})\n'
						pyperclip.copy(entities_info)

				case 'Copy Camera Position':
					if foreground_client:
						camera = await foreground_client.game_client.selected_camera_controller()
						camera_pos = await camera.position()

						logger.debug('Copied Selected Camera Position')
						pyperclip.copy(f'XYZ(x={camera_pos.x}, y={camera_pos.y}, z={camera_pos.z})')

				case 'Copy Camera Rotation':
					if foreground_client:
						camera = await foreground_client.game_client.selected_camera_controller()
						camera_yaw = await camera.yaw()
						camera_roll = await camera.roll()
						camera_pitch = await camera.pitch()

						logger.debug('Copied Camera Rotations')
						pyperclip.copy(f'Yaw={camera_yaw}\nRoll={camera_roll}\nPitch={camera_pitch}')

				case 'Print UI Tree':
					foreground: Client = foreground_client
					if foreground_client:
						await foreground.root_window.debug_print_ui_tree()

				case 'Go To Zone':
					if foreground_client:
						clients = [foreground_client]
						zoneChanged = await toZoneDisplayName(clients, str(inputs[15]))

						if zoneChanged == 0:
							logger.debug('Reached destination zone: ' + await foreground_client.zone_name())
						else:
							logger.error('Failed to go to zone.  It may be spelled incorrectly, or may not be supported.')

				case 'Mass Go To Zone':
					if foreground_client:
						clients = [foreground_client]
						for c in background_clients:
							clients.append(c)

						zoneChanged = await toZoneDisplayName(clients, str(inputs[15]))

						if zoneChanged == 0:
							logger.debug('Reached destination zone: ' + await foreground_client.zone_name())
						else:
							logger.error('Failed to go to zone.  It may be spelled incorrectly, or may not be supported.')

				case 'Go To World':
					if foreground_client:
						if inputs[16] and foreground_client:
							clients = [foreground_client]

							await to_world(clients, inputs[16])

				case 'Mass Go To World':
					if foreground_client:
						if inputs[16] and foreground_client:
							clients = [foreground_client]
							for c in background_clients:
								clients.append(c)

							await to_world(clients, inputs[16])

				case 'Go To Bazaar':
					if foreground_client:
						clients = []
						clients.append(foreground_client)
						zoneChanged = await toZone(clients, 'WizardCity/WC_Streets/Interiors/WC_OldeTown_AuctionHouse')

						if zoneChanged == 0:
							logger.debug('Reached destination zone: ' + await foreground_client.zone_name())
						else:
							logger.error('Failed to go to zone.  It may be spelled incorrectly, or may not be supported.')

				case 'Mass Go To Bazaar':
					if foreground_client:
						clients = [foreground_client]
						for c in background_clients:
							clients.append(c)
						zoneChanged = await toZone(clients, 'WizardCity/WC_Streets/Interiors/WC_OldeTown_AuctionHouse')

						if zoneChanged == 0:
							logger.debug('Reached destination zone: ' + await foreground_client.zone_name())
						else:
							logger.error(
								'Failed to go to zone.  It may be spelled incorrectly, or may not be supported.')

				case 'Refill Potions':
					if foreground_client:
						await auto_potions_force_buy(foreground_client, True)

				case 'Mass Refill Potions':
					if foreground_client:
						clients = [foreground_client]
						for c in background_clients:
							clients.append(c)

						await asyncio.gather(*[auto_potions_force_buy(client, True) for client in clients])

				case _:
					pass

			window["SigilStatus"].update(bool_to_string(sigil_status))
			window["CombatStatus"].update(bool_to_string(combat_status))
			window["DialogueStatus"].update(bool_to_string(dialogue_status))
			window["SpeedhackStatus"].update(bool_to_string(speed_status))
			window["QuestingStatus"].update(bool_to_string(questing_status))

			await asyncio.sleep(0.5)


	async def potion_usage_loop():
		# Auto potion usage on a per client basis.
		async def async_potion(client: Client):
			while True:
				await asyncio.sleep(1)
				if await is_free(client) and not any([freecam_status, client.sigil_status, client.questing_status]):
					await auto_potions(client, buy = False)

		await asyncio.gather(*[async_potion(p) for p in walker.clients])


	async def rpc_loop():
		if rpc_status:
			# Connect to the discord dev app
			rpc = AioPresence(1000159655357587566)
			await rpc.connect()

			# Assign foreground client locally
			client: Client = walker.clients[0]
			zone_name: str = None
			while True:
				for c in walker.clients:
					c: Client
					if c.is_foreground:
						client = c
						break

				# Assign zone name of client
				await asyncio.sleep(1)
				if await client.zone_name() is not None:
					zone_name = await client.zone_name()

				zone_list = zone_name.split('/')
				if len(zone_list):
					status_str = zone_list[0]
				else:
					status_str = zone_name

				# parse zone name and make it more visually appealing
				if len(zone_list) > 1:
					if 'Housing_' in zone_name:
						status_str = status_str.replace('Housing_', '')
						end_zone_list = zone_list[-1].split('_')
						end_zone = f' - {end_zone_list[-1]}'

					elif 'Housing' in zone_name:
						end_zone_list = zone_list[-1].split('_')

						if 'School' in zone_list:
							status_str = end_zone_list[0] + 'House'

						else:
							status_str = zone_list[1]

						end_zone = f' - {end_zone_list[-1]}'

					else:
						end_zone = None

					if not end_zone:
						area_list: list[str] = zone_list[-1].split('_')
						del area_list[0]

						for a in area_list.copy():
							if any([s.isdigit() for s in a]):
								area_list.remove(a)

						seperator = ' '
						area = seperator.join(area_list)
						zone_word_list = re.findall('[A-Z][^A-Z]*', area)
						if zone_word_list:
							end_zone = f' - {seperator.join(zone_word_list)}'

						else:
							end_zone = ''

				else:
					end_zone = ''

				status_str = status_str.replace('DragonSpire', 'Dragonspyre')
				status_list = status_str.split('_')
				if len(status_list[0]) <= 3:
					del status_list[0]

				seperator = ' '
				status_str = seperator.join(status_list)

				status_list = re.findall('[A-Z][^A-Z]*', status_str)
				status_str = seperator.join(status_list)

				if 'ext' in end_zone.lower():
					end_zone = ' - Outside'

				elif 'int' in end_zone.lower():
					end_zone = ' - Inside'

				# Read combat members, this check is only needed since WW combat detection breaks upon fleeing
				fighter = Fighter(client, walker.clients)
				members = await fighter.get_members()

				# Assign current task to show in discord status
				if await client.in_battle() and members:
					task_str = 'Fighting '

				elif questing_status:
					task_str = 'Questing '

				elif sigil_status:
					task_str = 'Farming '

				else:
					task_str = ''

				# Assign if a client is currently selected or not
				if not any([client.is_foreground for client in walker.clients]):
					details_pane = 'Idle'

				else:
					details_pane = 'Active'

				# Update the discord RPC status
				await rpc.update(state=f'{task_str}In {status_str}{end_zone}', details=details_pane)


	async def drop_logging_loop():
		# Auto potion usage on a per client basis.
		await asyncio.gather(*[logging_loop(p) for p in walker.clients])


	async def zone_check_loop():
		zone_blacklist = ['WizardCity-TreasureTower-WC_TT', 'Raids', 'Battlegrounds']

		async def async_zone_check(client: Client):
			while True:
				await asyncio.sleep(0.25)
				zone_name = await client.zone_name()
				if zone_name and '/' in zone_name:
					split_zone_name = zone_name.split('/')

					if any([i in split_zone_name[0] for i in zone_blacklist]):
						logger.critical(f'Client {client.title} entered area with known anticheat, killing {tool_name}.')
						await kill_tool(False)

		await asyncio.gather(*[async_zone_check(p) for p in walker.clients])


	await asyncio.sleep(0)
	walker = ClientHandler()
	# walker.clients = []
	walker.get_new_clients()
	await asyncio.sleep(0)
	await asyncio.sleep(0)
	print(f'{tool_name} now has a discord! Join here:')
	print('https://discord.gg/59UrPJwYDm')
	print('Be sure to join the WizWalker discord, as this project is built using it. Join here:')
	print('https://discord.gg/JHrdCNK')
	print('\n')
	logger.debug(f'Welcome to {tool_name} version {tool_version}!')
	async def hooking_logic(default_logic : bool = False):
		await asyncio.sleep(0.1)
		if not default_logic:
			if not walker.clients:
				logger.debug('Waiting for a Wizard101 client to be opened...')
				while not walker.clients:
					walker.get_new_clients()
					await asyncio.sleep(0)
					await asyncio.sleep(1)
			# p1, p2, p3, p4 = [*clients, None, None, None, None][:4]
			# child_clients = clients[1:]
			for i, p in enumerate(walker.clients, 1):
				title = 'p' + str(i)
				p.title = title
			logger.debug('Activating hooks for all clients, please be patient...')
			try:
				await asyncio.gather(*[p.activate_hooks() for p in walker.clients])
			except wizwalker.errors.PatternFailed:
				logger.critical('Error occured in the hooking process. Please restart all Wizard101 clients.')
				# sg.Popup('Atlas Error', 'Error occured in the hooking process. Please restart all Wizard101 clients.', non_blocking=True)
				clients_check = walker.clients
				async def refresh_clients(delay: float = 0.5):
					walker.remove_dead_clients()
					walker.get_new_clients()
					await asyncio.sleep(delay)
				logger.debug('Waiting for all Wizard101 clients to be closed...')
				while walker.clients:
					await refresh_clients()
					await asyncio.sleep(0.1)
				logger.debug('Waiting for all previous Wizard101 clients to be reopened...')
				while not walker.clients:
					await refresh_clients()
					await asyncio.sleep(0.1)
				while len(walker.clients) != len(clients_check):
					await refresh_clients()
					await asyncio.sleep(0.1)
				await hooking_logic()
	await hooking_logic()
	logger.debug('Hooks activated. Setting up hotkeys...')
	# set initial speed for speed multipler so it knows what to reset to. Instead I should just have this track changes in speed multiplier per-client.
	client_speeds = {}

	for p in walker.clients:
		p: Client
		client_speeds[p] = await p.client_object.speed_multiplier()
		p.combat_status = False
		p.questing_status = False
		p.sigil_status = False
		p.questing_status = False
		p.use_team_up = use_team_up
		p.mouseless_status = False
		p.entity_detect_combat_status = False
		p.invincible_combat_timer = False
		p.original_location_before_combat = None
		p.duel_circle_joinable = True
		p.in_solo_zone = False
		p.wizard_name = None
		p.latest_drops: List[Tuple[str, int]] = []

		# Set follower/leader statuses for auto questing/sigil

		if client_to_follow:
			if client_to_follow in p.title:
				global sigil_leader_pid
				sigil_leader_pid = p.process_id

		if client_to_boost:
			if client_to_boost in p.title:
				global questing_leader_pid
				questing_leader_pid = p.process_id


	await listener.add_hotkey(Keycode[kill_tool_key], kill_tool_hotkey, modifiers=ModifierKeys.NOREPEAT)
	await enable_hotkeys()
	logger.debug('Hotkeys ready!')
	tool_status = True
	try:
		foreground_client_switching_task = asyncio.create_task(foreground_client_switching())
		assign_foreground_clients_task = asyncio.create_task(assign_foreground_clients())
		speed_switching_task = asyncio.create_task(speed_switching())
		combat_loop_task = asyncio.create_task(combat_loop())
		dialogue_loop_task = asyncio.create_task(dialogue_loop())
		anti_afk_loop_task = asyncio.create_task(anti_afk_loop())
		sigil_loop_task = asyncio.create_task(sigil_loop())
		in_combat_loop_task = asyncio.create_task(is_client_in_combat_loop())
		gui_task = asyncio.create_task(handle_gui())
		questing_loop_task = asyncio.create_task(questing_loop())
		questing_leader_combat_detection_task = asyncio.create_task(entity_detect_combat_loop())
		potion_usage_loop_task = asyncio.create_task(potion_usage_loop())
		rpc_loop_task = asyncio.create_task(rpc_loop())
		drop_logging_loop_task = asyncio.create_task(drop_logging_loop())
		zone_check_loop_task = asyncio.create_task(zone_check_loop())
		while True:
			await asyncio.wait([foreground_client_switching_task, speed_switching_task, combat_loop_task, assign_foreground_clients_task, dialogue_loop_task, anti_afk_loop_task, sigil_loop_task, in_combat_loop_task, questing_loop_task, questing_leader_combat_detection_task, gui_task, potion_usage_loop_task, rpc_loop_task, drop_logging_loop_task, zone_check_loop_task])

	finally:
		await tool_finish()


def bool_to_string(input: bool):
	if input:
		return 'Enabled'
	else:
		return 'Disabled'


if __name__ == "__main__":
	# Validate configs and update the tool
	version = get_latest_version()
	if version and auto_updating:
		if is_version_greater(version, tool_version):
			auto_update()

		if not is_version_greater(tool_version, version):
			config_update()

	current_log = logger.add(f"logs/{tool_name} - {generate_timestamp()}.log", encoding='utf-8', enqueue=True)

	# Steam support and config path support
	if wiz_path:
		utils.override_wiz_install_location(wiz_path)
	elif not os.path.exists(r'C:\Program Files (x86)\Steam\steamapps\common\Wizard101'):
		utils.override_wiz_install_location(r'C:\ProgramData\KingsIsle Entertainment\Wizard101')
	else:
		utils.override_wiz_install_location(r'C:\Program Files (x86)\Steam\steamapps\common\Wizard101')

	asyncio.run(main())