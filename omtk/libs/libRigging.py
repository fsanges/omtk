from maya import cmds
import pymel.core as pymel
import logging
import libPymel
import libPython

'''
This method facilitate the creation of utility nodes by connecting/settings automaticly attributes.
'''
__aBasicTypes = [int, float, bool, pymel.datatypes.Matrix, pymel.datatypes.Vector]


def is_basic_type(_val):
    global __aBasicTypes
    return type(_val) in __aBasicTypes


def connect_or_set_attr(_attr, _val):
    if isinstance(_val, list) or isinstance(_val, tuple):

        # Note: List attribute and compound attribute don't have the same way of iterating.
        if _attr.isArray():
            for i, val in enumerate(_val):
                connect_or_set_attr(_attr.elementByLogicalIndex(i), val)
        elif _attr.isCompound():
            children = _attr.getChildren()
            for child, val in zip(children, _val):
                connect_or_set_attr(child, val)
        else:
            raise Exception("Can't apply value {0} on attribute {1}, need an array or compound".format(_val, _attr))

        '''
        for i, pSubValue in enumerate(_val):
            ConnectOrSetAttr(_attr.elementByLogicalIndex(i), pSubValue)
        '''
    else:
        if isinstance(_val, pymel.Attribute):
            pymel.connectAttr(_val, _attr, force=True)
        elif is_basic_type(_val):
            _attr.set(_val)
        else:
            logging.error(
                '[ConnectOrSetAttr] Invalid value for attribute {0} of type {1} and value {2}'.format(_attr.name(),
                                                                                                      type(_val),
                                                                                                      _val))
            raise TypeError


def create_utility_node(_sClass, *args, **kwargs):
    uNode = pymel.shadingNode(_sClass, asUtility=True)
    for sAttrName, pAttrValue in kwargs.items():
        if not uNode.hasAttr(sAttrName):
            raise Exception(
                '[CreateUtilityNode] UtilityNode {0} doesn\'t have an {1} attribute. Skipping it.'.format(_sClass,
                                                                                                          sAttrName))
        else:
            connect_or_set_attr(uNode.attr(sAttrName), pAttrValue)
    return uNode


#
# CtrlShapes Backup
#
def hold_ctrl_shapes(transform, parent=None):
    shapes = filter(lambda x: isinstance(x, pymel.nodetypes.CurveShape), transform.getShapes())
    snapshot = pymel.duplicate(transform, parentOnly=True, returnRootsOnly=True)[0]
    for shape in shapes:
        shape.setParent(snapshot, s=True, r=True)
    if parent:
        snapshot.setParent(parent)
    else:
        snapshot.setParent(world=True)

    new_name = '_{0}'.format(transform.name())
    cmds.rename(snapshot.longName(), new_name)  # For strange reasons, using .rename don't always work.
    return snapshot


def fetch_ctrl_shapes(source, target):
    # Remove any previous shapes
    pymel.delete(filter(lambda x: isinstance(x, pymel.nodetypes.CurveShape), target.getShapes()))
    for source_shape in source.getShapes():
        source_shape.setParent(target, r=True, s=True)
        source_shape.rename(target.name() + 'Shape')

    # TODO: Support AnnotationShapes
    pymel.delete(source)


def hold_all_ctrl_shapes(**kwargs):
    aCtrls = [o.getParent() for o in pymel.ls('anm_*', type='nurbsCurve')]
    return [hold_ctrl_shapes(oCtrl, **kwargs) for oCtrl in aCtrls]


def fetch_all_ctrl_shapes():
    ctrls = [o.getParent() for o in pymel.ls('_anm_*', type='nurbsCurve')]

    for ctrl in ctrls:
        target_name = ctrl.name()[1:]
        if pymel.objExists(target_name):
            target = pymel.PyNode(str(target_name))
            fetch_ctrl_shapes(ctrl, target)


def create_squash_atts(attr_stretch, samples):
    """
    Create attributes resolving a curve using the following formula.
    s^(e^(x^2)))
    :param attr_stretch: # The stretch attribute.
    :param samples: Number of samples to resolve.
    """
    import libFormula
    if not isinstance(attr_stretch, pymel.Attribute):
        raise IOError("Expected pymel Attribute, got {0} ({1})".format(attr_stretch, type(attr_stretch)))
    return_vals = []
    for i in range(samples):
        pos = float(i) / (samples - 1) * 2.0 - 1.0
        attr_squash = libFormula.parse("s^(e^(x^2)))", s=attr_stretch, x=pos)
        return_vals.append(attr_squash)
    return return_vals


def create_nurbsCurve_from_joints(obj_s, obj_e, samples=2, num_cvs=3):
    pos_s = obj_s.getTranslation(worldSpace=True)
    pos_e = obj_e.getTranslation(worldSpace=True)
    coords = []
    for i in range(num_cvs):
        ratio = float(i) / (num_cvs - 1)
        oord = (pos_s + (ratio * (pos_e - pos_s)))
        coords.append(oord)

    nurbsCurve = pymel.curve(d=samples, p=coords)

    return nurbsCurve


def create_hyerarchy(_oObjs):
    for i in range(1, len(_oObjs)):
        _oObjs[i].setParent(_oObjs[i-1])


def create_chain_between_objects(obj_s, obj_e, samples, parented=True):
    tm = obj_s.getMatrix(worldSpace=True)
    pos_s = obj_s.getTranslation(space='world')
    pos_e = obj_e.getTranslation(space='world')

    new_objs = []

    pymel.select(clear=True)
    for iCurJnt in range(0, samples):
        ratio = float(iCurJnt) / (samples - 1.00)
        pos = pos_s + (pos_e - pos_s) * ratio

        new_obj = pymel.duplicate(obj_s, parentOnly=True)[0]
        new_obj.setMatrix(tm)
        new_obj.setTranslation(pos, space='world')
        new_objs.append(new_obj)

    new_objs[0].setParent(world=True)
    if parented:
        create_hyerarchy(new_objs)

    return libPymel.PyNodeChain(new_objs)
from maya import OpenMaya

def get_affected_geometries(obj):
    """
    :param obj: A reference object, generally a pymel.nodetypes.Join.
    :return: The geometries affected by the object.
    """
    geometries = set()

    if isinstance(obj, pymel.nodetypes.Joint):
        # Collect all geometries affected by the joint.
        skinClusters = set()
        for hist in obj.listHistory(future=True):
            if isinstance(hist, pymel.nodetypes.SkinCluster):
                skinClusters.add(hist)

        for skinCluster in skinClusters:
            geometries.update(skinCluster.getOutputGeometry())

    return geometries


def reshape_ctrl(ctrl_shape, ref, multiplier=1.25):
    if not isinstance(ctrl_shape, pymel.nodetypes.NurbsCurve):
        raise Exception("Unexpected input, expected NurbsCurve, got {0}.".format(type(ctrl_shape)))

    geometries = get_affected_geometries(ref)
    if not geometries:
        print "Cannot resize {0}, found no affected geometries!".format(ctrl_shape)
        return
    pos = ctrl_shape.getParent().getTranslation(space='world')
    pos = OpenMaya.MPoint(pos.x, pos.y, pos.z)

    results = OpenMaya.MPointArray()

    for i in range(ctrl_shape.numCVs()):
        cv_pos = ctrl_shape.cv[i].getPosition(space='world')
        length = None
        dir = cv_pos - pos
        dir.normalize()
        dir = OpenMaya.MVector(dir.x, dir.y, dir.z)

        # Resolve desired new length using raycast projection.
        for geometry in geometries:
            mfn_geometry = geometry.__apimfn__()
            if mfn_geometry.intersect(pos, dir, results, 1.0e-10, OpenMaya.MSpace.kWorld):
                cur_length = results[0].distanceTo(pos)
                if length is None or cur_length > length:
                    length = cur_length

        if length is None:
            continue

        cv_new_pos = pos + (dir * length * multiplier)
        ctrl_shape.cv[i].setPosition(cv_new_pos, space='world')


@libPython.memoized
def get_recommended_ctrl_size(obj, default_value=1.0, weight_x=0.0, weight_neg_x=0.0, weight_y=1.0,
                              weight_neg_y=1.0, weight_z=0.0, weight_neg_z=0.0):
    """
    Return the recommended size of a controller if it was created for this obj.
    :param obj: The object to analyze.
    """
    # TODO: Move to a cleaner location?
    if isinstance(obj, pymel.nodetypes.Joint):

        # Collect all geometries affected by the joint.
        skinClusters = set()
        for hist in obj.listHistory(future=True):
            if isinstance(hist, pymel.nodetypes.SkinCluster):
                skinClusters.add(hist)
        geometries = set()
        for skinCluster in skinClusters:
            geometries.update(skinCluster.getOutputGeometry())

        # Create a number of raycast for each geometry. Use the longuest distance.
        # Note that we are not using the negative Y axis, this give bettern result for example on shoulders.
        ref_tm = obj.getMatrix(worldSpace=True)
        pos = ref_tm.translate
        pos = OpenMaya.MPoint(pos.x, pos.y, pos.z)

        dirs = []
        if weight_x:
            dirs.append(OpenMaya.MVector(ref_tm.a00, ref_tm.a01, ref_tm.a02))  # X Axis
        if weight_neg_x:
            dirs.append(OpenMaya.MVector(-ref_tm.a00, -ref_tm.a01, -ref_tm.a02))  # X Axis
        if weight_y:
            dirs.append(OpenMaya.MVector(ref_tm.a10, ref_tm.a11, ref_tm.a12))  # Y Axis
        if weight_neg_y:
            dirs.append(OpenMaya.MVector(-ref_tm.a10, -ref_tm.a11, -ref_tm.a12))  # Y Axis
        if weight_z:
            dirs.append(OpenMaya.MVector(ref_tm.a20, ref_tm.a21, ref_tm.a22))  # Z Axis
        if weight_neg_z:
            dirs.append(OpenMaya.MVector(-ref_tm.a20, -ref_tm.a21, -ref_tm.a22))  # Z Axis

        length = 0
        results = OpenMaya.MPointArray()
        for geometry in geometries:
            mfn_geo = geometry.__apimfn__()
            for dir in dirs:
                if mfn_geo.intersect(pos, dir, results, 1.0e-10, OpenMaya.MSpace.kWorld):
                    cur_length = min((results[0].distanceTo(pos) for i in range(results.length())))
                    if cur_length > length:
                        length = cur_length
        if not length:
            length = obj.radius.get()
        return length

    print "Cannot get recommended size for {0}, return default value of {1}".format(
        obj.name(), default_value
    )
    return default_value


# TODO: Benchmark performances
def snap(obj_dst, obj_src):
    obj_dst.setMatrix(obj_src.getMatrix(worldSpace=True), worldSpace=True)
