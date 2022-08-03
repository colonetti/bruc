# -*- coding: utf-8 -*-
"""
@author: Colonetti
"""

def get_eq_units(thermals):
    '''Get equivalent units and their respective plants'''
    EQ_UNITS = [g for g in thermals.UNIT_NAME if thermals.EQ_UNIT[g]]

    CC_PLANTS = []
    for g in EQ_UNITS:
        if thermals.PLANT_ID[g] not in CC_PLANTS:
            CC_PLANTS.append(thermals.PLANT_ID[g])

    EQ_UNITS_OF_PLANTS = {cc_p: [] for cc_p in CC_PLANTS}
    for g in EQ_UNITS:
        for c_i in range(len(CC_PLANTS)):
            if thermals.PLANT_ID[g] == CC_PLANTS[c_i]:
                EQ_UNITS_OF_PLANTS[CC_PLANTS[c_i]].append(g)
                break
    return(CC_PLANTS, EQ_UNITS_OF_PLANTS)

class Thermals:
    '''Class of thermal units'''
    def __init__(self):
        self.setup()

    def setup(self):
        '''Initialize the attributes'''

        # the keys of the unit dictionaries are the plant id and the unit id (plant id, unit id)
        self.UNIT_NAME = {}
        self.UNIT_ID = {}

        self.PLANT_NAME, self.PLANT_ID = {}, {}

        self.MIN_P, self.MAX_P  = {}, {}      # power limits

        self.GEN_COST = {}                   # unitary cost in $/(p.u.) for a 30-min period
        # constant cost if unit is operating, start-up cost, shut-down cost
        self.CONST_COST, self.STUP_COST, self.STDW_COST = {}, {}, {}

        self.RAMP_UP, self.RAMP_DOWN = {}, {}   # ramps

        self.MIN_UP, self.MIN_DOWN = {}, {}     # minimum times

        self.BUS = {}                           # bus the unit is connected to

        # Previous state
        self.STATE_0 = {}
        self.TG_0 = {}
        self.HOURS_IN_PREVIOUS_STATE = {}

        self.STUP_TRAJ = {}         # power steps in the start-up trajectory
        self.STDW_TRAJ = {}         # power steps in the shut-down trajectory

        self.EQ_UNIT = {}           # flag that indicates whether the unit is real or it is a
                                    # equivalent unit

        self.REAL_UNITS_IN_EQ = {}  # list of real units that compose the equivalent unit. if the
                                    # unit is real, then this list is empty

        self.TRANS_RAMP = {}        # transition ramp between equivalent units in combined-cycle
                                    # operations

        return()

    def add_new_unit(self, row, header, params):
        '''Add a new thermal unit'''

        P_ID = int(row[header["Plant\'s ID"]])  # plant id
        U_ID = int(row[header["Unit's ID"]])    # unit id

        self.UNIT_NAME[(P_ID, U_ID)] = row[header["Plant's Name"]].strip() + '-G-' + str(U_ID)
        self.UNIT_ID[(P_ID, U_ID)] = U_ID
        self.PLANT_NAME[(P_ID, U_ID)] = row[header["Plant's Name"]].strip()
        self.PLANT_ID[(P_ID, U_ID)] = int(row[header["Plant\'s ID"]])
        self.MIN_P[(P_ID, U_ID)] = float(row[header['Minimum power output (MW)']])/params.POWER_BASE
        self.MAX_P[(P_ID, U_ID)] = float(row[header['Maximum power output (MW)']])/params.POWER_BASE

        self.RAMP_UP[(P_ID,U_ID)]=(params.DISCRETIZATION*float(row[header["Ramp-up limit (MW/h)"]])/
                                                                    params.POWER_BASE)
        self.RAMP_DOWN[(P_ID, U_ID)] = (params.DISCRETIZATION*
                                    float(row[header["Ramp-down limit (MW/h)"]])/params.POWER_BASE)

        self.MIN_UP[(P_ID, U_ID)] = int(row[header["Minimum up-time (h)"]])
        self.MIN_DOWN[(P_ID, U_ID)] = int(row[header["Minimum down-time (h)"]])
        self.BUS[(P_ID, U_ID)] = int(row[header['Bus']])

        self.GEN_COST[(P_ID, U_ID)] = 0.000
        self.CONST_COST[(P_ID, U_ID)] = float(row[header["Constant cost ($)"]])*params.SCAL_OBJ_FUNC
        self.STUP_COST[(P_ID, U_ID)] = float(row[header["Start-up cost ($)"]])*params.SCAL_OBJ_FUNC
        self.STDW_COST[(P_ID, U_ID)] = float(row[header["Shut-down cost ($)"]])*params.SCAL_OBJ_FUNC

        self.STATE_0[(P_ID, U_ID)] = 0
        self.TG_0[(P_ID, U_ID)] = 0.000
        self.HOURS_IN_PREVIOUS_STATE[(P_ID, U_ID)] = 0

        self.STUP_TRAJ[(P_ID, U_ID)] = []
        self.STDW_TRAJ[(P_ID, U_ID)] = []

        self.EQ_UNIT[(P_ID, U_ID)] = False

        self.REAL_UNITS_IN_EQ[(P_ID, U_ID)] = []

        self.TRANS_RAMP[(P_ID, U_ID)] = 99999/params.POWER_BASE

        return()
