# -*- coding: utf-8 -*-
"""
@author: Colonetti
"""

from gurobipy import tuplelist, GRB, quicksum
from hydro_model.hydros import get_groups_of_identical_units

def add_hydro_vars(m, params, hydros):
    '''Add the hydro vars
    params:             an instance of OptOptions (opt_options.py) that contains the
                            parameters for the problem and the algorithm
    hydros:             an instance of Hydros (hydro_model.hydros.py) with all hydro data
    '''

    h_g = {}    # dictionary of power injection (generation by turbines and consumption by pumps)

    #### Reservoir variables
    tl_h = tuplelist([(h, t) for t in range(params.T) for h in hydros.RESERVOIR_NAME])

    # Reservoir volume in hm3
    v = m.addVars(tl_h, vtype = GRB.CONTINUOUS,
                lb = [hydros.MIN_VOL[h] for t in range(params.T) for h in hydros.RESERVOIR_NAME],
                ub = [hydros.MAX_VOL[h] for t in range(params.T) for h in hydros.RESERVOIR_NAME],
                name = "v")

    # Forebay level in m
    fb = m.addVars(tl_h, vtype = GRB.CONTINUOUS, lb = 0, name = "fb")

    # Tailrace level in m
    tr = m.addVars(tl_h, vtype = GRB.CONTINUOUS, lb = 0, name = "tr")

    # Gross head in m
    gross_head = m.addVars(tl_h, vtype = GRB.CONTINUOUS, lb = 0, name = "gross_head")

    # Spillage in m3/s
    spil = m.addVars(tl_h, vtype = GRB.CONTINUOUS, obj = 0,
                lb = 0,
                ub = [hydros.MAX_SPIL[h] for t in range(params.T) for h in hydros.RESERVOIR_NAME],
                name = "spil")

    # Water bypass in m3/s
    tl_h = tuplelist([(h, t) for t in range(params.T) for h in hydros.BYPASS_DR_PLANT_NAME])
    q_bypass = m.addVars(tl_h, vtype = GRB.CONTINUOUS, lb = 0,
                ub = [hydros.MAX_BYPASS[h] for t in range(params.T)
                                        for h in hydros.BYPASS_DR_PLANT_NAME],
                name = 'q_bypass')

    #### Generating units variables
    tl_u = tuplelist([(u, t) for t in range(params.T) for u in hydros.UNIT_NAME])

    # turbine discharge in m3/s
    q = m.addVars(tl_u, vtype = GRB.CONTINUOUS, lb = 0, ub = [hydros.MAX_Q[k[0]] for k in tl_u],
                                                                                        name = "q")

    # power generation
    h_g.update(m.addVars(tl_u, vtype = GRB.CONTINUOUS,lb=0, ub = [hydros.MAX_P[k[0]] for k in tl_u],
                                                                                    name = "h_g"))

    #### Pump variables
    tl_p = tuplelist([(h, t) for t in range(params.T) for h in hydros.PUMP_NAME])

    # pumped water
    q_pump = m.addVars(tl_p, vtype = GRB.CONTINUOUS, lb = 0,
                ub = [hydros.MAX_PUMP_Q[u] for t in range(params.T) for u in hydros.PUMP_NAME],
                name = "q_pump")

    # power consumption by the pumps
    h_g.update(m.addVars(tl_p, vtype = GRB.CONTINUOUS,
                lb = [-hydros.MAX_PUMP_Q[k[0]]*hydros.PUMP_CONV_RATE[k[0]] for k in tl_p],
                ub = 0,
                name = "h_g"))

    ##### Expected future cost of water storage (cost-to-go function) in $
    alpha = m.addVar(lb = 0, obj = 1, vtype = GRB.CONTINUOUS, name = "alpha")

    #### Previous states
    for h in hydros.RESERVOIR_NAME:
        v[h, -1] = hydros.V_0[h]# reservoir volume in hm3 immediatelly before the beginning of the
                                # planning horizon

        if h in hydros.DOWNRIVER_PLANT_NAME:
            for t in range(-hydros.WATER_TRAVEL_TIME[h], 0, 1):
                spil[h, t] = hydros.SPIL_0[h, t]

        if h in hydros.DOWNRIVER_PLANT_NAME and h in hydros.UNIT_RESERVOIR_ID.values():
            for u in [u for u in hydros.UNIT_NAME if hydros.UNIT_RESERVOIR_ID[u] == h]:
                for t in range(-hydros.WATER_TRAVEL_TIME[h], 0, 1):
                    q[u, t] = 0

        if h in hydros.BYPASS_DR_PLANT_NAME:
            for t in range(-hydros.WATER_TRAVEL_BYPASS[h], 0, 1):
                q_bypass[h, t] = 0

        if h in hydros.PUMP_RESERVOIR_ID.values():
            f_u = [u for u in hydros.PUMP_NAME if hydros.PUMP_RESERVOIR_ID[u] == h][0]
            for t in range(-hydros.PUMP_WATER_TRAVELLING_TIME[f_u], 0, 1):
                q_pump[f_u, t] = 0
    ############################################################################

    return(v, fb, tr, gross_head, spil, q, q_bypass, q_pump, h_g, alpha)

def add_HPF_approximation_q_v_s(m, v, q, s, h_g, params, hydros):
    '''Add the approximation of the hydropower function'''
    for h in [h for h in hydros.RESERVOIR_NAME if len([u for u in hydros.UNIT_NAME
                                                        if hydros.UNIT_RESERVOIR_ID[u] == h]) > 0]:
        UNITS = [u for u in hydros.UNIT_NAME if hydros.UNIT_RESERVOIR_ID[u] == h]
        for t in range(params.T):
            for i in range(len(hydros.A0[h])):
                m.addConstr((quicksum(h_g[u, t] for u in UNITS)\
                        - hydros.A0[h][i]*quicksum(q[u, t] for u in UNITS)
                            - hydros.A1[h][i]*v[h, t]\
                                    - hydros.A2[h][i]*s[h, t] - hydros.A3[h][i] <= 0),\
                                        name = f"HPF[{h},{i},{t}]")

    return()

def add_HPF_approximation_gross_head_q(m, gross_head, q, h_g, params, hydros):
    '''Add the approximation of the hydropower function'''
    for h in [h for h in hydros.RESERVOIR_NAME if len([u for u in hydros.UNIT_NAME
                                                        if hydros.UNIT_RESERVOIR_ID[u] == h]) > 0]:
        UNITS = [u for u in hydros.UNIT_NAME if hydros.UNIT_RESERVOIR_ID[u] == h]
        for t in range(params.T):
            for i in range(len(hydros.A0[h])):
                m.addConstr((quicksum(h_g[u, t] for u in UNITS)\
                        - hydros.A0[h][i]*quicksum(q[u, t] for u in UNITS)
                            - hydros.A1[h][i]*gross_head[h, t] - hydros.A3[h][i] <= 0),\
                                        name = f"HPF[{h},{i},{t}]")

    return()

def add_HPF_approximation_fb_q_spil(m, fb, q, spil, h_g, params, hydros):
    '''Add the approximation of the hydropower function'''
    for h in [h for h in hydros.RESERVOIR_NAME if len([u for u in hydros.UNIT_NAME
                                                        if hydros.UNIT_RESERVOIR_ID[u] == h]) > 0]:
        UNITS = [u for u in hydros.UNIT_NAME if hydros.UNIT_RESERVOIR_ID[u] == h]
        for t in range(params.T):
            for i in range(len(hydros.A0[h])):
                m.addConstr((quicksum(h_g[u, t] for u in UNITS)\
                        - hydros.A0[h][i]*quicksum(q[u, t] for u in UNITS)
                            - hydros.A1[h][i]*fb[h, t] - hydros.A2[h][i]*spil[h, t]
                            - hydros.A3[h][i] <= 0),\
                                        name = f"HPF[{h},{i},{t}]")

    return()


def add_fb_tr(m, v, q, spil, fb, tr, gross_head, params, hydros):
    '''Add linear approximations for the forebay level and tailrace level'''

    for h in hydros.RESERVOIR_NAME:
        for t in range(params.T):
            m.addConstr(fb[h, t] - hydros.FB_COEF[h]*v[h, t] - hydros.FB_CONST[h] == 0,
                                                    name = f'forebay_level[{h},{t}]')

    for h in hydros.RESERVOIR_NAME:
        UNITS = [u for u in hydros.UNIT_NAME if hydros.UNIT_RESERVOIR_ID[u] == h]
        if hydros.INFLUENCE_OF_SPIL[h]:
            for t in range(params.T):
                m.addConstr(tr[h, t]
                            - hydros.TR_COEF[h]*(spil[h, t] + quicksum(q[u, t] for u in UNITS))
                                - hydros.TR_CONST[h] == 0, name = f'tailrace_level[{h},{t}]')
        else:
            for t in range(params.T):
                m.addConstr(tr[h, t] - hydros.TR_COEF[h]*quicksum(q[u, t] for u in UNITS)
                            - hydros.TR_CONST[h] == 0, name = f'tailrace_level[{h},{t}]')

    for h in hydros.RESERVOIR_NAME:
        for t in range(params.T):
            m.addConstr(gross_head[h, t] - fb[h, t] + tr[h, t] == 0,
                                                    name = f'gross_head_constr[{h},{t}]')

    return()

def add_bin_var_limits(m, params, hydros, q, h_g, h_status):
    '''Add lower and upper limits on turbine discharge and generation'''
    list_of_plants_with_turbines = list({hydros.UNIT_RESERVOIR_ID[u] for u in hydros.UNIT_NAME})
    list_of_plants_with_turbines.sort()

    if params.HYDRO_MODEL == 'aggr':
        for h in list_of_plants_with_turbines:
            UNITS = [u for u in hydros.UNIT_NAME if hydros.UNIT_RESERVOIR_ID[u] == h]
            UB_h_g = sum([hydros.MAX_P[u] for u in UNITS])
            LB_h_g = min([hydros.MIN_P[u] for u in UNITS])
            UB_q = sum([hydros.MAX_Q[u] for u in UNITS])
            LB_q = min([hydros.MIN_Q[u] for u in UNITS])
            for t in range(params.T):
                m.addConstr(quicksum(h_g[u, t] for u in UNITS) - h_status[h, t]*UB_h_g <= 0,
                                                            name = f'upper_bound_h_g[{h},{t}]')
                m.addConstr(h_status[h, t]*LB_h_g - quicksum(h_g[u, t] for u in UNITS) <= 0,
                                                            name = f'lower_bound_h_g[{h},{t}]')
            for t in range(params.T):
                m.addConstr(quicksum(q[u, t] for u in UNITS) - h_status[h, t]*UB_q <= 0,
                                                            name = f'upper_bound_q[{h},{t}]')
                m.addConstr(h_status[h, t]*LB_q - quicksum(q[u, t] for u in UNITS) <= 0,
                                                            name = f'lower_bound_q[{h},{t}]')

    elif params.HYDRO_MODEL in ('indv', 'zones'):
        for u in hydros.UNIT_NAME:
            for t in range(params.T):
                m.addConstr(h_g[u, t] - h_status[u, t]*hydros.MAX_P[u] <= 0,
                                                            name = f'upper_bound_h_g[{u},{t}]')
                m.addConstr(h_status[u, t]*hydros.MIN_P[u] - h_g[u, t] <= 0,
                                                            name = f'lower_bound_h_g[{u},{t}]')
            for t in range(params.T):
                m.addConstr(q[u, t] - h_status[u, t]*hydros.MAX_Q[u] <= 0,
                                                            name = f'upper_bound_q[{u},{t}]')
                m.addConstr(h_status[u, t]*hydros.MIN_Q[u] - q[u, t] <= 0,
                                                            name = f'lower_bound_q[{u},{t}]')

    return()

def add_mass_balance(m, v, q, q_bypass, q_pump, spil, params, hydros):
    '''Add mass balance constraints to the reservoirs'''

    # Outflow of the hydro reservoirs in hm3
    tl_h = [(h, t) for t in range(params.T) for h in hydros.RESERVOIR_NAME]
    outflow = m.addVars(tl_h, vtype = GRB.CONTINUOUS, lb = 0, name = "outflow")

    # Inflow to the hydro reservoirs in hm3
    inflow = m.addVars(tl_h, vtype = GRB.CONTINUOUS, lb = 0, name = "inflow")

    # Total outflow in hm3
    for h in hydros.RESERVOIR_NAME:
        UNITS_OF_PLANT = [u for u in hydros.UNIT_NAME
                                    if hydros.UNIT_RESERVOIR_NAME[u] == hydros.RESERVOIR_NAME[h]]
        PUMPS_OF_PLANT = [u for u in hydros.PUMP_NAME
                                    if hydros.PUMP_RESERVOIR_NAME[u] == hydros.RESERVOIR_NAME[h]]

        qbp = q_bypass if h in hydros.BYPASS_DR_PLANT_NAME else {(h, t): 0 for t in range(params.T)}

        for t in range(params.T):
            m.addConstr((outflow[h, t] - params.C_H*(\
                                    spil[h, t]
                                    + qbp[h, t]
                                    + quicksum(q_pump[u, t] for u in PUMPS_OF_PLANT)
                                    + quicksum(q[u, t] for u in UNITS_OF_PLANT)
                                    ) == 0), name = f"totalOutflow[{h},{t}]")

    # Total inflow in hm3. Water coming from other reservoirs as well as from incremental inflow
    for h in hydros.RESERVOIR_NAME:
        UP_RIVER_PLANTS = [h2 for h2 in hydros.DOWNRIVER_PLANT_NAME
                                    if hydros.DOWNRIVER_PLANT_NAME[h2] == hydros.RESERVOIR_NAME[h]]
        UP_RIVER_UNITS = [u for u in hydros.UNIT_NAME
                                    if hydros.UNIT_RESERVOIR_ID[u] in UP_RIVER_PLANTS]
        UP_RIVER_BYPASS = [h2 for h2 in hydros.BYPASS_DR_PLANT_NAME
                                    if hydros.BYPASS_DR_PLANT_NAME[h2] == hydros.RESERVOIR_NAME[h]]
        DOWN_RIVER_PUMPS = [u for u in hydros.PUMP_NAME
                                    if hydros.PUMP_UPRIVER_RESERVOIR[u] == hydros.RESERVOIR_NAME[h]]
        for t in range(params.T):
            lhs = inflow[h, t] - params.C_H*(
                        quicksum(spil[up_r, t - hydros.WATER_TRAVEL_TIME[up_r]]
                                                                    for up_r in UP_RIVER_PLANTS)
                        + quicksum(q[u, t - hydros.WATER_TRAVEL_TIME[hydros.UNIT_RESERVOIR_ID[u]]]
                                                                    for u in UP_RIVER_UNITS)
                        + quicksum(q_bypass[up_r, t - hydros.WATER_TRAVEL_BYPASS[up_r]]
                                                                    for up_r in UP_RIVER_BYPASS)
                        + quicksum(q_pump[u, t - hydros.PUMP_WATER_TRAVELLING_TIME[u]]
                                                                    for u in DOWN_RIVER_PUMPS))
            m.addConstr((lhs == params.C_H*hydros.INFLOWS[h, t]), name = f"totalInflow[{h},{t}]")

    #### Reservoir volume balance
    for h in hydros.RESERVOIR_NAME:
        for t in range(params.T):
            m.addConstr((v[h, t] - v[h, t - 1]  + outflow[h, t] - inflow[h, t] == 0),
                                                                name = f"MassBalance[{h},{t}]")

    return (inflow, outflow)

def add_hydro_binaries(m, params, hydros, var_type = GRB.BINARY):
    '''Add status variables either for plants or units'''
    h_status = {}

    if params.HYDRO_MODEL == 'aggr':
        tl_list = list({hydros.UNIT_RESERVOIR_ID[u] for u in hydros.UNIT_NAME})
        tl_list.sort()
        tl_list = tuplelist([(h, t) for t in range(params.T) for h in tl_list])
        h_status.update(m.addVars(tl_list, lb = 0, ub = 1, vtype = var_type, name = 'h_status'))

    elif params.HYDRO_MODEL in ('indv', 'zones'):
        tl_u = tuplelist([(u, t) for t in range(params.T) for u in hydros.UNIT_NAME])
        h_status.update(m.addVars(tl_u, lb = 0, ub = 1, vtype = var_type, name = 'h_status'))

    if params.HYDRO_MODEL == 'zones':
        tl_list = list({hydros.UNIT_RESERVOIR_ID[u] for u in hydros.UNIT_NAME})
        for h in tl_list:
            GROUPS = list({hydros.UNIT_GROUP_ID[u] for u in hydros.UNIT_NAME
                                    if hydros.UNIT_RESERVOIR_NAME[u] == hydros.RESERVOIR_NAME[h]})
            GROUPS.sort()
            UNITS_IN_GROUPS = {group: [u for u in hydros.UNIT_NAME
                                        if hydros.UNIT_RESERVOIR_NAME[u] == hydros.RESERVOIR_NAME[h]
                                        and hydros.UNIT_GROUP_ID[u] == group] for group in GROUPS}
            for group in [group for group in GROUPS if len(UNITS_IN_GROUPS[group]) > 1]:
                # only necessary if there is more than one equivalent unit in this group
                for t in range(params.T):
                    m.addConstr(quicksum(h_status[u, t] for u in UNITS_IN_GROUPS[group]) <= 1,
                                                            name = f'unique_unit[{h},{group},{t}]')

    if params.HYDRO_MODEL == 'indv':
        list_of_plants_with_turbines, groups_of_identical_units = get_groups_of_identical_units(
                                                                                            hydros)

        for h in list_of_plants_with_turbines:
            for group in groups_of_identical_units[h]:
                for i in range(1, len(groups_of_identical_units[h][group]), 1):
                    u1 = groups_of_identical_units[h][group][i - 1]
                    u2 = groups_of_identical_units[h][group][i]
                    for t in range(params.T):
                        m.addConstr(h_status[u1, t] - h_status[u2, t]>= 0,
                                                        name = f'priority[{h},{group},{u2},{t}]')

    return(h_status)

def add_hydro(m, params, hydros, h_status):
    '''Add hydro variables and constraints to the model
    m:                  optimization model
    params:             an instance of OptOptions (opt_options.py) that contains the
                            parameters for the problem and the algorithm
    hydros:             an instance of Hydros (hydro_model.hydros.py) with all hydro data
    '''

    v, fb, tr, gross_head, spil, q, q_bypass, q_pump, h_g, alpha = add_hydro_vars(m, params, hydros)

    if params.HYDRO_MODEL in ('aggr', 'indv', 'zones'):
        add_bin_var_limits(m, params, hydros, q, h_g, h_status)

    inflow, outflow = add_mass_balance(m, v, q, q_bypass, q_pump, spil, params, hydros)

    #### Cost-to-go function
    for c in range(len(hydros.CTF_RHS)):
        m.addConstr(-1*(alpha + quicksum(v[h, params.T - 1]*hydros.CTF[c][h]
                    for h in hydros.RESERVOIR_NAME)) <= -hydros.CTF_RHS[c], name = f"CostToGo[{c}]")

    #### Pumps
    for u in hydros.PUMP_NAME:
        for t in range(params.T):
            m.addConstr(h_g[u, t] + q_pump[u, t]*hydros.PUMP_CONV_RATE[u] == 0,\
                                                                        name = f"convPump[{u},{t}]")

    #### add linear approximation of the forebay level and the tailrace level
    add_fb_tr(m, v, q, spil, fb, tr, gross_head, params, hydros)

    #### Add piecewise-linear model of the hydropower function
    #add_HPF_approximation_q_v_s(m, v, q, spil, h_g, params, hydros)
    #add_HPF_approximation_gross_head_q(m, gross_head, q, h_g, params, hydros)
    add_HPF_approximation_fb_q_spil(m, fb, q, spil, h_g, params, hydros)

    return (h_g, v, fb, tr, gross_head, q, q_bypass, q_pump, spil, inflow, outflow, alpha)
