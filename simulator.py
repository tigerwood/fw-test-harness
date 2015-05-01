#!/usr/bin/env python
from __future__ import print_function, division, absolute_import, \
    unicode_literals
import os
from jsbsim import FGFDMExec
import matplotlib.pyplot as plt
import argparse
from pint import UnitRegistry
from html_report_generator import HtmlReportGenerator
ureg = UnitRegistry()


class Simulator:

    """Simulate mtecs"""

    def __init__(self, args):
        """Constructor"""
        self.args = args

        self.fdm = FGFDMExec(root_dir=args["jsbsim_root"])
        self.fdm.load_model("c172p")

        # settings
        self.sim_end_time_s = 60.0
        self.dt = 0.1
        self.ic = {
            "hgt": 400 * ureg.meter
        }

    def init_sim(self):
        """init/reset simulation"""

        # init states
        self.jsbs_states = {
            "ic/gamma-rad": [0],
            "position/h-sl-meters": [self.ic["hgt"].magnitude],
            "attitude/phi-rad": [0],
            }
        self.jsbs_ic = {
            "ic/h-sl-ft": [self.ic["hgt"].to(ureg.foot).magnitude],
            "ic/vc-kts": [122],
            "ic/gamma-rad": [0],
            }
        self.jsbs_inputs = {
            "fcs/elevator-cmd-norm": [0]
            }
        self.sim_states = {
            "t": [0.0]
        }

        # set initial conditions and trim
        for k, v in self.jsbs_ic.items():
            self.fdm.set_property_value(k, v[0])
        self.fdm.set_dt(self.dt)
        self.fdm.reset_to_initial_conditions(0)
        self.fdm.do_trim(0)

    def step(self):
        """Perform one simulation step
        implementation is accoding to FGFDMExec's own simulate but we don't
        want to move the parameters in and out manually
        """
        # control
        self.jsbs_inputs["fcs/elevator-cmd-norm"].append(0.01 * (400 -
                                                         self.jsbs_states["position/h-sl-meters"][-1]))

        # pass to jsbsim
        for k, v in self.jsbs_inputs.items():
            self.fdm.set_property_value(k, v[0])
        self.fdm.run()
        for k, v in self.jsbs_states.items():
            self.jsbs_states[k].append(self.fdm.get_property_value(k))

        return self.fdm.get_sim_time()

    def output_results(self):
        """Generate a report of the simulation"""
        rg = HtmlReportGenerator(self.args)

        # altitude pitch figure
        fig = plt.figure(1)
        plt.plot(
            self.sim_states["t"],
            self.jsbs_states["position/h-sl-meters"],
            )
        plt.plot(
            self.sim_states["t"],
            ureg.Quantity(
                self.jsbs_states["attitude/phi-rad"],
                "rad").to(
                ureg.deg).magnitude)
        plt.xlabel("time [s]")
        plt.legend(['h [m]', 'pitch[deg]'])
        rg.plots["Altitude and Pitch"] = fig

        # elevator pitch figure
        fig = plt.figure(2)
        plt.xlabel("t, sec")
        plt.plot(
            self.sim_states["t"],
            self.jsbs_inputs["fcs/elevator-cmd-norm"],
            )
        plt.plot(
            self.sim_states["t"],
            ureg.Quantity(
                self.jsbs_states["attitude/phi-rad"],
                "rad").to(
                ureg.deg).magnitude)
        plt.xlabel("time [s]")
        plt.legend(['elevator normed', 'pitch[deg]'])
        rg.plots["Pitch and elevator"] = fig

        rg.generate()
        rg.save()
        print("Report saved to {0}".format(self.args["filename_out"]))

    def main(self):
        """main method of the simulator"""
        self.init_sim()

        # run simulation
        while self.sim_states["t"][-1] < self.sim_end_time_s:
            self.sim_states["t"].append(self.step())

        self.output_results()

if __name__ == "__main__":
    """run with python2 simulator.py ~/src/jsbsim"""
    parser = argparse.ArgumentParser(
        description='simulates aircraft control with px4/mtecs')
    parser.add_argument('--test', dest='test', action='store_true')
    parser.add_argument(
        '--jsbsim_root',
        dest='jsbsim_root',
        default=os.path.expanduser('./jsbsim/'))
    parser.add_argument('-o', dest='filename_out', default='report.html')
    args = parser.parse_args()
    s = Simulator(vars(args))
    if args.test:
        s.test()
    else:
        s.main()