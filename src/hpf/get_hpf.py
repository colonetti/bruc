# -*- coding: utf-8 -*-
"""
@author: Colonetti
"""

import numpy as np
import gurobipy as grbpy
from numpy.lib.function_base import average
from sklearn.linear_model import LinearRegression

def get_planes(points_x, points_y):
    '''For given numpy arrays of x and y points, distributed them over planes and
        get some useful objects'''

    if (max(points_y) > min(points_y)):
        points_x_per_plane = 5      # points x in each plane
        points_y_per_plane = 5      # points y in each plane
    else:
        points_x_per_plane = 2
        points_y_per_plane = 1      # points y in each plane

    if (max(points_y) > min(points_y)):
        y_div = int((points_y.shape[0] - 1)/4)  # Divisions of y
        x_div = int((points_x.shape[0] - 1)/4)  # Divisions of x
    else:
        y_div = 1
        x_div = points_x.shape[0] - 1

    # The hyperplanes
    planes = list(range(x_div*y_div))

    map_to_planes = {(i, j): None for i in range(x_div) for j in range(y_div)}

    planes_of_x_div = {i: [] for i in range(x_div)} # all planes share the same points
    planes_of_y_div = {i: [] for i in range(y_div)} # all planes share the same points

    p = 0
    for j in range(y_div):
        for i in range(x_div):
            map_to_planes[i, j] = p
            planes_of_x_div[i].append(p)
            planes_of_y_div[j].append(p)
            p += 1

    points_x_in_planes = {p: [] for p in planes}    # store the turb-discharge points of each plane
    points_y_in_planes = {p: [] for p in planes}    # store the volume points of each plane

    i = 0
    for qd in range(x_div):
        # get the points in this particular division
        qp_ = []
        for _ in range(points_x_per_plane):
            qp_.append(points_x[i])
            if len(qp_) < points_x_per_plane:
                i += 1
        # now, assign these points to the planes that include this division
        for p in planes_of_x_div[qd]:
            for qp in qp_:
                points_x_in_planes[p].append(qp)

    j = 0
    for vd in range(y_div):
        # get the points in this particular division
        vp_ = []
        for _ in range(points_y_per_plane):
            vp_.append(points_y[j])
            if len(vp_) < points_y_per_plane:
                j += 1
        # now, assign these points to the planes that include this division
        for p in planes_of_y_div[vd]:
            for vp in vp_:
                points_y_in_planes[p].append(vp)

    return(points_x_in_planes, points_y_in_planes, planes)

def min_eq_error(h, hpf_model, params, hydros, points_x, points_y,
                            points_x_in_planes, points_y_in_planes, planes,
                            max_rhs, function_approximated,
                            W_RANK):
    '''Optimization model for finding coefficients of planes that minimize the squared distance
        to given function points.
        Turbine-discharge points must always be the x points
        '''

    assert function_approximated in ('get_power_output_gross_head_turb',
                            'get_power_output_fb_turb_spil'), 'The function to be approximated'+\
                                ' is either get_power_output_gross_head_turb or '+\
                                    'get_power_output_fb_turb_spil'

    additional_plane = function_approximated in ('get_power_output_gross_head_turb',
                                                    'get_power_output_fb_turb_spil')

    all_planes = planes + [max(planes) + 1] if additional_plane else planes

    min_coef_of_turb = max(
                    min(get_power_output_fb_turb_spil(h, hpf_model, max(points_y), 1, 0, W_RANK),
                    get_power_output_fb_turb_spil(
                            h, hpf_model, min(points_y), max(points_x), 0, W_RANK)/max(points_x)),
                        0)

    max_coef_of_turb = min(
                    max(get_power_output_fb_turb_spil(h, hpf_model, max(points_y), 1, 0, W_RANK),
                    get_power_output_fb_turb_spil(
                            h, hpf_model, min(points_y), max(points_x), 0, W_RANK)/max(points_x)),
                        10)*1.5

    max_tries = 2
    count_tries = 1

    m = grbpy.Model("min_sq_error_x_y")

    while m.status != 2 and count_tries <= max_tries:
        # variables for the coefficients of the turbine discharge
        coeff_x = m.addVars(grbpy.tuplelist(all_planes),
                obj = 0,
                lb = min_coef_of_turb,
                ub = max_coef_of_turb,
                vtype = grbpy.GRB.CONTINUOUS, name = "coeff_turb")
        # variables for the coefficients of the reservoir volume
        coeff_y = m.addVars(grbpy.tuplelist([0]),
                obj = 0, lb = hpf_model.AVRG_PROD[h], ub = hpf_model.AVRG_PROD[h],
                vtype = grbpy.GRB.CONTINUOUS, name = "coeff_y")
        for p in set(all_planes) - set([max(planes) + 1]) - set([0]):
            coeff_y[p] = coeff_y[0]

        coeff_y[max(planes) + 1] = m.addVar(
                        obj = 0, lb = 0, ub = 0, vtype = grbpy.GRB.CONTINUOUS, name = "coeff_y")

        # variables for the right-hand sides
        rhs = m.addVars(grbpy.tuplelist(all_planes),
                obj = 0, lb = -0.000000000000000000000000000*max_rhs, ub = max_rhs, vtype = grbpy.GRB.CONTINUOUS, name = "rhs")

        # remember that, without binaries, there is a extra plane to avoid generation when
        # the turbine discharge is zero
        if additional_plane:
            coeff_y[max(planes)+1].lb = 0
            coeff_y[max(planes)+1].ub = 0
            rhs[max(planes)+1].lb = 0
            rhs[max(planes)+1].ub = 0

        obj_func = grbpy.QuadExpr(0)

        # Approximated point
        approx_p = m.addVars(grbpy.tuplelist([(p, i, j)
                                for p in planes for i in range(len(points_x_in_planes[p]))
                                    for j in range(len(points_y_in_planes[p]))]),
                                lb = 0, ub = 15000, vtype = grbpy.GRB.CONTINUOUS, name = "approx_p")

        for p in planes:
            for i in range(len(points_x_in_planes[p])):
                for j in range(len(points_y_in_planes[p])):
                    if function_approximated == 'get_power_output_gross_head_turb':
                        REAL_POINT = get_power_output_gross_head_turb(h, hpf_model,
                                                                    points_y_in_planes[p][j],
                                                                    points_x_in_planes[p][i],
                                                                    W_RANK)
                    elif function_approximated == 'get_power_output_fb_turb_spil':
                        REAL_POINT = get_power_output_fb_turb_spil(h, hpf_model,
                                                                    points_y_in_planes[p][j],
                                                                    points_x_in_planes[p][i],
                                                                    0, W_RANK)

                    # For each point (Q, V), the approximated power is given by
                    m.addConstr(approx_p[p, i, j] == coeff_x[p]*points_x_in_planes[p][i] +
                                                    coeff_x[p]*points_y_in_planes[p][j] + rhs[p])

                    # add the euclidean distance between the approximation and the
                    # real power to the objective function
                    # Note that the constant part, pointsP*pointsP, is not necessary
                    obj_func.add(approx_p[p, i, j]*approx_p[p, i, j]
                                                            - 2*approx_p[p, i, j]*REAL_POINT)

            # Make sure that, on its domain, plane i is dominant, i.e.,
            # it is less than or equal to all other planes
            for p1 in [p_ for p_ in planes if p_ != p]:
                m.addConstr(coeff_x[p]*average(points_x_in_planes[p]) +
                                    coeff_y[p]*average(points_y_in_planes[p]) + rhs[p]
                                        <= coeff_x[p1]*average(points_x_in_planes[p]) +
                                            coeff_y[p1]*average(points_y_in_planes[p]) + rhs[p1])

        # Ensure that the approx is always nonnegative
        for p in planes:
            m.addConstr(coeff_y[p]*min(points_y) + rhs[p] >= 0)

        # When the turbine discharge is zero, so should be the power
        # Create an additional plane that, at all points, is equal to or greater
        # than all other planes. This is a single-dimension plane on the turbine discharge.
        # Thus, when the turbine discharge is zero, the power will also be zero
        if function_approximated == 'get_power_output_gross_head_turb':
            for x in points_x:
                for y in points_y:
                    m.addConstr(coeff_x[max(planes)+1]*x >= get_power_output_gross_head_turb(
                                                                h, hpf_model, y, x, W_RANK))
        elif function_approximated == 'get_power_output_fb_turb_spil':
            for x in points_x:
                for y in points_y:
                    m.addConstr(coeff_x[max(planes)+1]*x >= get_power_output_fb_turb_spil(
                                                                h, hpf_model,
                                                                y,
                                                                x,
                                                                0, W_RANK))
        if additional_plane:
            obj_func.add(coeff_x[max(planes)+1])

        obj_func.add(grbpy.quicksum(-rhs[k] for k in rhs.keys()))

        m.setObjective(obj_func/(max_rhs**2))
        m.setParam('OutputFlag', 0)
        if count_tries == 1:
            m.setParam('Method', 2)
        else:
            m.setParam('Method', 1)
        m.optimize()

        if m.status != 2:
            m.dispose()
            m = grbpy.Model("min_sq_error_x_y")

        count_tries += 1

    return(m, coeff_x, coeff_y, rhs)

def get_linear_approx_fb(h, hpf_model, points_vol, points_fb):
    '''Get a linear approximation of the forebay level through linear regression'''

    if max(points_vol) > min(points_vol):
        model = LinearRegression().fit(points_vol.reshape((-1, 1)), points_fb)

        r_sq = model.score(points_vol.reshape((-1, 1)), points_fb)

        intercept = model.intercept_
        coef = model.coef_
    else:
        intercept = points_fb[0]
        coef = 0.0

    max_error = -1e12

    points_vol_test = np.linspace(min(points_vol), max(points_vol), 100)

    for v in points_vol_test:
        max_error = max(abs((coef*v + intercept) - get_forebay_level(h, hpf_model, v)), max_error)

    return(coef if isinstance(coef, float) else coef[0],
            intercept if isinstance(intercept, float) else intercept[0],
                max_error if isinstance(max_error, float) else max_error[0])

def get_linear_approx_tr(h, hpf_model, points_turb, points_tr):
    '''Get a linear approximation of the tailrace level through linear regression'''

    if points_turb.shape[0] > 1:
        model = LinearRegression().fit(points_turb.reshape((-1, 1)), points_tr)

        r_sq = model.score(points_turb.reshape((-1, 1)), points_tr)

        intercept = model.intercept_
        coef = model.coef_
    else:
        intercept = points_tr[0]
        coef = 0.0

    max_error = -1e12

    points_turb_test = np.linspace(min(points_turb), max(points_turb), 100)

    for q in points_turb_test:
        max_error = max(abs((coef*q + intercept) - get_tailrace_level(h, hpf_model, q)), max_error)

    return(coef if isinstance(coef, float) else coef[0],
            intercept if isinstance(intercept, float) else intercept[0],
                max_error if isinstance(max_error, float) else max_error[0])

def compute_errors(h, hpf_model, hydros, points_turb, planes,
                    coeff_turb, coeff_y, rhs,
                    fb_approx, tr_approx,
                    min_vol, max_vol,
                    function_approximated,
                    W_RANK):
    '''Compute errors of the hydropower function approximation for several points of
        turbine discharge and reservoir volume'''

    assert function_approximated in ('get_power_output_gross_head_turb',
                            'get_power_output_fb_turb_spil'), 'The function to be approximated'+\
                                ' is either get_power_output_gross_head_turb or '+\
                                    'get_power_output_fb_turb_spil'

    fb_is_approx = True
    tr_is_approx = True

    # All points of turbine discharge
    points_turb_test = np.linspace(min(points_turb), max(points_turb), 100)
    # All points of reservoir volume
    #points_vol_test = np.linspace(min(points_vol), max(points_vol), 100)
    points_vol_test = np.linspace(min_vol, max_vol, 100)

    max_error, planes_to_del = -1e12, []

    for p in planes:
        if (len(planes) - len(planes_to_del)) >= 2:
            diff = -1e12
            for q in points_turb_test:
                for v in points_vol_test:
                    if fb_is_approx:
                        fb = fb_approx[0]*v + fb_approx[1]
                    if tr_is_approx:
                        tr = tr_approx[0]*q + tr_approx[1]

                    gross_head = (fb - tr)

                    assert gross_head >= 0, 'Gross head is negative for ' + hydros.RESERVOIR_NAME[h]

                    if function_approximated == 'get_power_output_gross_head_turb':
                        valueEQ1 = (coeff_turb[p]*q + coeff_y[p]*gross_head + rhs[p])

                        valueOthers = min([(coeff_turb[p1]*q +
                                            coeff_y[p1]*gross_head + rhs[p1])
                                            for p1 in set(planes) - {p} - set(planes_to_del)])

                        zero_plane = coeff_turb[max(planes)+1]*q +\
                                        coeff_y[max(planes)+1]*gross_head + rhs[max(planes)+1]

                    elif function_approximated == 'get_power_output_fb_turb_spil':
                        valueEQ1 = (coeff_turb[p]*q + coeff_y[p]*fb + rhs[p])

                        valueOthers = min([(coeff_turb[p1]*q +
                                            coeff_y[p1]*fb + rhs[p1])
                                            for p1 in set(planes) - {p} - set(planes_to_del)])

                        zero_plane = coeff_turb[max(planes)+1]*q +\
                                        coeff_y[max(planes)+1]*fb + rhs[max(planes)+1]


                    diff = max(valueOthers - valueEQ1, diff)

                    REAL_POWER = get_power_output_vol_turb_spil(h, hpf_model, v, q, 0, W_RANK)

                    max_error = max(abs(REAL_POWER - min(valueEQ1, valueOthers, zero_plane)),
                                                                                    max_error)

            if (diff <= 1) and ((len(planes) - len(planes_to_del)) >= 1):
                planes_to_del.append(p)

    planes_to_del.sort(reverse = True)
    for p in planes_to_del:
        del planes[p]

    return(max_error if isinstance(max_error, float) else max_error[0], planes_to_del)

def get_forebay_level(h, hpf_model, vol):
    '''Get forebay level'''
    return(hpf_model.HPF_FB[h]['F0'] + hpf_model.HPF_FB[h]['F1']*(vol) + \
                hpf_model.HPF_FB[h]['F2']*(vol**2) + hpf_model.HPF_FB[h]['F3']*(vol**3)\
                + hpf_model.HPF_FB[h]['F4']*(vol**4))

def get_tailrace_level(h, hpf_model, D):
    '''Get tailrace level as a function of the total outflow
    Note that, depending on the reservoir, the total outflow D relevant
    for the tailrace level might only be composed of the turbine outflow'''
    return(hpf_model.HPF_TR[h]['T0'][0] + hpf_model.HPF_TR[h]['T1'][0]*D + \
            hpf_model.HPF_TR[h]['T2'][0]*(D**2) + hpf_model.HPF_TR[h]['T3'][0]*(D**3)\
            + hpf_model.HPF_TR[h]['T4'][0]*(D**4))

def getPowerLoss(h, hpf_model, vol, Q, S):
    '''Loss of potential power due to tailrace level and head loss'''
    D = Q + S
    if (hpf_model.HEAD_LOSS_TYPE[h] == 1):
        grossHead = get_forebay_level(h, hpf_model, vol) - get_tailrace_level(h, hpf_model, D)
        headLoss = grossHead*(hpf_model.HEAD_LOSS[h]/100)
    elif (hpf_model.HEAD_LOSS_TYPE[h] == 2):
        headLoss =hpf_model.HEAD_LOSS[h]

    return(hpf_model.AVRG_PROD[h]*Q*(get_tailrace_level(h, hpf_model, D) + headLoss))

def getPotentialPower(h, hpf_model, vol, Q):
    '''Power if the tailrace level is ignored'''
    return(hpf_model.AVRG_PROD[h]*Q*get_forebay_level(h, hpf_model, vol))

def get_power_output_vol_turb_spil(h, hpf_model, vol, q, spil, W_RANK):
    '''For volume vol in hm3, turbine discharge q in m3/s and spillage spil in m3/s,
        get the power output in MW for plant h'''
    d = q + spil   # total outflow
    gross_head = get_forebay_level(h, hpf_model, vol) - get_tailrace_level(h, hpf_model, d)

    if (hpf_model.HEAD_LOSS_TYPE[h] == 1):
        net_head = gross_head*(1 - hpf_model.HEAD_LOSS[h]/100)
    elif (hpf_model.HEAD_LOSS_TYPE[h] == 2):
        net_head = gross_head - hpf_model.HEAD_LOSS[h]

    return(hpf_model.AVRG_PROD[h]*q*net_head)

def get_power_output_fb_turb_spil(h, hpf_model, fb, q, spil, W_RANK):
    '''For forebay level fb in m, turbine discharge q in m3/s and spillage spil in m3/s,
        get the power output in MW for plant h'''
    d = q + spil   # total outflow
    gross_head = fb - get_tailrace_level(h, hpf_model, d)

    if (hpf_model.HEAD_LOSS_TYPE[h] == 1):
        net_head = gross_head*(1 - hpf_model.HEAD_LOSS[h]/100)
    elif (hpf_model.HEAD_LOSS_TYPE[h] == 2):
        net_head = gross_head - hpf_model.HEAD_LOSS[h]

    return(hpf_model.AVRG_PROD[h]*q*net_head)

def get_power_output_fb_tr_turb(h, hpf_model, fb, tr, q, W_RANK):
    '''For forebay level fb and tailrace level tr, and turbine discharge q,
            compute the power output'''

    gross_head = fb - tr

    if (hpf_model.HEAD_LOSS_TYPE[h] == 1):
        net_head = gross_head*(1 - hpf_model.HEAD_LOSS[h]/100)
    elif (hpf_model.HEAD_LOSS_TYPE[h] == 2):
        net_head = gross_head - hpf_model.HEAD_LOSS[h]

    return(hpf_model.AVRG_PROD[h]*q*net_head)

def get_power_output_gross_head_turb(h, hpf_model, gross_head, q, W_RANK):
    '''For gross head gross_head, and turbine discharge q,
            compute the power output'''

    if (hpf_model.HEAD_LOSS_TYPE[h] == 1):
        net_head = gross_head*(1 - hpf_model.HEAD_LOSS[h]/100)
    elif (hpf_model.HEAD_LOSS_TYPE[h] == 2):
        net_head = gross_head - hpf_model.HEAD_LOSS[h]

    return(hpf_model.AVRG_PROD[h]*q*net_head)

def write_3Dim_HPF(params, hydros, filename, hyperplanes, hpfs_to_generate):
    '''Write the three-dimensional HPF'''
    f = open(filename, 'w', encoding = 'ISO-8859-1')
    f.write('<BEGIN>\n')
    i = 0
    for hpf in hpfs_to_generate:
        f.write('<Hydro>\n')
        f.write('ID;Name\n')
        f.write(str(hpf[1]) + ';' + hydros.RESERVOIR_NAME[hpf[1]] + '\n')
        f.write('<HPF>\n')
        f.write('coeff(in MW/(m3/s))*Q;coeff(in MW/(hm3))*V')
        f.write(';coeff(in MW/(m3/s))*S')
        f.write(';const in MW\n')
        for c in range(len(hyperplanes[i])):
            f.write(str(hyperplanes[i][c][0]) + ';' \
                    + str(hyperplanes[i][c][1]) +\
                    ';' + str(hyperplanes[i][c][2]) +\
                    ';' + str(hyperplanes[i][c][3]) +\
                    '\n')
        f.write('</HPF>\n')
        f.write('</Hydro>\n')
        i += 1
    f.write('</END>')
    f.close()
    del f

    return()

def write_tr_approx(params, hydros, filename, tr_approx):
    '''Write the linear approximation of the tailrace-level function'''
    f = open(filename, 'w', encoding = 'ISO-8859-1')
    f.write('<BEGIN>\n')
    f.write('ID;Name;outflow coeff (in m/(m3/s));constant (in m);maximum error (in m)\n')
    for h in tr_approx:
        f.write(str(h) + ';' + hydros.RESERVOIR_NAME[h] + ';')
        f.write(str(tr_approx[h][0]) + ';' \
                + str(tr_approx[h][1]) +\
                ';' + str(tr_approx[h][2]) +\
                '\n')
    f.write('</END>')
    f.close()
    del f

    return()

def write_fb_approx(params, hydros, filename, fb_approx):
    '''Write the linear approximation of the forebay-level function'''
    f = open(filename, 'w', encoding = 'ISO-8859-1')
    f.write('<BEGIN>\n')
    f.write('ID;Name;reservoir volume coeff (in m/hm3);constant (in m);maximum error (in m)\n')
    for h in fb_approx:
        f.write(str(h) + ';' + hydros.RESERVOIR_NAME[h] + ';')
        f.write(str(fb_approx[h][0]) + ';' \
                + str(fb_approx[h][1]) +\
                ';' + str(fb_approx[h][2]) +\
                '\n')
    f.write('</END>')
    f.close()
    del f

    return()

def points_turb_and_spil(params, hydros, hpf_model, h, W_RANK, hpf_min_vol,
                                hpf_max_turb, hpf_min_turb):
    '''Get turbine discharge and spillage points'''

    max_spil_HPF = hpf_model.MAX_SPIL_HPF[h]
    spil_ref = max_spil_HPF   # Maximum spillage for which the power loss does not become negative

    if hydros.INFLUENCE_OF_SPIL[h] and (max_spil_HPF > 0):
        found = False
        while not(found):
            if ((get_power_output_vol_turb_spil(h, hpf_model, hpf_min_vol, hpf_max_turb,
                                                spil_ref, W_RANK) > 0)\
                and (getPowerLoss(h, hpf_model, hpf_min_vol, hpf_max_turb, spil_ref) > 0))\
                and (getPowerLoss(h, hpf_model, hpf_min_vol, hpf_max_turb, spil_ref) >=\
                        getPowerLoss(h, hpf_model, hpf_min_vol, hpf_max_turb, 0.95*spil_ref))\
                and (get_tailrace_level(h, hpf_model,\
                        spil_ref + hpf_max_turb) >= get_tailrace_level(h, hpf_model,\
                                                                0.95*spil_ref + hpf_max_turb)):
                found = True
            else:
                spil_ref = 0.95*spil_ref
                if (spil_ref <= 1e-1):
                    found = True
                    spil_ref = 0

        points_spil = np.linspace(0, max_spil_HPF, num = hpf_model.N_SPIL_POINTS[h])
    else:
        points_spil = np.linspace(0, 0, num = 1)

    return(max_spil_HPF, points_spil)


def points_turb_and_vol(params, hydros, h, hpf_model):
    '''Get the turbine discharge and reservoir volume points'''

    hpf_min_vol = max(hydros.MIN_VOL[h], hydros.V_0[h]*(1-(hpf_model.V_RANGE[h]/100)))
    hpf_max_vol = min(hydros.MAX_VOL[h], hydros.V_0[h]*(1+(hpf_model.V_RANGE[h]/100)))

    hpf_min_turb = 0
    hpf_max_turb =sum([hydros.MAX_Q[u] for u in hydros.UNIT_NAME if hydros.UNIT_RESERVOIR_ID[u]==h])

    points_turb = np.round(np.linspace(hpf_min_turb,hpf_max_turb, num=hpf_model.N_TURB_POINTS[h]),2)

    if ((hpf_max_vol - hpf_min_vol) < 1) or \
        (abs(hpf_model.HPF_FB[h]['F1']) + abs(hpf_model.HPF_FB[h]['F2'])\
                + abs(hpf_model.HPF_FB[h]['F3']) + abs(hpf_model.HPF_FB[h]['F4']) == 0):
        # either range is too small or the forebay level is constant
        # (only the F0 component is not zero). in either case, use the average
        points_vol = np.round(np.array([0.5*(hpf_min_vol + hpf_max_vol)], dtype = 'd'), 2)
    else:
        points_vol = np.round(np.linspace(hpf_min_vol, hpf_max_vol,
                                        num = hpf_model.N_VOL_POINTS[h]), 2)

    return(points_turb, points_vol)

def build_3DHPF(params, hydros, h, hpf_hyperplanes, fb_approx, tr_approx,
                W_RANK, hpf_model, hpf_index):
    '''Create a threedimensional model for the HPF'''

    points_turb, points_vol = points_turb_and_vol(params, hydros, h, hpf_model)

    max_spil_HPF, points_spil = points_turb_and_spil(params, hydros, hpf_model, h, W_RANK,
                                                min(points_vol),
                                                max(points_turb), min(points_turb))

    points_fb = np.array([get_forebay_level(h, hpf_model, v) for v in points_vol], dtype = 'd')

    fb_approx[h][0], fb_approx[h][1], fb_approx[h][2] = get_linear_approx_fb(h, hpf_model,
                                                                            points_vol, points_fb)

    points_fb = np.array([0.5*(max(points_fb) - min(points_fb)) + min(points_fb),
                        0.5*(max(points_fb) - min(points_fb)) + min(points_fb)], dtype = 'd')

    if hydros.INFLUENCE_OF_SPIL[h]:
        max_outflow = max(points_turb) + max(points_spil)
        while (get_tailrace_level(h, hpf_model, max_outflow) <\
                            get_tailrace_level(h, hpf_model, max_outflow*0.95)) or\
                (get_tailrace_level(h, hpf_model, max_outflow) > min(points_fb)):
            max_outflow = max_outflow*0.95
        points_outflow = np.linspace(min(points_turb), max_outflow, 100)
    else:
        points_outflow = points_turb

    points_tr = np.array([get_tailrace_level(h, hpf_model, outflow) for outflow in points_outflow],
                                                                                    dtype = 'd')

    tr_approx[h][0], tr_approx[h][1], tr_approx[h][2] = get_linear_approx_tr(h, hpf_model,
                                                                        points_outflow, points_tr)

    function_approximated = 'get_power_output_fb_turb_spil'

    points_x_in_planes, points_y_in_planes, planes = get_planes(points_turb, points_fb)

    m, coeff_turb, coeff_y, rhs = min_eq_error(h, hpf_model, params, hydros,
                                points_turb, points_fb,
                                points_x_in_planes, points_y_in_planes, planes,
                                sum([hydros.MAX_P[u] for u in hydros.UNIT_NAME
                                    if hydros.UNIT_RESERVOIR_ID[u]==h])*params.POWER_BASE,
                                function_approximated,
                                W_RANK)

    if m.status == 2:
        # coefficients of the turbine discharge
        coeff_turb_x = {k: coeff_turb[k].x for k in coeff_turb.keys()}
        # coefficients of y
        coeff_y_x = {k: coeff_y[k].x for k in coeff_y.keys()}
        # right-hand sides
        rhs_x = {k: rhs[k].x for k in rhs.keys()}

        max_error, planes_to_del = compute_errors(h, hpf_model, hydros, points_turb, planes,
                                    coeff_turb_x, coeff_y_x, rhs_x,
                                    fb_approx[h], tr_approx[h], min(points_vol), max(points_vol),
                                    function_approximated,
                                    W_RANK)

        print(f'{hydros.RESERVOIR_NAME[h]}:\t\t\t\t\t{max_error:.4f}' +\
                                                        f'\t{len(planes_to_del)}\t{len(planes)}')


        coeff_turb_last = np.array([coeff_turb_x[k] for k in coeff_turb_x.keys()
                                                        if not(k in planes_to_del)],dtype='d')
        coeff_y_last = np.array([coeff_y_x[k] for k in coeff_y_x.keys()
                                                        if not(k in planes_to_del)], dtype = 'd')
        rhs_last = np.array([rhs_x[k] for k in rhs_x.keys() if not(k in planes_to_del)], dtype='d')
        spil_last = np.array([0 for k in rhs_x.keys() if not(k in planes_to_del)], dtype = 'd')

        m.dispose()

        # Include the spillage in the hyperplanes
        if hydros.INFLUENCE_OF_SPIL[h] and (max_spil_HPF > 0):

            counter = 0
            for p in planes:
                m  = grbpy.Model("min_sq_error_spillage")
                coeff_spil = m.addVar(lb = - 10, ub = -hpf_model.AVRG_PROD[h]*tr_approx[h][0],
                                        vtype = grbpy.GRB.CONTINUOUS, name = "coeff_spil")

                # Approximated power
                approx_p = m.addVars(grbpy.tuplelist([(k, i, j)
                                            for k in range(points_spil.shape[0])
                                                for i in range(len(points_x_in_planes[p]))
                                                    for j in range(len(points_y_in_planes[p]))]),
                                                        lb = 0, ub = 15000,
                                                            vtype = grbpy.GRB.CONTINUOUS,
                                                                name = "approx_p")

                objFunc = grbpy.QuadExpr(0)

                for k in range(points_spil.shape[0]):
                    spil = points_spil[k]
                    for i in range(len(points_x_in_planes[p])):
                        for j in range(len(points_y_in_planes[p])):
                            if function_approximated == 'get_power_output_gross_head_turb':
                                raise NotImplementedError()

                            if function_approximated == 'get_power_output_fb_turb_spil':
                                REAL_POWER = get_power_output_fb_turb_spil(h, hpf_model,
                                                        points_y_in_planes[p][j],
                                                        points_x_in_planes[p][i], spil, W_RANK)

                            # Approx power
                            m.addConstr(
                                approx_p[k, i, j] == coeff_turb_x[p]*points_x_in_planes[p][i]+
                                                        coeff_y_x[p]*points_y_in_planes[p][j] +
                                                        rhs_x[p] + coeff_spil*spil)
                            m.addConstr(
                                coeff_turb_x[p]*points_x_in_planes[p][i] +
                                                        coeff_y_x[p]*points_y_in_planes[p][j] +
                                                        rhs_x[p] + coeff_spil*spil >= 0)

                            objFunc.add(approx_p[k, i, j]*approx_p[k, i, j]
                                                                - 2*approx_p[k, i, j]*REAL_POWER)

                m.setObjective(objFunc)
                m.setParam('OutputFlag', 0)
                m.optimize()

                if m.status == 2:
                    spil_last[counter] = coeff_spil.x if abs(coeff_spil.x) >= 1e-4 else 0

                m.dispose()

                counter += 1

    else:
        raise Exception('The model was not solved to optimality')

    for i in range(coeff_turb_last.shape[0]):
        hpf_hyperplanes[hpf_index].append([coeff_turb_last[i], coeff_y_last[i],
                                                        spil_last[i], rhs_last[i]])

    return()
