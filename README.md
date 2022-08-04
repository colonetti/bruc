# bruc
# (Br)azilian (u)nit (c)ommitment 

Real unit-commitment data is hard to come by. System operators are generally secretive about the data used for building their unit-commitment (UC) problems. Even when data is available, it is sometimes difficult to read, especially if one is not deeply familiar with the data-format used and the problem itself.

As a consequence of this lack of real data, researchers usually resort to synthetic systems, which might not accurately represent the difficulties of a real UC.

Thus, this Python package converts real input data used by the Brazilian Independent System Operator (ISO) for the UC into more friendly formats and builds the associated UC with gurobipy in an effort to reduce the gap between industry UCs and academic UCs. The result is a collection of large-scale mixed-integer linear programming problems of UC instances with more than 7,000 buses, 10,000 transmission lines, 300 thermal generating units, and 700 hydro generating units.

Although the UC built with bruc is not exactly the one solved by the Brazilian ISO, it has all the components that make it a challenging optimization problem:

- Binary variables 
- Network representation
- Hydro constraints

The optimization model built with bruc is a mixed-integer linear programming (MILP) problem and it can be divided into three main components:

- Thermal model
- Hydro model 
- Network model

# Thermal model
Includes all constraints of the thermal generating units generally used in UC.
- Ramps
- Start-up and shut-down trajectories
- Minimum up and minimum down times
- Combined-cycle operation

# Hydro model
- Reservoir volume, turbine discharge, spillage, bypass discharges, pumping operation
- Linear approximations of the forebay and tailrace levels
- Piecewise linear approximation of the hydropower function (on forebay level, turbine discharge and spillage)
- Spatial coupling 
- Pumping units
- Cost-to-go function
- Status of the plant/unit

The last component basically determines how the forbidden zones of operation are modelled. Currently, we have four options: no hydro binaries, aggr, indv, zones.

*no hydro binaries*:  forbidden zones are neglected. No binary variable is used in the hydro model.

*aggr*:               a single binary variable is used for each hydro plant. It models the first forbidden zone of turbine discharge and generation.

*indv*:               a binary variable is used for each hydro generating unit to model its lower and upper limits on turbine discharge and generation.

*zones*:              is equivalent to *indv*, however, instead of explicitly including one binary variable for each hydro generating unit, it includes one binary variable for each operating zone (as oppose to forbidden zone) of each group of identical hydro generating units (by identical, we mean units with exactly the same operational limits connected to the same bus).

We illustrate below the piecewise linear approximation of the hydropower function, the linear approximations of the forebay level and tailrace level, and the main difference of hydro models *no hydro binaries*, *aggr*, *indv*, *zones*. 

The variables are: $q_{(h, 1)}$, turbine discharge of hydro generating unit $1$ of $h$; $q_{(h, 2)}$ turbine discharge of unit 2; $s_h$, spillage; $fb_h$ forebay level of the plant; $hg_{(h, 1)}$, $hg_{(h, 2)}$, power outputs of units $1$ and $2$; $v_h$, reservoir volume. The 'pieces' of the piecewise linear approximation are indexed by $i \in I_h$. The variables' coefficients and the constants are given in uppercase $C$. If the hydro generating unit $1$ is operating, i.e., it is committed (it is on), then its turbine discharge must be within the closed interval $\[{Q}^{min}, Q^{max}\]$, and its generation within $\[{HG}^{min}, HG^{max}\]$. Hydro unit $2$ has these same limits and it is also connected to the same bus as $1$. Further assume that these limits are such that, when looking at the total turbine discharge and total generation of the plant, the plant has a single operating zone: $\[{Q}^{min}, 2 \cdot Q^{max}\]$ and $\[{HG}^{min}, 2 \cdot HG^{max}\]$. Hence, the model is as follows.

$$ fb_h - C^{v,fb} \cdot v_h - C^{const,fb} = 0 $$

$$ tr_h - C^{q,tr} \cdot (q_{(h, 1} + q_{(h, 2} + s_h) - C^{const,tr} = 0 $$

$$ hg_{(h, 1)} + hg_{(h, 2)} - C_{h,i}^{fb,hpf} \cdot fb_h - C_{h,i}^{q,hpf} \cdot (q_{(h, 1)} + q_{(h, 2)}) - C_{h,i}^{s,hpf} \cdot s_h - C_{h,i}^{const,hpf} \leq 0 \qquad \forall i \in I_h $$

| no hydro binaries                                         | aggr                                                                                  | indv  | zones |
| :-----:                                                   | :-:                                                                                   | :-:               | :-: |
| $0 \leq q_{(h, 1)} + q_{(h, 2)}   \leq  2 \cdot Q^{max} $ | $Q^{min} \cdot u_h \leq q_{(h, 1)} + q_{(h, 2)}   \leq  2 \cdot Q^{max} \cdot u_h $   | $Q^{min} \cdot u_{(h,1)} \leq q_{(h, 1)} \leq Q^{max} \cdot u_{(h,1)} $, <br /> $Q^{min} \cdot u_{(h,2)} \leq q_{(h, 2)} \leq Q^{max} \cdot u_{(h,2)} $ |   $Q^{min} \cdot u_{h,zone} \leq q_{(h, 1)} + q_{(h, 2)}   \leq  2 \cdot Q^{max} \cdot u_{h,zone} $  |
| $0 \leq hg_{(h, 1)} + hg_{(h, 2)} \leq  2 \cdot HG^{max}$ | $HG^{min} \cdot u_h \leq hg_{(h, 1)} + hg_{(h, 2)} \leq  2 \cdot HG^{max} \cdot u_h $ | $HG^{min} \cdot u_{(h,1)} \leq hg_{(h, 1)} \leq HG^{max} \cdot u_{(h,1)} $, <br /> $HG^{min} \cdot u_{(h,2)} \leq hg_{(h, 2)} \leq HG^{max} \cdot u_{(h,2)} $            |   $HG^{min} \cdot u_{h,zone} \leq hg_{(h, 1)} + hg_{(h, 2)} \leq  2 \cdot HG^{max} \cdot u_{h,zone} $  |

where $u$ are additional binary variables. In this simple example, *aggr* and *zones* are equivalent. However, this is generally not true, especially if the plant has many units and their lower and upper limits are close. 

# Network model
We use the common DC representation of the network.

It is well known that, in such representations, many network constraints are actually redundant: they are not binding in any feasible solution of the problem. Thus, these constraints can be safely removed from the model without altering the feasible set. The problem, of course, is identifying these constraints in a timely manner. Luckily, some of them are very easy to find. Consider the 7-bus network below in which buses with nonzero net power injections are given in red, while buses with no net power injections, i.e., there are no loads or generation facilities connected to them, are given in blue. Here, by power injection, we mean any power withdraw from loads or power insertion by generation facilities.

<a href="url"><img src="https://github.com/colonetti/bruc/blob/main/images/example.jpg" align="right" width="480" ></a>

In this simple illustration, note that if the largest possible power injection at Bus 1 is no more than the capacity of Line 1, then it is safe to say that Line 1's capacity cannot possibly be violated by any feasible DC power flow for this network. Moreover, because Bus 1 is a 'end-of-line' bus (it is connected to the rest of the network by a single line), then any nonzero power injection at Bus 1 must be met by a corresponding nonzero power injection of the same magnitude and oppose sign at Bus 5. Therefore, we can actually remove from this network both Line 1 and Bus 1 and reallocate any load or generation at Bus 1 to Bus 5. A simpler case is that of Bus 4, since it has no load and no generation, its net power injection is necessarily 0. Consequently, power flowing through Line 5 necessarily also flows through Line 4. Thus, these two lines can be combined into a single one, resulting in the removal of one bus and one line from the network.

As simple as these steps are, they can easily identify thousands of unnecessary buses and lines, significantly reducing the problem size. Note, however, that it may or may not be reflected in speed-ups in solution times because the optimization solver itself might be able to identify these redundant constraints.

# Overview of the optimization model

For all cases, the planning horizon contains 48 periods of 30 minutes. The number of constraints and variables slightly varies with the test case used and with the model chosen for the operation of the hydro plants, an average model size is given below for case DS_ONS_012022_RV1D14 with no binary variables for the hydro generating units (no hydro binaries).

| Constraints | Continuous variables  | Binary variables  |
| :-----:     | :-:                   | :-:               |
| 687,653     | 714,145               | 55,440            |

Choosing to include binary variables for the hydro units significantly increases the difficulty of the model, although the number of additional binary variables might not reflect it. We summarize below the number of additional variables included in the model for each of the hydro models.

| Hydro model           | Additional binary variables   | 
| :-----:               | :-:                           | 
| no hydro binaries     | 0                             | 
| aggr                  | 7,200                         | 
| indv                  | 35,088                        | 
| zones                 | 17,568                        | 

Currently, we have 75 cases taken from early February 2021 up to late July 2022.

