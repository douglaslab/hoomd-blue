# Copyright (c) 2009-2019 The Regents of the University of Michigan
# This file is part of the HOOMD-blue project, released under the BSD 3-Clause
# License.

# Maintainer: joaander / All Developers are free to add commands for new
# features

R""" Apply forces to particles.
"""

from hoomd import _hoomd
from hoomd.md import _md
from hoomd.operation import _Operation
from hoomd.typeparam import TypeParameter
from hoomd.typeconverter import OnlyType
from hoomd.parameterdicts import ParameterDict, TypeParameterDict
from hoomd.filter import _ParticleFilter
from hoomd.logging import Loggable
import hoomd
from hoomd.md.constrain import _ConstraintForce


def ellip_preprocessing(constraint):
    if constraint is not None:
        if (constraint.__class__.__name__ == "constraint_ellipsoid") :
            return act_force
        else:
            raise RuntimeError("Active force constraint is not accepted (currently only accepts ellipsoids)")
    else:
        return None


class _force(hoomd.meta._metadata):
    pass


class _Force(_Operation):
    '''Constructs the force.

    Initializes some loggable quantities.
    '''

    def attach(self, simulation):
        self._simulation = simulation
        super().attach(simulation)

    @Loggable.log
    def energy(self):
        if self.is_attached:
            self._cpp_obj.compute(self._simulation.timestep)
            return self._cpp_obj.calcEnergySum()
        else:
            return None

    @Loggable.log(flag='particles')
    def energies(self):
        if self.is_attached:
            self._cpp_obj.compute(self._simulation.timestep)
            return self._cpp_obj.getEnergies()
        else:
            return None

    @Loggable.log(flag='particles')
    def forces(self):
        """
        Returns: The force for all particles.
        """
        if self.is_attached:
            self._cpp_obj.compute(self._simulation.timestep)
            return self._cpp_obj.getForces()
        else:
            return None

    @Loggable.log(flag='particles')
    def torques(self):
        """
        Returns: The torque for all particles.
        """
        if self.is_attached:
            self._cpp_obj.compute(self._simulation.timestep)
            return self._cpp_obj.getTorques()
        else:
            return None

    @Loggable.log(flag='particles')
    def virials(self):
        R"""
        Returns: The virial for the members in the group.
        """
        if self.is_attached:
            self._cpp_obj.compute(self._simulation.timestep)
            return self._cpp_obj.getVirials()
        else:
            return None


class constant(_Force):
    R""" Constant force.

    Args:
        fvec (tuple): force vector (in force units)
        tvec (tuple): torque vector (in torque units)
        fx (float): x component of force, retained for backwards compatibility
        fy (float): y component of force, retained for backwards compatibility
        fz (float): z component of force, retained for backwards compatibility
        group (:py:mod:`hoomd.group`): Group for which the force will be set.
        callback (`callable`): A python callback invoked every time the forces are computed

    :py:class:`constant` specifies that a constant force should be added to every
    particle in the simulation or optionally to all particles in a group.

    Note:
        Forces are kept constant during the simulation. If a callback should re-compute
        particle forces every time step, it needs to overwrite the old forces of **all**
        particles with new values.

    Note:
        Per-particle forces take precedence over a particle group, which takes precedence over constant forces for all particles.

    Examples::

        force.constant(fx=1.0, fy=0.5, fz=0.25)
        const = force.constant(fvec=(0.4,1.0,0.5))
        const = force.constant(fvec=(0.4,1.0,0.5),group=fluid)
        const = force.constant(fvec=(0.4,1.0,0.5), tvec=(0,0,1) ,group=fluid)

        def updateForces(timestep):
            global const
            const.setForce(tag=1, fvec=(1.0*timestep,2.0*timestep,3.0*timestep))
        const = force.constant(callback=updateForces)
    """
    def __init__(self, fx=None, fy=None, fz=None, fvec=None, tvec=None, group=None, callback=None):

        if (fx is not None) and (fy is not None) and (fz is not None):
            self.fvec = (fx,fy,fz)
        elif (fvec is not None):
            self.fvec = fvec
        else:
            self.fvec = (0,0,0)

        if (tvec is not None):
            self.tvec = tvec
        else:
            self.tvec = (0,0,0)

        if (self.fvec == (0,0,0)) and (self.tvec == (0,0,0) and callback is None):
            hoomd.context.current.device.cpp_msg.warning("The constant force specified has no non-zero components\n")

        # initialize the base class
        Force.__init__(self)

        # create the c++ mirror class
        if (group is not None):
            self.cppForce = _hoomd.ConstForceCompute(hoomd.context.current.system_definition,
                group.cpp_group,
                self.fvec[0],
                self.fvec[1],
                self.fvec[2],
                self.tvec[0],
                self.tvec[1],
                self.tvec[2])
        else:
            self.cppForce = _hoomd.ConstForceCompute(hoomd.context.current.system_definition,
                self.fvec[0],
                self.fvec[1],
                self.fvec[2],
                self.tvec[0],
                self.tvec[1],
                self.tvec[2])

        if callback is not None:
            self.cppForce.setCallback(callback)

        # store metadata
        self.metadata_fields = ['fvec', 'tvec']
        if group is not None:
            self.metadata_fields.append('group')
            self.group = group

        hoomd.context.current.system.addCompute(self.cppForce, self.force_name)

    R""" Change the value of the constant force.

    Args:
        fx (float) New x-component of the force (in force units)
        fy (float) New y-component of the force (in force units)
        fz (float) New z-component of the force (in force units)
        fvec (tuple) New force vector
        tvec (tuple) New torque vector
        group Group for which the force will be set
        tag (int) Particle tag for which the force will be set
            .. versionadded:: 2.3

     Using setForce() requires that you saved the created constant force in a variable. i.e.

     Examples:
        const = force.constant(fx=0.4, fy=1.0, fz=0.5)

        const.setForce(fx=0.2, fy=0.1, fz=-0.5)
        const.setForce(fx=0.2, fy=0.1, fz=-0.5, group=fluid)
        const.setForce(fvec=(0.2,0.1,-0.5), tvec=(0,0,1), group=fluid)
    """
    def setForce(self, fx=None, fy=None, fz=None, fvec=None, tvec=None, group=None, tag=None):

        if (fx is not None) and (fy is not None) and (fx is not None):
            self.fvec = (fx,fy,fz)
        elif fvec is not None:
            self.fvec = fvec
        else:
            self.fvec = (0,0,0)

        if tvec is not None:
            self.tvec = tvec
        else:
            self.tvec = (0,0,0)

        if (fvec==(0,0,0)) and (tvec==(0,0,0)):
            hoomd.context.current.device.cpp_msg.warning("You are setting the constant force to have no non-zero components\n")

        self.check_initialization()
        if (group is not None):
            self.cppForce.setGroupForce(group.cpp_group, self.fvec[0], self.fvec[1], self.fvec[2],
                                                          self.tvec[0], self.tvec[1], self.tvec[2])
        elif (tag is not None):
            self.cppForce.setParticleForce(tag, self.fvec[0], self.fvec[1], self.fvec[2],
                                                 self.tvec[0], self.tvec[1], self.tvec[2])
        else:
            self.cppForce.setForce(self.fvec[0], self.fvec[1], self.fvec[2], self.tvec[0], self.tvec[1], self.tvec[2])

    R""" Set a python callback to be called before the force is evaluated

    Args:
        callback (`callable`) The callback function

     Examples:
        const = force.constant(fx=0.4, fy=1.0, fz=0.5)

        def updateForces(timestep):
            global const
            const.setForce(tag=1, fvec=(1.0*timestep,2.0*timestep,3.0*timestep))

        const.set_callback(updateForces)
        run(100)

        # Reset the callback
        const.set_callback(None)
    """
    def set_callback(self, callback=None):
        self.cppForce.setCallback(callback)

    # there are no coeffs to update in the constant force compute
    def update_coeffs(self):
        pass


class Active(_Force):
    R""" Active force.

    Attributes:
        filter (:py:mod:`hoomd.filter`): Subset of particles on which to apply active forces.
        seed (int): required user-specified seed number for random number generator.
        constraint (:py:class:`hoomd.md.update.constraint_ellipsoid`): specifies a constraint surface, to which particles are confined, such as update.constraint_ellipsoid.
        rotation_diff (float): rotational diffusion constant, :math:`D_r`, for all particles in the group.
        active_force (tuple): active force vector in reference to the orientation of a particle. It is defined per particle type and stays constant during the simulation. 
        active_torque (tuple): active torque vector in reference to the orientation of a particle. It is defined per particle type and stays constant during the simulation. 

    :py:class:`Active` specifies that an active force should be added to all particles.
    Obeys :math:`\delta {\bf r}_i = \delta t v_0 \hat{p}_i`, where :math:`v_0` is the active velocity. In 2D
    :math:`\hat{p}_i = (\cos \theta_i, \sin \theta_i)` is the active force vector for particle :math:`i` and the
    diffusion of the active force vector follows :math:`\delta \theta / \delta t = \sqrt{2 D_r / \delta t} \Gamma`,
    where :math:`D_r` is the rotational diffusion constant, and the gamma function is a unit-variance random variable,
    whose components are uncorrelated in time, space, and between particles.
    In 3D, :math:`\hat{p}_i` is a unit vector in 3D space, and diffusion follows
    :math:`\delta \hat{p}_i / \delta t = \sqrt{2 D_r / \delta t} \Gamma (\hat{p}_i (\cos \theta - 1) + \hat{p}_r \sin \theta)`, where
    :math:`\hat{p}_r` is an uncorrelated random unit vector. The persistence length of an active particle's path is
    :math:`v_0 / D_r`.
    The rotational diffusion is applied to the orientation vector/quaternion of each particle. This implies that both the active 
    force and the active torque vectors in the particle frame stay constant during the simulation. Hence, the active forces in the system
    frame are composed of the forces in particle frame and the current orientation of the particle.  

    Examples::


        all = filter.All()
        ellipsoid = update.constraint_ellipsoid(group=groupA, P=(0,0,0), rx=3, ry=4, rz=5)
        active = hoomd.md.force.Active(filter=hoomd.filter.All(), seed=1,rotation_diff=0.01,constraint=ellipsoid)
        active.active_force['A','B'] = (1,0,0)
        active.active_torque['A','B'] = (0,0,0)
    """
    def __init__(self, filter, seed,constraint=None,rotation_diff=0.1):

        # store metadata
        param_dict = ParameterDict(
            filter=_ParticleFilter,
            seed=int(seed),
            rotation_diff=float(rotation_diff),
            constraint=OnlyType(_ConstraintForce,allow_none=True,preprocess=ellip_preprocessing),
        )
        param_dict.update(dict(constraint=constraint,rotation_diff=rotation_diff,seed=seed, filter=filter))
        # set defaults
        self._param_dict.update(param_dict)

        active_force =  TypeParameter('active_force', type_kind='particle_types', param_dict=TypeParameterDict( (1,0,0), len_keys=1) )
        active_torque =  TypeParameter('active_torque', type_kind='particle_types',  param_dict=TypeParameterDict( (0,0,0), len_keys=1) )


        self._extend_typeparam([active_force, active_torque])
        
    def attach(self, simulation):

        
        # initialize the reflected c++ class
        if not simulation.device.cpp_exec_conf.isCUDAEnabled():
            my_class = _md.ActiveForceCompute
        else:
            my_class = _md.ActiveForceComputeGPU

        self._cpp_obj = my_class(simulation.state._cpp_sys_def,
                                 simulation.state.get_group(self.filter),
                                 self.seed, self.rotation_diff,_hoomd.make_scalar3(0,0,0), 0, 0, 0)

        # Attach param_dict and typeparam_dict
        super().attach(simulation)


    # there are no coeffs to update in the active force compute
    def update_coeffs(self):
        pass


class dipole(_Force):
    R""" Treat particles as dipoles in an electric field.

    Args:
        field_x (float): x-component of the field (units?)
        field_y (float): y-component of the field (units?)
        field_z (float): z-component of the field (units?)
        p (float): magnitude of the particles' dipole moment in the local z direction

    Examples::

        force.external_field_dipole(field_x=0.0, field_y=1.0 ,field_z=0.5, p=1.0)
        const_ext_f_dipole = force.external_field_dipole(field_x=0.0, field_y=1.0 ,field_z=0.5, p=1.0)
    """
    def __init__(self, field_x,field_y,field_z,p):

        # initialize the base class
        Force.__init__(self)

        # create the c++ mirror class
        self.cppForce = _md.ConstExternalFieldDipoleForceCompute(hoomd.context.current.system_definition, field_x, field_y, field_z, p)

        hoomd.context.current.system.addCompute(self.cppForce, self.force_name)

        # store metadata
        self.metadata_fields = ['field_x', 'field_y', 'field_z']
        self.field_x = field_x
        self.field_y = field_y
        self.field_z = field_z

    def set_params(field_x, field_y,field_z,p):
        R""" Change the constant field and dipole moment.

        Args:
            field_x (float): x-component of the field (units?)
            field_y (float): y-component of the field (units?)
            field_z (float): z-component of the field (units?)
            p (float): magnitude of the particles' dipole moment in the local z direction

        Examples::

            const_ext_f_dipole = force.external_field_dipole(field_x=0.0, field_y=1.0 ,field_z=0.5, p=1.0)
            const_ext_f_dipole.setParams(field_x=0.1, field_y=0.1, field_z=0.0, p=1.0))

        """
        self.check_initialization()

        self.cppForce.setParams(field_x,field_y,field_z,p)

    # there are no coeffs to update in the constant ExternalFieldDipoleForceCompute
    def update_coeffs(self):
        pass
