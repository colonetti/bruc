# -*- coding: utf-8 -*-
"""
@author: Colonetti
"""
import time
from mpi4py import MPI
import numpy as np

from read_and_load_data.read_csv import read_HPF_model
from hpf.get_hpf import build_3DHPF, write_3Dim_HPF, write_fb_approx, write_tr_approx

def build_approx_HPFs(params, hydros, W_COMM, W_SIZE, W_RANK):
    '''Build piecewise-linear approximations of the HPFs'''

    hpf_model = read_HPF_model(params.IN_FOLDER +\
                                    'HPF data - ' + params.PS + '.csv', params, hydros)

    # linear approximation of the forebay level.
    # [coefficient, constant, max error in (m) for 100 points]
    fb_approx = {h: [0, 0, 0] for h in hydros.RESERVOIR_NAME}

    # linear approximation of the tailrace level.
    # [coefficient, constant, max error in (m) for 100 points]
    tr_approx = {h: [0, 0, 0] for h in hydros.RESERVOIR_NAME}

    # One for each reservoir. The first key is used for identifying tasks
    hpfs_to_generate = [(1e3, h) for h in {hydros.UNIT_RESERVOIR_ID[u] for u in hydros.UNIT_NAME}]

    hpf_hyperplanes = [[] for i in hpfs_to_generate]

    i = 0
    for hpf in hpfs_to_generate:
        build_3DHPF(params, hydros, hpf[1], hpf_hyperplanes, fb_approx, tr_approx,
                                                            W_RANK, hpf_model, i)
        i += 1

    write_fb_approx(params, hydros, params.IN_FOLDER +\
                             params.CASE + '/' +\
                            'linear approximation of the forebay level - ' +\
                            params.PS + ' - ' +\
                             params.CASE + '.csv', fb_approx)

    write_tr_approx(params, hydros, params.IN_FOLDER +\
                             params.CASE + '/' +\
                            'linear approximation of the tailrace level - ' +\
                            params.PS + ' - ' +\
                             params.CASE + '.csv', tr_approx)


    # Write the piecewise-linear approximation to be read later
    write_3Dim_HPF(params, hydros, params.IN_FOLDER +\
                             params.CASE + '/' +\
                            'aggregated_3Dim - ' +\
                            params.PS + ' - ' +\
                             params.CASE + ' - HPF without binaries.csv',\
                            hpf_hyperplanes, hpfs_to_generate)

    W_COMM.Barrier()

    return()
