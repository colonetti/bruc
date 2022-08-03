# -*- coding: utf-8 -*-
"""
@author: Colonetti
"""
import numpy as np
from gurobipy import tuplelist, GRB, quicksum

def add_DC_network(m, thermals, network, hydros,\
                    h_g, t_g, list_T, s_gen, s_load, s_renewable, flow_AC, flow_DC):
    '''Add a DC representation of the network to the model'''

    # network buses' voltage angle in rad
    tpl = tuplelist([(bus, t) for t in list_T for bus in network.BUS_ID])
    theta = m.addVars(tpl, lb = - network.THETA_BOUND, ub = network.THETA_BOUND,
                                                vtype = GRB.CONTINUOUS, name = 'theta_bus')

    #### Set the voltage angle reference
    for bus in network.REF_BUS_ID:
        for t in list_T:
            theta[bus, t].lb = 0
            theta[bus, t].ub = 0

    #### Active power balance
    exp = {(bus, t): None for t in list_T for bus in network.BUS_ID}
    for bus in network.BUS_ID:
        for t in list_T:
            exp[bus, t] = - quicksum(flow_AC[network.LINE_F_T[l][0],
                                                            network.LINE_F_T[l][1], l, t]
                                                            for l in network.LINES_FROM_BUS[bus])\
                            + quicksum(flow_AC[network.LINE_F_T[l][0],
                                                            network.LINE_F_T[l][1], l, t]
                                                            for l in network.LINES_TO_BUS[bus])\
                            - network.NET_LOAD[network.BUS_HEADER[bus]][t]

    for dc in network.LINK_ID:
        for t in list_T:
            exp[network.LINK_F_T[dc][0], t].addTerms(-1.0, flow_DC[network.LINK_F_T[dc][0],
                                                            network.LINK_F_T[dc][1], dc, t])
        for t in list_T:
            exp[network.LINK_F_T[dc][1], t].addTerms(1, flow_DC[network.LINK_F_T[dc][0],
                                                            network.LINK_F_T[dc][1], dc, t])

    for g in thermals.UNIT_NAME:
        for t in list_T:
            exp[thermals.BUS[g], t].addTerms(1, t_g[g, t])

    for u in hydros.UNIT_NAME:
        for t in list_T:
            exp[hydros.UNIT_BUS_ID[u], t].addTerms(1, h_g[u, t])

    for u in hydros.PUMP_NAME:
        for t in list_T:
            exp[hydros.PUMP_BUS_ID[u], t].addTerms(1, h_g[u, t])

    for k in s_gen:
        exp[k].addTerms(1, s_gen[k])

    for k in s_load:
        exp[k].addTerms(-1, s_load[k])

    for k in s_renewable:
        exp[k].addTerms(-1, s_renewable[k])

    for bus in network.BUS_ID:
        for t in list_T:
            m.addConstr(exp[bus, t] == 0, name = f"bus[{bus},{t}]")

    ## AC transmission limits
    for l in network.LINE_ID:
        ADMT = 1/network.LINE_B[l]
        if abs(ADMT) >= 1e3:
            for t in list_T:
                m.addConstr((1e-3)*flow_AC[network.LINE_F_T[l][0], network.LINE_F_T[l][1], l, t]\
                                                == (1e-3)*ADMT*\
                                                    (theta[network.LINE_F_T[l][0], t] -\
                                                    theta[network.LINE_F_T[l][1], t]), \
                    name=f"AC_flow[{network.LINE_F_T[l][0]},{network.LINE_F_T[l][1]},{l},{t}]")
        else:
            for t in list_T:
                m.addConstr(flow_AC[network.LINE_F_T[l][0], network.LINE_F_T[l][1], l, t]\
                                                == ADMT*\
                                                    (theta[network.LINE_F_T[l][0], t] -\
                                                    theta[network.LINE_F_T[l][1], t]), \
                    name=f"AC_flow[{network.LINE_F_T[l][0]},{network.LINE_F_T[l][1]},{l},{t}]")
    return(theta)

def add_network( m, params, thermals, network, hydros, h_g, t_g, t_ang, t_single_bus):
    '''Add variables and constrains associated with the network
    m:                  optimization model
    params:             an instance of OptOptions (optoptions.py) that contains the
                            parameters for the problem and the algorithm
    network:            an instance of Network
    thermals:           an instance of Thermals
    hydros:             an instance of Hydros
    h_g:                variables for the hydro generation
    t_g:                variables for the thermal generation
    t_ang:              set containing the periods for each the model for the network is DC
    t_single_bus:       set containing the period for each the model is a single bus
    '''

    assert len(t_ang) + len(t_single_bus) > 0,\
                                "There must be at least one period in either t_ang or tSingleBus"

    theta, s_gen, s_load, s_renewable  = {}, {}, {}, {}

    #### Flows in AC transmission lines
    tpl = tuplelist([(network.LINE_F_T[l][0], network.LINE_F_T[l][1], l, t)
                                            for t in t_ang for l in network.LINE_ID])

    flow_AC = m.addVars(tpl,lb = [-network.LINE_MAX_P[k[2]] for k in tpl],
                            ub = [network.LINE_MAX_P[k[2]] for k in tpl],
                                                vtype = GRB.CONTINUOUS, name = 'flow_AC')
    #### Flows in DC links
    tpl = tuplelist([(network.LINK_F_T[l][0], network.LINK_F_T[l][1], l, t)
                                            for t in t_ang for l in network.LINK_ID])

    flow_DC = m.addVars(tpl,lb = [-network.LINK_MAX_P[k[2]] for k in tpl],
                            ub = [network.LINK_MAX_P[k[2]] for k in tpl],
                                                vtype = GRB.CONTINUOUS, name = 'flow_DC')

    if len(t_ang) > 0:
        tpl = tuplelist([(bus, t) for t in t_ang for bus in network.LOAD_BUSES])
        s_gen.update(m.addVars(tpl, lb = 0, obj = params.NETWORK_VIOL_UNIT_COST,
                                            vtype = GRB.CONTINUOUS, name = 's_gen'))

        tpl = tuplelist([(bus, t) for t in t_ang for bus in network.GEN_BUSES])
        s_load.update(m.addVars(tpl, lb = 0, obj = params.NETWORK_VIOL_UNIT_COST/3,
                                            vtype = GRB.CONTINUOUS, name = 's_load'))

        tpl = tuplelist([(bus, t) for t in t_ang for bus in network.RENEWABLE_BUSES])
        s_renewable.update(m.addVars(tpl, lb = 0, obj = 0,
                                            vtype = GRB.CONTINUOUS, name = 's_renewable'))

        for bus in network.RENEWABLE_BUSES:
            for t in t_ang:
                # Make sure that, at each bus, the amount of generation shedding is not greater
                # than the amount of renewable energy forecasted to the respective buses
                s_renewable[bus, t].ub = max(-1*network.NET_LOAD[network.BUS_HEADER[bus]][t], 0)

        theta = add_DC_network(m, thermals, network, hydros, h_g,\
                                t_g, t_ang, s_gen, s_load, s_renewable, flow_AC, flow_DC)

    if len(t_single_bus) > 0:
        # Create the variables of flows between subsystems
        for t in t_single_bus:
            m.addConstr(quicksum(t_g[g, t] for g in thermals.UNIT_NAME)
                                + quicksum(h_g[u, t] for u in hydros.UNIT_NAME)
                                    + quicksum(h_g[u, t] for u in hydros.PUMP_NAME)
                                        == np.sum(network.NET_LOAD[:, t]), name = f'single_bus{t}')

    return (theta, flow_AC, flow_DC, s_gen, s_load, s_renewable)
