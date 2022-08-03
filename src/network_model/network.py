# -*- coding: utf-8 -*-
"""
@author: Colonetti
"""

from math import pi
import csv

def update_buses_of_gen_units(params, network, hydros, thermals):
    '''Buses to which the units are connected might change from case to case'''

    f = open(params.IN_FOLDER +  params.CASE + '/leve.pwf', 'r', encoding = 'ISO-8859-1')
    reader = csv.reader(f, delimiter = ';')

    row = next(reader)

    while len(row) == 0 or row[0][0:4] != 'DUSI':
        row = next(reader)

    row = next(reader) # header
    row = next(reader) # header 2
    row = next(reader) # header 3
    row = next(reader) # first bar or end

    old_hydro_id = None
    old_group_id = None
    count_unit_id = 1

    while len(row) == 0 or row[0][0:5] != '99999':
        if len(row) > 0 and row[0][0] != '(':
            if row[0][77] == 'H':
                # update the bus of a hydro generating unit
                HYDRO_ID = int(row[0][72:76].strip())
                GROUP_ID = int(row[0][76])
                NUMBER_OF_UNITS = int(row[0][26:28].strip())
                NEW_BUS = int(row[0][6:11].strip())

                if old_hydro_id == HYDRO_ID and old_group_id == GROUP_ID:
                    count_unit_id += NUMBER_OF_UNITS
                else:
                    count_unit_id = 0

                UNITS = [u for u in hydros.UNIT_NAME if hydros.UNIT_RESERVOIR_ID[u] == HYDRO_ID and
                                                        hydros.UNIT_GROUP_ID[u] == GROUP_ID]

                #assert count_unit_id + NUMBER_OF_UNITS <= len(UNITS), 'There seems to be too few'+\
                #                ' units in group ' + str(GROUP_ID) + ' of plant ' +\
                #                    hydros.RESERVOIR_NAME[HYDRO_ID] + ' (' + str(HYDRO_ID) + ').'
                if count_unit_id + NUMBER_OF_UNITS <= len(UNITS):
                    for u in UNITS[count_unit_id:(count_unit_id + NUMBER_OF_UNITS)]:
                        hydros.UNIT_BUS_ID[u] = NEW_BUS
                else:
                    for u in [u for u in UNITS
                                    if count_unit_id <= u[1] <= (count_unit_id + NUMBER_OF_UNITS)]:
                        hydros.UNIT_BUS_ID[u] = NEW_BUS

                old_hydro_id = HYDRO_ID
                old_group_id = GROUP_ID
            elif row[0][77] == 'T':
                # update the bus of a thermal generating unit
                THERMAL_PLANT_ID = int(row[0][72:76].strip())
                THERMAL_UNIT_ID = int(row[0][26:28].strip())
                NEW_BUS = int(row[0][6:11].strip())

                if (THERMAL_PLANT_ID, THERMAL_UNIT_ID) in thermals.UNIT_NAME:
                    thermals.BUS[(THERMAL_PLANT_ID, THERMAL_UNIT_ID)] = NEW_BUS

            elif row[0][77] == 'E':
                # update the bus of a pump
                pass #

            else:
                raise Exception('I dont know what ' + row[0][77] + ' is in ' + str(row[0]))

        row = next(reader)

    return()

def add_new_parallel_line(reactance_existing_line,
        normal_P_max_existing_line, emerg_P_max_existing_line,
        reactance_new_line, normal_P_max_new_line, emerg_P_max_new_line):
    '''Add a new parallel line to the system. powers must be in p.u.'''

    if (reactance_existing_line <= 0 and reactance_new_line <= 0) or\
            (reactance_existing_line > 0 and reactance_new_line > 0):
        # the new parallel line is primarily inductive
        new_reactance = (reactance_existing_line*reactance_new_line)/\
                            (reactance_existing_line + reactance_new_line)
        new_normal_P_max = normal_P_max_existing_line + normal_P_max_new_line
        new_normal_P_emerg = emerg_P_max_existing_line + emerg_P_max_new_line
    else:
        # the new parallel line is primarily capacitive
        new_reactance = (reactance_existing_line*reactance_new_line)/\
                            (reactance_new_line - reactance_existing_line)

        # compute the maximum angular difference between the end-point buses
        dtheta_max_normal = min(abs(reactance_existing_line*normal_P_max_existing_line),\
                                abs(reactance_new_line*normal_P_max_new_line))

        new_normal_P_max = abs(dtheta_max_normal/new_reactance)

        dtheta_max_emergency = min(abs(reactance_existing_line*emerg_P_max_existing_line),\
                                abs(reactance_new_line*emerg_P_max_new_line))

        new_normal_P_emerg = abs(dtheta_max_emergency/new_reactance)

    return(new_reactance, new_normal_P_max, new_normal_P_emerg)

class Network:
    '''Class of network DC model'''
    def __init__(self):
        self.setup()

    def setup(self):
        '''Initialize the attributes'''

        self.BUS_ID, self.BUS_NAME, self.BUS_AREA = [], {}, {}
        # bus subsystem and bus base voltage in kV
        self.BUS_SUBSYSTEM_ID, self.BUS_SUBSYSTEM, self.BUS_BASE_V = {}, {}, {}

        self.THETA_BOUND = 2*pi

        # a (len(self.BUS_ID), T) numpy array of the net load at each bus and period
        self.NET_LOAD = []

        # name of reference bus as in self.BUS_NAME
        self.REF_BUS_NAME = []
        self.REF_BUS_ID = []

        # gets bus id (as in self.BUS_ID) as returns the bus index in self.BUS_ID
        self.BUS_HEADER = {}

        # buses with net load strictly greater than zero in at least one period
        self.LOAD_BUSES = set()

        # buses to which at least one controlled-generation device is connected to
        self.GEN_BUSES = set()

        # buses at which the net load is strictly negative in at least one period, i.e., buses
        # with renewable generation for which the renewable generation exceeds energy demand for
        # at least one period
        self.RENEWABLE_BUSES = set()

        #### Transmission lines
        self.LINE_ID = []
        # line from-to: a list of tuples (from, to).
        # from is the index of the source bus (as in self.BUS_ID) and to is the index in self.BUS_ID
        # of the sink (destiny) bus
        self.LINE_F_T = {}

        self.LINE_B = {}                # susceptance of the lines in (p.u.)/rad with 100-MVA basis

        self.LINE_MAX_P = {}            # normal rating in p.u.

        self.LINE_EMERG_MAX_P = {}      # emergency rating in p.u.

        self.LINES_FROM_BUS = {}        # all lines whose 'from' bus is the key 'bus'
        self.LINES_TO_BUS = {}          # all lines whose 'to' bus is the key 'bus'


        #### DC links
        self.LINK_ID = []

        # line from-to: a list of tuples (from, to).
        # from is the index of the source bus (as in self.BUS_ID) and to is the index in self.BUS_ID
        # of the sink (destiny) bus
        self.LINK_F_T = {}

        self.LINK_MAX_P = {}            # normal rating in p.u.

        self.LINKS_FROM_BUS = {}        # all links whose 'from' bus is the key 'bus'
        self.LINKS_TO_BUS = {}          # all links whose 'to' bus is the key 'bus'


        #### Flows between subsystems
        self.FLOWS_BETW_SUBSYS = {}     # Flows between subsystems

        return()

    def add_new_bus(self, row, header):
        '''Add a new bus to the network'''

        assert int(row[header['ID']].strip()) not in self.BUS_ID, 'A bus with ID' +\
                                            row[header['ID']].strip() + ' is already in the system'

        self.BUS_ID.append(int(row[header['ID']].strip()))
        self.BUS_NAME[self.BUS_ID[-1]] = row[header['Name']].strip()
        self.BUS_AREA[self.BUS_ID[-1]] = int(row[header['Area']].strip())
        self.BUS_SUBSYSTEM[self.BUS_ID[-1]] = row[header['Subsystem market - Name']].strip()
        self.BUS_SUBSYSTEM_ID[self.BUS_ID[-1]] = int(row[header['Subsystem market - ID']].strip())
        self.BUS_BASE_V[self.BUS_ID[-1]] = float(row[header['Base voltage (kV)']].strip())

        return()

    def add_new_line(self, row, header, params):
        '''Add a new transmission line to the network'''

        if ((int(row[header['From (ID)']].strip()), int(row[header['To (ID)']].strip()))\
                in self.LINE_F_T.values() or\
            (int(row[header['To (ID)']].strip()), int(row[header['From (ID)']].strip()))\
                in self.LINE_F_T.values()):
            # the new line is paralleled to a line that is already in the system

            keys = list(self.LINE_F_T.keys())
            values = list(self.LINE_F_T.values())

            try:
                l_index = values.index((int(row[header['From (ID)']].strip()),
                                int(row[header['To (ID)']].strip())))
            except ValueError:
                l_index = values.index((int(row[header['To (ID)']].strip()),
                                int(row[header['From (ID)']].strip())))

            l = keys[l_index]   # id of line

            self.LINE_B[l], self.LINE_MAX_P[l], self.LINE_EMERG_MAX_P[l] =\
                            add_new_parallel_line(self.LINE_B[l],
                            self.LINE_MAX_P[l], self.LINE_EMERG_MAX_P[l],
                            float(row[header['Reactance (%) - 100-MVA base']].strip())/100,\
                            float(row[header['Line rating (MW)']].strip())/params.POWER_BASE,\
                            float(row[header['Emergency rating (MW)']].strip())/params.POWER_BASE)

            return()

        assert int(row[header['ID']].strip()) not in self.LINE_ID, 'A line with ID' +\
                                            row[header['ID']].strip() + ' is already in the system'

        if header['ID'] is not None:
            self.LINE_ID.append(int(row[header['ID']].strip()))
        else:
            self.LINE_ID.append(len(self.LINE_ID))

        #### make sure to follow the non-official standard that the 'from' bus is always the
        #### one with the smallest id
        if int(row[header['From (ID)']].strip()) < int(row[header['To (ID)']].strip()):
            self.LINE_F_T[self.LINE_ID[-1]] = (int(row[header['From (ID)']].strip()),
                                                    int(row[header['To (ID)']].strip()))
        else:
            self.LINE_F_T[self.LINE_ID[-1]] = (int(row[header['To (ID)']].strip()),
                                                    int(row[header['From (ID)']].strip()))

        self.LINE_B[self.LINE_ID[-1]] =\
                                    float(row[header['Reactance (%) - 100-MVA base']].strip())/100
        self.LINE_MAX_P[self.LINE_ID[-1]] =\
                            float(row[header['Line rating (MW)']].strip())/params.POWER_BASE
        self.LINE_EMERG_MAX_P[self.LINE_ID[-1]] =\
                            float(row[header['Emergency rating (MW)']].strip())/params.POWER_BASE

        return()

    def add_new_DC_link(self, row, header, params):
        '''Add a new DC link to the system'''

        assert int(row[header['ID']].strip()) not in self.LINK_ID, 'A link with ID' +\
                                            row[header['ID']].strip() + ' is already in the system'

        if header['ID'] is not None:
            self.LINK_ID.append(int(row[header['ID']].strip()))
        else:
            self.LINK_ID.append(len(self.LINK_ID))

        self.LINK_F_T[self.LINK_ID[-1]] = (int(row[header['From (ID)']].strip()),
                                            int(row[header['To (ID)']].strip()))
        self.LINK_MAX_P[self.LINK_ID[-1]] =\
                                    float(row[header['Rating (MW)']].strip())/params.POWER_BASE

        return()

    def classify_buses(self, thermals, hydros):
        '''Classify buses into load buses, generation buses, and buses with renewable generation
            Note that buses might be in two classes at the same time
        '''

        self.BUS_HEADER = {}

        b = 0
        for bus in self.BUS_ID:
            self.BUS_HEADER[bus] = b
            b += 1

        self.LOAD_BUSES, self.GEN_BUSES, self.RENEWABLE_BUSES = set(), set(), set()

        ALL_HYDRO_BUSES = set(hydros.UNIT_BUS_ID.values())
        ALL_PUMP_BUSES = set(hydros.PUMP_BUS_ID.values())
        ALL_THERMAL_BUSES = set(thermals.BUS.values())

        for bus in self.BUS_ID:
            if max(self.NET_LOAD[self.BUS_HEADER[bus]][:]) > 0 or bus in ALL_PUMP_BUSES:
                # bus with strictly positive net load
                self.LOAD_BUSES.add(bus)

            if min(self.NET_LOAD[self.BUS_HEADER[bus]][:]) < 0:
                # bus with renewable generation
                self.RENEWABLE_BUSES.add(bus)

            if bus in ALL_THERMAL_BUSES or bus in ALL_HYDRO_BUSES:
                # generation bus
                self.GEN_BUSES.add(bus)

        return()

    def buses_from_to(self):
        '''get the buses from and to each transmission line and DC link
        '''
        # all lines whose 'from' bus is the key 'bus'
        self.LINES_FROM_BUS = {bus: [] for bus in self.BUS_ID}
        # all lines whose 'to' bus is the key 'bus'
        self.LINES_TO_BUS = {bus: [] for bus in self.BUS_ID}

        # all links whose 'from' bus is the key 'bus'
        self.LINKS_FROM_BUS = {bus: [] for bus in self.BUS_ID}
        # all links whose 'to' bus is the key 'bus'
        self.LINKS_TO_BUS = {bus: [] for bus in self.BUS_ID}

        for bus in self.BUS_ID:
            for l in self.LINE_ID:
                if self.LINE_F_T[l][0] == bus:
                    self.LINES_FROM_BUS[bus].append(l)
                elif self.LINE_F_T[l][1] == bus:
                    self.LINES_TO_BUS[bus].append(l)
            for dc in self.LINK_ID:
                if self.LINK_F_T[dc][0] == bus:
                    self.LINKS_FROM_BUS[bus].append(dc)
                elif self.LINK_F_T[dc][1] == bus:
                    self.LINKS_TO_BUS[bus].append(dc)
        return()
