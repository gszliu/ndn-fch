#!/usr/bin/env python3

import pickle as pickle

geocode = pickle.load(open('gc.pkl'))

def confirm(s):
    try:
	return input(s)[0].lower() == 'y'
    except IndexError:
	print("Please enter 'y' or 'n'")
	return confirm(s)

def accept_input():
    s = input('\nEnter command: ')
    if s.strip() not in ['quit', 'q', 'exit']:
        process_command(s)
        accept_input()
    else:
        print('Exiting...')

def print_help():
    print('Available commands:')
    print('  display all\t\tdisplays all hub information with all fields')
    print('  display foo bar\tdisplays foo and bar hub information')
    print('  modify BAR\t\tmodifys BAR\'s hub information')
    print('  add BAR a b c d\tadds entry BAR w/ fullname a, loc (b, c), site d')
    print('  delete BAR\t\tremoves BAR information from the database')
    print('  help\t\t\tdisplay this help')

def is_hub(hub_name):
    return hub_name in list(geocode.keys())

def all_hubs():
    return list(geocode.keys())

def print_hub_rows(hubs):
    
    short_ml = max([len(hub) for hub in hubs] + [5])
    full_ml = max([len(geocode[hub][0]) for hub in hubs])
    loc_ml = max([len(str(geocode[hub][1])) for hub in hubs])
    site_ml = max([len(geocode[hub][2]) for hub in hubs])
    
    DISPLAY_FORMAT = '| {:<%d} | {:<%d} | {:^%d} | {:<%d} |' % (short_ml, full_ml, loc_ml, site_ml)
    
    print(DISPLAY_FORMAT.format('Short', 'Full Name', 'Location (Lat, Lon)', 'Site'))
    
    print('+' + '-' * (short_ml+2) + '+' + '-' * (full_ml+2) + '+' + '-' * (loc_ml+2) + '+' + '-' * (site_ml+2) + '+')
    
    for hub in hubs:
        print(DISPLAY_FORMAT.format(hub, *geocode[hub]))

def display(hubs):
    if hubs == ['all']:
        hubs = all_hubs()
    else:
        to_remove = []
        for hub in hubs:
            if not is_hub(hub):
                print('%s is not a valid hub.' % hub)
                to_remove.append(hub)
        hubs = list(set(hubs).difference(to_remove))
    
    if len(hubs) > 0:
        print('Displaying hub information...\n')
        print_hub_rows(sorted(hubs))
    else:
        print('No valid hub information to display.')
        
def modify_hub(hub):
    print_hub_rows([hub])
    choice = input('Modify which attribute (SHORT, FULL, LOC, SITE)? ')
    choice = choice.lower()
    if choice == 'short':
	while True:
	    new_short = input('Enter new short hub name: ')
	    if new_short in geocode:
		print('Name already exists in geocode.')
	    else:
		break
	if confirm("Confirm change from '%s' to '%s'? " % (hub, new_short)):
	    print('Modification successful')
	    geocode[new_short] = geocode.pop(hub)
	else:
	    print('Modification cancelled')	
    elif choice == 'full' or choice == 'site':
	string_map = {'full' : 'full name', 'site' : 'site'}
	index_map = {'full' : 0, 'site' : 2}
        new_full_name = input('Enter new %s name: ' % string_map[choice])
        if confirm("Confirm change from '%s' to '%s'? " % (geocode[hub][index_map[choice]], new_full_name)):
	    print('Modification successful')
	    geocode[hub][index_map[choice]] = new_full_name
	    print_hub_rows([hub])
	else:
	    print('Modification cancelled')
    elif choice == 'loc':
	print('Enter new location latitude and longitude:')
	new_lat = float(input('\tLatitude: '))
	new_long = float(input('\tLongitude: '))
	if confirm("Confirm change from [%s, %s] to [%s, %s]? " % (geocode[hub][1][0], geocode[hub][1][1], new_lat, new_long)):
	    print('Modification successful')
	    geocode[hub][1] = [new_lat, new_long]
	    print_hub_rows([hub])
	else:
	    print('Modification cancelled')
    else:
	print('Invalid choice')
	
    # Save current geocode file as pickle
    pickle.dump(geocode, open('gc.pkl', 'wb'))

def add_hub(hub_info):
    geocode[hub_info[0]] = [hub_info[1], [float(hub_info[2]), float(hub_info[3])], hub_info[4]]
    pickle.dump(geocode, open('gc.pkl', 'wb'))
    print('Hub addition successful')
    print_hub_rows([hub_info[0]])

def process_command(s):
    command_list = s.split()
    command = command_list[0].lower()
    if command == 'help':
        print_help()
    if len(command_list) < 2:
        print('Missing arguments for command: ' + command)
    elif command == 'display':
        display(command_list[1:])
    elif command == 'modify':
	if is_hub(command_list[1]):
	    modify_hub(command_list[1])
	else:
	    print('Invalid hub: ' + command_list[1])
    elif command == 'add':
	if len(command_list) != 6:
	    print('Improper command length. See help for ADD command format')
	elif command_list[1] in geocode:
	    print('Hub %s already exists:' % command_list[1])
	    print_hub_rows([command_list[1]])
	else:
	    add_hub(command_list[1:])
    elif command == 'delete':
	print_hub_rows([command_list[1]])
	if confirm('Remove hub \'%s\'? ' % command_list[1]):
	    geocode.pop(command_list[1])
	    pickle.dump(geocode, open('gc.pkl', 'wb'))
	    print('Removed information for hub \'%s\'.' % command_list[1])

def main():
    print_help()
    accept_input()

main()
