# -*- coding: utf-8 -*-
"""
@author: Colonetti
"""

import locale
from gurobipy import Model, GRB
from thermal_model.add_thermal_to_opt_model import thermal_bin, thermal_cont
from network_model.add_network_to_opt_model import add_network
from hydro_model.add_hydro_to_opt_model import add_hydro, add_hydro_binaries

from write import write_readable_solution, write_readable_thermal_solution,\
                    write_readable_hydro_solution

def post_optimization(params, thermals, hydros, network, fixed_vars):
    '''Optimize the model with the decision variables fixed and write the result to csv files'''

    print('\n\nPost-optimization problem\n\n', flush = True)

    locale.setlocale(locale.LC_ALL, 'en_US.utf-8')

    m = Model('m')

    h_status = add_hydro_binaries(m, params, hydros, var_type = GRB.BINARY)

    h_g, vol, fb, tr, gross_head, q, q_bypass, q_pump, spil, inflow, outflow, alpha =\
                                                        add_hydro(m, params, hydros, h_status)

    stup_tg, stdw_tg, disp_tg, disp_tg_cc_plant, trans_stup_tg_cc_plant, trans_stdw_tg_cc_plant =\
                                thermal_bin(m, params, thermals, var_nature = GRB.BINARY)

    t_g, t_g_disp = thermal_cont(m, params, thermals, stup_tg, stdw_tg, disp_tg,
                                trans_stup_tg_cc_plant, trans_stdw_tg_cc_plant)

    theta, flow_AC, flow_DC, s_gen, s_load, s_renewable = \
                   add_network(m, params, thermals, network, hydros, h_g, t_g, range(params.T), {})

    m.update()

    m.setParam('LogFile', params.OUT_FOLDER + '/post-optimization logfile - '+\
                        params.PS + ' - case ' + params.CASE + '.txt')
    m.setParam('Method', 2)
    m.setParam('BarConvTol', 1e-12)
    m.setParam('BarHomogeneous', 1)
    m.setParam('ScaleFlag', 3)
    m.setParam('Presolve', 2)
    m.setParam('TimeLimit', 3600)

    m.optimize()

    if m.status == 2 or m.SolCount >= 1:
        print('\n\n')

        print(f"Gap (%): {100*((m.objVal - m.objBound)/(m.objVal + 1e-12)):.4f}")

        print('\n\nThe total present cost is ' +\
                            locale.currency((m.objVal - alpha.x*alpha.obj)/params.SCAL_OBJ_FUNC,
                                grouping = True))

        print('The future cost is ' +\
                        locale.currency(alpha.x*alpha.obj/params.SCAL_OBJ_FUNC, grouping = True))

        print('The total cost is ' +\
                    locale.currency(m.objVal/params.SCAL_OBJ_FUNC, grouping = True), flush = True)
        print('\n')
        print('The best bound is ' +\
                    locale.currency(m.objBound/params.SCAL_OBJ_FUNC, grouping = True), flush = True)
        print('\n\n', flush = True)

        f = open(params.OUT_FOLDER + '/final results - '+\
                    params.PS + ' - case ' + params.CASE + '.csv', 'w', encoding = 'utf-8')
        f.write('Present cost ($);' + str((m.objVal - alpha.x)/params.SCAL_OBJ_FUNC) + '\n')
        f.write('Future cost ($);' + str(alpha.x/params.SCAL_OBJ_FUNC) + '\n')
        f.write('Total cost ($);' + str(m.objVal/params.SCAL_OBJ_FUNC)+'\n')
        f.close()
        del f

        # Print all variables
        f = open(params.OUT_FOLDER + '/variables - Part 1 - '+\
                        params.PS + ' - case ' + params.CASE + '.csv', 'w', encoding = 'utf-8')
        f.write('Var;x\n')
        for v in m.getVars():
            if 'theta' not in v.VarName and 'flow_AC' not in v.VarName\
                                                        and 'flow_DC' not in v.VarName:
                f.write(v.VarName + ';' + str(v.x) + '\n')
        f.close()
        del f

        f = open(params.OUT_FOLDER + '/variables - Part 2 - Angles and Flows - '+\
                        params.PS + ' - case ' + params.CASE + '.csv', 'w', encoding = 'utf-8')
        f.write('Var;x;max;min\n')
        for v in m.getVars():
            if 'theta' in v.VarName or 'flow_AC' in v.VarName or 'flow_DC' in v.VarName:
                if 'theta' in v.VarName:
                    f.write(v.VarName + ';' + str(v.x) + ';2pi;-2pi\n')
                elif 'flow_AC' in v.VarName:
                    f.write(v.VarName + ';' + str(v.x) + ';'\
                                + str(network.LINE_MAX_P
                                        [int(v.VarName.split(',')[2].replace(']', ''))])+';'+\
                                    str(-network.LINE_MAX_P
                                        [int(v.VarName.split(',')[2].replace(']', ''))]) + '\n')
                else:
                    f.write(v.VarName + ';' + str(v.x) + ';'\
                                + str(network.LINK_MAX_P
                                        [int(v.VarName.split(',')[2].replace(']', ''))]) +';'+\
                                str(-1*network.LINK_MAX_P
                                        [int(v.VarName.split(',')[2].replace(']', ''))]) + '\n')

        f.close()
        del f

        # Print only the slack variables
        f = open(params.OUT_FOLDER + '/network slack variables - '+\
                        params.PS + ' - case ' + params.CASE + '.csv', 'w', encoding = 'utf-8')
        f.write('Var;x\n')
        for v in m.getVars():
            if 'slack' in v.VarName:
                f.write(v.VarName + ';' + str(v.x) + '\n')
        f.close()
        del f

        write_readable_solution(params, thermals, hydros, network,
                                {k: h_g[k].x for k in h_g},
                                {k: t_g[k].x for k in [k for k in t_g if k[-1] >= 0]},
                                {k: s_gen[k].x for k in s_gen},
                                {k: s_load[k].x for k in s_load},
                                {k: s_renewable[k].x for k in s_renewable})

        write_readable_thermal_solution(params, thermals,
                                {k: stup_tg[k].x for k in [k for k in stup_tg if k[-1] >= 0]},
                                {k: stdw_tg[k].x for k in [k for k in stdw_tg if k[-1] >= 0]},
                                {k: disp_tg[k].x for k in [k for k in disp_tg if k[-1] >= 0]},
                                {k: disp_tg_cc_plant[k].x for k in
                                                [k for k in disp_tg_cc_plant if k[-1] >= 0]},
                                {k: trans_stup_tg_cc_plant[k].x for k in
                                                [k for k in trans_stup_tg_cc_plant if k[-1] >= 0]},
                                {k: trans_stdw_tg_cc_plant[k].x for k in
                                                [k for k in trans_stdw_tg_cc_plant if k[-1] >= 0]},
                                {k: t_g_disp[k].x for k in [k for k in t_g_disp if k[-1] >= 0]},
                                {k: t_g[k].x for k in [k for k in t_g if k[-1] >= 0]})

        if len(hydros.RESERVOIR_NAME.values()) > 0:
            write_readable_hydro_solution(params, hydros,
                                {k: vol[k].x for k in [k for k in vol if k[-1] >= 0]},
                                {k: fb[k].x for k in [k for k in fb if k[-1] >= 0]},
                                {k: tr[k].x for k in [k for k in tr if k[-1] >= 0]},
                                {k: gross_head[k].x for k in [k for k in gross_head if k[-1] >= 0]},
                                {k: q[k].x for k in [k for k in q if k[-1] >= 0]},
                                {k: spil[k].x for k in [k for k in spil if k[-1] >= 0]},
                                {k: q_pump[k].x for k in [k for k in q_pump if k[-1] >= 0]},
                                {k: q_bypass[k].x for k in [k for k in q_bypass if k[-1] >= 0]},
                                {k: inflow[k].x for k in [k for k in inflow if k[-1] >= 0]},
                                {k: outflow[k].x for k in [k for k in outflow if k[-1] >= 0]},
                                {k: h_g[k].x for k in [k for k in h_g if k[-1] >= 0]})
    elif m.status in (3, 12):
        m.write('D:\\m-' + params.CASE + '.lp')
        m.write('D:\\m-' + params.CASE + '.rlp')
        m.write('D:\\m-' + params.CASE + '.mps')
        #raise Exception('Post-optimization problem was not solved to optimality')
    else:
        print(f'\nExited with status {m.status}', flush = True)

    return()
