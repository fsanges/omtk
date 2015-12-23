import pymel.core as pymel
import logging
from className import Name
from classCtrl import BaseCtrl
from libs import libPymel, libAttr, libPython

def getattrs_by_type(val, type, recursive=False):
    for key, val in val.__dict__.iteritems():
        if isinstance(val, type):
            yield val
        elif isinstance(val, Module):
            if recursive:
                for subval in getattrs_by_type(val, type):
                    yield subval

class Module(object):
    """
    A Module is built from at least one input, specific via the constructor.
    To build a Module, use the .build method.
    To unbuild a Module, use the .unbuild() method.
    """

    def is_built(self):
        """
        Check in maya the existence of the grp_anm and grp_rig properties.
=        Returns: True if the rig think it have been built.
        """
        return self.grp_anm is not None or self.grp_rig is not None

    @property
    def outputs(self):
        return self.__dict__['_outputs']

    @libPython.cached_property()
    def name_anm(self):
        ref = next(iter(self.input), None)
        if ref:
            name = Name(ref.nodeName(), prefix='anm')
            name.add_tokens(self.__class__.__name__.lower())
            return name

    @libPython.cached_property()
    def name_rig(self):
        ref = next(iter(self.input), None)
        if ref:
            name = Name(ref.nodeName(), prefix='rig')
            name.add_tokens(self.__class__.__name__.lower())
            return name

    @libPython.cached_property()
    def name_jnt(self):
        ref = next(iter(self.input), None)
        if ref:
            name = Name(ref.nodeName(), prefix='jnt')
            name.add_tokens(self.__class__.__name__.lower())
            return name

    @property
    def parent(self):
        first_input = next(iter(self.input), None)
        if libPymel.is_valid_PyNode(first_input):
            return first_input.getParent()
        return None

    @libPython.cached_property()
    def chain(self):
        return libPymel.PyNodeChain(self.input)  # todo: approve PyNodeChain class

    # todo: since args is never used, maybe use to instead of _input?
    def __init__(self, input=None, *args, **kwargs):
        self.iCtrlIndex = 2
        self.grp_anm = None
        self.grp_rig = None
        self.canPinTo = True  # If raised, the network can be used as a space-switch pin-point
        self.globalScale = None  # Each module is responsible for handling it scale!

        #  since we're using hook on inputs, assign it last!
        self.input = input if input else []

    def __str__(self):
        if self.name_anm:
            return '{0} ({1})'.format(str(self.name_anm), self.__class__.__name__)
        else:
            return '{0} (no inputs)'.format(self.__class__.__name__)

    # Used in libSerialization
    def __getNetworkName__(self):
        """
        Determine the name of the maya network.
        Override this to customize.
        Returns: The desired network name for this instance.
        """
        return 'net_{0}'.format(self.__class__.__name__)

    def __createMayaNetwork__(self):
        return pymel.createNode('network', name=self.name_anm.resolve('net'))

    def build(self, create_grp_anm=True, create_grp_rig=True, *args, **kwargs):
        logging.info('Building {0}'.format(self.name_rig))

        '''
        if len(self.input) == 0:
            logging.error("[Module:Build] Can't build, inputs is empty"); return False
        '''

        # Disable segment scale compensate by default.
        # Otherwise we might have scale issues since the rig won't propagate uniform scale change.
        for inn in self.input:
            if inn.hasAttr('segmentScaleCompensate'):
                inn.segmentScaleCompensate.set(False)

        if create_grp_anm:
            grp_anm_name = self.name_anm.resolve()
            self.grp_anm = pymel.createNode('transform', name=grp_anm_name)
        if create_grp_rig:
            grp_rig_name = self.name_rig.resolve()
            self.grp_rig = pymel.createNode('transform', name=grp_rig_name)

            # todo: keep it here?
            pymel.addAttr(self.grp_rig, longName='globalScale', defaultValue=1.0)
            self.globalScale = self.grp_rig.globalScale

    def unbuild(self):
        """
        Call unbuild on each individual ctrls
        This allow the rig to save his ctrls appearance (shapes) and animation (animCurves).
        Note that this happen first so the rig can return to it's bind pose before anything else is done.
        """

        # Ensure that there's no more connections in the input chain
        for obj in self.input:
            if isinstance(obj, pymel.nodetypes.Transform):
                libAttr.disconnectAttr(obj.tx)
                libAttr.disconnectAttr(obj.ty)
                libAttr.disconnectAttr(obj.tz)
                libAttr.disconnectAttr(obj.rx)
                libAttr.disconnectAttr(obj.ry)
                libAttr.disconnectAttr(obj.rz)
                libAttr.disconnectAttr(obj.sx)
                libAttr.disconnectAttr(obj.sy)
                libAttr.disconnectAttr(obj.sz)

        for ctrl in self.get_ctrls(recursive=False):
            ctrl.unbuild()

        if self.grp_anm is not None:
            pymel.delete(self.grp_anm)
            self.grp_anm = None
        if self.grp_rig is not None:
            pymel.delete(self.grp_rig)
            self.grp_rig = None

        self.globalScale = None

        # Reset any cached properties
        # todo: ensure it's the best way
        if '_cache' in self.__dict__:
            self.__dict__.pop('_cache')

    def get_ctrls(self, recursive=False):
        return getattrs_by_type(self, BaseCtrl, recursive=recursive)

    def get_pin_locations(self):
        """
        Return the objs that child Module can pin themself to (space-switching)
        In the vast majority of cases, the desired behavior is to return the first joint in the inputs.
        """
        first_joint = next((input for input in self.input if isinstance(input, pymel.nodetypes.Joint)), None)
        return [first_joint] if first_joint is not None else []
