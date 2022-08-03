# -*- coding: utf-8 -*-
"""
@author: Colonetti
"""

from copy import deepcopy
import numpy as np

from network_model.network import add_new_parallel_line

def update_load_and_network(params, network, thermals, hydros, indices_of_buses_to_delete,
                                buses_to_delete, buses_deleted):
    '''Buses and/lines have been deleted. Update the the network object'''

    # The buses to be kept are
    indices_of_buses_to_keep = list(set(range(len(network.BUS_ID)))-set(indices_of_buses_to_delete))

    indices_of_buses_to_keep.sort()
    # Update the load
    network.NET_LOAD = deepcopy(network.NET_LOAD[indices_of_buses_to_keep, :])

    for bus in buses_to_delete:
        del network.BUS_NAME[bus]
        del network.BUS_AREA[bus]
        del network.BUS_SUBSYSTEM_ID[bus]
        del network.BUS_SUBSYSTEM[bus]
        del network.BUS_BASE_V[bus]
        network.BUS_ID.remove(bus)

    network.classify_buses(thermals, hydros)

    buses_deleted += len(buses_to_delete)

    return (buses_deleted)

def del_end_of_line_buses(params, network, buses_no_load_no_gen,\
                                        buses_to_delete, index_of_buses_to_delete, lines_deleted):
    '''Delete buses with no load and no generation connected to a single line'''

    for bus in buses_no_load_no_gen:
        if ((len(network.LINES_FROM_BUS[bus]) + len(network.LINES_TO_BUS[bus])) <= 1) and\
            (len(network.LINKS_FROM_BUS[bus]) + len(network.LINKS_TO_BUS[bus]) == 0):
            buses_to_delete.append(bus)
            index_of_buses_to_delete.append(network.BUS_ID.index(bus))

            for l in (network.LINES_FROM_BUS[bus] + network.LINES_TO_BUS[bus]):
                if not(network.LINE_F_T[l][0] == bus):
                    # Remove the line from the other bus connected to 'bus'
                    network.LINES_FROM_BUS[network.LINE_F_T[l][0]].remove(l)
                elif not(network.LINE_F_T[l][1] == bus):
                    # Remove the line from the other bus connected to 'bus'
                    network.LINES_TO_BUS[network.LINE_F_T[l][1]].remove(l)

                del network.LINE_ID[network.LINE_ID.index(l)]
                del network.LINE_F_T[l]
                del network.LINE_MAX_P[l]
                del network.LINE_EMERG_MAX_P[l]
                del network.LINE_B[l]

                lines_deleted += 1

            del network.LINES_FROM_BUS[bus]
            del network.LINES_TO_BUS[bus]

    return(lines_deleted)

def del_mid_point_buses(params, network, buses_no_load_no_gen,\
                                    buses_to_delete, index_of_buses_to_delete, lines_deleted):
    '''Delete buses with no generation and no load connected only to two lines'''

    for bus in buses_no_load_no_gen:
        if ((len(network.LINES_FROM_BUS[bus]) + len(network.LINES_TO_BUS[bus])) == 2) and\
            (len(network.LINKS_FROM_BUS[bus]) + len(network.LINKS_TO_BUS[bus]) == 0):
            buses_to_delete.append(bus)
            index_of_buses_to_delete.append(network.BUS_ID.index(bus))

            # Add a new transmission line
            buses_of_new_connection = []
            cap, cap_emerg, reactance = 1e12, 1e12, 0

            for l in (network.LINES_FROM_BUS[bus] + network.LINES_TO_BUS[bus]):
                if not(network.LINE_F_T[l][0] == bus) and \
                                            not(network.LINE_F_T[l][0] in buses_of_new_connection):
                    buses_of_new_connection.append(network.LINE_F_T[l][0])
                    # Remove the line from the buses connected to 'bus'
                    network.LINES_FROM_BUS[network.LINE_F_T[l][0]].remove(l)

                elif not(network.LINE_F_T[l][1] == bus) and \
                                            not(network.LINE_F_T[l][1] in buses_of_new_connection):
                    buses_of_new_connection.append(network.LINE_F_T[l][1])
                    # Remove the line from the buses connected to 'bus'
                    network.LINES_TO_BUS[network.LINE_F_T[l][1]].remove(l)

                cap = min(cap, network.LINE_MAX_P[l])
                cap_emerg = min(cap_emerg, network.LINE_EMERG_MAX_P[l])
                reactance += network.LINE_B[l]

                del network.LINE_ID[network.LINE_ID.index(l)]
                del network.LINE_F_T[l]
                del network.LINE_MAX_P[l]
                del network.LINE_EMERG_MAX_P[l]
                del network.LINE_B[l]

                lines_deleted += 1

            # Add the new line. Note that this new line adopts the key l from the last deleted line
            buses_of_new_connection.sort()

            #### Check if connection already exists
            found = False
            for l2 in [l2 for l2 in network.LINES_FROM_BUS[buses_of_new_connection[0]]
                                    if network.LINE_F_T[l2][1] == buses_of_new_connection[1]]:
                # Then the line already exists
                found = True

                network.LINE_B[l2], network.LINE_MAX_P[l2], network.LINE_EMERG_MAX_P[l2] =\
                                add_new_parallel_line(network.LINE_B[l2], network.LINE_MAX_P[l2],
                                                        network.LINE_EMERG_MAX_P[l2],\
                                                        reactance, cap, cap_emerg)
                break

            if not(found):
                network.LINE_ID.append(l)
                network.LINE_F_T[l] = (buses_of_new_connection[0], buses_of_new_connection[1])
                network.LINE_MAX_P[l] = cap
                network.LINE_EMERG_MAX_P[l] = cap_emerg
                network.LINE_B[l] = reactance
                network.LINES_FROM_BUS[buses_of_new_connection[0]].append(l)
                network.LINES_TO_BUS[buses_of_new_connection[1]].append(l)

                lines_deleted -= 1

            del network.LINES_FROM_BUS[bus]
            del network.LINES_TO_BUS[bus]

    return(lines_deleted)

def reduce_network(params, hydros, thermals, network, W_RANK):
    '''Build the DC network model'''

    done, it, buses_deleted, lines_deleted = False, 0, 0, 0

    #### Set of candidate buses to be deleted
    buses_no_load_no_gen = set(network.BUS_ID) - network.GEN_BUSES - network.LOAD_BUSES\
                                - network.RENEWABLE_BUSES - set(network.REF_BUS_ID)

    while not(done):
        it += 1
        buses_to_delete, indices_of_buses_to_delete = [], []

        lines_deleted = del_end_of_line_buses(params, network, buses_no_load_no_gen,\
                                    buses_to_delete, indices_of_buses_to_delete, lines_deleted)

        buses_no_load_no_gen = buses_no_load_no_gen - set(buses_to_delete)

        lines_deleted = del_mid_point_buses(params, network, buses_no_load_no_gen,\
                                    buses_to_delete, indices_of_buses_to_delete, lines_deleted)

        buses_no_load_no_gen = buses_no_load_no_gen - set(buses_to_delete)

        buses_deleted = update_load_and_network(params, network, thermals, hydros,
                                        indices_of_buses_to_delete, buses_to_delete, buses_deleted)
        if len(buses_to_delete) == 0:
            done = True

    if (W_RANK == 0):
        print(f'\n\n\n{it} iterations were performed', flush = True)
        print(f'{buses_deleted} buses and {lines_deleted} lines were removed\n\n\n', flush = True)

    return()

def del_end_of_line_buses_and_reassign_injection(params, network, thermals, hydros,\
            candidate_buses, buses_to_delete, indices_of_buses_to_delete, lines_deleted):
    '''End-of-line buses are those connected to a single power line.
   Delete these buses and move their power injections to the neighbouring bus'''
    for bus in candidate_buses:
        buses_to_delete.append(bus)
        indices_of_buses_to_delete.append(network.BUS_ID.index(bus))

        # The elements connected to the bus to be deleted must be
        # relocated to a new bus
        new_bus = -1e12
        for l in (network.LINES_FROM_BUS[bus] + network.LINES_TO_BUS[bus]):
            if not(network.LINE_F_T[l][0] == bus):
                # Remove the line from the buses connected to 'bus'
                network.LINES_FROM_BUS[network.LINE_F_T[l][0]].remove(l)
                new_bus = network.LINE_F_T[l][0]
            elif not(network.LINE_F_T[l][1] == bus):
                # Remove the line from the buses connected to 'bus'
                network.LINES_TO_BUS[network.LINE_F_T[l][1]].remove(l)
                new_bus = network.LINE_F_T[l][1]

            del network.LINE_F_T[l]
            del network.LINE_MAX_P[l]
            del network.LINE_EMERG_MAX_P[l]
            del network.LINE_B[l]
            network.LINE_ID.remove(l)

            lines_deleted += 1

        del network.LINES_FROM_BUS[bus]
        del network.LINES_TO_BUS[bus]

        #### Remove old bus and add elements to the new bus
        if (bus in network.LOAD_BUSES) or (bus in network.RENEWABLE_BUSES):
            network.NET_LOAD[network.BUS_HEADER[new_bus], :] = np.add(\
                                                network.NET_LOAD[network.BUS_HEADER[new_bus], :],\
                                                network.NET_LOAD[network.BUS_HEADER[bus], :])

        if bus in hydros.UNIT_BUS_ID.values():
            connected_to_old_bus = [u for u in hydros.UNIT_NAME if bus == hydros.UNIT_BUS_ID[u]]
            for u in connected_to_old_bus:
                hydros.UNIT_BUS_ID[u] = new_bus

        if bus in hydros.PUMP_BUS_ID.values():
            connected_to_old_bus = [u for u in hydros.PUMP_NAME if bus == hydros.PUMP_BUS_ID[u]]
            for u in connected_to_old_bus:
                hydros.PUMP_BUS_ID[u] = new_bus

        if bus in thermals.BUS.values():
            connected_to_old_bus = [g for g in thermals.UNIT_NAME if bus == thermals.BUS[g]]
            for g in connected_to_old_bus:
                thermals.BUS[g] = new_bus

    return(lines_deleted)

def remove_end_of_line_buses_with_injections(params, hydros, thermals, network, W_RANK):
    '''Even buses with power injection (either positive or negative) can be removed from the
    network without any damage to the representation as long as the maximum injection is at
    most equal to the capacity of the line connecting such bus to the rest of the network'''

    # Get the minimum and maximum loads of each bus during the planning horizon
    min_load = np.min(network.NET_LOAD[:, 0:params.T], axis = 1)
    max_load = np.max(network.NET_LOAD[:, 0:params.T], axis = 1)

    # Remember that loads (power withdraws) are positive in network.NET_LOAD, while generation
    # in NET_LOAD is negative.

    max_gen_of_bus = {bus: 0 for bus in network.BUS_ID}

    for g in thermals.UNIT_NAME:
        max_gen_of_bus[thermals.BUS[g]] += thermals.MAX_P[g]

    for u in hydros.UNIT_NAME:
        max_gen_of_bus[hydros.UNIT_BUS_ID[u]] += hydros.MAX_P[u]

    for u in hydros.PUMP_NAME:
        max_load[network.BUS_HEADER[hydros.PUMP_BUS_ID[u]]] += hydros.MAX_PUMP_Q[u]*\
                                                                        hydros.PUMP_CONV_RATE[u]
    done, it, buses_deleted, lines_deleted = False, 0, 0, 0

    #### Set of candidate buses to be deleted
    candidate_buses = set()
    for bus in network.BUS_ID:
        if (bus not in network.REF_BUS_ID) and\
            ((len(network.LINES_FROM_BUS[bus]) + len(network.LINES_TO_BUS[bus])) <= 1) and\
            (len(network.LINKS_FROM_BUS[bus]) + len(network.LINKS_TO_BUS[bus]) == 0):
            # if there is a single line connecting bus to the network, and it is not a DC link
            for l in (network.LINES_FROM_BUS[bus] + network.LINES_TO_BUS[bus]):
                if (network.LINE_MAX_P[l] >= (9999/params.POWER_BASE))\
                    or\
                        (abs(max_load[network.BUS_HEADER[bus]]) <= network.LINE_MAX_P[l] and
                        abs(-1*min_load[network.BUS_HEADER[bus]] + max_gen_of_bus[bus])
                                                                        <= network.LINE_MAX_P[l]):
                    # either the load has limitless capacity or its possible most
                    # negative power injection (largest possible load) and most positive
                    # power injection (largest possible generation) are both within its capacity
                    candidate_buses.add(bus)

    while not(done):
        it += 1
        buses_to_delete, indices_of_buses_to_delete = [], []

        #### Delete end-of-line buses
        lines_deleted = del_end_of_line_buses_and_reassign_injection(
                                                    params, network, thermals, hydros,
                                                        candidate_buses, buses_to_delete,
                                                        indices_of_buses_to_delete, lines_deleted)

        candidate_buses = candidate_buses - set(buses_to_delete)

        buses_deleted = update_load_and_network(params, network, thermals, hydros,
                                                indices_of_buses_to_delete,
                                                buses_to_delete, buses_deleted)
        ########################################################################

        #### Delete midpoint buses
        buses_to_delete, indices_of_buses_to_delete = [], []

        buses_no_load_no_gen = set(network.BUS_ID) - network.GEN_BUSES - network.LOAD_BUSES\
                                - network.RENEWABLE_BUSES - set(network.REF_BUS_ID)

        lines_deleted = del_mid_point_buses(params, network, buses_no_load_no_gen,\
                                    buses_to_delete, indices_of_buses_to_delete, lines_deleted)

        buses_deleted = update_load_and_network(params, network, thermals, hydros,
                                                indices_of_buses_to_delete,
                                                buses_to_delete, buses_deleted)
        ########################################################################

        # Get the minimum and maximum loads of each bus during the planning horizon
        min_load = np.min(network.NET_LOAD[:, 0:params.T], axis = 1)
        max_load = np.max(network.NET_LOAD[:, 0:params.T], axis = 1)

        # Remember that loads (power withdraws) are positive in network.NET_LOAD, while generation
        # in NET_LOAD is negative.

        max_gen_of_bus = {bus: 0 for bus in network.BUS_ID}

        for g in thermals.UNIT_NAME:
            max_gen_of_bus[thermals.BUS[g]] += thermals.MAX_P[g]

        for u in hydros.UNIT_NAME:
            max_gen_of_bus[hydros.UNIT_BUS_ID[u]] += hydros.MAX_P[u]

        for u in hydros.PUMP_NAME:
            max_load[network.BUS_HEADER[hydros.PUMP_BUS_ID[u]]] += hydros.MAX_PUMP_Q[u]*\
                                                                        hydros.PUMP_CONV_RATE[u]

        #### Set of candidate buses to be deleted
        candidate_buses = set()
        for bus in network.BUS_ID:
            if (bus not in network.REF_BUS_ID) and\
                ((len(network.LINES_FROM_BUS[bus]) + len(network.LINES_TO_BUS[bus])) <= 1) and\
                (len(network.LINKS_FROM_BUS[bus]) + len(network.LINKS_TO_BUS[bus]) == 0):
                # if there is a single line connecting bus to the network, and it is not a DC link
                for l in (network.LINES_FROM_BUS[bus] + network.LINES_TO_BUS[bus]):
                    if (network.LINE_MAX_P[l] >= (9999/params.POWER_BASE))\
                        or\
                        (abs(max_load[network.BUS_HEADER[bus]]) <= network.LINE_MAX_P[l] and
                        abs(-1*min_load[network.BUS_HEADER[bus]] + max_gen_of_bus[bus])
                                                                        <= network.LINE_MAX_P[l]):
                    # either the load has limitless capacity or its possible most
                    # negative power injection (largest possible load) and most positive
                    # power injection (largest possible generation) are both within its capacity
                        candidate_buses.add(bus)

        if len(candidate_buses) == 0:
            done = True

    if (W_RANK == 0):
        print('\n\n\n')
        print(f'{it} iterations were performed')
        print(f'{buses_deleted} buses and {lines_deleted} lines were removed')
        print('\n\n\n', flush = True)

    return()
