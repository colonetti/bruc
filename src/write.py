# -*- coding: utf-8 -*-
"""
@author: Colonetti
"""

import numpy as np
from read_and_load_data.read_csv import read_HPF_model
from hpf.get_hpf import get_power_output_vol_turb_spil, get_forebay_level, get_tailrace_level
from thermal_model.thermals import get_eq_units

def write_readable_solution(params, thermals, hydros, network,\
                    h_g, t_g, s_gen, s_load, s_renewable):
    '''Write the solution in a way humans can understand'''

    f = open(params.OUT_FOLDER + 'readableSolution - ' + \
                params.PS + ' - case ' + params.CASE + '.csv', 'w', encoding = 'ISO-8859-1')

    for h in hydros.RESERVOIR_NAME:
        f.write(hydros.RESERVOIR_NAME[h] + ';')
        gen = [0 for t in range(params.T)]
        if h in hydros.UNIT_RESERVOIR_ID.values() or h in hydros.PUMP_RESERVOIR_ID.values():
            if h in hydros.UNIT_RESERVOIR_ID.values():
                UNITS = [u for u in hydros.UNIT_NAME if hydros.UNIT_RESERVOIR_ID[u] == h]
                for u in UNITS:
                    for t in range(params.T):
                        gen[t] += h_g[u, t]
            if h in hydros.PUMP_RESERVOIR_ID.values():
                PUMPS_OF_PLANT = [u for u in hydros.PUMP_NAME
                                    if hydros.PUMP_RESERVOIR_NAME[u] == hydros.RESERVOIR_NAME[h]]
                for u in PUMPS_OF_PLANT:
                    for t in range(params.T):
                        gen[t] += h_g[u, t]

            for t in range(params.T):
                f.write(str(round(gen[t]*params.POWER_BASE, 4)) + ';')
        else:
            for t in range(params.T):
                f.write('0;')
        f.write('\n')
    for g in thermals.UNIT_NAME:
        f.write(thermals.UNIT_NAME[g] + ';')
        for t in range(params.T):
            f.write(str(round(t_g[g, t]*params.POWER_BASE, 4)) + ';')
        f.write('\n')
    f.write('Net load;')
    for t in range(params.T):
        f.write(str(round(np.sum(network.NET_LOAD[:, t])*params.POWER_BASE, 4)) + ';')

    f.write('\n')

    if len(s_gen.keys()) > 0:
        f.write('Load Shedding;')
        for t in range(params.T):
            f.write(str(round(sum([s_gen[bus, t] for bus in network.LOAD_BUSES])\
                                                *params.POWER_BASE, 4)) + ';')

        f.write('\n')

    if len(s_load.keys()) > 0:
        f.write('Generation surplus;')
        for t in range(params.T):
            f.write(str(round(sum([s_load[bus, t] for bus in\
                                (network.GEN_BUSES - network.RENEWABLE_BUSES)])\
                                                *params.POWER_BASE, 4)) + ';')
        f.write('\n')

    if len(s_renewable.keys()) > 0:
        f.write('Renewable generation curtailment;')
        for t in range(params.T):
            f.write(str(round(sum([s_renewable[bus, t] for bus in network.RENEWABLE_BUSES])\
                                                *params.POWER_BASE, 4)) + ';')

    f.close()
    del f

    return()

def write_readable_thermal_solution(params, thermals, stup_tg, stdw_tg, disp_tg,
                disp_tg_cc_plant, trans_stup_tg_cc_plant, trans_stdw_tg_cc_plant, t_g_disp, t_g):
    '''Write the decisions for the thermal units'''

    f = open(params.OUT_FOLDER + 'thermal decisions of individual units - ' + \
                params.PS + ' - case ' + params.CASE + '.csv', 'w', encoding = 'ISO-8859-1')
    f.write('<BEGIN>\n')
    f.write('Period;ID;Thermal name;Start-up decision;Shut-down decision;Dispatch phase;')
    f.write('Generation in dispacth (MW);Total generation (MW)\n')
    for g in thermals.UNIT_NAME:
        for t in range(params.T):
            f.write(str(t) + ';')
            f.write(str(g) + ';')
            f.write(thermals.UNIT_NAME[g] + ';')
            f.write(str(stup_tg[g, t]) + ';')
            f.write(str(stdw_tg[g, t]) + ';')
            f.write(str(disp_tg[g, t]) + ';')
            f.write(str(round((t_g_disp[g, t]+thermals.MIN_P[g]*disp_tg[g, t])*
                                                    params.POWER_BASE, 4)) + ';')
            f.write(str(round(t_g[g, t]*params.POWER_BASE, 4))+';')
            f.write('\n')
    f.write('</END>')
    f.close()

    CC_PLANTS, EQ_UNITS_OF_PLANTS = get_eq_units(thermals)

    f = open(params.OUT_FOLDER + 'thermal decisions of combined-cycle plants - ' + \
                params.PS + ' - case ' + params.CASE + '.csv', 'w', encoding = 'ISO-8859-1')
    f.write('<BEGIN>\n')
    f.write('Period;Plant id;Plant name;cc plant dispatch status;')
    f.write('Total generation of plant (MW);')
    for _ in range(20):
        f.write('Unit id;Start-up decision of unit;Shut-down decision of unit;')
        f.write('Dispatch status of unit;')
        f.write('Start-up transition variable of unit;Shut-down transition variable of unit;')
        f.write('Total generation of unit (MW);Generation in dispatch phase of unit (MW);')
    f.write('\n')

    for cc_p in CC_PLANTS:
        for t in range(params.T):
            f.write(str(t) + ';')
            f.write(str(cc_p) + ';')
            f.write(thermals.PLANT_NAME[EQ_UNITS_OF_PLANTS[cc_p][0]] + ';')
            f.write(str(disp_tg_cc_plant[cc_p, t]) + ';')
            f.write(str(sum([t_g[g, t] for g in EQ_UNITS_OF_PLANTS[cc_p]])*params.POWER_BASE) + ';')
            for g in EQ_UNITS_OF_PLANTS[cc_p]:
                f.write(str(thermals.UNIT_ID[g]) + ';')
                f.write(str(stup_tg[g, t]) + ';')
                f.write(str(stdw_tg[g, t]) + ';')
                f.write(str(disp_tg[g, t]) + ';')
                f.write(str(trans_stup_tg_cc_plant[cc_p, g, t]) + ';')
                f.write(str(trans_stdw_tg_cc_plant[cc_p, g, t]) + ';')
                f.write(str(t_g[g, t]*params.POWER_BASE) + ';')
                f.write(str((t_g_disp[g, t] + thermals.MIN_P[g]*disp_tg[g, t])
                                                                        *params.POWER_BASE) + ';')
            f.write('\n')
    f.write('</END>')
    f.close()
    del f

    return()

def write_readable_hydro_solution(params, hydros, v, fb, tr, gross_head, q, spil, q_pump,
                                    q_bypass, inflow, outflow, h_g):
    '''Write the decisions for the hydro plants'''

    # firstly, for the decisions of volume, turbine discharge and spillage, get the real generation
    hpf_model = read_HPF_model(params.IN_FOLDER +\
                                    'HPF data - ' + params.PS + '.csv', params, hydros)

    real_generation = {(h, t): 0 for h in hydros.RESERVOIR_NAME for t in range(params.T)}

    for h in hydros.RESERVOIR_NAME:
        UNITS = [u for u in hydros.UNIT_NAME if hydros.UNIT_RESERVOIR_ID[u] == h]
        if len(UNITS) > 0:
            if hydros.INFLUENCE_OF_SPIL:
                for t in range(params.T):
                    real_generation[h, t] = get_power_output_vol_turb_spil(h, hpf_model, v[h, t],
                                    sum(q[u, t] for u in UNITS), spil[h, t], 0)/params.POWER_BASE
            else:
                for t in range(params.T):
                    real_generation[h, t] = get_power_output_vol_turb_spil(h, hpf_model, v[h, t],
                                    sum(q[u, t] for u in UNITS), 0, 0)/params.POWER_BASE

    f = open(params.OUT_FOLDER + 'hydro decisions - ' + \
                params.PS + ' - case ' + params.CASE + '.csv', 'w', encoding = 'ISO-8859-1')
    f.write('<BEGIN>\n')
    f.write('Reservoir ID;')
    f.write('Reservoir name;')
    f.write('Period;')
    f.write('Reservoir volume (hm3);')
    f.write('Turbine discharge (hm3);Spillage (hm3);')
    f.write('Pumping (hm3);Bypass (hm3);Incremental inflow (hm3);')
    f.write('Total inflow (hm3);Total outflow (hm3);')
    f.write('Total inflow minus total outflow (hm3);Total imbalance (hm3);')
    f.write('Approximation of the forebay level (m);Real forebay level (m);')
    f.write('Forebay error (m);')
    f.write('Approximation of the tailrace level (m);Real tailrace level (m);')
    f.write('Tailrace error (m);')
    f.write('Approximation of the gross head (m);Real gross head (m);')
    f.write('Gross head error (m);')
    f.write('Power given by approximation (MW);Real power (MW);Error (approx - real) (MW)')
    f.write('\n')
    for h in hydros.RESERVOIR_NAME:
        UNITS = [u for u in hydros.UNIT_NAME if hydros.UNIT_RESERVOIR_ID[u] == h]
        PUMPS_OF_PLANT = [u for u in hydros.PUMP_NAME
                                    if hydros.PUMP_RESERVOIR_NAME[u] == hydros.RESERVOIR_NAME[h]]
        for t in range(params.T):
            f.write(str(h) + ';')
            f.write(hydros.RESERVOIR_NAME[h] + ';')
            f.write(str(t) + ';')
            f.write(str(round(v[h, t], 4)) + ';')
            f.write(str(round(sum(q[u, t] for u in UNITS)*params.C_H, 4)) + ';')
            f.write(str(round(spil[h, t]*params.C_H, 4)) + ';')
            if len(PUMPS_OF_PLANT) > 0:
                f.write(str(round(sum(q_pump[u, t] for u in PUMPS_OF_PLANT)*params.C_H, 4)) + ';')
            else:
                f.write('0;')
            if h in hydros.BYPASS_DR_PLANT_NAME:
                f.write(str(round(q_bypass[h, t]*params.C_H, 4)) + ';')
            else:
                f.write('0;')
            f.write(str(round(hydros.INFLOWS[h, t]*params.C_H, 4)) + ';')

            f.write(str(round(inflow[h, t], 4)) + ';')
            f.write(str(round(outflow[h, t], 4)) + ';')

            # Total inflow minus total outflow (hm3)
            f.write(str(round(inflow[h,t] - outflow[h, t], 4)) + ';')

            # Total imbalance (hm3)
            if t == 0:
                f.write(str(round((v[h,t] - hydros.V_0[h]) - (inflow[h,t] - outflow[h, t]), 4))+';')
            else:
                f.write(str(round((v[h,t] - v[h, t - 1]) - (inflow[h,t] - outflow[h, t]), 4))+';')

            if len(UNITS) > 0:
                real_fb = get_forebay_level(h, hpf_model, v[h, t])
                if hydros.INFLUENCE_OF_SPIL[h]:
                    real_tr = get_tailrace_level(h, hpf_model, sum(q[u, t] for u in UNITS)
                                                    + spil[h, t])
                else:
                    real_tr = get_tailrace_level(h, hpf_model, sum(q[u, t] for u in UNITS))
                real_gross_head = real_fb - real_tr
            else:
                real_fb = 0
                real_tr = 0
                real_gross_head = 0

            f.write(str(round(fb[h, t], 4)) + ';')
            f.write(str(round(real_fb, 4)) + ';')
            f.write(str(round(fb[h, t] - real_fb, 4)) + ';')

            f.write(str(round(tr[h, t], 4)) + ';')
            f.write(str(round(real_tr, 4)) + ';')
            f.write(str(round(tr[h, t] - real_tr, 4)) + ';')

            f.write(str(round(gross_head[h, t], 4)) + ';')
            f.write(str(round(real_gross_head, 4)) + ';')
            f.write(str(round(gross_head[h, t] - real_gross_head, 4)) + ';')

            # Power (MW)
            p = 0
            if len(UNITS) > 0:
                p += sum(h_g[u, t] for u in UNITS)
            if len(PUMPS_OF_PLANT) > 0:
                p += sum(h_g[u, t] for u in PUMPS_OF_PLANT)

            f.write(str(round(p*params.POWER_BASE, 4)) + ';')

            f.write(str(round(real_generation[h, t]*params.POWER_BASE, 4)) + ';')

            f.write(str(round((p - real_generation[h, t])*params.POWER_BASE, 4)) + ';')

            f.write('\n')
    f.write('</END>')
    f.close()
    return()
