# -*- coding: utf-8 -*-
"""
@author: Colonetti
"""

from gurobipy import quicksum, GRB, tuplelist
from thermal_model.thermals import get_eq_units

def fromHoursToTindex2(numberOfHours, indexFrom):
    ''' How many indices should it go back to account for numberOfHours?'''
    sumHours = 0
    t = 0
    while sumHours < numberOfHours:
        t += 1
        if indexFrom - t < 0:
            sumHours += 1
        else:
            sumHours += 0.5
    return(t)

def combined_cycle(m, params, thermals, stup_tg, stdw_tg, disp_tg, var_nature = GRB.BINARY):
    '''Insert constraints and variables related to the operation of combined cycles'''

    CC_PLANTS, EQ_UNITS_OF_PLANTS = get_eq_units(thermals)

    #### Create variables assocaited with the plants that have the possibility of operating
    #### in combined cycle

    tpl = tuplelist([(cc_p, t) for cc_p in CC_PLANTS for t in range(params.T)])
    #### Dispatch phase
    disp_tg_cc_plant = m.addVars(tpl, lb = 0, ub = 1, vtype = GRB.CONTINUOUS,
                                                                name = 'disp_tg_cc_plant')

    tpl = tuplelist([(cc_p, g, t) for cc_p in CC_PLANTS for g in EQ_UNITS_OF_PLANTS[cc_p]
                                                                    for t in range(params.T)])

    #### transition variable for start-up decision
    trans_stup_tg_cc_plant = m.addVars(tpl, lb = 0, ub = 1, vtype = GRB.CONTINUOUS,
                                                                name = 'trans_stup_tg_cc_plant')
    #### transition variable for shut-down decision
    trans_stdw_tg_cc_plant = m.addVars(tpl, lb = 0, ub = 1, vtype = GRB.CONTINUOUS,
                                                                name = 'trans_stdw_tg_cc_plant')

    #### previous state
    for cc_p in CC_PLANTS:
        disp_tg_cc_plant[cc_p, - 1] = max([disp_tg[g, -1] for g in EQ_UNITS_OF_PLANTS[cc_p]])

    for cc_p in EQ_UNITS_OF_PLANTS:
        for g in EQ_UNITS_OF_PLANTS[cc_p]:
            for t in range(- 4*thermals.MIN_UP[g] - len(thermals.STUP_TRAJ[g]), 0, 1):
                trans_stup_tg_cc_plant[cc_p, g, t] = 0

            for t in range(- max(thermals.MIN_DOWN[g] + len(thermals.STDW_TRAJ[g]),\
                                thermals.MIN_UP[g], len(thermals.STUP_TRAJ[g]), 1), 0, 1):
                trans_stdw_tg_cc_plant[cc_p, g, t] = 0

    #### plants' statuses
    for cc_p in CC_PLANTS:
        for t in range(params.T):
            m.addConstr((disp_tg_cc_plant[cc_p, t]
                        - quicksum(disp_tg[g, t] for g in EQ_UNITS_OF_PLANTS[cc_p]) == 0),
                                name = f'cc_plant_status[{cc_p},{t}]')

    #### make sure that at all times only one equivalent unit can be started up
    for cc_p in CC_PLANTS:
        for t in range(params.T):
            m.addConstr((quicksum(quicksum(
                        stup_tg[g, t2] for t2 in range(t - len(thermals.STUP_TRAJ[g]), t + 1, 1))
                            for g in EQ_UNITS_OF_PLANTS[cc_p])
                                <= 1 - disp_tg_cc_plant[cc_p, t - 1]),
                                    name = f'cc_plant_single_start_up[{cc_p},{t}]')

    #### start-ups, shut-downs and transitions cannot happen at the same time
    for cc_p in CC_PLANTS:
        for t in range(params.T):
            m.addConstr((quicksum(
                    quicksum(
                        stup_tg[g, t2] for t2 in range(t - len(thermals.STUP_TRAJ[g]), t + 1, 1))
                    + quicksum(
                        stdw_tg[g, t2] for t2 in range(t -len(thermals.STDW_TRAJ[g]) + 1, t + 1, 1))
                    + trans_stup_tg_cc_plant[cc_p, g, t]
                        for g in EQ_UNITS_OF_PLANTS[cc_p])
                            <= 1),
                                name = f'cc_plant_prevent_simultaneous_changes[{cc_p},{t}]')

    #### transitions between different equivalent units of the same plant must match
    for cc_p in CC_PLANTS:
        for t in range(params.T):
            m.addConstr((quicksum(
                            trans_stup_tg_cc_plant[cc_p, g, t] - trans_stdw_tg_cc_plant[cc_p, g, t]
                            for g in EQ_UNITS_OF_PLANTS[cc_p]) == 0),
                            name = f'cc_plant_matching_transitions[{cc_p},{t}]')

    #### Logical constraints
    for cc_p in EQ_UNITS_OF_PLANTS:
        for g in EQ_UNITS_OF_PLANTS[cc_p]:
            st_up_traj = len(thermals.STUP_TRAJ[g])
            for t in range(params.T):
                m.addConstr((stup_tg[g, t - st_up_traj]
                        + trans_stup_tg_cc_plant[cc_p, g, t]
                        - stdw_tg[g, t]
                        - trans_stdw_tg_cc_plant[cc_p, g, t]
                        - disp_tg[g, t] + disp_tg[g, t - 1] == 0), name = f'logical[{g},{t}]')

    #### Constrain the transition start-up variable
    for cc_p in EQ_UNITS_OF_PLANTS:
        for g in EQ_UNITS_OF_PLANTS[cc_p]:
            for t in range(params.T):
                m.addConstr(trans_stup_tg_cc_plant[cc_p, g, t] + disp_tg[g, t- 1] <= 1,
                                            name = f'trans_start_up_ub1[{g},{t}]')
                m.addConstr(trans_stup_tg_cc_plant[cc_p, g, t]
                                            + (1 - disp_tg_cc_plant[cc_p,t - 1]) <= 1,
                                                name = f'trans_start_up_ub2[{g},{t}]')
                m.addConstr(trans_stup_tg_cc_plant[cc_p, g, t]
                            - disp_tg_cc_plant[cc_p, t - 1] - (disp_tg[g, t] - disp_tg[g, t - 1])
                                    >= -1, name = f'trans_start_up_lb1[{g},{t}]')

    #### Constrain the transition shut-down variable
    for cc_p in EQ_UNITS_OF_PLANTS:
        for g in EQ_UNITS_OF_PLANTS[cc_p]:
            for t in range(params.T):
                m.addConstr(((trans_stdw_tg_cc_plant[cc_p, g, t] + stdw_tg[g, t])
                                + (1 - disp_tg[g, t- 1]) <= 1),
                                            name = f'trans_shut_down_ub1_{g}_{t}')
                m.addConstr(((trans_stdw_tg_cc_plant[cc_p, g, t] + stdw_tg[g, t])
                                + (1 - disp_tg_cc_plant[cc_p,t-1])<=1),
                                            name = f'trans_shut_down_ub2_{g}_{t}')
                m.addConstr(((trans_stdw_tg_cc_plant[cc_p, g, t] + stdw_tg[g, t])
                                - disp_tg_cc_plant[cc_p,t-1]
                                - (disp_tg[g, t- 1] - disp_tg[g, t])
                                    >= -1), name = f'trans_shut_down_lb1[{g},{t}]')

    #### Minimum up time for equivalent units
    for cc_p in EQ_UNITS_OF_PLANTS:
        for g in [g for g in EQ_UNITS_OF_PLANTS[cc_p] if thermals.MIN_UP[g] > 0]:
            st_up_traj = len(thermals.STUP_TRAJ[g])
            for t in range(params.T):
                m.addConstr(quicksum(stup_tg[g, t2 - st_up_traj] + trans_stup_tg_cc_plant[cc_p,g,t2]
                    for t2 in range(t - fromHoursToTindex2(thermals.MIN_UP[g], t) + 1, t + 1, 1))
                                        <= disp_tg[g, t], name = f'min_up[{g},{t}]')

    #### Minimum down time for equivalent units
    for cc_p in EQ_UNITS_OF_PLANTS:
        for g in [g for g in EQ_UNITS_OF_PLANTS[cc_p] if thermals.MIN_DOWN[g] > 0]:
            for t in range(params.T):
                m.addConstr(quicksum(stdw_tg[g, t2] + trans_stdw_tg_cc_plant[cc_p, g, t2]
                    for t2 in range(t - fromHoursToTindex2(thermals.MIN_DOWN[g], t) + 1, t + 1, 1))
                                                <= (1 - disp_tg[g, t]), name = f'min_down[{g},{t}]')

    return(disp_tg_cc_plant, trans_stup_tg_cc_plant, trans_stdw_tg_cc_plant)

def previous_states(params, thermals, stup_tg, stdw_tg, disp_tg):
    '''Create auxiliary keys and set variables bounds according to the states
    previous to the optimization horizon'''

    #### Previous states
    for g in thermals.UNIT_NAME:
        for t in range(- 4*thermals.MIN_UP[g] - len(thermals.STUP_TRAJ[g]), 0, 1):
            disp_tg[g, t] = thermals.STATE_0[g]
            stup_tg[g, t] = 0

        for t in range(- max(thermals.MIN_DOWN[g] + len(thermals.STDW_TRAJ[g]),
                            thermals.MIN_UP[g], len(thermals.STUP_TRAJ[g]), 1), 0, 1):
            stdw_tg[g, t] = 0

        if (thermals.STATE_0[g] == 1):
            # If the unit is currently in the dispatch phase, then it means that, at some point,
            # the unit was started-up and it successfully completed its start-up trajectory.
            # Thus, the unit was started-up at period 0 minus the number of periods it has been
            # in the dispatch phase (thermals.HOURS_IN_PREVIOUS_STATE[g]) minus the number
            # of periods necessary to complete the start-up trajectory
            stup_tg[g, min(- len(thermals.STUP_TRAJ[g])- thermals.HOURS_IN_PREVIOUS_STATE[g], -1)]=1
            disp_tg[g, -1] = 1
        else:
            stdw_tg[g, min(-thermals.HOURS_IN_PREVIOUS_STATE[g]- len(thermals.STDW_TRAJ[g]), -1)] =1
            disp_tg[g, -1] = 0

    return()

def thermal_bin(m, params, thermals, var_nature = GRB.BINARY):
    '''Add binary variables associated with the thermals units
    m:                  optimization model
    params:             an instance of OptOptions (opt_options.py) that contains the
                            parameters for the problem and the algorithm
    thermals:           an instance of Thermals (network.py) with all thermal data
    '''

    # gurobi's tuplelist containing the indices of thermal units' variables (unit index, time)
    tpl = tuplelist([(g, t) for g in thermals.UNIT_NAME for t in range(params.T)])

    #### Start-up decision
    stup_tg = m.addVars(tpl, lb = 0, ub = 1, obj = [thermals.CONST_COST[k[0]] for k in tpl],
                                vtype = var_nature, name = 'stup_tg')
    #### Shut-down decision
    stdw_tg = m.addVars(tpl, lb = 0, ub = 1, obj = [thermals.STUP_COST[k[0]] for k in tpl],
                                vtype = var_nature, name = 'stdw_tg')

    #### Dispatch phase
    disp_tg = m.addVars(tpl, lb = 0, ub = 1, obj = [thermals.STDW_COST[k[0]] for k in tpl],
                                vtype = var_nature, name = 'disp_tg')

    previous_states(params, thermals, stup_tg, stdw_tg, disp_tg)

    #### Logical constraitns
    for g in [g for g in thermals.UNIT_NAME if not(thermals.EQ_UNIT[g])]:
        for t in range(params.T):
            m.addConstr((stup_tg[g, t - len(thermals.STUP_TRAJ[g])] - stdw_tg[g, t]
                        - disp_tg[g, t] + disp_tg[g, t - 1] == 0), name = f'logical[{g},{t}]')

    #### Minimum up time for physical units
    for g in [g for g in thermals.UNIT_NAME if not(thermals.EQ_UNIT[g])
                                                                    and thermals.MIN_UP[g] > 0]:
        stUp = len(thermals.STUP_TRAJ[g])
        for t in range(params.T):
            m.addConstr(quicksum(stup_tg[g, t2] for t2 in range(t -
                            fromHoursToTindex2(thermals.MIN_UP[g], t) - stUp + 1, t - stUp + 1, 1))
                                    <= disp_tg[g, t], name = f'min_up[{g},{t}]')

    #### Minimum down time for physical units
    for g in [g for g in thermals.UNIT_NAME if not(thermals.EQ_UNIT[g])
                                                                    and thermals.MIN_DOWN[g] > 0]:
        for t in range(params.T):
            m.addConstr(quicksum(stdw_tg[g, t2] for t2 in range(t -
                                        fromHoursToTindex2(thermals.MIN_DOWN[g], t) + 1, t + 1, 1))\
                                            <= (1 - disp_tg[g, t]), name = f'min_down[{g},{t}]')

    #### if the start-up decision within the planning horizon will result in dispatch operation only
    #### after the planning horizon, then force the start-up decisions to be zero
    for g in [g for g in thermals.UNIT_NAME if len(thermals.STUP_TRAJ[g]) > 0]:
        m.addConstr(quicksum(stup_tg[g, t] for t in [t for t in range(params.T)
                                if (t + len(thermals.STUP_TRAJ[g])) >= params.T]) <= 0,
                                    f'prevent_after_opt_startups_[{g}]')

    disp_tg_cc_plant, trans_stup_tg_cc_plant, trans_stdw_tg_cc_plant =\
                        combined_cycle(m, params, thermals, stup_tg, stdw_tg, disp_tg, var_nature)

    stup_tg = {(g, t): stup_tg[g, t] for g in thermals.UNIT_NAME for t in range(params.T)}
    stdw_tg = {(g, t): stdw_tg[g, t] for g in thermals.UNIT_NAME for t in range(params.T)}
    disp_tg = {(g, t): disp_tg[g, t] for g in thermals.UNIT_NAME for t in range(params.T)}

    return (stup_tg, stdw_tg, disp_tg, disp_tg_cc_plant,
                                    trans_stup_tg_cc_plant, trans_stdw_tg_cc_plant)

def thermal_cont(m, params, thermals, stup_tg, stdw_tg, disp_tg,
                    trans_stup_tg_cc_plant, trans_stdw_tg_cc_plant):
    '''Add continuous variables and their constraints for the thermal model
    m:                      optimization model
    params:                 an instance of OptOptions (optoptions.py) that contains the
                                parameters for the problem and the algorithm
    thermals:               an instance of Thermals (network.py) with all thermal data
    stup_tg:                start-up decisions
    stdw_tg:                shut-down decisions
    disp_tg:                dispatch-status decisions
    trans_stup_tg_cc_plant: start-up transition decisions
    trans_stdw_tg_cc_plant: shut-down transition decisions
    '''

    for g in thermals.UNIT_NAME:
        for t in range(- len(thermals.STUP_TRAJ[g]), 0, 1):
            stup_tg[g, t] = 0

    # gurobi's tuplelist containing the indices of thermal units' variables (unit index, time)
    tpl = tuplelist([(g, t) for g in thermals.UNIT_NAME for t in range(params.T)])

    t_g = m.addVars(tpl, lb = 0, obj = [thermals.GEN_COST[k[0]] for k in tpl],
                                                    vtype = GRB.CONTINUOUS, name = 't_g')

    t_g_disp = m.addVars(tpl, lb = 0, obj = 0, vtype = GRB.CONTINUOUS, name = 't_g_disp')

    for g in thermals.UNIT_NAME:
        t_g[g, -1] = thermals.TG_0[g]

    #### Start-up trajectory
    tg_up_tj = {(g, t): 0 for t in range(params.T) for g in thermals.UNIT_NAME}

    #### Shut-down trajectory
    tg_down_tj = {(g, t): 0 for t in range(params.T) for g in thermals.UNIT_NAME}

    #### Start-up trajectory
    for g in thermals.UNIT_NAME:
        if len(thermals.STUP_TRAJ[g]) > 0:
            steps = len(thermals.STUP_TRAJ[g])
            for t in range(params.T):
                tg_up_tj[g, t] = quicksum(stup_tg[g, i]*thermals.STUP_TRAJ[g][t - steps - i]
                                                for i in range(max(t - steps + 1, 0), t + 1, 1))

    #### Shut-down trajectory
    #### Note that it is implicitly assumed that the power output of the
    #### thermal unit is zero when stDwTG = 1
    for g in thermals.UNIT_NAME:
        steps = len(thermals.STDW_TRAJ[g])
        for t in range(params.T):
            tg_down_tj[g, t] = quicksum(stdw_tg[g, t - i]*thermals.STDW_TRAJ[g][i]
                                                for i in [j for j in range(steps) if (t - j) >= 0])

    #### lower and upper operating limits of thermal units
    for g in thermals.UNIT_NAME:
        for t in range(params.T):
            m.addConstr(t_g_disp[g, t] - (thermals.MAX_P[g] - thermals.MIN_P[g])*disp_tg[g, t] <= 0,
                                                                        name = f'max_p[{g},{t}]')

    #### total generation
    for g in thermals.UNIT_NAME:
        for t in range(params.T):
            m.addConstr(t_g[g, t] - t_g_disp[g, t] - thermals.MIN_P[g]*disp_tg[g, t]
                                - tg_up_tj[g, t] - tg_down_tj[g, t] == 0, name = f'gen[{g},{t}]')

    # new constraints
    for g in thermals.UNIT_NAME:
        if (thermals.STATE_0[g] == 0):
            m.addConstr(t_g_disp[g, 0] <= 0, name = f'ramp_up_{g}_{0}')
        else:
            m.addConstr(t_g_disp[g, 0] - (thermals.TG_0[g] - thermals.MIN_P[g])
                                            <= thermals.RAMP_UP[g], name = f'ramp_up[{g},{0}]')
            m.addConstr(- t_g_disp[g, 0] + (thermals.TG_0[g] - thermals.MIN_P[g])
                                            <= thermals.RAMP_DOWN[g], name = f'ramp_down[{g},{0}]')

    #### only add the ramp constraints if they are really necessary
    for g in [g for g in thermals.UNIT_NAME
                            if (thermals.RAMP_UP[g] < (thermals.MAX_P[g] - thermals.MIN_P[g]))]:
        for t in range(1, params.T, 1):
            m.addConstr(t_g_disp[g, t] - t_g_disp[g, t - 1] <= thermals.RAMP_UP[g],
                                                            name = f'ramp_up[{g},{t}]')
    for g in [g for g in thermals.UNIT_NAME
                            if (thermals.RAMP_DOWN[g] < (thermals.MAX_P[g] - thermals.MIN_P[g]))]:
        for t in range(1, params.T, 1):
            m.addConstr(- t_g_disp[g, t] + t_g_disp[g, t - 1] <= thermals.RAMP_DOWN[g],
                                                                name = f'ramp_down[{g},{t}]')

    #### start and shut down at minimum power
    for g in thermals.UNIT_NAME:
        for t in range(1, params.T, 1):
            m.addConstr(t_g_disp[g, t] <=
                            (thermals.MAX_P[g] - thermals.MIN_P[g])*(disp_tg[g, t]
                                - stup_tg[g, t - len(thermals.STUP_TRAJ[g])]),
                                                    name = f'minGenAtFirstPeriod_startUP[{g},{t}]')
            m.addConstr(t_g_disp[g, t - 1] <=
                        (thermals.MAX_P[g] - thermals.MIN_P[g])*(disp_tg[g, t-1] - stdw_tg[g,t]),\
                                                    name = f'minGenAtFirstPeriod_shutDown[{g},{t}]')

    for g in thermals.UNIT_NAME:
        if (thermals.STATE_0[g] == 1) and (thermals.MAX_P[g] - thermals.MIN_P[g]) > 0:
            m.addConstr(thermals.TG_0[g] - thermals.MAX_P[g] <=
                            - (thermals.MAX_P[g] - thermals.MIN_P[g])*stdw_tg[g, 0],
                                            name = f'minGenAtFirstPeriod_shutDown[{g},{0}]')

    #### Transition ramps between different equivalent units of the same plant
    CC_PLANTS, EQ_UNITS_OF_PLANTS = get_eq_units(thermals)

    M = max(thermals.MAX_P.values())
    for cc_p in CC_PLANTS:
        first_unit = EQ_UNITS_OF_PLANTS[cc_p][0]# the transition ramp is the same for all equivalent
                                                # units at the same plant
        if thermals.TRANS_RAMP[first_unit] < 99999/params.POWER_BASE:
            for t in range(params.T):
                m.addConstr(quicksum(t_g[g, t] for g in EQ_UNITS_OF_PLANTS[cc_p])
                            - quicksum(t_g[g, t - 1] for g in EQ_UNITS_OF_PLANTS[cc_p])
                            - M*(1 - quicksum(trans_stup_tg_cc_plant[cc_p, g, t]
                                    for g in EQ_UNITS_OF_PLANTS[cc_p]))
                                    <= thermals.TRANS_RAMP[first_unit],
                                        name = f'cc_plant_up_transition_ramp[{cc_p},{t}]')
                m.addConstr(- quicksum(t_g[g, t] for g in EQ_UNITS_OF_PLANTS[cc_p])
                            + quicksum(t_g[g, t - 1] for g in EQ_UNITS_OF_PLANTS[cc_p])
                            - M*(1 - quicksum(trans_stup_tg_cc_plant[cc_p, g, t]
                                    for g in EQ_UNITS_OF_PLANTS[cc_p]))
                                    <= thermals.TRANS_RAMP[first_unit],
                                        name = f'cc_plant_down_transition_ramp[{cc_p},{t}]')

    return (t_g, t_g_disp)
