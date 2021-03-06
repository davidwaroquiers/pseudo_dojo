"""Unit tests for dojo works"""
from __future__ import division, print_function, unicode_literals

import os
import pytest
import tempfile

from abipy import abilab
from abipy import data as abidata
from pseudo_dojo.core import PseudoDojoTest
from pseudo_dojo.dojo.works import *


class DeltaFactorTest(PseudoDojoTest):

    def test_nc_silicon_df(self):
        """Testing df factory for NC silicon."""
        flow = abilab.Flow(workdir=tempfile.mkdtemp())
        df_factory = DeltaFactory()

        extra_abivars = {
            "mem_test": 0,
            "fband": 2,
            "nstep": 100,
            "paral_kgb": 0,
        }

        # Create a tmp pseudo because the flow will add the DOJO_REPORT 
        pseudo = abidata.pseudo("14si.pspnc").as_tmpfile()
        work = df_factory.work_for_pseudo(pseudo, kppa=1, ecut=2, pawecutdg=None, **extra_abivars)
        flow.register_work(work)

        flow.build_and_pickle_dump()
        isok, results = flow.abivalidate_inputs()
        assert isok

        flow.make_scheduler().start()
        assert flow.all_ok
        assert pseudo.has_dojo_report

        flow.rmtree()


class GbrvTest(PseudoDojoTest):

    def test_nc_silicon_gbrv_factory(self):
        """Testing GBRV work for NC silicon."""
        flow = abilab.Flow(workdir=tempfile.mkdtemp())
        gbrv_factory = GbrvFactory()

        extra_abivars = {
            "mem_test": 0,
            "fband": 2,
            "nstep": 100,
            "paral_kgb": 0,
        }

        # Create a tmp pseudo because the flow will add the DOJO_REPORT 
        pseudo = abidata.pseudo("14si.pspnc").as_tmpfile()
        for struct_type in ("fcc", "bcc"):
            work = gbrv_factory.relax_and_eos_work(pseudo, struct_type, ecut=3, pawecutdg=None, **extra_abivars)
            flow.register_work(work)

        flow.build_and_pickle_dump()
        isok, results = flow.abivalidate_inputs()
        assert isok

        flow.make_scheduler().start()
        assert flow.all_ok
        assert pseudo.has_dojo_report

        flow.rmtree()


if __name__ == "__main__":
    import unittest
    unittest.main()
