""" Reformulation solver. """
import time
import pyutilib.misc
import pyomo.opt
from pyomo.core import TransformationFactory


@pyomo.opt.SolverFactory.register('pro.robust.reformulation',
                                  doc='Robust reformulation solver.')
class ReformulationSolver(pyomo.opt.OptSolver):
    """
    A solver which identifies the types of constraints and uncertainty sets in
    a robust problem and uses a robust counterpart strategy to solve it.
    """

    def __init__(self, **kwargs):
        kwargs['type'] = 'pro.robust.reformulation'
        pyomo.opt.OptSolver.__init__(self, **kwargs)
        self._metasolver = True

    def _presolve(self, *args, **kwargs):
        self._instance = args[0]
        super()._presolve(*args, **kwargs)

    def _apply_solver(self):
        start_time = time.time()
        instance = self._instance

        # Either:
        transformations = ['pro.robust.ellipsoidal',
                           'pro.robust.polyhedral']
        for transform in transformations:
            xfrm = TransformationFactory(transform)
            xfrm.apply_to(instance)

        # Or:
        # xfrm = TransformationFactory('pro.robust.reformulation')
        # xfrm.apply_to(instance)

        if not self.options.solver:
            solver = 'glpk'
        else:
            solver = self.options.solver

        with pyomo.opt.SolverFactory(solver) as opt:
            self.results = []
            results = opt.solve(self._instance,
                                tee=self._tee,
                                timelimit=self._timelimit)
            self.results.append(results)

        stop_time = time.time()
        self.wall_time = stop_time - start_time
        self.results_obj = self._setup_results_obj()
        #
        # Return the sub-solver return condition value and log
        #
        return pyutilib.misc.Bunch(rc=getattr(opt, '_rc', None),
                                   log=getattr(opt, '_log', None))

        # Stuff to represent results in robust model

    def _postsolve(self):
        self._instance = None
        return self.results_obj

    def _setup_results_obj(self):
        results = pyomo.opt.SolverResults()
        #
        # SOLVER
        #
        solv = results.solver
        solv.name = self.options.subsolver
        solv.wallclock_time = self.wall_time
        cpu_ = []
        for res in self.results:
            if not getattr(res.solver, 'cpu_time', None) is None:
                cpu_.append(res.solver.cpu_time)
        if cpu_:
            solv.cpu_time = sum(cpu_)
        #
        # TODO: detect infeasibilities, etc
        solv.termination_condition = pyomo.opt.TerminationCondition.optimal
        #
        # PROBLEM
        #
        prob = results.problem
        stats = self._instance.statistics
        prob.name = self._instance.name
        prob.number_of_constraints = stats.number_of_constraints
        prob.number_of_variables = stats.number_of_variables
        prob.number_of_binary_variables = stats.number_of_binary_variables
        prob.number_of_integer_variables = stats.number_of_integer_variables
        prob.number_of_continuous_variables =\
            stats.number_of_continuous_variables
        prob.number_of_objectives = stats.number_of_objectives
        #
        # SOLUTION(S)
        #
        self._instance.solutions.store_to(results)
        return results


@pyomo.opt.SolverFactory.register('pro.robust.cuts',
                                  doc='Robust cutting plane solver.')
class CuttingPlaneSolver(pyomo.opt.OptSolver):
    def __init__(self, **kwargs):
        kwargs['type'] = 'pro.robust.cuts'
        pyomo.opt.OptSolver.__init__(self, **kwargs)
        self._metasolver = True

    def _presolve(self, *args, **kwargs):
        self._instance = args[0]
        super()._presolve(*args, **kwargs)

    def _apply_solver(self):
        start_time = time.time()
        instance = self._instance

        xfrm = TransformationFactory('pro.robust.generator')
        xfrm.apply_to(instance)
        tdata = instance._transformation_data['pro.robust.generators']
        generators = tdata.generators

        # Need to set this up for master and sub solver
        if not self.options.solver:
            solver = 'glpk'
        else:
            solver = self.options.solver

        with pyomo.opt.SolverFactory(solver) as opt:
            self.results = []
            feasible = {}
            for g in generators:
                feasible[g.name] = g.add_cut()
            # Keep adding cuts until feasible
            while not all(feasible.values()):
                results = opt.solve(instance,
                                    tee=self._tee,
                                    timelimit=self._timelimit)
                for g in generators:
                    # Only add cut if uncertain constraint isnt feasible
                    if not feasible[g.name]:
                        feasible[g.name] = g.add_cut()
                    self.results.append(results)

        stop_time = time.time()
        self.wall_time = stop_time - start_time
        self.results_obj = self._setup_results_obj()
        #
        # Return the sub-solver return condition value and log
        #
        return pyutilib.misc.Bunch(rc=getattr(opt, '_rc', None),
                                   log=getattr(opt, '_log', None))

        # Stuff to represent results in robust model

    def _postsolve(self):
        self._instance = None
        return self.results_obj