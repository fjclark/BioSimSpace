import numpy as np
import pytest

from BioSimSpace.Sandpit.Exscientia.Align import decouple
from BioSimSpace.Sandpit.Exscientia.FreeEnergy import Restraint
from BioSimSpace.Sandpit.Exscientia.Units.Length import angstrom
from BioSimSpace.Sandpit.Exscientia.Units.Angle import radian, degree
from BioSimSpace.Sandpit.Exscientia.Units.Energy import kcal_per_mol
from BioSimSpace.Sandpit.Exscientia.Units.Temperature import kelvin
import BioSimSpace.Sandpit.Exscientia as BSS

@pytest.fixture(scope='module')
def restraint():
    '''Generate the Boresch restaint object.'''
    ligand = BSS.IO.readMolecules(BSS.IO.glob("test/input/ligands/ligand01*")).getMolecule(0)
    decoupled_ligand = decouple(ligand)

    protein = BSS.IO.readMolecules(['test/input/molecules/1jr5.crd',
                                    'test/input/molecules/1jr5.top']).getMolecule(0)

    system = (protein + decoupled_ligand).toSystem()

    # Assign three atoms from the ligand
    ligand_2 = decoupled_ligand.getAtoms()[2]
    ligand_1 = decoupled_ligand.getAtoms()[1]
    ligand_0 = decoupled_ligand.getAtoms()[0]

    # And three atoms from the protein
    protein_0 = protein.getAtoms()[0]
    protein_1 = protein.getAtoms()[1]
    protein_2 = protein.getAtoms()[2]

    restraint_dict = {
        "anchor_points":{"r1":protein_0, "r2":protein_1, "r3":protein_2,
                         "l1":ligand_0, "l2":ligand_1, "l3":ligand_2},
        "equilibrium_values":{"r0": 5.08 * angstrom,
                              "thetaA0": 64.051 * degree,
                              "thetaB0": 39.618 * degree,
                              "phiA0":2.59 * radian,
                              "phiB0":-1.20 * radian,
                              "phiC0":2.63 * radian},
        "force_constants":{"kr":10 * kcal_per_mol / angstrom ** 2,
                           "kthetaA":10 * kcal_per_mol / (radian * radian),
                           "kthetaB":10 * kcal_per_mol / (radian * radian),
                           "kphiA":10 * kcal_per_mol / (radian * radian),
                           "kphiB":10 * kcal_per_mol / (radian * radian),
                           "kphiC":10 * kcal_per_mol / (radian * radian)}}
    restraint = Restraint(system, restraint_dict, 300 * kelvin,
                          rest_type='Boresch')
    return restraint

def test_sanity(restraint):
    'Sanity check'
    assert isinstance(restraint, Restraint)

def test_semi_analytical_correction(restraint):
    dG = restraint.getCorrection(method="semi-analytical") / kcal_per_mol
    assert np.isclose(-7.2, dG, atol=0.1)

def test_analytical_correction(restraint):
    dG = restraint.getCorrection(method="analytical") / kcal_per_mol
    assert np.isclose(-7.2, dG, atol=0.1)

class TestGromacsOutput():
    @staticmethod
    @pytest.fixture(scope='class')
    def Topology(restraint):
        return restraint.toString(engine='Gromacs').split('\n')

    def test_sanity(self, Topology):
        'Sanity check'
        assert 'intermolecular_interactions' in Topology[0]

    def test_bond(self, Topology):
        ai, aj, type, bA, kA, bB, kB = Topology[3].split()
        assert ai == '1'
        assert aj == '1496'
        assert bA == '0.508'
        assert bB == '0.508'
        assert kB == '4184.00'

    def test_angle(self, Topology):
        ai, aj, ak, type, thA, kA, thB, kB = Topology[6].split()
        assert ai == '2'
        assert aj == '1'
        assert ak == '1496'
        assert thA == '64.051'
        assert thB == '64.051'
        assert kB == '41.84'
        ai, aj, ak, type, thA, kA, thB, kB = Topology[7].split()
        assert ai == '1'
        assert aj == '1496'
        assert ak == '1497'

    def test_dihedral(self, Topology):
        ai, aj, ak, al, type, phiA, kA, phiB, kB = Topology[10].split()
        assert ai == '3'
        assert aj == '2'
        assert ak == '1'
        assert al == '1496'
        assert phiA == '148.396'
        assert phiB == '148.396'
        assert kB == '41.84'
        ai, aj, ak, al, type, phiA, kA, phiB, kB = Topology[11].split()
        assert ai == '2'
        assert aj == '1'
        assert ak == '1496'
        assert al == '1497'
        ai, aj, ak, al, type, phiA, kA, phiB, kB = Topology[12].split()
        assert ai == '1'
        assert aj == '1496'
        assert ak == '1497'
        assert al == '1498'


class TestSomdOutput():
    @staticmethod
    @pytest.fixture(scope='class')
    def getRestraintSomd(restraint):
        boresch_str = restraint.toString(engine='SOMD').split('=')[1].strip()
        boresch_dict = eval(boresch_str)
        return boresch_dict

    def test_sanity(self, getRestraintSomd):
        'Sanity check'
        boresch_dict = getRestraintSomd
        assert type(boresch_dict) ==  dict

    def test_indices(self, getRestraintSomd):
        anchor_points = getRestraintSomd["anchor_points"]
        assert anchor_points["r1"] == 0
        assert anchor_points["r2"] == 1
        assert anchor_points["r3"] == 2
        assert anchor_points["l1"] == 1495
        assert anchor_points["l2"] == 1496
        assert anchor_points["l3"] == 1497

    def test_equil_vals(self, getRestraintSomd):
        equil_vals = getRestraintSomd["equilibrium_values"]
        assert equil_vals["r0"] == 5.08
        assert equil_vals["thetaA0"] == 1.12
        assert equil_vals["thetaB0"] == 0.69
        assert equil_vals["phiA0"] == 2.59
        assert equil_vals["phiB0"] == -1.20
        assert equil_vals["phiC0"] == 2.63
