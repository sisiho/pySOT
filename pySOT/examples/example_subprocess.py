"""
.. module:: example_subprocess
  :synopsis: Example of an external objective function
.. moduleauthor:: David Eriksson <dme65@cornell.edu>
"""

from pySOT.adaptive_sampling import CandidateDYCORS
from pySOT.experimental_design import SymmetricLatinHypercube
from pySOT.strategy import SRBFStrategy
from pySOT.surrogate import RBFInterpolant, CubicKernel, LinearTail
from pySOT.optimization_problems import Sphere

from poap.controller import ThreadController, ProcessWorkerThread
import numpy as np
import sys
import os.path
import logging
from subprocess import Popen, PIPE


def array2str(x):
    return ",".join(np.char.mod('%f', x.ravel()))


# Find path of the executable
path = os.path.dirname(os.path.abspath(__file__)) + "/sphere_ext"


class CppSim(ProcessWorkerThread):
    def handle_eval(self, record):
        try:
            self.process = Popen([path, array2str(record.params[0])],
                                 stdout=PIPE, bufsize=1, universal_newlines=True)
            val = self.process.communicate()[0]
            self.finish_success(record, float(val))
        except ValueError:
            self.finish_cancelled(record)
            logging.info("WARNING: Incorrect output or crashed evaluation")


def example_subprocess():
    if not os.path.exists("./logfiles"):
        os.makedirs("logfiles")
    if os.path.exists("./logfiles/example_subprocess.log"):
        os.remove("./logfiles/example_subprocess.log")
    logging.basicConfig(filename="./logfiles/example_subprocess.log",
                        level=logging.INFO)

    print("\nNumber of threads: 1")
    print("Maximum number of evaluations: 200")
    print("Search strategy: Candidate DYCORS")
    print("Experimental design: Symmetric Latin Hypercube")
    print("Surrogate: Cubic RBF")

    assert os.path.isfile(path), "You need to build sphere_ext"

    nthreads = 1
    max_evals = 200

    sphere = Sphere(dim=10)
    print(sphere.info)

    rbf = RBFInterpolant(dim=sphere.dim, kernel=CubicKernel(), 
                         tail=LinearTail(sphere.dim))
    dycors = CandidateDYCORS(opt_prob=sphere, max_evals=max_evals, numcand=100*sphere.dim)
    slhd = SymmetricLatinHypercube(dim=sphere.dim, npts=2 * (sphere.dim + 1))

    # Create a strategy and a controller
    controller = ThreadController()
    controller.strategy = \
        SRBFStrategy(max_evals=max_evals, opt_prob=sphere, asynchronous=True,
                     exp_design=slhd, surrogate=rbf, adapt_sampling=dycors,
                     batch_size=nthreads)

    # Launch the threads and give them access to the objective function
    for _ in range(nthreads):
        controller.launch_worker(CppSim(controller))

    # Run the optimization strategy
    result = controller.run()

    print('Best value found: {0}'.format(result.value))
    print('Best solution found: {0}\n'.format(
        np.array_str(result.params[0], max_line_width=np.inf,
                     precision=5, suppress_small=True)))


if __name__ == '__main__':
    example_subprocess()
