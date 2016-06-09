from omtk.modules import rigFaceAvar
from omtk.modules import rigFaceAvarGrps
from omtk.libs import libCtrlShapes
from omtk.libs import libRigging
from omtk.libs import libAttr
import pymel.core as pymel

class CtrlJaw(rigFaceAvar.BaseCtrlFace):
    def __createNode__(self, **kwargs):
        node = libCtrlShapes.create_triangle_low()
        node.r.lock()
        node.s.lock()
        return node


class AvarJaw(rigFaceAvar.AvarSimple):
    """
    This avar is not designed to use any surface.
    """
    SHOW_IN_UI = False
    _CLS_CTRL = CtrlJaw
    IS_SIDE_SPECIFIC = False

    def get_module_name(self):
        return 'Jaw'

    def get_ctrl_tm(self, rig):
        """
        Find the chin location. This is the preffered location for the jaw doritos.
        :return:
        """
        # TODO: Prevent multiple calls? cached?
        jnt = next(iter(self.jnts), None)
        geos = rig.get_meshes()
        if not geos:
            return super(AvarJaw, self).get_ctrl_tm(rig)

        ref = jnt.getMatrix(worldSpace=True)
        pos_s = pymel.datatypes.Point(jnt.getTranslation(space='world'))
        pos_e = pymel.datatypes.Point(1,0,0) * ref
        dir = pos_e - pos_s
        result = libRigging.ray_cast_farthest(pos_s, dir, geos)
        if not result:
            raise Exception("Can't resolve doritos location for {0}".format(self))

        tm = pymel.datatypes.Matrix([1,0,0,0, 0,1,0,0, 0,0,1,0, result.x, result.y, result.z, 1])
        return tm

    def connect_ctrl(self, ctrl, **kwargs):
        attr_pt_inn = ctrl.translateY
        attr_yw_inn = ctrl.translateX

        # UD Low
        attr_pt_low = libRigging.create_utility_node('multiplyDivide', input1X=attr_pt_inn, input2X=-1).outputX
        '''
        attr_pt_inn = libRigging.create_utility_node('condition', operation=4,  # Less than
                                       firstTerm=attr_pt_inn,
                                       colorIfTrueR=attr_pt_low,
                                       colorIfFalseR=0.0
                                       ).outColorR
        '''

        libRigging.connectAttr_withLinearDrivenKeys(
            attr_pt_low, self.attr_pt, kv=[0.0, 0.0, 10.0]
        )
        libRigging.connectAttr_withLinearDrivenKeys(
            attr_yw_inn, self.attr_yw, kv=[-5.0, 0.0, 5.0]
        )

    def build(self, *args, **kwargs):
        super(AvarJaw, self).build(*args, **kwargs)

        # HACK: Hijack the jaw PT avar so the jaw don't go over 0.
        # TODO: Bulletproof
        attr_pt_out = next(iter(self.attr_pt.outputs(plugs=True, skipConversionNodes=True)), None)

        attr_pt_clamp = libRigging.create_utility_node('condition', operation=2,  # Greater than
                                       firstTerm=self.attr_pt,
                                       colorIfTrueR=self.attr_pt,
                                       colorIfFalseR=0.0
                                       ).outColorR
        pymel.connectAttr(attr_pt_clamp, attr_pt_out, force=True)


class FaceJaw(rigFaceAvarGrps.AvarGrp):
    """
    The Jaw is a special zone since it doesn't happen in pre-deform, it happen in the main skinCluster.
    The Jaw global avars are made
    """
    _CLS_AVAR = AvarJaw
    SHOW_IN_UI = True


