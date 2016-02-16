"""
An avar is a facial control unit inspired from The Art of Moving Points.
This is the foundation for the facial animation modules.
"""
import pymel.core as pymel
from omtk import classCtrl, classModule, classNode
from omtk import classModule
from omtk import classNode
from omtk.libs import libPymel, libPython, libRigging
from omtk.libs import libPython
from omtk.libs import libRigging
from omtk.libs import libCtrlShapes


class CtrlFaceMicro(classCtrl.BaseCtrl):
    """
    If you need specific ctrls for you module, you can inherit from BaseCtrl directly.
    """

    def __createNode__(self, normal=(0, 0, 1), **kwargs):
        return super(CtrlFaceMicro, self).__createNode__(normal=normal, **kwargs)


class CtrlFaceMacro(classCtrl.BaseCtrl):
    ATTR_NAME_SENSIBILITY = 'sensibility'

    def __createNode__(self, normal=(0, 0, 1), **kwargs):
        return libCtrlShapes.create_square(normal=normal, **kwargs)

    def __init__(self, *args, **kwargs):
        super(CtrlFaceMacro, self).__init__(*args, **kwargs)
        self.sensibility = 0.5
        self._attr_sensibility = None

    def build(self, sensibility=None, *args, **kwargs):
        super(CtrlFaceMacro, self).build(*args, **kwargs)

        # Create sensibility setup
        # This allow us to tweak how much the ctrl is sensible to movement.
        # The secret is to scale the ctrl offset node and adjust the shape in consequence.
        pymel.addAttr(self.node, longName=self.ATTR_NAME_SENSIBILITY, defaultValue=sensibility, k=True)
        self._attr_sensibility = self.node.attr(self.ATTR_NAME_SENSIBILITY)
        attr_sensibility_inv = libRigging.create_utility_node('multiplyDivide', operation=2, input1X=1.0,
                                                              input2X=self._attr_sensibility).outputX
        '''
        if sensibility is None:
            sensibility = self.sensibility
        else:
            self.sensibility = sensibility
        '''

        scaleInv = self.add_layer('scaleInv')

        pymel.connectAttr(attr_sensibility_inv, scaleInv.scaleX)
        pymel.connectAttr(attr_sensibility_inv, scaleInv.scaleY)
        pymel.connectAttr(attr_sensibility_inv, scaleInv.scaleZ)

        ctrl_shape = self.node.getShape()  # Note: this only work with single shape
        ctrl_shape_orig = pymel.duplicate(self.node.getShape())[0]
        ctrl_shape_orig.intermediateObject.set(True)
        ctrl_shape_orig.setParent(self.offset, shape=True, relative=True)

        attr_adjustement_tm = libRigging.create_utility_node('composeMatrix', inputScaleX=self._attr_sensibility,
                                                             inputScaleY=self._attr_sensibility,
                                                             inputScaleZ=self._attr_sensibility).outputMatrix
        attr_transform_geometry = libRigging.create_utility_node('transformGeometry', transform=attr_adjustement_tm,
                                                                 inputGeometry=ctrl_shape_orig.local).outputGeometry
        pymel.connectAttr(attr_transform_geometry, ctrl_shape.create)

    # TODO: SHOULD NOT BE NEEDED, MAKE BaseCtrl MORE INTELLIGENT
    def unbuild(self):
        self.sensibility = self._attr_sensibility.get()
        self._attr_sensibility = None
        super(CtrlFaceMacro, self).unbuild()


class Avar(classModule.Module):
    """
    This low-level module is a direct interpretation of "The Art of Moving Points" of "Brian Tindal".
    A can be moved in space using it's UD (Up/Down), IO (Inn/Out) and FB (FrontBack) attributes.
    In general, changing thoses attributes will make the FacePnt move on a NurbsSurface.
    """
    AVAR_NAME_UD = 'avar_ud'
    AVAR_NAME_LR = 'avar_lr'
    AVAR_NAME_FB = 'avar_fb'
    AVAR_NAME_YAW = 'avar_yw'
    AVAR_NAME_PITCH = 'avar_pt'
    AVAR_NAME_ROLL = 'avar_rl'

    def __init__(self, *args, **kwargs):
        super(Avar, self).__init__(*args, **kwargs)
        self.attr_avar_up = None
        self.attr_avar_lr = None
        self.attr_aval_fb = None
        self.attr_aval_yw = None
        self.attr_aval_pt = None
        self.attr_aval_rl = None

        self.ctrl_micro = None

    @libPython.cached_property()
    def jnt(self):
        fn_is_nurbsSurface = lambda obj: libPymel.isinstance_of_transform(obj, pymel.nodetypes.Joint)
        objs = filter(fn_is_nurbsSurface, self.input)
        return next(iter(objs), None)

    def _build_dag_stack(self, rig):
        """
        The dag stack is a stock of dagnode that act as additive deformer to controler the final position of
        the drived joint.
        """
        nomenclature_rig = self.get_nomenclature_rig(rig)
        dag_stack_name = nomenclature_rig.resolve('stack')
        stack = classNode.Node(name=dag_stack_name)
        stack.build()

        # Create an offset layer so everything start at the same parent space.
        layer_offset_name = nomenclature_rig.resolve('offset')
        layer_offset = stack.add_layer()
        layer_offset.rename(layer_offset_name)
        layer_offset.setMatrix(self.jnt.getMatrix(worldSpace=True))

        # Create a layer before the ctrl to apply the YW, PT and RL avar.
        layer_rot_name = nomenclature_rig.resolve('rot')
        layer_rot = stack.add_layer()
        layer_rot.rename(layer_rot_name)

        pymel.connectAttr(self.attr_avar_yw, layer_rot.rotateX)
        pymel.connectAttr(self.attr_avar_pt, layer_rot.rotateY)
        pymel.connectAttr(self.attr_avar_rl, layer_rot.rotateZ)

        return stack

    def _add_avar_attrs(self):
        # Define macro avars
        libPymel.addAttr_separator(self.grp_rig, 'Avars')

        pymel.addAttr(self.grp_rig, longName=self.AVAR_NAME_UD, k=True)
        self.attr_avar_ud = self.grp_rig.attr(self.AVAR_NAME_UD)
        pymel.addAttr(self.grp_rig, longName=self.AVAR_NAME_LR, k=True)
        self.attr_avar_lr = self.grp_rig.attr(self.AVAR_NAME_LR)
        pymel.addAttr(self.grp_rig, longName=self.AVAR_NAME_FB, k=True)
        self.attr_avar_fb = self.grp_rig.attr(self.AVAR_NAME_FB)
        pymel.addAttr(self.grp_rig, longName=self.AVAR_NAME_YAW, k=True)
        self.attr_avar_yw = self.grp_rig.attr(self.AVAR_NAME_YAW)
        pymel.addAttr(self.grp_rig, longName=self.AVAR_NAME_PITCH, k=True)
        self.attr_avar_pt = self.grp_rig.attr(self.AVAR_NAME_PITCH)
        pymel.addAttr(self.grp_rig, longName=self.AVAR_NAME_ROLL, k=True)
        self.attr_avar_rl = self.grp_rig.attr(self.AVAR_NAME_ROLL)

    def _create_doritos_setup_2(self, rig, ctrl):
        """
        A doritos setup allow a ctrl to be directly constrained on the final mesh via a follicle.
        To prevent double deformation, the trick is an additional layer before the final ctrl that invert the movement.
        For clarity purposes, this is built in the rig so the animator don't need to see the whole setup.
        """
        nomenclature_rig = self.get_nomenclature_rig(rig)

        obj_mesh = libRigging.get_farest_affected_mesh(self.jnt)
        if obj_mesh is None:
            pymel.warning("Can't find mesh affected by {0}. Skipping doritos ctrl setup.")
            return False

        # doritos_name
        stack_name = nomenclature_rig.resolve('doritos_stack')
        stack = classNode.Node(self, name=stack_name)
        # stack.rename(stack_name)
        stack.build(rig)
        stack.setMatrix(ctrl.getMatrix(worldSpace=True))

        layer_doritos_fol_name = nomenclature_rig.resolve('doritos_fol')
        layer_doritos_fol = stack.add_layer()
        layer_doritos_fol.rename(layer_doritos_fol_name)

        layer_doritos_name = nomenclature_rig.resolve('doritos_inv')
        layer_doritos = stack.add_layer()
        layer_doritos.rename(layer_doritos_name)

        attr_ctrl_inv_t = libRigging.create_utility_node('multiplyDivide', input1=ctrl.t, input2=[-1, -1, -1]).output
        attr_ctrl_inv_r = libRigging.create_utility_node('multiplyDivide', input1=ctrl.r, input2=[-1, -1, -1]).output
        pymel.connectAttr(attr_ctrl_inv_t, layer_doritos.t)
        pymel.connectAttr(attr_ctrl_inv_r, layer_doritos.r)

        # TODO: Validate that we don't need to inverse the rotation separately.

        libRigging.create_follicle(layer_doritos_fol, obj_mesh)

        # The doritos setup can be hard to control when the rotation of the controller depend on the follicle since
        # any deformation can affect the normal of the faces.
        jnt_head = rig.get_head_jnt()
        if jnt_head:
            pymel.disconnectAttr(layer_doritos_fol.rx)
            pymel.disconnectAttr(layer_doritos_fol.ry)
            pymel.disconnectAttr(layer_doritos_fol.rz)
            pymel.orientConstraint(jnt_head, layer_doritos_fol, maintainOffset=True)

        stack.setParent(self.grp_rig)

        return layer_doritos

    def build(self, rig, constraint=True, **kwargs):
        """
        Any FacePnt is controlled via "avars" (animation variables) in reference to "The Art of Moving Points".
        """
        super(Avar, self).build(rig)
        nomenclature_anm = self.get_nomenclature_anm(rig)
        nomenclature_rig = self.get_nomenclature_rig(rig)

        ref_tm = self.jnt.getMatrix(worldSpace=True)

        self._add_avar_attrs()

        dag_stack_name = nomenclature_rig.resolve('dagStack')
        self._dag_stack = self._build_dag_stack(rig, **kwargs)
        self._dag_stack.setMatrix(ref_tm)
        self._dag_stack.setParent(self.grp_rig)

        #
        # Create the layers for the manual ctrl
        # Any avar can be manually overrided by the animator using a small controller.
        # TODO: Automatically project the ctrl on the face yo
        #

        layer_ctrl_name = nomenclature_rig.resolve('perCtrl')
        layer_ctrl = self._dag_stack.add_layer(name=layer_ctrl_name)
        layer_ctrl.rename(layer_ctrl_name)

        ctrl_offset_name = nomenclature_anm.resolve('offset')
        if not isinstance(self.ctrl_micro, CtrlFaceMicro):
            self.ctrl_micro = CtrlFaceMicro()
        self.ctrl_micro.build(name=ctrl_offset_name)
        self.ctrl_micro.setParent(self.grp_anm)
        self.ctrl_micro.setMatrix(self.jnt.getMatrix(worldSpace=True))

        util_decomposeTM = libRigging.create_utility_node('decomposeMatrix',
                                                          inputMatrix=layer_ctrl.worldMatrix
                                                          )
        # pymel.parentConstraint(self.ctrl_offset.offset)
        pymel.connectAttr(util_decomposeTM.outputTranslate, self.ctrl_micro.offset.translate)
        pymel.connectAttr(util_decomposeTM.outputRotate, self.ctrl_micro.offset.rotate)

        # pymel.parentConstraint(layer_offset, self.ctrl_offset.offset)
        pymel.connectAttr(self.ctrl_micro.translate, layer_ctrl.translate)
        pymel.connectAttr(self.ctrl_micro.rotate, layer_ctrl.rotate)
        pymel.connectAttr(self.ctrl_micro.scale, layer_ctrl.scale)

        doritos = self._create_doritos_setup_2(rig, self.ctrl_micro)

        pymel.parentConstraint(doritos, self.ctrl_micro.offset, maintainOffset=False)

        if constraint:
            pymel.parentConstraint(self._dag_stack.node, self.jnt)


class AvarFollicle(Avar):
    ATTR_NAME_U_BASE = 'BaseU'
    ATTR_NAME_V_BASE = 'BaseV'
    ATTR_NAME_U = 'U'
    ATTR_NAME_V = 'V'
    ATTR_NAME_U_MULT = 'UMultiplier'
    ATTR_NAME_V_MULT = 'VMultiplier'

    """
    A FacePnt on wich the UD and LR avar controls a movement on a nurbsSurface using follicles.
    """

    def __init__(self, *args, **kwargs):
        super(AvarFollicle, self).__init__(*args, **kwargs)
        self._attr_u_base = None
        self._attr_v_base = None
        self._attr_u_mult_inn = None
        self._attr_v_mult_inn = None

    @libPython.cached_property()
    def surface(self):
        fn_is_nurbsSurface = lambda obj: libPymel.isinstance_of_shape(obj, pymel.nodetypes.NurbsSurface)
        objs = filter(fn_is_nurbsSurface, self.input)
        return next(iter(objs), None)

    def _build_dag_stack(self, rig, mult_u=1.0, mult_v=1.0):
        stack = super(AvarFollicle, self)._build_dag_stack(rig)

        jnt_tm = self.jnt.getMatrix(worldSpace=True)
        nomenclature_rig = self.get_nomenclature_rig(rig)

        #
        # Create follicle setup
        #

        # Create two follicles, one for the "bind pose" and one for the deformation.
        offset_name = nomenclature_rig.resolve('bindPose')
        obj_offset = pymel.createNode('transform', name=offset_name)
        obj_offset.setMatrix(jnt_tm)
        obj_offset.setParent(stack._layers[0])

        fol_offset_name = nomenclature_rig.resolve('bindPoseFollicle')
        fol_offset = libRigging.create_follicle(obj_offset, self.surface, name=fol_offset_name)
        fol_offset.setParent(self.grp_rig)

        influence_name = nomenclature_rig.resolve('influence')
        influence = pymel.createNode('transform', name=influence_name)
        influence.setMatrix(jnt_tm)
        influence.setParent(stack._layers[0])

        fol_influence_name = nomenclature_rig.resolve('influenceFollicle')
        fol_influence = libRigging.create_follicle(influence, self.surface, name=fol_influence_name)
        fol_influence.setParent(self.grp_rig)

        # Extract the delta of the influence follicle and it's initial pose follicle
        tm_local_displacement = libRigging.create_utility_node('multMatrix', matrixIn=[
            influence.worldMatrix,
            obj_offset.worldInverseMatrix
        ]).matrixSum
        util_decomposeTM = libRigging.create_utility_node('decomposeMatrix',
                                                          inputMatrix=tm_local_displacement
                                                          )

        layer_follicle_name = 'follicle'
        layer_follicle = stack.add_layer(name=layer_follicle_name)
        pymel.connectAttr(util_decomposeTM.outputTranslate, layer_follicle.translate)
        pymel.connectAttr(util_decomposeTM.outputRotate, layer_follicle.rotate)

        # Create and connect follicle-related parameters
        u_base = fol_influence.parameterU.get()
        v_base = 0.5  # fol_influence.parameterV.get()

        self._attr_u_base = libPymel.addAttr(self.grp_rig, longName=self.ATTR_NAME_U_BASE, defaultValue=u_base)
        self._attr_v_base = libPymel.addAttr(self.grp_rig, longName=self.ATTR_NAME_V_BASE, defaultValue=v_base)

        attr_u_inn = libPymel.addAttr(self.grp_rig, longName=self.ATTR_NAME_U, k=True)
        attr_v_inn = libPymel.addAttr(self.grp_rig, longName=self.ATTR_NAME_V, k=True)

        self._attr_u_mult_inn = libPymel.addAttr(self.grp_rig, longName=self.ATTR_NAME_U_MULT, defaultValue=mult_u)
        self._attr_v_mult_inn = libPymel.addAttr(self.grp_rig, longName=self.ATTR_NAME_V_MULT, defaultValue=mult_v)

        #attr_u_inn = libRigging.create_utility_node('multiplyDivide', input1X=attr_u_inn, input2X=mult_u).outputX
        #attr_v_inn = libRigging.create_utility_node('multiplyDivide', input1X=attr_v_inn, input2X=mult_v).outputX

        # Connect UD to V
        attr_get_v_offset = libRigging.create_utility_node('multiplyDivide',
                                                           input1X=self.attr_avar_ud,
                                                           input2X=0.5
                                                           ).outputX
        attr_get_v_multiplied = libRigging.create_utility_node('multiplyDivide',
                                                               input1X=attr_get_v_offset,
                                                               input2X=self._attr_v_mult_inn).outputX
        attr_v_cur = libRigging.create_utility_node('addDoubleLinear',
                                                    input1=self._attr_v_base,
                                                    input2=attr_get_v_multiplied
                                                    ).output
        pymel.connectAttr(attr_v_cur, attr_v_inn)

        # Connect LR to U
        attr_get_u_offset = libRigging.create_utility_node('multiplyDivide',
                                                           input1X=self.attr_avar_lr,
                                                           input2X=0.5
                                                           ).outputX
        attr_get_u_multiplied = libRigging.create_utility_node('multiplyDivide',
                                                               input1X=attr_get_u_offset,
                                                               input2X=self._attr_u_mult_inn).outputX
        attr_u_cur = libRigging.create_utility_node('addDoubleLinear',
                                                    input1=self._attr_u_base,
                                                    input2=attr_get_u_multiplied
                                                    ).output
        pymel.connectAttr(attr_u_cur, attr_u_inn)

        pymel.connectAttr(attr_u_inn, fol_influence.parameterU)
        pymel.connectAttr(attr_v_inn, fol_influence.parameterV)
        pymel.connectAttr(self._attr_u_base, fol_offset.parameterU)
        pymel.connectAttr(self._attr_v_base, fol_offset.parameterV)

        #
        # Connect UD and LR avar to their respective follicle.
        #
        return stack

    def unbuild(self):
        super(AvarFollicle, self).unbuild()
        self._attr_u_base = None
        self._attr_v_base = None
        self._attr_u_mult_inn = None
        self._attr_v_mult_inn = None
