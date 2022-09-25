import pytest

import MDAnalysis as mda
import numpy as np

import BioSimSpace.Sandpit.Exscientia as BSS
from BioSimSpace.Sandpit.Exscientia.Align import decouple
from BioSimSpace.Sandpit.Exscientia.FreeEnergy import RestraintSearch, Restraint
from BioSimSpace.Sandpit.Exscientia.Trajectory import Trajectory
from BioSimSpace.Sandpit.Exscientia.Units.Length import nanometer
from BioSimSpace.Sandpit.Exscientia.Units.Angle import degree

@pytest.fixture(scope="module")
def setup_system():
    'Setup the system for the tests'
    ligand = BSS.IO.readMolecules(BSS.IO.glob("test/input/ligands/ligand04*")).getMolecule(0)
    decouple_system = decouple(ligand).toSystem()
    protocol = BSS.Protocol.Production(
        runtime=BSS.Types.Time(8, "FEMTOSECOND"))
    return ligand, decouple_system, protocol

# Make sure GROMSCS is installed.
has_gromacs = BSS._gmx_exe is not None
@pytest.mark.skipif(has_gromacs is False, reason="Requires GROMACS to be installed.")
def test_run_Gromacs(setup_system):
    'Test if the normal run works on Gromacs'
    ligand, decouple_system, protocol = setup_system
    restraint_search = RestraintSearch(decouple_system, protocol=protocol,
                                       engine='GROMACS')
    restraint_search.start()
    restraint_search.wait()
    assert not restraint_search._process.isError()

def test_run_Somd(setup_system):
    'Test if the normal run works with SOMD'
    ligand, decouple_system, protocol = setup_system
    restraint_search = RestraintSearch(decouple_system, protocol=protocol,
                                       engine='SOMD')
    restraint_search.start()
    restraint_search.wait()
    assert not restraint_search._process.isError()

class Trajectory(Trajectory):
    def __init__(self):
        pass

    def getTrajectory(self, format='mdanalysis'):
        return mda.Universe(
            "test/Sandpit/Exscientia/input/protein_ligand/complex.tpr",
            "test/Sandpit/Exscientia/input/protein_ligand/traj.xtc")

is_MDRestraintsGenerator = BSS.FreeEnergy._restraint_search.is_MDRestraintsGenerator is not None
@pytest.mark.skipif((is_MDRestraintsGenerator is False or has_gromacs is False),
                    reason="Requires MDRestraintsGenerator and Gromacs to be installed.")
class TestMDRestraintsGenerator_analysis():
    @staticmethod
    @pytest.fixture(scope='class')
    def restraint_search(tmp_path_factory):
        outdir = tmp_path_factory.mktemp("out")
        system = BSS.IO.readMolecules(["test/Sandpit/Exscientia/input/protein_ligand/crd.gro",
                                       "test/Sandpit/Exscientia/input/protein_ligand/complex.top"])
        ligand = system.getMolecule(1)
        decoupled_ligand = decouple(ligand)
        protein = system.getMolecule(0)
        new_system = (protein + decoupled_ligand).toSystem()

        protocol = BSS.Protocol.Production()
        restraint_search = BSS.FreeEnergy.RestraintSearch(new_system,
                                                          protocol=protocol,
                                                          engine='GROMACS',
                                                          work_dir=str(outdir))
        restraint_search._process.getTrajectory = lambda: Trajectory()
        restraint = restraint_search.analyse(method='MDRestraintsGenerator',
                                             rest_type='Boresch',
                                             block=False)
        return restraint, outdir

    def test_sanity(self, restraint_search):
        restraint, outdir = restraint_search
        assert isinstance(restraint, Restraint)

    def test_plots(self, restraint_search):
        '''Test if all the plots has been generated correctly'''
        restraint, outdir = restraint_search
        assert (outdir / 'bond_1.png').is_file()
        assert (outdir / 'angle_1.png').is_file()
        assert (outdir / 'angle_2.png').is_file()
        assert (outdir / 'dihedral_1.png').is_file()
        assert (outdir / 'dihedral_2.png').is_file()
        assert (outdir / 'dihedral_3.png').is_file()

    def test_dG_off(self, restraint_search):
        '''Test if the restraint generated is valid'''
        restraint, outdir = restraint_search
        assert (outdir / 'dG_off.dat').is_file()
        dG = np.loadtxt(outdir / 'dG_off.dat')
        assert isinstance(dG, np.ndarray)

    def test_top(self, restraint_search):
        '''Test if the restraint generated has the same energy'''
        restraint, outdir = restraint_search
        assert (outdir / 'BoreschRestraint.top').is_file()
        with open(outdir / 'BoreschRestraint.top', 'r') as f:
            assert 'intermolecular_interactions' in f.read()

    # @pytest.mark.xfail()
    def test_best_frame(self, restraint_search):
        restraint, outdir = restraint_search
        assert (outdir / 'ClosestRestraintFrame.gro').is_file()
        best_frame = mda.Universe(outdir / 'ClosestRestraintFrame.gro')
        ref_dim = best_frame.dimensions
        ref_coord = best_frame.atoms[0].position
        system = restraint.system
        # TODO: Check if the box dimension and coordiants are correct
        # Need to wait for BSS to fix the getFrame

    def test_bond(self, restraint_search):
        restraint, outdir = restraint_search
        equilibrium_values_r0 = restraint._restraint_dict['equilibrium_values']['r0'] / nanometer
        assert np.isclose(0.575, equilibrium_values_r0, atol=0.001)

    def test_angles(self, restraint_search):
        restraint, outdir = restraint_search
        equilibrium_values_thetaA0 = restraint._restraint_dict['equilibrium_values']['thetaA0'] / degree
        assert np.isclose(67.319, equilibrium_values_thetaA0, atol=0.001)
        equilibrium_values_thetaB0 = restraint._restraint_dict['equilibrium_values']['thetaB0'] / degree
        assert np.isclose(127.802, equilibrium_values_thetaB0, atol=0.001)

    def test_dihedrals(self, restraint_search):
        restraint, outdir = restraint_search
        equilibrium_values_phiA0 = restraint._restraint_dict['equilibrium_values']['phiA0'] / degree
        assert np.isclose(-176.627, equilibrium_values_phiA0, atol=0.001)
        equilibrium_values_phiB0 = restraint._restraint_dict['equilibrium_values']['phiB0'] / degree
        assert np.isclose(-69.457, equilibrium_values_phiB0, atol=0.001)
        equilibrium_values_phiC0 = restraint._restraint_dict['equilibrium_values']['phiC0'] / degree
        assert np.isclose(-24.517, equilibrium_values_phiC0, atol=0.001)

    def test_index(self, restraint_search):
        restraint, outdir = restraint_search
        outstring = restraint.toString('Gromacs')
        # Ligand index
        assert ' 2615 ' in outstring
        assert ' 2610 ' in outstring
        assert ' 2611 ' in outstring
        # Protein index
        assert ' 1337 ' in outstring
        assert ' 1322 ' in outstring
        assert ' 1320 ' in outstring

class TestBSS_analysis():
    """Test selection of restraints using the inbuilt BSS method."""
    @staticmethod
    @pytest.fixture(scope='class')
    def restraint_search(tmp_path_factory):
        outdir = tmp_path_factory.mktemp("out")
        system = BSS.IO.readMolecules(["test/Sandpit/Exscientia/input/protein_ligand/crd.gro",
                                       "test/Sandpit/Exscientia/input/protein_ligand/complex.top"])
        ligand = system.getMolecule(1)
        decoupled_ligand = decouple(ligand)
        protein = system.getMolecule(0)
        new_system = (protein + decoupled_ligand).toSystem()

        protocol = BSS.Protocol.Production()
        restraint_search = BSS.FreeEnergy.RestraintSearch(new_system,
                                                          protocol=protocol,
                                                          engine='GROMACS',
                                                          work_dir=str(outdir))
        restraint_search._process.getTrajectory = lambda: Trajectory()
        restraint = restraint_search.analyse(method='BSS',
                                             rest_type='Boresch',
                                             block=False)
        return restraint, outdir

    def test_sanity(self, restraint_search):
        restraint, outdir = restraint_search
        assert isinstance(restraint, Restraint)

    def test_plots(self, restraint_search):
        '''Test if all the plots have been generated correctly'''
        restraint, outdir = restraint_search
        assert (outdir / 'restraint_idx0_dof_time.png').is_file()
        assert (outdir / 'restraint_idx0_dof_hist.png').is_file()

    def test_dG_off(self, restraint_search):
        '''Test if the restraint generated has the same energy'''
        restraint, outdir = restraint_search
        assert np.isclose(-42.27400951174584, restraint.correction.value(), atol=0.01)

    # TODO: Test best frame when implemented

    def test_bond(self, restraint_search):
        restraint, outdir = restraint_search
        equilibrium_values_r0 = restraint._restraint_dict['equilibrium_values']['r0'] / nanometer
        assert np.isclose(0.5420, equilibrium_values_r0, atol=0.001)

    def test_angles(self, restraint_search):
        restraint, outdir = restraint_search
        equilibrium_values_thetaA0 = restraint._restraint_dict['equilibrium_values']['thetaA0'] / degree
        assert np.isclose(129.1723, equilibrium_values_thetaA0, atol=0.001)
        equilibrium_values_thetaB0 = restraint._restraint_dict['equilibrium_values']['thetaB0'] / degree
        assert np.isclose(64.6300, equilibrium_values_thetaB0, atol=0.001)

    def test_dihedrals(self, restraint_search):
        restraint, outdir = restraint_search
        equilibrium_values_phiA0 = restraint._restraint_dict['equilibrium_values']['phiA0'] / degree
        assert np.isclose(16.4355, equilibrium_values_phiA0, atol=0.001)
        equilibrium_values_phiB0 = restraint._restraint_dict['equilibrium_values']['phiB0'] / degree
        assert np.isclose(50.3718, equilibrium_values_phiB0, atol=0.001)
        equilibrium_values_phiC0 = restraint._restraint_dict['equilibrium_values']['phiC0'] / degree
        assert np.isclose(101.1527, equilibrium_values_phiC0, atol=0.001)

    def test_index(self, restraint_search):
        restraint, outdir = restraint_search
        idxs = {k:restraint._restraint_dict['anchor_points'][k].index() for k \
                in restraint._restraint_dict['anchor_points']}
        assert idxs == {'r1':1560, 'r2':1558, 'r3':1562,
                        'l1':9, 'l2':8, 'l3':10}

