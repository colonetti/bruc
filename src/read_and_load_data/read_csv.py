# -*- coding: ISO-8859-1 -*-
"""
@author: Colonetti
"""

from datetime import date, timedelta
import csv
import numpy as np

from thermal_model.thermals import get_eq_units

def update_level_functions(params, hydros, hpf_model):
    '''Update forebay-level and tailrace level functions'''

    f = open(params.IN_FOLDER +  params.CASE + '/entdados.dat', 'r',encoding='ISO-8859-1')
    reader = csv.reader(f, delimiter = ';')
    row = next(reader)  # <BEGIN>

    #### Now, find the actual data
    while (len(row)) == 0 or not('&   ALTERACOES DE CADASTRO' in row[0]):
        row = next(reader)

    while not('&  TAXA DE DESVIO DE AGUA' in row[0]):
        #### Check if the plant is in the reduced system
        if row[0][0] != '&' and int(row[0][4:7]) in hydros.RESERVOIR_NAME:
            if ('COTVOL' in row[0]):
                if int(row[0][19:21]) == 0:
                    hpf_model.HPF_FB[int(row[0][4:7])]['F0'] = float(row[0][24:40].strip())
                    hpf_model.HPF_FB[int(row[0][4:7])]['F1'] = 0.00
                    hpf_model.HPF_FB[int(row[0][4:7])]['F2'] = 0.00
                    hpf_model.HPF_FB[int(row[0][4:7])]['F3'] = 0.00
                    hpf_model.HPF_FB[int(row[0][4:7])]['F4'] = 0.00
                elif int(row[0][19:21]) == 1:
                    hpf_model.HPF_FB[int(row[0][4:7])]['F1'] = float(row[0][24:40].strip())
                    hpf_model.HPF_FB[int(row[0][4:7])]['F2'] = 0.00
                    hpf_model.HPF_FB[int(row[0][4:7])]['F3'] = 0.00
                    hpf_model.HPF_FB[int(row[0][4:7])]['F4'] = 0.00
                elif int(row[0][19:21]) == 2:
                    hpf_model.HPF_FB[int(row[0][4:7])]['F2'] = float(row[0][24:40].strip())
                    hpf_model.HPF_FB[int(row[0][4:7])]['F3'] = 0.00
                    hpf_model.HPF_FB[int(row[0][4:7])]['F4'] = 0.00
                elif int(row[0][19:21]) == 3:
                    hpf_model.HPF_FB[int(row[0][4:7])]['F3'] = float(row[0][24:40].strip())
                    hpf_model.HPF_FB[int(row[0][4:7])]['F4'] = 0.00
                elif int(row[0][19:21]) == 4:
                    hpf_model.HPF_FB[int(row[0][4:7])]['F4'] = float(row[0][24:40].strip())
                else:
                    raise Exception('I couldnt reconize the index of the FBL function in ' + row[0])

            elif ('COTVAZ' in row[0]):
                if int(row[0][19:21]) == 0:
                    hpf_model.HPF_TR[int(row[0][4:7])]['T0'][0] = float(row[0][24:40].strip())
                    hpf_model.HPF_TR[int(row[0][4:7])]['T1'][0] = 0.00
                    hpf_model.HPF_TR[int(row[0][4:7])]['T2'][0] = 0.00
                    hpf_model.HPF_TR[int(row[0][4:7])]['T3'][0] = 0.00
                    hpf_model.HPF_TR[int(row[0][4:7])]['T4'][0] = 0.00
                elif int(row[0][19:21]) == 1:
                    hpf_model.HPF_TR[int(row[0][4:7])]['T1'][0] = float(row[0][24:40].strip())
                    hpf_model.HPF_TR[int(row[0][4:7])]['T2'][0] = 0.00
                    hpf_model.HPF_TR[int(row[0][4:7])]['T3'][0] = 0.00
                    hpf_model.HPF_TR[int(row[0][4:7])]['T4'][0] = 0.00
                elif int(row[0][19:21]) == 2:
                    hpf_model.HPF_TR[int(row[0][4:7])]['T2'][0] = float(row[0][24:40].strip())
                    hpf_model.HPF_TR[int(row[0][4:7])]['T3'][0] = 0.00
                    hpf_model.HPF_TR[int(row[0][4:7])]['T4'][0] = 0.00
                elif int(row[0][19:21]) == 3:
                    hpf_model.HPF_TR[int(row[0][4:7])]['T3'][0] = float(row[0][24:40].strip())
                    hpf_model.HPF_TR[int(row[0][4:7])]['T4'][0] = 0.00
                elif int(row[0][19:21]) == 4:
                    hpf_model.HPF_TR[int(row[0][4:7])]['T4'][0] = float(row[0][24:40].strip())
                else:
                    raise Exception('I couldnt reconize the index of the TRL function in ' + row[0])
        row = next(reader)

    f.close()
    del f

    return()
def readTrajectories(filename, params, thermals):
    '''Read shut-down and start-up tracjetories'''

    units_with_data = {'stup_traj': [], 'stdw_traj': []}

    f = open(filename, 'r', encoding = 'utf-8')
    reader = csv.reader(f, delimiter = ';')

    row = next(reader)  # <BEGIN>
    while row[0].strip() != '<Trajectories of units>':
        row = next(reader)

    row = next(reader)  # header

    header = {'Plant name': 0, 'Plant ID': 0, 'Unit': 0,'Trajectory': 0,'Steps': 0}

    for h in header:
        header[h] = row.index(h)

    row = next(reader)  # either the first unit or end

    while row[0].strip() != '</Trajectories of units>':
        g = (int(row[header['Plant ID']].strip()), int(row[header['Unit']].strip()))

        if g in thermals.UNIT_NAME:
            if row[header['Trajectory']].strip() == 'Start-up trajectory':
                trajectory = 'stup_traj'
            elif row[header['Trajectory']].strip() == 'Shut-down trajectory':
                trajectory = 'stdw_traj'
            else:
                trajectory = None
                raise Exception('I dont know what to do with trajectory ' +
                                        row[header['Trajectory']].strip() + ' of unit ' + str(g[1])
                                                                        + ' of plant ' + str(g[0]))

            units_with_data[trajectory].append(g)

            if trajectory == 'stup_traj':
                for step in [float(step) for step in row[header['Steps']:] if len(step) > 0]:
                    thermals.STUP_TRAJ[g].append(step/params.POWER_BASE)

            elif trajectory == 'stdw_traj':
                for step in [float(step) for step in row[header['Steps']:] if len(step) > 0]:
                    thermals.STDW_TRAJ[g].append(step/params.POWER_BASE)

        row = next(reader)

    for g in thermals.UNIT_NAME:
        if (g not in units_with_data['stup_traj'] or g not in units_with_data['stdw_traj']):
            raise Exception('I could not find trajectories for unit ' + str(thermals.UNIT_ID[g])\
                            + ' of plant ' + thermals.PLANT_NAME[g])

    for g in thermals.UNIT_NAME:
        if len(thermals.STDW_TRAJ[g]) > 0:
            if not(thermals.MIN_P[g] >= max(thermals.STDW_TRAJ[g])):
                raise Exception('There is something wrong with the shut-down trajectory of '+\
                                        ' unit ' + str(thermals.UNIT_ID[g]) + ' of plant ' +\
                                            thermals.PLANT_NAME[g])

        if len(thermals.STUP_TRAJ[g]) > 0:
            if not(thermals.MIN_P[g] >= max(thermals.STUP_TRAJ[g])):
                raise Exception('There is something wrong with the start-up trajectory of '+\
                                        ' unit ' + str(thermals.UNIT_ID[g]) + ' of plant ' +\
                                            thermals.PLANT_NAME[g])
    f.close()
    del f

    return()

def read_thermal_initial_states(filename, params, thermals):
    '''Read the initial state of the thermal units'''

    found = set()   # ids of thermal generating units for whom the initial state has been found

    EQ_UNITS = [g for g in thermals.UNIT_NAME if thermals.EQ_UNIT[g]]

    CC_PLANTS = []
    for g in EQ_UNITS:
        if thermals.PLANT_ID[g] not in CC_PLANTS:
            CC_PLANTS.append(thermals.PLANT_ID[g])

    ini_state_of_CC_PLANTS = {cc_p: 0 for cc_p in CC_PLANTS}

    f = open(filename, mode = 'r', encoding = 'ISO-8859-1')
    reader = csv.reader(f, delimiter = ';')

    row = next(reader)

    while len(row) == 0 or row[0].strip() != 'INIT':
        row = next(reader)

    row = next(reader)  # &us     nome       ug   st   GerInic     tempo MH A/D T  TITULINFLX
    row = next(reader)  # &XX XXXXXXXXXXXX  XXX   XX   XXXXXXXXXX  XXXXX  X  X  X  XXXXXXXXXX
    row = next(reader)  # either first unit or end

    while len(row) == 0 or row[0].strip() != 'FIM':
        if len(row) > 0 and row[0][0] != '&':
            g = (int(row[0][0:3].strip()), int(row[0][18:21].strip()))
            ini_state, ini_gen, time = int(row[0][24:26].strip()), float(row[0][29:39].strip()),\
                                                            max(int(row[0][41:46].strip()), 1)
            assert ini_state in (0, 1), 'I dont understand what state ' + str(ini_state) +\
                                        ' of unit ' + str(g[1]) + ' of plant ' + str(g[0])
            try:
                thermals.HOURS_IN_PREVIOUS_STATE[g] = time

                if thermals.PLANT_ID[g] in CC_PLANTS:
                    # the initial state of the combined-cycle plant is 1. this block has been added
                    # to avoid having two or more equivalent units at the same plant with a
                    # 1 initial state
                    if ini_state == 1 and ini_state_of_CC_PLANTS[thermals.PLANT_ID[g]] == 0:
                        thermals.STATE_0[g] = ini_state
                        ini_state_of_CC_PLANTS[thermals.PLANT_ID[g]] = ini_state
                        if ini_state == 1:
                            if thermals.MIN_P[g] <= ini_gen/params.POWER_BASE <= thermals.MAX_P[g]:
                                thermals.TG_0[g] = ini_gen/params.POWER_BASE
                            elif ini_gen/params.POWER_BASE > thermals.MAX_P[g]:
                                thermals.TG_0[g] = thermals.MAX_P[g]
                            else:
                                thermals.TG_0[g] = thermals.MIN_P[g]
                        else:
                            thermals.TG_0[g] = 0
                    # else:
                    #     thermals.STATE_0[g] = 0
                    #     thermals.TG_0[g] = 0

                    # note that if ini_state == 1 and there already is an equivalent unit who is
                    # operating (state 1), and thus
                    # ini_state_of_CC_PLANTS[thermals.PLANT_ID[g]] == 1, the initial state of
                    # current unit g will be forced to be 0
                else:
                    thermals.STATE_0[g] = ini_state
                    if ini_state == 1:
                        if thermals.MIN_P[g] <= ini_gen/params.POWER_BASE <= thermals.MAX_P[g]:
                            thermals.TG_0[g] = ini_gen/params.POWER_BASE
                        elif ini_gen/params.POWER_BASE > thermals.MAX_P[g]:
                            thermals.TG_0[g] = thermals.MAX_P[g]
                        else:
                            thermals.TG_0[g] = thermals.MIN_P[g]
                    else:
                        thermals.TG_0[g] = 0
                found.add(g)

            except KeyError:
                print('Unit ' + str(g[1]) + ' of plant ' + str(g[0]) +\
                                            ' could not be found in the system. (Initial state.)')

        row = next(reader)

    f.close()
    del f

    if found != set(g for g in thermals.UNIT_NAME):
        print('\n\nWarning!')
        print('Initial state could not be found for units '\
                                                +str(set(g for g in thermals.UNIT_NAME) - found))
        print(flush = True)

    return()

def read_thermal_linear_costs(filename, params, thermals):
    '''Read the linear costs of thermal generation'''

    found = set()

    f = open(filename, mode = 'r', encoding = 'ISO-8859-1')
    reader = csv.reader(f, delimiter = ';')

    row = next(reader)

   #### now read the linear generation costs
    while len(row) == 0 or row[0][0:4] != 'OPER':
        row = next(reader)

    row = next(reader)

    row = next(reader)  # &us    nome      un di hi m df hf m Gmin     Gmax       Custo
    row = next(reader)  # &XX XXXXXXXXXXXX XX XX XX X XX XX X XXXXXXXXXXxxxxxxxxxxXXXXXXXXXX

    while len(row) == 0 or row[0].strip() != 'FIM':
        if len(row) > 0 and row[0][0] != '&':
            g = (int(row[0][0:3].strip()), int(row[0][17:19].strip()))
            cost = float(row[0][57:66].strip())*params.DISCRETIZATION*params.POWER_BASE

            try:
                thermals.GEN_COST[g] = cost*params.SCAL_OBJ_FUNC
                found.add(g)
            except KeyError:
                print('Unit ' + str(g[1]) + ' of plant ' + str(g[0]) +\
                                            ' could not be found in the system. (Linear costs.)')

        row = next(reader)

    f.close()
    del f

    if found != set(g for g in thermals.UNIT_NAME):
        print('\n\nWarning!')
        print('Linear generation costs could not be found for units ' +\
                                                    str(set(g for g in thermals.UNIT_NAME) - found))
        print(flush = True)

    return()

def read_thermal_gen_units(filename, params, thermals):
    '''Read data of thermal generating units
    thermals is a instance of class Thermals
    '''

    f = open(filename, mode = 'r', encoding = 'ISO-8859-1')
    reader = csv.reader(f, delimiter = ';')

    row = next(reader)

    while row[0] != '<Thermal generating units>':
        row = next(reader)

    row = next(reader) # header

    header = {"Plant's Name": -9, "Plant\'s ID": -9, "Unit's ID": -9, 'Bus': -9,\
            'Minimum power output (MW)': 1e3, 'Maximum power output (MW)': -1e3,\
            "Ramp-up limit (MW/h)": -9, "Ramp-down limit (MW/h)": -9,\
            "Minimum up-time (h)": -9, "Minimum down-time (h)": -9,\
            "Constant cost ($)": -9, "Start-up cost ($)": -9, "Shut-down cost ($)": -9}

    for h in header:
        header[h] = row.index(h)

    row = next(reader) # either first unit or end

    while row[0] != '</Thermal generating units>':
        thermals.add_new_unit(row, header, params)
        row = next(reader)

    f.close()
    del f

    return ()

def read_combined_cycles_eq_units(filename, params, thermals):
    '''Read configurations of combined-cycle equivalent units.
    This functions alters thermals. It removes real units from thermals that participate in
    a combined-cycle unit. It also adds to thermals equivalent units
    '''

    f = open(filename, mode = 'r', encoding = 'ISO-8859-1')
    reader = csv.reader(f, delimiter = ';')

    row = next(reader)

    while row[0] != '<Equivalent units>':
        row = next(reader)

    row = next(reader) # header

    header = {"Plant's ID": -9, "Plant's Name": -9, "Unit's ID": -9,
                    "Real units part of equivalent unit (units are separated by semicolons)": -9}
    header.update({'Minimum power output (MW)': 0, 'Maximum power output (MW)': 0,
                        'Ramp-up limit (MW/h)': 0, 'Ramp-down limit (MW/h)': 0,
                            'Minimum up-time (h)': 0, 'Minimum down-time (h)': 0,
                                'Transition ramp (MW/h)': 0, 'Bus': 0,
                                    'Constant cost ($)': 0, 'Start-up cost ($)': 0,
                                        'Shut-down cost ($)': 0})
    for h in header:
        header[h] = row.index(h)

    row = next(reader)          # either first unit or end


    plants_with_eq_units = set()    # a plant must have either only real units or only eq units

    while row[0] != '</Equivalent units>':
        plant_id = int(row[header["Plant's ID"]].strip())
        unit_id = int(row[header["Unit's ID"]])
        real_units_of_plant = [thermals.UNIT_ID[g] for g in thermals.UNIT_NAME
                                                            if thermals.PLANT_ID[g] == plant_id]
        plants_with_eq_units.add(plant_id)
        #all real units of plants in <Equivalent units> must be part of at least one equivalent unit

        thermals.add_new_unit(row, header, params)

        thermals.EQ_UNIT[(plant_id, unit_id)] = True
        thermals.TRANS_RAMP[(plant_id, unit_id)] = params.DISCRETIZATION*\
                            float(row[header['Transition ramp (MW/h)']].strip())/params.POWER_BASE

        for real_unit in [int(real_unit) for real_unit in
            row[header["Real units part of equivalent unit (units are separated by semicolons)"]:]
                    if real_unit != '']:
            # check if unit really exists
            assert real_unit in real_units_of_plant, 'Unit ' + str(real_unit) + ' of plant ' +\
                                            row[header["Plant's name"]].strip() + ' does not exist'
            thermals.REAL_UNITS_IN_EQ[(plant_id, unit_id)].append(real_unit)

        row = next(reader)

    f.close()
    del f

    # real units that will be deleted because they are part of equivalent units
    real_units_to_delete = {g for g in thermals.UNIT_NAME
                    if thermals.PLANT_ID[g] in plants_with_eq_units and not(thermals.EQ_UNIT[g])}

    # now, delete from thermals the real units that participate in a equivalent unit
    for real_unit in real_units_to_delete:
        for k in thermals.__dict__:
            x = getattr(thermals, k)
            del x[real_unit]

    # either the plant has only equivalent units or it has only real units, a plant cannot have both
    PLANTS = set(thermals.PLANT_NAME[g] for g in thermals.UNIT_NAME)
    for plant in PLANTS:
        # get the flags, True or False, that indicate wheather a unit is real or is equivalent
        eq_unit_flags = set(thermals.EQ_UNIT[g] for g in thermals.UNIT_NAME
                                                                if thermals.PLANT_NAME[g] == plant)
        # if a plant has only real or equivalent units,
        # then eq_unit_flags should contain only False or True
        assert len(eq_unit_flags) == 1,\
                                'Units of plant '+plant+' are not either only real or equivalent'

    #### Some units are give as equivalent units when they can actually be treated as a physical one
    #### This is particularly true if a plant has a single operation model. In this context,
    #### only one equivalent unit is necessary, and it can be treated as an ordinary unit
    EQ_UNITS = [g for g in thermals.UNIT_NAME if thermals.EQ_UNIT[g]]

    CC_PLANTS, EQ_UNITS_OF_PLANTS = get_eq_units(thermals)

    CC_PLANTS_WITH_SINGLE_UNITS = []
    for cc_plant in CC_PLANTS:
        if len(EQ_UNITS_OF_PLANTS[cc_plant]) == 1:
            CC_PLANTS_WITH_SINGLE_UNITS.append(cc_plant)

    #### now change the units for the plants in CC_PLANTS_WITH_SINGLE_UNITS from equivalent units
    #### to physical ones
    for cc_plant in CC_PLANTS_WITH_SINGLE_UNITS:
        for g in [g for g in EQ_UNITS if thermals.PLANT_ID[g] == cc_plant]:
            thermals.EQ_UNIT[g] = False

    return ()

def read_network_model(filename, params, network):
    '''Read data of the DC network model
    '''

    f = open(filename, mode = 'r', encoding = 'ISO-8859-1')
    reader = csv.reader(f, delimiter = ';')

    row = next(reader)

    while row[0] != '<GENERAL INFORMATION>':
        row = next(reader)

    while row[0] != '<Reference buses>':
        row = next(reader)

    row = next(reader) # header

    row = next(reader) # first or end
    while row[0] != '</Reference buses>':
        network.REF_BUS_ID.append(int(row[0].strip()))   # get reference bus' id
        network.REF_BUS_NAME.append(row[1].strip())     # get reference bus' name
        row = next(reader)

    while row[0] != '<BUSES>':
        row = next(reader)

    row = next(reader)                      # header

    header = {"ID": -9, "Name": -9, "Base voltage (kV)": -9, 'Area': -9,
                'Subsystem market - Name': -1, 'Subsystem market - ID': -1}

    for h in header:
        header[h] = row.index(h)

    row = next(reader) # either first bus or end

    while row[0] != '</BUSES>':
        network.add_new_bus(row, header)
        row = next(reader)

    while row[0] != '<AC Transmission lines>':
        row = next(reader)

    row = next(reader)                      # header

    header = {"ID": -99, "From (ID)": -99, "From (Name)": -99, 'To (ID)': -99,
                'To (Name)': -99, 'Line rating (MW)': -99, 'Emergency rating (MW)': -99,
                'Reactance (%) - 100-MVA base': -99}

    for h in header:
        header[h] = row.index(h)

    row = next(reader) # either first line or end

    while row[0] != '</AC Transmission lines>':
        network.add_new_line(row, header, params)
        row = next(reader)

    f.close()
    del f

    return()

def read_DC_links(filename, params, network):
    '''Read data of DC links
    '''

    f = open(filename, mode = 'r', encoding = 'ISO-8859-1')
    reader = csv.reader(f, delimiter = ';')

    row = next(reader) # BEGIN

    while row[0] != '<DC Links>':
        row = next(reader)

    row = next(reader) # header

    header = {'ID': -9, 'From (ID)': -9, 'From (Name)': -9, 'To (ID)': -9, 'To (Name)': -9,
        'Rating (MW)': -9}

    for h in header:
        header[h] = row.index(h)

    row = next(reader)  # first link or end
    while row[0] != '</DC Links>':
        network.add_new_DC_link(row, header, params)
        row = next(reader)

    f.close()
    del f

    return()

def read_network_DESSEM(filename, params):
    '''Read the network model from the DESSEM files
        Write the model to a more human-friendly file
    '''

    networkBuses = {}       # buses
    networkACLines = {}     # ac lines
    baseVoltages = {}

    f = open(filename, 'r', encoding = 'ISO-8859-1')
    reader = csv.reader(f, delimiter = ';')

    row = next(reader)

    while len(row) == 0 or row[0][0:4] != 'DBAR':
        row = next(reader)

    row = next(reader) # header
    row = next(reader) # first bar or end

    while len(row) == 0 or row[0][0:5] != '99999':
        networkBuses[row[0][0:5].strip()] = {'name': row[0][10:22].strip(),
                                        'load (MW)': float(row[0][58:63].strip())
                                                        if len(row[0][58:63].strip()) > 0 else 0,
                                        'renewable generation (MW)': 0,
                                        'area': int(row[0][73:76].strip()),
                                        'subsystem': int(row[0][98]),
                                        'baseVoltage (kV)': row[0][8:10].strip()}
        row = next(reader)

    row = next(reader)

    while len(row) == 0 or row[0][0:4] != 'DLIN':
        row = next(reader)

    row = next(reader) # header
    row = next(reader) # first line or end

    l = 0
    while len(row) == 0 or row[0][0:5] != '99999':
        if row[0][0] != '(':
            networkACLines[str(l)] = {'from': row[0][0:5].strip(), 'to': row[0][10:15].strip(),
                                'X (%)': float(row[0][26:32].strip()),
                                'rating (MW)': max(float(row[0][64:68].strip()),
                                                float(row[0][74:78].strip())),
                                'emergency rating (MW)': max(float(row[0][64:68].strip()),
                                                            float(row[0][68:72].strip()),
                                                            float(row[0][74:78].strip()))}
            l += 1
        row = next(reader)

    while len(row) == 0 or row[0][0:4] != 'DGBT':
        row = next(reader)

    row = next(reader) # header
    row = next(reader) # first area or end

    while len(row) == 0 or row[0][0:5] != '99999':
        baseVoltages[row[0][0:2].strip()] = float(row[0][3:8].strip())
        row = next(reader)

    f.close()
    del f

    f = open(params.IN_FOLDER +  params.CASE + '/network - ' + params.PS + ' - case ' +
                                            params.CASE + '.csv', 'w', encoding = 'ISO-8859-1')
    f.write('<BEGIN>\n')
    f.write('<GENERAL INFORMATION>\n')
    f.write('Power basis (MVA);100\n')
    f.write('<Reference buses>\n')
    f.write('ID;Name\n')
    f.write('10;ANGRA1UNE001\n')
    f.write('</Reference buses>\n')
    f.write('</GENERAL INFORMATION>\n')
    f.write('<BUSES>\n')
    f.write('ID;Name;Base voltage (kV);Area;')
    f.write('Subsystem market - Name;Subsystem market - ID\n')
    for bus_id in networkBuses:
        f.write(str(bus_id) + ';')
        f.write(networkBuses[bus_id]['name'] + ';')
        if networkBuses[bus_id]['baseVoltage (kV)'] in baseVoltages:
            f.write(str(baseVoltages[networkBuses[bus_id]['baseVoltage (kV)']]) + ';')
        else:
            f.write('-1;')
        f.write(str(networkBuses[bus_id]['area']) + ';')
        if networkBuses[bus_id]['subsystem'] == 1:
            f.write('SE' + ';')
        elif networkBuses[bus_id]['subsystem'] == 2:
            f.write('S' + ';')
        elif networkBuses[bus_id]['subsystem'] == 3:
            f.write('NE' + ';')
        elif networkBuses[bus_id]['subsystem'] == 4:
            f.write('N' + ';')
        else:
            raise Exception('I dont know what subsystem ' + str(networkBuses[bus_id]['subsystem']) +
                            ' of bus ' + networkBuses[bus_id]['name'] + ' is.')

        f.write(str(networkBuses[bus_id]['subsystem']) + ';')
        f.write('\n')
    f.write('</BUSES>\n')

    f.write('<AC Transmission lines>\n')
    f.write('ID;From (ID);From (Name);To (ID);To (Name);Line rating (MW);Emergency rating (MW);')
    f.write('Reactance (%) - 100-MVA base')
    f.write('\n')
    for line in networkACLines:
        f.write(str(line) + ';')
        f.write(str(networkACLines[line]['from']) + ';')
        f.write(networkBuses[networkACLines[line]['from']]['name'] + ';')
        f.write(str(networkACLines[line]['to']) + ';')
        f.write(networkBuses[networkACLines[line]['to']]['name'] + ';')
        f.write(str(networkACLines[line]['rating (MW)']) + ';')
        f.write(str(networkACLines[line]['emergency rating (MW)']) + ';')
        f.write(str(networkACLines[line]['X (%)']) + ';')
        f.write('\n')
    f.write('</AC Transmission lines>\n')
    f.write('</END>')
    f.close()
    del f

    return()

def read_load_DESSEM(params, network, hydros):
    '''Read the load from the DESSEM input files
    '''

    levels = {}                 # load level for each period
    edit_file_per_period = {}   # a tuple of the form (level, pat file)

    f = open(params.IN_FOLDER +  params.CASE + '/desselet.dat', 'r', encoding='ISO-8859-1')
    reader = csv.reader(f, delimiter = ';')

    row = next(reader)

    while len(row) < 1 or\
                    row[0][0:len('( Arquivos de caso base')].strip() != '( Arquivos de caso base':
        row = next(reader)

    row = next(reader) # header
    row = next(reader) # first level

    while len(row) < 1 or row[0].strip() != '99999':
        if len(row) > 0 and row[0][0] != '(':
            levels[int(row[0][0:3].strip())] = row[0][5:17].strip()
        row = next(reader)

    while len(row) < 1 or\
            row[0][0:len('(( Alteracoes dos casos base')].strip() != '(( Alteracoes dos casos base':
        row = next(reader)

    row = next(reader) # header
    row = next(reader) # first period

    t = 0
    while len(row) < 1 or row[0].strip() != '99999':
        if len(row) > 0:
            edit_file_per_period[t] = (levels[int(row[0][40:44].strip())], row[0][45:].strip())
        row = next(reader)
        t += 1

    f.close()
    del f

    # gross load and renewable generation at each bus and time period
    gross_load = {bus: [0 for t in range(params.T)] for bus in network.BUS_ID}
    renewable_gen = {bus: [0 for t in range(params.T)] for bus in network.BUS_ID}

    for t in range(params.T):
        # base load for each bus at time period t
        base_load = {bus: 0 for bus in network.BUS_ID}

        f = open(params.IN_FOLDER +  params.CASE + '/' +
                                edit_file_per_period[t][0] + '.pwf', 'r', encoding = 'ISO-8859-1')
        reader = csv.reader(f, delimiter = ';')

        row = next(reader)

        while len(row) == 0 or row[0][0:4] != 'DBAR':
            row = next(reader)

        row = next(reader) # header
        row = next(reader) # first bar or end

        while len(row) == 0 or row[0][0:5] != '99999':
            base_load[int(row[0][0:5].strip())] = float(row[0][58:63].strip())\
                                                            if len(row[0][58:63].strip()) > 0 else 0
            row = next(reader)

        f.close()
        del f

        # with the base load as reference, the loading per area indicates how the load of the buses
        # of a given area vary over time
        loading_per_area = {area: -9999 for area in set(network.BUS_AREA.values())}

        #### Get the buses
        f = open(params.IN_FOLDER +  params.CASE + '/' + edit_file_per_period[t][1],
                                                                'r', encoding = 'ISO-8859-1')
        reader = csv.reader(f, delimiter = ';')

        row = next(reader)

        while len(row) < 1 or row[0].strip() != 'DANC MUDA':
            row = next(reader)

        row = next(reader) # first area

        while len(row) < 1 or row[0].strip() != '99999':
            if len(row) > 0 and row[0][0] != '(':
                loading_per_area[int(row[0][0:3].strip())] = float(row[0][4:10].strip())
            row = next(reader)

        area_list = [area for area in loading_per_area if loading_per_area[area] < 0]
        for area in area_list:
            assert sum([base_load[bus] for bus in network.BUS_ID
                            if network.BUS_AREA[bus]==area]) == 0,\
                                    'The loading of area ' + str(area) + ' is less than zero'

        while len(row) < 1 or row[0].strip() != 'DBAR MUDA':
            row = next(reader)

        row = next(reader) # header
        row = next(reader) # first bus

        while len(row) < 1 or row[0].strip() != '99999':
            if len(row) > 0:
                renewable_gen[int(row[0][1:6].strip())][t] = float(row[0][32:38].strip())
            row = next(reader)

        f.close()
        del f

        for bus in network.BUS_ID:
            gross_load[bus][t] = base_load[bus]*(loading_per_area[network.BUS_AREA[bus]]/100)


    #### Now read the load of ANDE

    # Itaipu ID: 66. Name of first 50-Hz unit: G1-ITAIPU. ID of this unit: (66, 1)
    bus50Hz = hydros.UNIT_BUS_ID[(66, 1)]

    original_load = [gross_load[bus50Hz][t] for t in range(params.T)]
    ANDE_load = [0 for t in range(params.T)]

    f = open(params.IN_FOLDER +  params.CASE + '/entdados.dat', 'r', encoding='ISO-8859-1')
    reader = csv.reader(f, delimiter = ';')

    row = next(reader)

    l = len('&   RESTRICAO DE ITAIPU 50HZ E 60HZ E PARCELA DA ANDE')
    while len(row) == 0 or len(row[0]) < l or\
                            row[0][0:l] != '&   RESTRICAO DE ITAIPU 50HZ E 60HZ E PARCELA DA ANDE':
        row = next(reader)

    row = next(reader)  # &
    row = next(reader)  # &   ind di hi m df hf m    Gh50 min  GH50 max  GH60 min  GH60 max    ANDE
    row = next(reader)  # &   XXX XX XX X XX XX X   XXXXXXXXXXxxxxxxxxxxXXXXXXXXXXxxxxxxxxxxXXXXXXX
    row = next(reader)  # first data or end

    while row[0][0] != '&':
        if row[0][8:10].strip() == 'I':
            first_day = params.CASE_DATE
        else:
            first_day = date(params.CASE_DATE.year,params.CASE_DATE.month,int(row[0][8:10].strip()))

            n_days = params.CASE_DATE - first_day
            if n_days.days <= -15:
                # Constraint from previous month
                first_day = date(params.CASE_DATE.year, params.CASE_DATE.month-1,\
                                                                        int(row[0][8:10].strip()))

        initial_hour = row[0][11:13].strip() if len(row[0][11:13].strip()) > 0 else '0'

        if (row[0][16:18].strip() == 'F'):
            last_day = params.CASE_DATE + timedelta(7)
        elif int(row[0][16:18].strip()) < params.CASE_DATE.day:
            last_day = date(params.CASE_DATE.year, params.CASE_DATE.month + 1,\
                            int(row[0][16:18].strip()))
        else:
            last_day =date(params.CASE_DATE.year, params.CASE_DATE.month,int(row[0][16:18].strip()))

        last_hour = row[0][19:21].strip() if len(row[0][19:21].strip()) > 0 else '0'

        first_time_step = -1e12
        for t in range(params.T):
            n_days = params.DATES_OF_TIME_STEPS[t][4] - first_day
            if (n_days.days >= 1) or (n_days.days == 0 and\
                                        params.DATES_OF_TIME_STEPS[t][1] >= int(initial_hour)):
                first_time_step = t
                break

        last_time_step = 1e12

        if first_time_step == -1e12:
            #This constraint begins after the horizon
            pass
        else:
            for t in range(first_time_step, params.T, 1):
                nDays = params.DATES_OF_TIME_STEPS[t][4] - last_day
                if nDays.days >= 0 and params.DATES_OF_TIME_STEPS[t][1] >= int(last_hour):
                    last_time_step = t
                    break

            if last_time_step == 1e12:
                last_time_step = params.T

            for t in range(first_time_step, last_time_step, 1):
                ANDE_load[t] = float(row[0][66:76].strip())

        row = next(reader) # next data

    for t in range(params.T):
        gross_load[bus50Hz][t] = original_load[t] + ANDE_load[t]

    f.close()
    del f

    f = open(params.IN_FOLDER +  params.CASE +
                    '/gross load - ' + params.PS + '.csv', 'w', encoding = 'ISO-8859-1')
    for bus in network.BUS_ID:
        f.write(str(bus) + ';')
    f.write('\n')
    for t in range(params.T):
        for bus in network.BUS_ID:
            f.write(str(gross_load[bus][t]) + ';')
        f.write('\n')
    f.close()
    del f

    f = open(params.IN_FOLDER +  params.CASE +
                    '/renewable generation - ' + params.PS + '.csv', 'w', encoding = 'ISO-8859-1')
    for bus in network.BUS_ID:
        f.write(str(bus) + ';')
    f.write('\n')
    for t in range(params.T):
        for bus in network.BUS_ID:
            f.write(str(renewable_gen[bus][t]) + ';')
        f.write('\n')
    f.close()
    del f

    return()

def read_load(params, network, filename_gross_load, filename_renewable_gen):
    '''Read the gross load and the renewable generation to get the net load at each bus'''

    header_gross_load = []

    f = open(filename_gross_load, 'r', encoding = 'ISO-8859-1')
    reader = csv.reader(f, delimiter = ';')

    row = next(reader)

    for bus in [bus for bus in row[:] if bus != '']:
        header_gross_load.append(bus.strip())

    gross_load = [[0 for t in range(params.T)] for bus in header_gross_load]

    for t in range(params.T):
        row = next(reader)
        for b in range(len(header_gross_load)):
            gross_load[b][t] = float(row[b])

    f.close()
    del f

    header_renewable_gen = []

    f = open(filename_renewable_gen, 'r', encoding = 'ISO-8859-1')
    reader = csv.reader(f, delimiter = ';')

    row = next(reader)

    for bus in [bus for bus in row[:] if bus != '']:
        header_renewable_gen.append(bus.strip())

    renewable_gen = [[0 for t in range(params.T)] for bus in header_renewable_gen]

    for t in range(params.T):
        row = next(reader)
        for b in range(len(header_renewable_gen)):
            renewable_gen[b][t] = float(row[b])

    f.close()
    del f

    network.NET_LOAD = np.subtract(np.array(gross_load), np.array(renewable_gen))/params.POWER_BASE

    b = 0
    for bus in network.BUS_ID:
        network.BUS_HEADER[bus] = b
        b += 1

    return()

def read_hydro_reservoirs(filename, params, hydros):
    '''Read data of hydro reservoirs
    '''

    f = open(filename, mode = 'r', encoding = 'ISO-8859-1')
    reader = csv.reader(f, delimiter = ';')

    row = next(reader) # BEGIN

    while row[0] != '<Hydro reservoirs>':
        row = next(reader)

    row = next(reader) # header

    header = {'ID': -30, 'Name': -30,
            'Minimum reservoir volume (hm3)': -30, 'Maximum reservoir volume (hm3)':-30,
            'Name of downriver reservoir': -30, 'Water travelling time (h)': -30,
            'Run-of-river plant? TRUE or FALSE': -30,
            'Minimum forebay level (m)': -30, 'Maximum forebay level (m)': -30,
            'Maximum spillage (m3/s)': -30, 'Basin': -30,
            'Downriver plant of bypass discharge': -30,
            'Maximum bypass discharge (m3/s)': -30,
            'Water travel time in bypass (h)': -30,
            'Influence of spillage on the HPF? Yes or No': -30}

    for h in header:
        header[h] = row.index(h)

    row = next(reader)  # first link or end
    while row[0] != '</Hydro reservoirs>':
        hydros.add_new_reservoir(row, header, params)
        row = next(reader)

    f.close()
    del f

    return()

def read_hydro_generating_units(filename, params, hydros):
    '''Read data of hydro generating units, the turbines
    '''

    f = open(filename, mode = 'r', encoding = 'ISO-8859-1')
    reader = csv.reader(f, delimiter = ';')

    row = next(reader) # BEGIN

    while row[0] != '<Hydro turbines>':
        row = next(reader)

    row = next(reader) # header

    header = {'Hydro reservoir ID': -9, 'Name': -9,
            'Hydro reservoir name': -9, 'Group ID':-9,
            'Group name': -9, 'Unit ID': -9,
            'Bus ID': -9,
            'Minimum generation (MW)': -9, 'Maximum generation (MW)': -9,
            'Minimum turbine discharge (m3/s)': -9, 'Maximum turbine discharge (m3/s)': -9,
            'Turbine type': -9}

    for h in header:
        header[h] = row.index(h)

    row = next(reader)  # first link or end
    while row[0] != '</Hydro turbines>':
        hydros.add_new_turbine(row, header, params)
        row = next(reader)

    f.close()
    del f

    return()

def read_hydro_pumps(filename, params, hydros):
    '''Read data of hydro pumps
    '''

    f = open(filename, mode = 'r', encoding = 'ISO-8859-1')
    reader = csv.reader(f, delimiter = ';')

    row = next(reader) # BEGIN

    while row[0] != '<Hydro pumps>':
        row = next(reader)

    row = next(reader) # header

    header = {'Hydro reservoir ID': -9, 'Name': -9,
            'Hydro reservoir name': -9, 'Unit ID': -9,
            'Bus ID': -9,
            'Minimum pumping discharge (m3/s)': -9, 'Maximum pumping discharge (m3/s)': -9,
            'Conversion rate MW/(m3/s/) for pumps': -9,
            'Downriver reservoir of pump units': -9,
            'Upriver reservoir of pump units': -9,
            'Water travel time in pumping (h)': -9}

    for h in header:
        header[h] = row.index(h)

    row = next(reader)  # first link or end
    while row[0] != '</Hydro pumps>':
        hydros.add_new_pump(row, header, params)
        row = next(reader)

    f.close()
    del f

    return()


def read_date(filename_desselet, params):
    '''Make a correspondence between the time steps and the actual dates'''

    f = open(filename_desselet, "r", encoding = 'ISO-8859-1')
    reader = csv.reader(f)
    row = next(reader)

    while not('Alteracoes dos casos base' in row[0]):
        row = next(reader)

    row = next(reader) # header
    row = next(reader) # first step or end
    t = 0
    while row[0][0:5] != '99999':
        params.DATES_OF_TIME_STEPS.append([-1e12, -1e12, -1e12, -1e12, None])
        # [day, hour, half-hour, duration in hours, date in daymonthyear]
        params.DATES_OF_TIME_STEPS[t] = [int(row[0][24:26].strip()),\
                                            int(row[0][27:29].strip()),\
                                            1 if float(row[0][30:32].strip()) > 0 else 0,\
                                            float(row[0][33:37].strip()),\
                                        date(int(row[0][18:22].strip()),\
                                            int(row[0][22:24].strip()),\
                                            int(row[0][24:26].strip()))]
        t += 1
        row = next(reader)

    if t > 48:
        raise NotImplementedError('The time horizon must be exactly composed of ' +
                                                                            '48 half-hour periods')
    f.close()
    del f

    params.CASE_DATE = params.DATES_OF_TIME_STEPS[0][4]

    return()

def read_hydro_initial_state_DESSEM(params, hydros, W_RANK,\
                                    filename_DEFLANT, filename_ENTDADOS):
    '''Read the initial states, volume and discharges, of the hydro units and planes from
    the DESSEM files'''

    ### Create a list to keep track of the initial volumes found
    found = {h: False for h in hydros.RESERVOIR_NAME}
    store_ini_vol = {h: None for h in hydros.RESERVOIR_NAME}

    f = open(filename_ENTDADOS, 'r', encoding = 'ISO-8859-1')
    reader = csv.reader(f, delimiter = ';')
    row = next(reader)  # <BEGIN>
    #### Find the header for the data
    while not('&   USINAS HIDRAULICAS' in row[0]):
        row = next(reader)

    #### Now, find the actual data
    while not('UH  ' in row[0]):
        row = next(reader)

    len_str = len('&  TEMPO DE VIAGEM')
    while row[0][0:len_str] != '&  TEMPO DE VIAGEM':
        #### Check if the plant is in the reduced system
        if len(row) > 0 and '&' != row[0][0]:
            try:
                found[int(row[0][4:7])] = True
                store_ini_vol[int(row[0][4:7])] = (float(row[0][29:36])/100)
            except ValueError:
                pass
        row = next(reader)

    #### Now, find the actual data
    while (len(row)) == 0 or not('&   ALTERACOES DE CADASTRO' in row[0]):
        row = next(reader)

    while not('&  TAXA DE DESVIO DE AGUA' in row[0]):
        #### Check if the plant is in the reduced system
        if row[0][0] != '&':
            if int(row[0][4:7]) in hydros.RESERVOIR_NAME:
                if ('VOLMAX' in row[0]):
                    hydros.MAX_VOL[int(row[0][4:7])] = float(row[0][19:30].strip())

                if ('VOLMIN' in row[0]):
                    hydros.MIN_VOL[int(row[0][4:7])] = float(row[0][19:30].strip())

        row = next(reader)

    f.close()
    del f

    for h in hydros.RESERVOIR_NAME:
        if not(found[h]):
            s = 'No initial reservoir volume has been found for hydro plant '\
                                                                        + hydros.RESERVOIR_NAME[h]
            raise Exception(s)
        hydros.V_0[h] = store_ini_vol[h]*(hydros.MAX_VOL[h] - hydros.MIN_VOL[h]) + hydros.MIN_VOL[h]

    #hydros.SPIL_0 = {(h, t): 0 for h in hydros.RESERVOIR_NAME for t in range(-1440, 0, 1)}

    end_reached = False

    f = open(filename_DEFLANT, 'r', encoding = 'ISO-8859-1')
    reader = csv.reader(f, delimiter = ';')
    row = next(reader)  # <BEGIN>
    #### Find the header for the data
    while not('DEFANT' in row[0]):
        row = next(reader)

    while not(end_reached):
        #### Check if the plant is in the reduced system
        if ('DEFANT' in row[0][0:6]) and int(row[0][9:13].strip()) in hydros.RESERVOIR_NAME:
            h = int(row[0][9:13].strip())
            found = True
        else:
            found = False

        if found:
            f_day = int(row[0][24:26].strip())

            if params.CASE_DATE.day < f_day:
                # from previous month
                if params.CASE_DATE.month - 1 > 0:
                    f_day = date(params.CASE_DATE.year, params.CASE_DATE.month - 1, f_day)
                elif params.CASE_DATE.month - 1 == 0:
                    # previous year
                    f_day = date(params.CASE_DATE.year - 1, 12, f_day)
                else:
                    raise Exception('What is this date?')
            else:
                f_day = date(params.CASE_DATE.year, params.CASE_DATE.month, f_day)

            n_days = params.CASE_DATE - f_day

            for t in range(-params.T*n_days.days, 0, 1):
                hydros.SPIL_0[h, t] = float(row[0][44:55].strip())

        try:
            row = next(reader)
        except StopIteration:
            end_reached = True

    for h in [h for h in hydros.RESERVOIR_NAME if h in hydros.DOWNRIVER_PLANT_NAME]:
        for t in [t for t in range(-hydros.WATER_TRAVEL_TIME[h], 0, 1)
                                                                    if hydros.SPIL_0[h, t] is None]:
            hydros.SPIL_0[h, t] = 0.00

    f.close()
    del f

    return()

def read_inflows_from_DADVAZ(params, hydros, W_RANK, filename):
    '''Read the inflows to the reservoirs'''
    # First week's inflows
    incremental_inflows = {h: [0 for t in range(params.T)] for h in hydros.RESERVOIR_NAME}

    # Keep track of the plants whose inflows have not yet been found
    found = {h: False for h in hydros.RESERVOIR_NAME}

    # Type of inflow 1: incremental and 2: natural
    typeOfInflow = {h: -1000 for h in hydros.RESERVOIR_NAME}

    f = open(filename, 'r', encoding = 'ISO-8859-1')
    reader = csv.reader(f, delimiter = ';')

    i = 0
    while i < 16:
        row = next(reader)  # <BEGIN>
        i += 1

    row = next(reader)  # First hydro or 'FIM'

    while row[0] != 'FIM':
        if row[0][0] != '&':
            h = int(row[0][0:3].strip())
            if h not in (88, 180) and int(row[0][24:26].strip()) <= params.CASE_DATE.day:
                # 180 is the reservoir TOCOS, not included in the system
                assert int(row[0][24:26].strip()) == params.CASE_DATE.day,\
                                                            'Day is different from the case date'

                found[h], typeOfInflow[h] = True, int(row[0][19].strip())

                inflow = float(row[0][44:53].strip())
                for t in range(0, params.T, 1):
                    incremental_inflows[h][t] = inflow

            row = next(reader)

        else:
            row = next(reader)

    f.close()
    del f

    #### Compute the incremental inflows. It's only necessary for those
    #### plants whose inflow types are 2, i.e., natural
    if 2 in set(typeOfInflow.values()):
        raise NotImplementedError('Natural inflows are not currently accepted')

    for h in hydros.RESERVOIR_NAME:
        if not(found[h]):
            raise Exception('No inflow has been found for hydro plant ' + hydros.RESERVOIR_NAME[h])

    for h in hydros.RESERVOIR_NAME:
        if min(incremental_inflows[h]) < 0:
            raise Exception('Negative incremental inflow for plant ' + hydros.RESERVOIR_NAME[h])

    if W_RANK == 0:
        f = open(params.OUT_FOLDER + 'inflows - ' + \
                params.PS + ' - case ' + str(params.CASE) + '.csv', 'w',\
                encoding = 'ISO-8859-1')
        for h in hydros.RESERVOIR_NAME:
            f.write(hydros.RESERVOIR_NAME[h] + ';')
            for t in range(params.T):
                f.write(str(incremental_inflows[h][t]) + ';')
            f.write('\n')
        f.close()
        del f

    for h in hydros.RESERVOIR_NAME:
        for t in range(params.T):
            hydros.INFLOWS[h, t] = incremental_inflows[h][t]

    return()

def read_cost_to_go_function(filename, params, hydros):
    '''Read the cost-to-go function'''

    f = open(filename, 'r', encoding = 'ISO-8859-1')
    reader = csv.reader(f, delimiter = ';')

    row = next(reader)  # <BEGIN>
    row = next(reader)  # Header
    header = {}
    for h in hydros.RESERVOIR_NAME:
        try:
            header[h] = row.index(hydros.RESERVOIR_NAME[h])
        except ValueError as e:
            raise Exception('Hydro plant '+ hydros.RESERVOIR_NAME[h] +' has not been found in the'
                                            + ' cost-to-go function file. ' + str(e)) from None
    header['rhs'] = row.index('RHS ($)')
    row = next(reader)  # First hydro or </END>

    while not(row[0] == '</END>'):
        hydros.CTF_RHS.append(float(row[header['rhs']])*params.SCAL_OBJ_FUNC)
        hydros.CTF.append({})   # list of coefficients
        for h in hydros.RESERVOIR_NAME:
            hydros.CTF[-1][h] = float(row[header[h]])*params.SCAL_OBJ_FUNC
        row = next(reader)
    f.close()
    del f

    # Check if there is any cut that appears more than once
    unique_cuts = []
    for c in range(len(hydros.CTF_RHS)):
        cand = {}
        cand.update(hydros.CTF[c])
        cand.update({'rhs': hydros.CTF_RHS[c]})
        if cand not in unique_cuts:
            unique_cuts.append(cand)

    hydros.CTF = [{h: unique_cuts[c][h] for h in hydros.RESERVOIR_NAME}\
                                                                for c in range(len(unique_cuts))]
    hydros.CTF_RHS = [unique_cuts[c]['rhs'] for c in range(len(unique_cuts))]

    return ()

def read_HPF_model(filename, params, hydros):
    '''Read parameters of the HPF'''

    class HPFModel:
        '''Model of the HPF'''
        def __init__(self, hydros):
            self.AVRG_PROD = {h: None for h in hydros.RESERVOIR_NAME}
            self.HEAD_LOSS_TYPE = {h: None for h in hydros.RESERVOIR_NAME}
            self.HEAD_LOSS = {h: None for h in hydros.RESERVOIR_NAME}
            self.HPF_FB = {h: {'F0': None, 'F1': None, 'F2': None, 'F3': None, 'F4': None}
                                                                    for h in hydros.RESERVOIR_NAME}

            self.HPF_TR = {h: {'T0': [], 'T1': [], 'T2': [], 'T3': [], 'T4': []}
                                                                    for h in hydros.RESERVOIR_NAME}

            self.NUM_TR_POL = {h: 0 for h in hydros.RESERVOIR_NAME}

            self.MAX_SPIL_HPF = {h: None for h in hydros.RESERVOIR_NAME}

            self.N_TURB_POINTS = {h: None for h in hydros.RESERVOIR_NAME}
            self.N_VOL_POINTS = {h: None for h in hydros.RESERVOIR_NAME}
            self.N_SPIL_POINTS = {h: None for h in hydros.RESERVOIR_NAME}
            self.V_RANGE = {h: None for h in hydros.RESERVOIR_NAME}

    hpf_model = HPFModel(hydros)

    f = open(filename, "r", encoding = 'ISO-8859-1')
    reader = csv.reader(f, delimiter = ';')

    row = next(reader)  # <BEGIN>
    row = next(reader)  # Header

    header = {}
    header['avrgProd'] = row.index('Average productivity ((MW/(m3/s))/m)')
    header['headLossType'] = row.index(\
                                'Head loss (1 if percentage of net head or 2 if given in meters)')
    header['headLoss'] = row.index('Head loss')

    for i in range(5):
        header['F'+str(i)]=row.index('Forebay level as function of reservoir volume coefficient F'\
                                                                                        + str(i))

    header['firstIndexOfTailracePolies'] = row.index(\
                                'Tailrace level as function of total outflow: T0 of polymial 1')

    header['id'] = row.index('ID')
    header['name'] = row.index('Name')
    header['maxSpil'] = row.index('Maximum spillage (m3/s)')
    header['vPoints'] = row.index('Number of volume points for the HPF')
    header['qPoints'] = row.index('Number of turbine discharge points for the HPF')
    header['sPoints'] = row.index('Number of spillage points for the HPF')
    header['vRange'] =row.index('Range of volume around the initial reservoir volume in percentage')

    row = next(reader)

    while row[0] != '</END>':
        try:
            h = int(row[header['id']].strip())
        except IndexError as e:
            raise Exception('Hydro reservoir with index ' + str(h) + ' and name ' +\
                        row[header['name']].strip() + ' is not in the system.' + str(e)) from None

        hpf_model.AVRG_PROD[h] = float(row[header['avrgProd']].strip())
        hpf_model.HEAD_LOSS_TYPE[h] = int(row[header['headLossType']].strip())
        assert hpf_model.HEAD_LOSS_TYPE[h] in (1, 2), 'Head loss type ' +\
                                                str(hpf_model.HEAD_LOSS_TYPE[h]) + ' is not valid'

        hpf_model.HEAD_LOSS[h] = float(row[header['headLoss']].strip())

        for i in range(5):
            hpf_model.HPF_FB[h]['F' + str(i)] = float(row[header['F' + str(i)]].strip())

        for t in range(6):
            hpf_model.HPF_TR[h]['T0'].append(float(row[\
                                            header['firstIndexOfTailracePolies'] + t*5].strip()))
            hpf_model.HPF_TR[h]['T1'].append(float(row[\
                                            header['firstIndexOfTailracePolies']+1 + t*5].strip()))
            hpf_model.HPF_TR[h]['T2'].append(float(row[\
                                            header['firstIndexOfTailracePolies']+2 + t*5].strip()))
            hpf_model.HPF_TR[h]['T3'].append(float(row[\
                                            header['firstIndexOfTailracePolies']+3 + t*5].strip()))
            hpf_model.HPF_TR[h]['T4'].append(float(row[\
                                            header['firstIndexOfTailracePolies']+4 + t*5].strip()))
            if abs(hpf_model.HPF_TR[h]['T0'][t]) + abs(hpf_model.HPF_TR[h]['T1'][t]) +\
                abs(hpf_model.HPF_TR[h]['T2'][t]) + abs(hpf_model.HPF_TR[h]['T3'][t]) +\
                                                            abs(hpf_model.HPF_TR[h]['T4'][t]) > 0:
                hpf_model.NUM_TR_POL[h] += 1

        hpf_model.MAX_SPIL_HPF[h] = float(row[header['maxSpil']])

        hpf_model.N_TURB_POINTS[h] = int(row[header['qPoints']])
        hpf_model.N_VOL_POINTS[h] = int(row[header['vPoints']])
        hpf_model.N_SPIL_POINTS[h] = int(row[header['sPoints']])
        hpf_model.V_RANGE[h] = float(row[header['vRange']])

        row = next(reader)

    f.close()
    del f

    #### Update the forebay-level and tailrace-level functions, if possible
    update_level_functions(params, hydros, hpf_model)

    return(hpf_model)

def read_aggreg_HPF(filename, params, hydros):
    '''Read the three-dimensional HPF'''

    f = open(filename, 'r', encoding = 'ISO-8859-1')
    reader = csv.reader(f, delimiter = ';')

    row = next(reader)  # <BEGIN>
    row = next(reader)  # First hydro or </END>

    while not(row[0] == '</END>'):
        row = next(reader)  # ID
        row = next(reader)  # Hydro plant ID and name

        h = int(row[0].strip())
        assert h in hydros.RESERVOIR_NAME, 'Plant ' + row[1].strip() + ' is not in the system.'

        row = next(reader)  # <HPF>
        row = next(reader)  # Header
        row = next(reader)  # Either first cut or </HPF>

        while not(row[0] == '</Hydro>'):
            while not(row[0] == '</HPF>'):
                hydros.A0[h].append((float(row[0]))/params.POWER_BASE)
                hydros.A1[h].append((float(row[1]))/params.POWER_BASE)
                hydros.A2[h].append((float(row[2]))/params.POWER_BASE)
                hydros.A3[h].append(float(row[3])/params.POWER_BASE)
                row = next(reader)  # Either next cut or </HPF>

            row = next(reader)

        row = next(reader)
    f.close()
    del f

    for h in hydros.RESERVOIR_NAME:
        if (sum([hydros.MAX_Q[u] for u in hydros.UNIT_NAME if hydros.UNIT_RESERVOIR_ID[u]==h]) > 0):
            if len(hydros.A0[h]) == 0:
                raise Exception('The hydropower function of ' + hydros.RESERVOIR_NAME[h] +\
                                                                        ' has not been found.')
    return()


def read_approx_fb(filename, params, hydros):
    '''read the approximation of the forebay level'''
    f = open(filename, 'r', encoding = 'ISO-8859-1')
    reader = csv.reader(f, delimiter = ';')

    row = next(reader)  # <BEGIN>
    row = next(reader)  # header

    header = {'ID': -20, 'Name': -20,
                'reservoir volume coeff (in m/hm3)': -20, 'constant (in m)': -20}
    for h in header:
        header[h] = row.index(h)

    row = next(reader)  # first entry or end

    while not(row[0] == '</END>'):
        hydros.FB_COEF[int(row[header['ID']])] =\
                                            float(row[header['reservoir volume coeff (in m/hm3)']])
        hydros.FB_CONST[int(row[header['ID']])] = float(row[header['constant (in m)']])
        row = next(reader)

    f.close()
    del f

def read_approx_tr(filename, params, hydros):
    '''read the approximation of the tailrace level'''
    f = open(filename, 'r', encoding = 'ISO-8859-1')
    reader = csv.reader(f, delimiter = ';')

    row = next(reader)  # <BEGIN>
    row = next(reader)  # header

    header = {'ID': -20, 'Name': -20, 'outflow coeff (in m/(m3/s))': -20, 'constant (in m)': -20}
    for h in header:
        header[h] = row.index(h)

    row = next(reader)  # first entry or end

    while not(row[0] == '</END>'):
        hydros.TR_COEF[int(row[header['ID']])] = float(row[header['outflow coeff (in m/(m3/s))']])
        hydros.TR_CONST[int(row[header['ID']])] = float(row[header['constant (in m)']])
        row = next(reader)

    f.close()
    del f
