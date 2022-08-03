# -*- coding: utf-8 -*-
"""
@author: Colonetti
"""

import os
from time import sleep
import numpy as np
from mpi4py import MPI

from preprocessing.reduce_network import reduce_network, remove_end_of_line_buses_with_injections
from read_and_load_data.read_csv import *
from thermal_model.thermals import Thermals
from network_model.network import Network, update_buses_of_gen_units
from hydro_model.hydros import Hydros, convert_unit_based_to_zone_based
from opt_options import OptOptions
from hpf.main_hpf import build_approx_HPFs

def set_params(ROOT_FOLDER, W_COMM, W_RANK, W_SIZE, experiment, exp_name):
    '''Create an instance of OptOptions and set the initial values for its attributes'''

    params = OptOptions(ROOT_FOLDER, W_RANK, W_SIZE, experiment['case'],\
                        exp_name = exp_name)

    params.OUT_FOLDER = ROOT_FOLDER + '/output/' +params.PS +'/case '+params.CASE+'/'+exp_name+'/'

    if (W_RANK == 0) and not(os.path.isdir(params.OUT_FOLDER)):
        os.makedirs(params.OUT_FOLDER)

    W_COMM.Barrier()

    if (W_RANK == 0) and (len(experiment) > 0):
        f = open(params.OUT_FOLDER + '/experiment - ' + params.PS +\
                                ' - case ' + str(params.CASE) + '.csv', 'w', encoding = 'utf-8')
        f.write('key;value\n')
        for k in experiment.keys():
            f.write(str(k) + ';' + str(experiment[k]) + '\n')
        f.close()
        del f

    return(params)

def load_data(ROOT_FOLDER, W_COMM, W_SIZE, W_RANK, experiment, exp_name):
    '''Read csv files with system's data and operating conditions'''

    # create an instance of OptOptions (optoptions.py) with all parameters for the problem
    # and the solution process
    params = set_params(ROOT_FOLDER, W_COMM, W_RANK, W_SIZE, experiment, exp_name)

    # create objects for the configurations of hydro plants, thermal plants, and the network model
    network, thermals, hydros = Network(), Thermals(), Hydros()

    read_hydro_reservoirs(params.IN_FOLDER + 'hydro reservoirs - ' + params.PS + '.csv',
                                                                        params, hydros)

    read_hydro_generating_units(params.IN_FOLDER + 'hydro generating units - ' + params.PS + '.csv',
                                                                        params, hydros)

    read_hydro_pumps(params.IN_FOLDER + 'hydro pump units - ' + params.PS + '.csv',
                                                                        params, hydros)

    read_hydro_initial_state_DESSEM(params, hydros, W_RANK,\
                                    params.IN_FOLDER +  params.CASE + '/deflant.dat',\
                                    params.IN_FOLDER +  params.CASE + '/entdados.dat')

    read_inflows_from_DADVAZ(params, hydros, W_RANK, params.IN_FOLDER +  params.CASE +\
                                    '/dadvaz.dat')

    read_cost_to_go_function(params.IN_FOLDER +\
                            'cost-to-go function - ' + params.PS + '.csv', params, hydros)

    #build_approx_HPFs(params, hydros, W_COMM, W_SIZE, W_RANK)

    read_approx_fb(params.IN_FOLDER +  params.CASE +\
                        '/linear approximation of the forebay level - ' + params.PS + ' - '+
                                params.CASE + '.csv', params, hydros)

    read_approx_tr(params.IN_FOLDER +  params.CASE +\
                        '/linear approximation of the tailrace level - ' + params.PS + ' - '+
                                params.CASE + '.csv', params, hydros)

    read_aggreg_HPF(params.IN_FOLDER +  params.CASE + '/' + 'aggregated_3Dim - ' +\
            params.PS + ' - ' + params.CASE + ' - HPF without binaries.csv', params, hydros)

    read_thermal_gen_units(params.IN_FOLDER + 'thermal generating units - ' + params.PS + '.csv',
                                                                        params, thermals)

    read_combined_cycles_eq_units(params.IN_FOLDER + 'equivalent units - combined cycle - ' +
                                                                    params.PS + '.csv',\
                                                                        params, thermals)

    readTrajectories(params.IN_FOLDER + 'thermal trajectories - ' + params.PS + '.csv',
                                                                        params, thermals)

    read_thermal_initial_states(params.IN_FOLDER +  params.CASE + '/operut.dat',
                                                                        params, thermals)

    read_thermal_linear_costs(params.IN_FOLDER +  params.CASE + '/operut.dat',
                                                                        params, thermals)

    read_DC_links(params.IN_FOLDER + 'DC links - ' + params.PS + '.csv', params, network)

    read_network_DESSEM(params.IN_FOLDER +  params.CASE + '/pesada.pwf', params)

    read_network_model(params.IN_FOLDER +  params.CASE + '/network - ' +
                            params.PS + ' - case ' + params.CASE + '.csv', params, network)

    read_load_DESSEM(params, network, hydros)

    read_load(params, network,  filename_gross_load = params.IN_FOLDER +  params.CASE +
                                                '/gross load - ' + params.PS + '.csv',
                                filename_renewable_gen = params.IN_FOLDER +  params.CASE +
                                                '/renewable generation - ' + params.PS + '.csv')

    update_buses_of_gen_units(params, network, hydros, thermals)

    network.buses_from_to()
    network.classify_buses(thermals, hydros)

    reduce_network(params, hydros, thermals, network, W_RANK)

    remove_end_of_line_buses_with_injections(params, hydros, thermals, network, W_RANK)

    if params.HYDRO_MODEL == 'zones':
        convert_unit_based_to_zone_based(params, hydros, W_RANK)

    return(params, thermals, network, hydros)
