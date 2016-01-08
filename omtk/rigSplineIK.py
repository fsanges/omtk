import math
import pymel.core as pymel
from classModule import Module
from omtk.libs import libRigging, libPymel, libPython, libFormula

# Todo: Support more complex IK limbs (ex: 2 knees)
class SplineIK(Module):
    def __init__(self, *args, **kwargs):
        super(SplineIK, self).__init__(*args, **kwargs)
        self.bStretch = True
        self.iCtrlIndex = 2
        self.ikEffector = None
        self.ikHandle = None

    def _post_setattr_inputs(self):
        super(SplineIK, self)._post_setattr_inputs()
        self._joints = [input for input in self.input if libPymel.isinstance_of_transform(input, pymel.nodetypes.Joint)]
        self._curves = [input for input in self.input if libPymel.isinstance_of_shape(input, pymel.nodetypes.CurveShape)]

    def build(self, *args, **kwargs):
        self._post_setattr_inputs() # update hack
        if len(self._joints) < 2:
            raise Exception("Can't build SplineIK. Expected at least two joints, got {0}".format(self._joints))
        if len(self._curves) < 1:
            raise Exception("Can't build SplineIK. Expected at least one nurbsCurve, got {0}".format(self._curves))

        super(SplineIK, self).build(*args, **kwargs)

        # todo: handle multiple curves?
        curve = next(iter(self._curves), None)
        curve_shape = next((shape for shape in curve.getShapes() if isinstance(shape, pymel.nodetypes.NurbsCurve)), None)

        # Create ik solver
        solver_name = self.name_rig.resolve('ikEffector')
        self.ikHandle, self.ikEffector = pymel.ikHandle(
            solver="ikSplineSolver",
            curve=curve,
            startJoint=self._joints[0],
            endEffector=self._joints[-1],
            createCurve=False,
            name=solver_name,
            parentCurve=False,
            snapCurve=False)
        self.ikHandle.setParent(self.grp_rig)

        # Create stretch
        # Todo: use shape instead of transform as curve input?
        curveLength = libRigging.create_utility_node('curveInfo', inputCurve=curve_shape.worldSpace).arcLength
        self.stretch_att = libRigging.create_utility_node('multiplyDivide', operation=2, input1X=curveLength, input2X=curveLength.get()).outputX

        # Create squash
        num_joints = len(self._joints)
        squash_atts = libRigging.create_squash_atts(self.stretch_att, num_joints)

        # Connect stretch/squash
        # Todo: Find correct axis orient
        for jnt, squash in zip(self._joints, squash_atts):
            pymel.connectAttr(self.stretch_att, jnt.sx)
            pymel.connectAttr(squash, jnt.sy)
            pymel.connectAttr(squash, jnt.sz)

        # Todo: Connect to parent?

    def unbuild(self, **kwargs):
        # hack: the ikEffector is parented to the bone chain and need to be deleted manually
        if libPymel.is_valid_PyNode(self.ikEffector):
            pymel.delete(self.ikEffector)

        super(SplineIK, self).unbuild(**kwargs)