# -*- coding: utf-8 -*-
"""
@author: Colonetti
"""

from read_and_load_data.read_csv import read_hydro_generating_units

def get_groups_of_identical_units(hydros):
    '''get groups of identical units'''
    list_of_plants_with_turbines = list({hydros.UNIT_RESERVOIR_ID[u] for u in hydros.UNIT_NAME})

    groups_of_identical_units = {h: {} for h in list_of_plants_with_turbines}

    for h in list_of_plants_with_turbines:
        UNITS = [u for u in hydros.UNIT_NAME if hydros.UNIT_RESERVOIR_ID[u] == h]
        for u in UNITS:
            if u not in groups_of_identical_units[h].values():
                # then u is not in any of the groups
                found = False   # a group of units identical to u has been found
                for group in groups_of_identical_units[h]:
                    first_unit_of_group = groups_of_identical_units[h][group][0]
                    if hydros.UNIT_BUS_ID[u] == hydros.UNIT_BUS_ID[first_unit_of_group] and\
                        hydros.MIN_P[u] == hydros.MIN_P[first_unit_of_group] and\
                            hydros.MAX_P[u] == hydros.MAX_P[first_unit_of_group] and\
                                hydros.MIN_Q[u] == hydros.MIN_Q[first_unit_of_group] and\
                                    hydros.MAX_Q[u] == hydros.MAX_Q[first_unit_of_group]:
                        found = True
                        groups_of_identical_units[h][group].append(u)
                        break
                if not(found):
                    new_group_id = max(groups_of_identical_units[h].keys()) + 1\
                                        if len(groups_of_identical_units[h].keys()) > 0 else 1
                    groups_of_identical_units[h][new_group_id] = []
                    groups_of_identical_units[h][new_group_id].append(u)

    return(list_of_plants_with_turbines, groups_of_identical_units)

def convert_unit_based_to_zone_based(params, hydros, W_RANK):
    '''Convert the unit-based data into zone-based data by aggregating identical hydro units
        while still satisfying lower and upper bound constraints'''

    list_of_plants_with_turbines, groups_of_identical_units = get_groups_of_identical_units(hydros)

    list_of_all_units = []
    for b in [list(groups_of_identical_units[h].values()) for h in list_of_plants_with_turbines]:
        for d in b:
            list_of_all_units = list_of_all_units + d

    assert len(list_of_all_units) == len(hydros.UNIT_NAME),\
                                                'It seems that not all units have been aggregated.'

    zones_of_each_group = {h: {group: [] for group in groups_of_identical_units[h]}
                                            for h in list_of_plants_with_turbines}

    # lower bound on generation for each zone in MW
    lb_h_g = {h: {group: {} for group in groups_of_identical_units[h]}
                                            for h in list_of_plants_with_turbines}
    # upper bound on generation for each zone in MW
    ub_h_g = {h: {group: {} for group in groups_of_identical_units[h]}
                                            for h in list_of_plants_with_turbines}
    # upper bound on turbine discharge for each zone
    lb_q = {h: {group: {} for group in groups_of_identical_units[h]}
                                            for h in list_of_plants_with_turbines}
    # lower bound on turbine discharge for each zone
    ub_q = {h: {group: {} for group in groups_of_identical_units[h]}
                                            for h in list_of_plants_with_turbines}

    for h in list_of_plants_with_turbines:
        for g in groups_of_identical_units[h]:
            c = 0 # count units
            for u in groups_of_identical_units[h][g]:
                c += 1
                if c == 1:
                    zones_of_each_group[h][g].append(1)
                    ub_h_g[h][g][zones_of_each_group[h][g][-1]] = hydros.MAX_P[u]
                    lb_h_g[h][g][zones_of_each_group[h][g][-1]] = hydros.MIN_P[u]
                    ub_q[h][g][zones_of_each_group[h][g][-1]] = hydros.MAX_Q[u]
                    lb_q[h][g][zones_of_each_group[h][g][-1]] = hydros.MIN_Q[u]
                else:
                    if (ub_h_g[h][g][zones_of_each_group[h][g][-1]] <\
                            (lb_h_g[h][g][zones_of_each_group[h][g][-1]] + hydros.MIN_P[u])) or\
                        (ub_q[h][g][zones_of_each_group[h][g][-1]] <\
                            (lb_q[h][g][zones_of_each_group[h][g][-1]] + hydros.MIN_Q[u])):
                        zones_of_each_group[h][g].append(zones_of_each_group[h][g][-1] + 1)
                        ub_h_g[h][g][zones_of_each_group[h][g][-1]] = hydros.MAX_P[u] +\
                                                        ub_h_g[h][g][zones_of_each_group[h][g][-2]]
                        lb_h_g[h][g][zones_of_each_group[h][g][-1]] = hydros.MIN_P[u] +\
                                                        lb_h_g[h][g][zones_of_each_group[h][g][-2]]
                        ub_q[h][g][zones_of_each_group[h][g][-1]] = hydros.MAX_Q[u] +\
                                                        ub_q[h][g][zones_of_each_group[h][g][-2]]
                        lb_q[h][g][zones_of_each_group[h][g][-1]] = hydros.MIN_Q[u] +\
                                                        lb_q[h][g][zones_of_each_group[h][g][-2]]
                    else:
                        ub_h_g[h][g][zones_of_each_group[h][g][-1]] += hydros.MAX_P[u]
                        ub_q[h][g][zones_of_each_group[h][g][-1]] += hydros.MAX_Q[u]

    if W_RANK == 0:
        f = open(params.IN_FOLDER +  params.CASE + '/'\
                                    'dataOfZones - ' + \
                        params.PS + ' - case ' + params.CASE + '.csv', 'w', encoding = 'ISO-8859-1')
        f.write('<BEGIN>\n')
        f.write('<Hydro turbines>\n')
        f.write('Name;')
        f.write('Hydro reservoir ID;')
        f.write('Hydro reservoir name;')
        f.write('Group ID;')
        f.write('Group name;')
        f.write('Unit ID;')
        f.write('Bus ID;')
        f.write('Minimum generation (MW);')
        f.write('Maximum generation (MW);')
        f.write('Minimum turbine discharge (m3/s);')
        f.write('Maximum turbine discharge (m3/s);')
        f.write('Turbine type;')
        f.write('\n')
        c = 0
        for h in list_of_plants_with_turbines:
            u_id = 1
            for g in groups_of_identical_units[h]:
                first_unit_of_group = groups_of_identical_units[h][g][0]
                for z in zones_of_each_group[h][g]:
                    f.write('Zone-' + str(z) + '-Group-' + str(g) + ';')
                    f.write(str(hydros.UNIT_RESERVOIR_ID[first_unit_of_group]) + ';')
                    f.write(hydros.UNIT_RESERVOIR_NAME[first_unit_of_group] + ';')
                    f.write(str(g) + ';')
                    f.write('Group ' + str(g) + ';')
                    f.write(str(u_id) + ';')
                    f.write(str(hydros.UNIT_BUS_ID[first_unit_of_group]) + ';')
                    f.write(str(lb_h_g[h][g][z]*params.POWER_BASE) + ';')
                    f.write(str(ub_h_g[h][g][z]*params.POWER_BASE) + ';')
                    f.write(str(lb_q[h][g][z]) + ';')
                    f.write(str(ub_q[h][g][z]) + ';')
                    f.write('\n')
                    u_id += 1
        f.write('</Hydro turbines>\n')
        f.write('</END>')
        f.close()
        del f

    # Now delete all individual hydro generating units
    all_units = list(hydros.UNIT_NAME.keys())
    for u in all_units:
        del hydros.UNIT_NAME[u]
        del hydros.UNIT_RESERVOIR_NAME[u]
        del hydros.UNIT_RESERVOIR_ID[u]
        del hydros.UNIT_GROUP_ID[u]
        del hydros.UNIT_GROUP_NAME[u]
        del hydros.UNIT_BUS_ID[u]
        del hydros.MIN_P[u]
        del hydros.MAX_P[u]
        del hydros.MIN_Q[u]
        del hydros.MAX_Q[u]

    read_hydro_generating_units(params.IN_FOLDER +  params.CASE + '/'\
                                    'dataOfZones - ' + \
                        params.PS + ' - case ' + params.CASE + '.csv', params, hydros)

    return()

class Hydros:
    '''Class of hydro reservoirs and units'''
    def __init__(self):
        self.setup()

    def setup(self):
        '''Initialize the attributes'''

        #### the keys of reservoir parameters are the IDs of the reservoirs
        self.RESERVOIR_NAME = {}

        self.RESERVOIR_BASIN = {}

        self.MIN_VOL, self.MAX_VOL = {}, {} # bounds on reservoir volume in hm3

        self.MIN_FOREBAY_L, self.MAX_FOREBAY_L = {}, {}

        self.MAX_SPIL = {}              # maximum spillage in m3/s

        self.INFLOWS = {}               # inflows to reservoirs in m3/s in each time period

        self.INFLUENCE_OF_SPIL = {}     # influence of spillage on the tailrace

        # coefficients of the linear approximation of the forebay level
        self.FB_COEF, self.FB_CONST = {}, {}

        # coefficients of the linear approximation of the tailrace level
        self.TR_COEF, self.TR_CONST = {}, {}

        # Initial state
        self.V_0, self.Q_0, self.SPIL_0 = {}, {}, {}

        #### The following two lists are used for storing the cost-to-go function.
        # Coefficients of the cost-to-go function
        self.CTF = []       # each entry in this list contains a dicionary whose keys are
                            # the ids of the reservoirs and values are the coefficients of the
                            # corresponding reservoirs in the cost-to-go function
        # RHS of the cost-to-go function
        self.CTF_RHS = []   # the entries are floats

        self.DOWNRIVER_PLANT_NAME = {}  # of turbine discharge and spillage
        self.WATER_TRAVEL_TIME = {}     # for the turbine discharge and spillage

        self.BYPASS_DR_PLANT_NAME = {}
        self.WATER_TRAVEL_BYPASS = {}
        self.MAX_BYPASS = {}

        #### piecewise-linear approximation of the HPF
        self.A0, self.A1, self.A2, self.A3 = {}, {}, {}, {}

        #### the keys of turbine-unit parameters are (plant_id, unit_id)
        self.UNIT_NAME = {}
        self.UNIT_RESERVOIR_NAME, self.UNIT_RESERVOIR_ID = {}, {}

        self.UNIT_GROUP_ID, self.UNIT_GROUP_NAME = {}, {}

        self.UNIT_BUS_ID = {}

        self.MIN_P, self.MAX_P = {}, {}
        self.MIN_Q, self.MAX_Q = {}, {}

        #### the keys of pump-unit parameters are (plant_id, pump_id)
        self.PUMP_NAME = {}
        self.PUMP_RESERVOIR_NAME, self.PUMP_RESERVOIR_ID = {}, {}

        self.PUMP_BUS_ID = {}

        self.PUMP_CONV_RATE = {}        # m3/s-to-MW conversion rate for the pumps

        self.MIN_PUMP_Q, self.MAX_PUMP_Q = {}, {}

        # for a pump, water goes from the downriver reservoir to the upriver reservoir
        self.PUMP_DOWNRIVER_RESERVOIR, self.PUMP_UPRIVER_RESERVOIR = {}, {}

        self.PUMP_WATER_TRAVELLING_TIME = {}

        return()

    def add_new_reservoir(self, row, header, params):
        '''Add a new reservoir'''

        HYDRO_ID = int(row[header['ID']].strip())

        self.RESERVOIR_NAME[HYDRO_ID] = row[header['Name']].strip()

        self.RESERVOIR_BASIN[HYDRO_ID] = row[header['Basin']].strip()

        self.FB_COEF[HYDRO_ID] = 0
        self.FB_CONST[HYDRO_ID] = 0

        self.TR_COEF[HYDRO_ID] = 0
        self.TR_CONST[HYDRO_ID] = 0

        self.INFLUENCE_OF_SPIL[HYDRO_ID] =\
                        row[header['Influence of spillage on the HPF? Yes or No']].strip() == 'Yes'

        self.MIN_VOL[HYDRO_ID] = float(row[header['Minimum reservoir volume (hm3)']].strip())
        self.MAX_VOL[HYDRO_ID] = float(row[header['Maximum reservoir volume (hm3)']].strip())

        self.MAX_SPIL[HYDRO_ID] = float(row[header['Maximum spillage (m3/s)']].strip())

        self.V_0[HYDRO_ID] = None
        if row[header['Name of downriver reservoir']].strip() != '0':
            self.Q_0.update({(HYDRO_ID, t): None for t in range(-int(float(
                    row[header['Water travelling time (h)']].strip())/params.BASE_TIME_STEP),0,1)})
            self.SPIL_0.update({(HYDRO_ID, t): None for t in range(-int(float(
                    row[header['Water travelling time (h)']].strip())/params.BASE_TIME_STEP),0,1)})
        else:
            self.Q_0.update({(HYDRO_ID, t): None for t in range(-1, 0, 1)})
            self.SPIL_0.update({(HYDRO_ID, t): None for t in range(-1, 0, 1)})

        self.MIN_FOREBAY_L[HYDRO_ID] = float(row[header['Minimum forebay level (m)']].strip())
        self.MAX_FOREBAY_L[HYDRO_ID] = float(row[header['Maximum forebay level (m)']].strip())

        if row[header['Name of downriver reservoir']].strip() != '0':
            self.DOWNRIVER_PLANT_NAME[HYDRO_ID] = row[header['Name of downriver reservoir']].strip()
            self.WATER_TRAVEL_TIME[HYDRO_ID] = int(
                    float(row[header['Water travelling time (h)']].strip())/params.BASE_TIME_STEP)

        if row[header['Downriver plant of bypass discharge']].strip() != '0':
            self.BYPASS_DR_PLANT_NAME[HYDRO_ID] =\
                                        row[header['Downriver plant of bypass discharge']].strip()
            self.WATER_TRAVEL_BYPASS[HYDRO_ID] = int(
                float(row[header['Water travel time in bypass (h)']].strip())/params.BASE_TIME_STEP)
            self.MAX_BYPASS[HYDRO_ID] =float(row[header['Maximum bypass discharge (m3/s)']].strip())

        self.A0[HYDRO_ID] = []
        self.A1[HYDRO_ID] = []
        self.A2[HYDRO_ID] = []
        self.A3[HYDRO_ID] = []

        return()

    def add_new_turbine(self, row, header, params):
        '''Add a new generating unit, a turbine'''

        u = (int(row[header['Hydro reservoir ID']].strip()), int(row[header['Unit ID']].strip()))

        assert u not in self.UNIT_NAME and u not in self.PUMP_NAME,\
                                        'Unit ' + row[header['Unit ID']].strip() + ' of plant ' +\
                                            row[header['Hydro reservoir name']].strip() +\
                                                ' is already in the system'

        self.UNIT_NAME[u] = row[header['Name']].strip()
        self.UNIT_RESERVOIR_NAME[u] = row[header['Hydro reservoir name']].strip()
        self.UNIT_RESERVOIR_ID[u] = int(row[header['Hydro reservoir ID']].strip())
        self.UNIT_GROUP_ID[u] = int(row[header['Group ID']].strip())
        self.UNIT_GROUP_NAME[u] = row[header['Group name']].strip()
        self.UNIT_BUS_ID[u] = int(row[header['Bus ID']].strip())
        self.MIN_P[u] = float(row[header['Minimum generation (MW)']].strip())/params.POWER_BASE
        self.MAX_P[u] = float(row[header['Maximum generation (MW)']].strip())/params.POWER_BASE
        self.MIN_Q[u] = float(row[header['Minimum turbine discharge (m3/s)']].strip())
        self.MAX_Q[u] = float(row[header['Maximum turbine discharge (m3/s)']].strip())

        return()

    def add_new_pump(self, row, header, params):
        '''Add a new pumping unit'''

        u = (int(row[header['Hydro reservoir ID']].strip()), int(row[header['Unit ID']].strip()))

        assert u not in self.UNIT_NAME and u not in self.PUMP_NAME,\
                                        'Unit ' + row[header['Unit ID']].strip() + ' of plant ' +\
                                            row[header['Hydro reservoir name']].strip() +\
                                                ' is already in the system'

        self.PUMP_NAME[u] = row[header['Name']].strip()
        self.PUMP_RESERVOIR_NAME[u] = row[header['Hydro reservoir name']].strip()
        self.PUMP_RESERVOIR_ID[u] = int(row[header['Hydro reservoir ID']].strip())
        self.PUMP_BUS_ID[u] = int(row[header['Bus ID']].strip())
        self.MIN_PUMP_Q[u] = float(row[header['Minimum pumping discharge (m3/s)']].strip())
        self.MAX_PUMP_Q[u] = float(row[header['Maximum pumping discharge (m3/s)']].strip())

        self.PUMP_CONV_RATE[u] =\
                float(row[header['Conversion rate MW/(m3/s/) for pumps']].strip())/params.POWER_BASE

        # for a pump, water goes from the downriver reservoir to the upriver reservoir
        self.PUMP_DOWNRIVER_RESERVOIR[u] = row[header['Downriver reservoir of pump units']].strip()
        self.PUMP_UPRIVER_RESERVOIR[u] = row[header['Upriver reservoir of pump units']].strip()
        self.PUMP_WATER_TRAVELLING_TIME[u] = int(
            float(row[header['Water travel time in pumping (h)']].strip())/params.BASE_TIME_STEP)

        return()
