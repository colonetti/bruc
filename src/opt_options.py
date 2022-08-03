# -*- coding: utf-8 -*-
"""
@author: Colonetti
"""

from read_and_load_data.read_csv import read_date

class OptOptions:
    'Class of optimization and problem parameters'
    def __init__(self, ROOT_FOLDER: str, W_RANK: int, W_SIZE: int, case: str, exp_name: str):

        self.setup(ROOT_FOLDER, W_RANK, W_SIZE, case, exp_name)

    def setup(self, ROOT_FOLDER: str, W_RANK: int, W_SIZE: int, case: str, exp_name:str):
        'Initialize the attributes'

        self.EXP_NAME = exp_name

        self.T = 48                     # number of periods in the planning horizon
        self.REL_GAP_TOL = 1e-3         # relative gap tolerance for the DDiP
        self.TIME_LIMIT = 3*3600        # time limit in seconds
        self.CASE = case#'1'#           # id of the instance

        self.START = 0                  # used to control the time limit. It is the time stamp
                                        # at which the optimization process begins
        self.LAST_TIME = 0              # used to control the time limit. It is the final time.
                                        # self.lastTime = self.start + self.timeLimit
        self.PS = 'SIN'                 # power system ('SIN')

        self.IN_FOLDER = ROOT_FOLDER + '/input/' + self.PS +'/'
        self.OUT_FOLDER = ''            # will be filled later

        self.CASE_DATE = None           # only used for the Brazilian system in daymonthyear
        self.DATES_OF_TIME_STEPS = []   #DATES_OF_TIME_STEPS[0]=
                                # [day, hour, half-hour, duration in hours, date in daymonthyear]

        read_date(self.IN_FOLDER +  self.CASE + '/desselet.dat', self)

        self.THREADS = 0

        self.BASE_TIME_STEP = 0.5                   # In hours
        self.DISCRETIZATION = 0.5                   # In hours

        self.STATUS = None

        self.REMOVEL_PARALLEL_LINES, self.REDUCE_SYSTEM = True, True

        self.POWER_BASE = 100               # in MW
        self.SCAL_OBJ_FUNC = 1e-6           # scaling for the objective function

        # in $/MW but scaled with POWER_BASE and SCAL_OBJ_FUNC
        self.NETWORK_VIOL_UNIT_COST = 10000*self.POWER_BASE*self.SCAL_OBJ_FUNC

        # penalize spillage in $/(m3/s)
        self.SPILLAGE_UNIT_COST = 1*self.POWER_BASE*self.SCAL_OBJ_FUNC

        self.C_H = self.DISCRETIZATION*(3600*1e-6)  # from flow in m3/s to volume in hm3

        self.HYDRO_MODEL = 'zones'   # ('no hydro binaries', 'aggr', 'indv', 'zones')
