import pyutilib.th as unittest
import pyomo.environ as pe
import pro.examples
import pro
from pro.reformulate import (EllipsoidalTransformation,
                             PolyhedralTransformation)
from pyomo.opt import check_available_solvers

solvers = check_available_solvers('gurobi')


class TestReformulation(unittest.TestCase):
    @unittest.skipIf('gurobi' not in solvers,
                     'gurobi not available')
    def test_polyhedral(self):
        m = pro.examples.Knapsack()
        m.w.uncset = m.P
        self.assertTrue(m.P.is_polyhedral())
        self.assertTrue(m.Plib.is_polyhedral())
        self.assertFalse(m.E.is_polyhedral())
        self.assertFalse(m.Elib.is_polyhedral())
        t = PolyhedralTransformation()
        t.apply_to(m)
        solver = pe.SolverFactory('gurobi')
        solver.solve(m)
        self.assertEqual(m.value(), 19.)

    @unittest.skipIf('gurobi' not in solvers,
                     'gurobi not available')
    def test_polyhedral_lib(self):
        m = pro.examples.Knapsack()
        m.w.uncset = m.Plib
        t = PolyhedralTransformation()
        t.apply_to(m)
        solver = pe.SolverFactory('gurobi')
        solver.solve(m)
        self.assertEqual(m.value(), 19.)

    def test_polyhedral_cons_lb(self):
        m = pe.ConcreteModel()
        m.x = pe.Var(range(2))
        m.P = pro.UncSet()
        m.w = pro.UncParam(range(2), nominal=(1, 2), uncset=m.P)
        m.P.cons = pe.ConstraintList()
        m.P.cons.add(pe.inequality(0.5, m.w[0], 1.5))
        m.P.cons.add(pe.inequality(1.5, m.w[1], 2.5))

        expr = pe.sum_product(m.w, m.x)
        m.cons = pe.Constraint(expr=2 <= expr)
        m.obj = pe.Objective(expr=m.x[0], sense=pe.minimize)
        t = pro.PolyhedralTransformation()
        t.apply_to(m)
        self.assertFalse(m.cons.active)
        self.assertTrue(hasattr(m, 'cons_counterpart_lower'))

    def test_polyhedral_cons_ub(self):
        m = pe.ConcreteModel()
        m.x = pe.Var(range(2))
        m.P = pro.UncSet()
        m.w = pro.UncParam(range(2), nominal=(1, 2), uncset=m.P)
        m.P.cons = pe.ConstraintList()
        m.P.cons.add(pe.inequality(0.5, m.w[0], 1.5))
        m.P.cons.add(pe.inequality(1.5, m.w[1], 2.5))

        expr = pe.sum_product(m.w, m.x)
        m.cons = pe.Constraint(expr=expr <= 2)
        m.obj = pe.Objective(expr=m.x[0], sense=pe.maximize)
        t = pro.PolyhedralTransformation()
        t.apply_to(m)
        self.assertFalse(m.cons.active)
        self.assertTrue(hasattr(m, 'cons_counterpart_upper'))

    def test_polyhedral_obj_min(self):
        m = pe.ConcreteModel()
        m.x = pe.Var(range(2))
        m.P = pro.UncSet()
        m.w = pro.UncParam(range(2), nominal=(1, 2), uncset=m.P)
        m.P.cons = pe.ConstraintList()
        m.P.cons.add(pe.inequality(0.5, m.w[0], 1.5))
        m.P.cons.add(pe.inequality(1.5, m.w[1], 2.5))

        expr = pe.sum_product(m.w, m.x)
        m.obj = pe.Objective(expr=expr, sense=pe.minimize)
        m.cons = pe.Constraint(expr=pe.quicksum(m.x[i] for i in m.x) >= 4)
        t = pro.PolyhedralTransformation()
        t.apply_to(m)
        self.assertFalse(m.obj.active)
        self.assertTrue(hasattr(m, 'obj_counterpart'))
        self.assertTrue(hasattr(m, 'obj_new'))
        self.assertIs(m.obj_new.sense, pe.minimize)

    def test_polyhedral_obj_max(self):
        m = pe.ConcreteModel()
        m.x = pe.Var(range(2))
        m.P = pro.UncSet()
        m.w = pro.UncParam(range(2), nominal=(1, 2), uncset=m.P)
        m.P.cons = pe.ConstraintList()
        m.P.cons.add(pe.inequality(0.5, m.w[0], 1.5))
        m.P.cons.add(pe.inequality(1.5, m.w[1], 2.5))

        expr = pe.sum_product(m.w, m.x)
        m.obj = pe.Objective(expr=expr, sense=pe.maximize)
        m.cons = pe.Constraint(expr=pe.quicksum(m.x[i] for i in m.x) <= 4)
        t = pro.PolyhedralTransformation()
        t.apply_to(m)
        self.assertFalse(m.obj.active)
        self.assertTrue(hasattr(m, 'obj_counterpart'))
        self.assertTrue(hasattr(m, 'obj_new'))
        self.assertIs(m.obj_new.sense, pe.maximize)

    @unittest.skipIf('gurobi' not in solvers,
                     'gurobi not available')
    def test_ellipsoidal(self):
        m = pro.examples.Knapsack()
        m.w.uncset = m.E
        self.assertFalse(m.P.is_ellipsoidal())
        self.assertFalse(m.Plib.is_ellipsoidal())
        self.assertTrue(m.E.is_ellipsoidal())
        self.assertTrue(m.Elib.is_ellipsoidal())
        t = EllipsoidalTransformation()
        t.apply_to(m)
        solver = pe.SolverFactory('gurobi')
        solver.options['NonConvex'] = 2
        solver.solve(m)
        self.assertEqual(m.value(), 25.)

    @unittest.skipIf('gurobi' not in solvers,
                     'gurobi not available')
    def test_ellipsoidal_lib(self):
        m = pro.examples.Knapsack()
        m.w.uncset = m.Elib
        t = EllipsoidalTransformation()
        t.apply_to(m)
        solver = pe.SolverFactory('gurobi')
        solver.options['NonConvex'] = 2
        solver.solve(m)
        self.assertEqual(m.value(), 25.)

    def test_ellipsoidal_cons_lb(self):
        m = pe.ConcreteModel()
        m.x = pe.Var(range(2))
        m.U = pro.UncSet()
        m.w = pro.UncParam(range(2), nominal=(1, 2), uncset=m.U)
        expr = ((m.w[0] - 1)**2
                + 0.1*(m.w[0] - 1)*(m.w[1] - 2)
                + (m.w[1] - 2)**2
                <= 0.1)
        m.U.cons = pe.Constraint(expr=expr)

        expr = pe.sum_product(m.w, m.x)
        m.cons = pe.Constraint(expr=2 <= expr)
        m.obj = pe.Objective(expr=m.x[0], sense=pe.minimize)
        t = pro.EllipsoidalTransformation()
        t.apply_to(m)
        self.assertFalse(m.cons.active)
        self.assertTrue(hasattr(m, 'cons_counterpart_lower'))

    def test_ellipsoidal_objective_min(self):
        m = pe.ConcreteModel()
        m.x = pe.Var(range(2))
        m.U = pro.UncSet()
        m.w = pro.UncParam(range(2), nominal=(1, 2), uncset=m.U)
        expr = ((m.w[0] - 1)**2
                + 0.1*(m.w[0] - 1)*(m.w[1] - 2)
                + (m.w[1] - 2)**2
                <= 0.1)
        m.U.cons = pe.Constraint(expr=expr)

        expr = pe.sum_product(m.w, m.x)
        m.obj = pe.Objective(expr=expr, sense=pe.minimize)
        m.cons = pe.Constraint(expr=pe.quicksum(m.x[i] for i in m.x) >= 4)
        t = pro.EllipsoidalTransformation()
        t.apply_to(m, root=False)
        self.assertFalse(m.obj.active)
        self.assertTrue(hasattr(m, 'obj_counterpart'))
        self.assertTrue(hasattr(m, 'obj_padding'))
        self.assertTrue(hasattr(m, 'obj_det'))
        self.assertIs(m.obj_counterpart.sense, pe.minimize)

    def test_ellipsoidal_objective_max(self):
        m = pe.ConcreteModel()
        m.x = pe.Var(range(2))
        m.U = pro.UncSet()
        m.w = pro.UncParam(range(2), nominal=(1, 2), uncset=m.U)
        expr = ((m.w[0] - 1)**2
                + 0.1*(m.w[0] - 1)*(m.w[1] - 2)
                + (m.w[1] - 2)**2
                <= 0.1)
        m.U.cons = pe.Constraint(expr=expr)

        expr = pe.sum_product(m.w, m.x)
        m.obj = pe.Objective(expr=expr, sense=pe.maximize)
        m.cons = pe.Constraint(expr=pe.quicksum(m.x[i] for i in m.x) <= 4)
        t = pro.EllipsoidalTransformation()
        t.apply_to(m, root=False)
        self.assertFalse(m.obj.active)
        self.assertTrue(hasattr(m, 'obj_counterpart'))
        self.assertTrue(hasattr(m, 'obj_det'))
        self.assertTrue(hasattr(m, 'obj_padding'))
        self.assertIs(m.obj_counterpart.sense, pe.maximize)

    def test_ellipsoidal_lib_root(self):
        m = pro.examples.Knapsack()
        m.w.uncset = m.Elib
        t = EllipsoidalTransformation()
        t.apply_to(m, root=True)
        solver = pe.SolverFactory('gams')
        solver.options['solver'] = 'Baron'
        solver.solve(m)
        self.assertEqual(m.value(), 25.)

    def test_empty_uncset(self):
        m = pro.examples.Knapsack()
        m.Uempty = pro.UncSet()
        m.w.uncset = m.Uempty
        solver = pe.SolverFactory('pro.robust.reformulation')
        self.assertRaises(RuntimeError,
                          lambda: solver.solve(m))

    def test_unknown_uncset(self):
        m = pe.ConcreteModel()
        m.x = pe.Var(range(2))
        m.U = pro.UncSet()
        m.w = pro.UncParam(range(2), nominal=(1, 2), uncset=m.U)
        m.obj = pe.Objective(expr=pe.sum_product(m.w, m.x), sense=pe.maximize)
        m.cons = pe.Objective(expr=pe.quicksum(m.x[i] for i in m.x) <= 4)
        m.U.cons = pe.Constraint(expr=(m.w[0] - 1)**4 + pe.sin(m.w[1]) <= 1)
        solver = pe.SolverFactory('pro.robust.reformulation')

        msg = "Cannot reformulate UncSet with unknown geometry: m.P"
        try:
            solver.solve(m)
        except RuntimeError as e:
            self.assertEqual(str(e), msg)
        else:
            self.fail('"solver.solve was expected to throw RuntimeError')
        solver.solve(m, ignore_unkown=False)

    def test_uncparam_has_no_uncset(self):
        m = pe.ConcreteModel()
        m.w = pro.UncParam(range(3), nominal=(1, 2, 3))
        m.x = pe.Var(range(3))
        expr = pe.quicksum(m.w[i]*m.x[i] for i in range(3))
        m.cons = pe.Constraint(expr=expr <= 5)
        m.obj = pe.Objective(expr=m.x[0], sense=pe.maximize)
        solver = pe.SolverFactory('pro.robust.reformulation')
        self.assertRaises(AssertionError, lambda: solver.solve(m))

    def test_cons_nonlinear_in_uncparam(self):
        m = pe.ConcreteModel()
        m.U = pro.UncSet()
        m.w = pro.UncParam(range(3), nominal=(1, 2, 3), uncset=m.U)
        m.x = pe.Var(range(3))
        expr = pe.quicksum(m.w[i]**2 * m.x[i] for i in range(3))
        m.cons = pe.Constraint(expr=expr <= 5)
        m.obj = pe.Objective(expr=m.x[0], sense=pe.maximize)
        solver = pe.SolverFactory('pro.robust.reformulation')
        self.assertRaises(AssertionError, lambda: solver.solve(m))


if __name__ == "__main__":
    unittest.main()
