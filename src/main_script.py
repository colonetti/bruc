# -*- coding: utf-8 -*-
"""
@author: Colonetti
"""
import mpi4py
mpi4py.rc.thread_level = 'single'
import itertools
import os
from timeit import default_timer
from mpi4py import MPI
import numpy as np

from read_and_load_data.load_data import load_data
from post_optimization import post_optimization
from thermal_model.thermals import get_eq_units

W_COMM = MPI.COMM_WORLD
W_RANK = W_COMM.Get_rank()
W_SIZE = W_COMM.Get_size()
HOST = MPI.Get_processor_name()

def main(exp_list, exp_names):
    '''main function'''

    ROOT_FOLDER = os.path.abspath(os.path.join(__file__ , "../..")).replace("\\","/")

    params, thermals, network, hydros = load_data(ROOT_FOLDER, W_COMM, W_SIZE, W_RANK,
                                                    exp_list, exp_names)

    if (W_RANK == 0):

        CC_PLANTS, EQ_UNITS_OF_PLANTS = get_eq_units(thermals)

        INST_CAP_T = sum(thermals.MAX_P[u] for u in thermals.UNIT_NAME if not(thermals.EQ_UNIT[u]))
        for ccp in CC_PLANTS:
            INST_CAP_T += max(thermals.MAX_P[u] for u in EQ_UNITS_OF_PLANTS[ccp])

        if params.HYDRO_MODEL in ('no hydro binaries', 'aggr', 'indv'):
            INST_CAP_H = sum(hydros.MAX_P.values())
        else:
            # if zones is used
            INST_CAP_H = 0
            hydros_with_units = {hydros.UNIT_RESERVOIR_ID[u] for u in hydros.UNIT_NAME}
            for h in hydros_with_units:
                GROUPS = list({hydros.UNIT_GROUP_ID[u] for u in hydros.UNIT_NAME
                                    if hydros.UNIT_RESERVOIR_NAME[u] == hydros.RESERVOIR_NAME[h]})
                GROUPS.sort()
                UNITS_IN_GROUPS = {group: [u for u in hydros.UNIT_NAME
                                        if hydros.UNIT_RESERVOIR_NAME[u] == hydros.RESERVOIR_NAME[h]
                                        and hydros.UNIT_GROUP_ID[u] == group] for group in GROUPS}
                for group in GROUPS:
                    INST_CAP_H += max(hydros.MAX_P[u] for u in UNITS_IN_GROUPS[group])

        INST_CAP = (INST_CAP_T + INST_CAP_H)

        print('#####################################################################')
        print('###################  Overview of the system  ########################')
        print(f'System: {params.PS}\tCase: {params.CASE}')
        print(f'{len(thermals.UNIT_NAME)} thermal units with ' +
                                    f'installed capacity {INST_CAP_T*params.POWER_BASE:.4f} MW')
        print(f'{len(hydros.UNIT_NAME)} hydro generating units with ' +
                f'installed capacity {INST_CAP_H*params.POWER_BASE:.4f} MW')
        print(f'The installed capacity (thermals + hydros) is {INST_CAP*params.POWER_BASE:.4f} MW')
        print('Peak net load (MW): ' +\
                            f'{(np.max(np.sum(network.NET_LOAD,axis=0))*params.POWER_BASE):.4f}')
        print(f'Buses: {len(network.BUS_ID)}')
        print(f'Transmission lines: {len(network.LINE_F_T)}')
        print(f'DC links: {len(network.LINK_F_T)}')
        print('#####################################################################')
        print('\n', flush = True)

    f = open(params.OUT_FOLDER + '/params - '+ params.PS + ' - ' +\
                    params.CASE + ' - W_RANK ' + str(W_RANK) + '.csv', 'w', encoding='ISO-8859-1')
    f.write('attribute;value\n')
    for attr in [attr for attr in dir(params) if attr[0] != '_']:
        f.write(attr + ';' + str(getattr(params, attr)) + '\n')
    f.close()
    del f

    fixed_vars = []

    post_optimization(params, thermals, hydros, network, fixed_vars)
    print('\n\ncase ' + params.CASE + ' done\n\n', flush = True)
    W_COMM.Barrier()
    params.START = default_timer()
    params.LAST_TIME = params.START + params.TIME_LIMIT
    W_COMM.Barrier()

    return()

if __name__ == '__main__':

    cases = ['DS_ONS_012022_RV1D14']
    experiments = {'case': cases}

    experiment = {}

    exp_ID = 0

    keys, values = zip(*experiments.items())

    for perm in [dict(zip(keys, v)) for v in itertools.product(*values)]:
        for key in experiments:
            experiment[key] = perm[key]

        # Run the experiment
        exp_name = 'exp' + str(exp_ID)

        main(experiment, exp_name)

        exp_ID += 1

        W_COMM.Barrier()
