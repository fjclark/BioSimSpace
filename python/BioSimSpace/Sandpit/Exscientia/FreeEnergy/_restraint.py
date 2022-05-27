######################################################################
# BioSimSpace: Making biomolecular simulation a breeze!
#
# Copyright: 2017-2022
#
# Authors: Lester Hedges <lester.hedges@gmail.com>
#
# BioSimSpace is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 2 of the License, or
# (at your option) any later version.
#
# BioSimSpace is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with BioSimSpace. If not, see <http://www.gnu.org/licenses/>.
#####################################################################

"""
A class for holding restraints.
"""

from .._SireWrappers import Atom
from ..Types import Length, Angle
from .._SireWrappers import System as _System
from ..Units.Length import nanometer
from ..Units.Angle import degree, radian
from ..Units.Energy import kj_per_mol

class Restraint():
    '''The Restraint class which holds the restraint information for the ABFE
    calculations. Currently only Boresch type restraint is supported.

    Boresch restraint is a set of harmonic restraints containing one bond, two
    angle and three dihedrals, which comes from three atoms in the ligand
    (l1, l2, l3) and three atoms in the protein (r1, r2, r3). The restraints
    are arranged in the format of atom1-atom2 (equilibrium value, force constant):

    Bonds: r1-l1 (r0, kr)
    Angles: r2-r1-l1 (thetaA0, kthetaA), r1-l1-l2 (thetaB0, kthetaB)
    Dihedrals: r3-r2-r1-l1 (phiA0, kphiA), r2-r1-l1-l2 (phiB0, kphiB), r1-l1-l2-l3 (phiC0, kphiC)
    '''
    def __init__(self, system, restraint_dict, rest_type='Boresch'):
        """Constructor.

           Parameters
           ----------

           system : :class:`System <BioSimSpace._SireWrappers.System>`
               The molecular system.

           restraint_dict : dict
               The dict for holding the restraint.

           rest_type : str
               The type of the restraint. (`Boresch`, )
        """

        if rest_type.lower() == 'boresch':
            self.rest_type = 'boresch'
            # Test if the atoms are of BioSimSpace._SireWrappers.Atom
            for key in ['r3', 'r2', 'r1', 'l1', 'l2', 'l3']:
                if not isinstance(restraint_dict['anchor_points'][key], Atom):
                    raise ValueError(f"restraint_dict['anchor_points']['{key}'] "
                                     f"must be of type "
                                     f"'BioSimSpace._SireWrappers.Atom'")

            # Test if the equilibrium length of the bond r1-l1 is a length unit
            # Such as angstrom or nanometer
            if not isinstance(restraint_dict['equilibrium_values']['r0'], Length):
                raise ValueError(
                    "restraint_dict['equilibrium_values']['r0'] must be of type 'BioSimSpace.Types.Length'")

            # Test if the equilibrium length of the angle and dihedral is a
            # angle unit such as radian or degree
            for key in ["thetaA0", "thetaB0", "phiA0", "phiB0", "phiC0"]:
                if not isinstance(restraint_dict['equilibrium_values'][key], Angle):
                    raise ValueError(
                        f"restraint_dict['equilibrium_values']['{key}'] must be "
                        f"of type 'BioSimSpace.Types.Angle'")

            # Test if the force constant of the bond r1-l1 is the correct unit
            # Such as kcal/mol/angstrom^2
            dim = restraint_dict['force_constants']['kr'].dimensions()
            if dim != (0, 0, 0, 1, -1, 0, -2):
                raise ValueError(
                    "restraint_dict['force_constants']['kr'] must be of type "
                    "'BioSimSpace.Types.Energy'/'BioSimSpace.Types.Length^2'")

            # Test if the force constant of the angle and dihedral is the correct unit
            # Such as kcal/mol/rad^2
            for key in ["kthetaA", "kthetaB", "kphiA", "kphiB", "kphiC"]:
                dim = restraint_dict['force_constants'][key].dimensions()
                if dim != (-2, 0, 2, 1, -1, 0, -2):
                    raise ValueError(
                        f"restraint_dict['force_constants']['{key}'] must be of type "
                        f"'BioSimSpace.Types.Energy'/'BioSimSpace.Types.Angle^2'")
        else:
            raise NotImplementedError(f'Restraint type {type} not implemented '
                                      f'yet. Only boresch restraint is supported.')

        self._restraint_dict = restraint_dict
        self.update_system(system)

    def update_system(self, system):
        """Update the system object.

           Parameters
           ----------

           system : :class:`System <BioSimSpace._SireWrappers.System>`
               The molecular system.
        """
        if not isinstance(system, _System):
            raise TypeError("'system' must be of type 'BioSimSpace._SireWrappers.System'")
        else:
            if self.rest_type == 'boresch':
                # Check if the ligand atoms are decoupled.
                # Find the decoupled molecule, assume that only one can be
                # decoupled.
                (decoupled_mol,) = system.getDecoupledMolecules()
                for key in ['l1', 'l2', 'l3']:
                    atom = self._restraint_dict['anchor_points'][key]
                    # Discussed in https://github.com/michellab/BioSimSpace/pull/337
                    if atom._sire_object.molecule().number() != decoupled_mol._sire_object.number():
                        raise ValueError(
                            f'The ligand atom {key} is not from decoupled moleucle.')
                for key in ['r1', 'r2', 'r3']:
                    atom = self._restraint_dict['anchor_points'][key]
                    if not atom in system:
                        raise ValueError(
                            f'The protein atom {key} is not in the system.')

            # Store a copy of solvated system.
            self._system = system.copy()

    def toString(self, engine='Gromacs'):
        """The method for convert the restraint to a format that could be used
        by MD Engines.

           Parameters
           ----------

           engine : str
               The molecular dynamics engine used to generate the restraint.
               Available options currently is "GROMACS" only. If this argument
               is omitted then BioSimSpace will choose an appropriate engine
               for you.
        """
        if engine.lower() == 'gromacs':
            if self.rest_type == 'boresch':
                # Format the atoms into index list
                def format_index(key_list):
                    formated_index = []
                    for key in key_list:
                        formated_index.append('{:<10}'.format(
                            self._system.getIndex(
                                self._restraint_dict['anchor_points'][key]) + 1))
                    return ' '.join(formated_index)

                parameters_string = '{eq0:<10} {fc0:<10} {eq1:<10} {fc1:<10}'
                # Format the parameters for the bonds
                def format_bond(equilibrium_values, force_constants):
                    converted_equ_val = \
                    self._restraint_dict['equilibrium_values'][equilibrium_values] / nanometer
                    converted_fc = \
                        self._restraint_dict['force_constants'][force_constants] / (kj_per_mol / nanometer ** 2)
                    return parameters_string.format(
                        eq0='{:.3f}'.format(converted_equ_val),
                        fc0='{:.2f}'.format(0),
                        eq1='{:.3f}'.format(converted_equ_val),
                        fc1='{:.2f}'.format(converted_fc),
                    )

                # Format the parameters for the angles and dihedrals
                def format_angle(equilibrium_values, force_constants):
                    converted_equ_val = \
                        self._restraint_dict['equilibrium_values'][equilibrium_values] / degree
                    converted_fc = \
                        self._restraint_dict['force_constants'][force_constants] / (kj_per_mol / (radian * radian))
                    return parameters_string.format(
                        eq0='{:.3f}'.format(converted_equ_val),
                        fc0='{:.2f}'.format(0),
                        eq1='{:.3f}'.format(converted_equ_val),
                        fc1='{:.2f}'.format(converted_fc),
                    )

                # basic format of the Gromacs string
                master_string = '  {index} {func_type} {parameters}'

                def write_bond(key_list, equilibrium_values, force_constants):
                    return master_string.format(
                        index=format_index(key_list),
                        func_type=6,
                        parameters=format_bond(equilibrium_values,
                                               force_constants),
                    )

                def write_angle(key_list, equilibrium_values, force_constants):
                    return master_string.format(
                        index=format_index(key_list),
                        func_type=1,
                        parameters=format_angle(equilibrium_values,
                                               force_constants),
                        )

                def write_dihedral(key_list, equilibrium_values, force_constants):
                    return master_string.format(
                        index=format_index(key_list),
                        func_type=2,
                        parameters=format_angle(equilibrium_values,
                                                   force_constants),
                        )

                # Writing the string
                output = ['[ intermolecular_interactions ]',]

                output.append('[ bonds ]')
                output.append('; ai         aj      type bA         kA         bB         kB')
                # Bonds: r1-l1 (r0, kr)
                output.append(
                    write_bond(('r1', 'l1'), 'r0', 'kr'))

                output.append('[ angles ]')
                output.append('; ai         aj         ak      type thA        fcA        thB        fcB')
                # Angles: r2-r1-l1 (thetaA0, kthetaA)
                output.append(
                    write_angle(('r2', 'r1', 'l1'), 'thetaA0', 'kthetaA'))
                # Angles: r1-l1-l2 (thetaB0, kthetaB)
                output.append(
                    write_angle(('r1', 'l1', 'l2'), 'thetaB0', 'kthetaB'))

                output.append('[ dihedrals ]')
                output.append('; ai         aj         ak         al      type phiA       fcA        phiB       fcB')
                # Dihedrals: r3-r2-r1-l1 (phiA0, kphiA)
                output.append(
                    write_dihedral(('r3', 'r2', 'r1', 'l1'), 'phiA0', 'kphiA'))
                # Dihedrals: r2-r1-l1-l2 (phiB0, kphiB)
                output.append(
                    write_dihedral(('r2', 'r1', 'l1', 'l2'), 'phiB0', 'kphiB'))
                # Dihedrals: r1-l1-l2-l3 (phiC0, kphiC)
                output.append(
                    write_dihedral(('r1', 'l1', 'l2', 'l3'),'phiC0', 'kphiC'))

                return '\n'.join(output)
            else:
                raise NotImplementedError(
                    f'Restraint type {self.rest_type} not implemented '
                    f'yet. Only boresch restraint is supported.')
        else:
            raise NotImplementedError(f'MD Engine {engine} not implemented '
                                      f'yet. Only Gromacs is supported.')
