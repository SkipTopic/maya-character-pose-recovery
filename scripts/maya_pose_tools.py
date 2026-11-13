"""Maya 2024-compatible pose diagnostics and analytic two-bone IK tools.

Run inside Maya. Functions do not open, save, or overwrite scenes.
All positions and targets are world-space values in the scene's linear unit.
"""

import math
import maya.cmds as cmds
import maya.api.OpenMaya as om


def world_position(node):
    """Return the evaluated world translation of a DAG node."""
    return list(cmds.xform(node, q=True, ws=True, t=True))


def world_rotation(node):
    """Return the evaluated world Euler rotation in degrees."""
    return list(cmds.xform(node, q=True, ws=True, ro=True))


def distance(a, b):
    return math.sqrt(sum((a[i] - b[i]) ** 2 for i in range(3)))


def _long(node):
    nodes = cmds.ls(node, long=True) or []
    if not nodes:
        raise ValueError("Missing DAG node: %s" % node)
    return nodes[0]


def _is_descendant(node, ancestor):
    current = _long(node)
    ancestor = _long(ancestor)
    while True:
        parents = cmds.listRelatives(current, parent=True, fullPath=True) or []
        if not parents:
            return False
        current = parents[0]
        if current == ancestor:
            return True


def _assert_writable_rotation(node):
    incoming = cmds.listConnections(node + ".rotate", s=True, d=False) or []
    if incoming:
        raise RuntimeError("Rotation has incoming connections; bake or intentionally remove them first: %s -> %s" % (node, incoming))


def _apply_world_rotation(node, euler_degrees):
    """Apply an absolute world orientation through a temporary orient constraint."""
    _assert_writable_rotation(node)
    locator = None
    constraint = None
    try:
        locator = cmds.spaceLocator(name="TMP_POSE_RECOVERY_ROT")[0]
        cmds.xform(locator, ws=True, ro=list(euler_degrees))
        constraint = cmds.orientConstraint(locator, node, maintainOffset=False)[0]
        cmds.refresh(force=True)
    finally:
        if constraint and cmds.objExists(constraint):
            cmds.delete(constraint)
        if locator and cmds.objExists(locator):
            cmds.delete(locator)
        cmds.refresh(force=True)


def rotate_world_delta(node, delta):
    """Apply a world-space delta using Maya's row-vector convention.

    The source case proved that the delta must be right-multiplied:
        new_q = old_q * delta
    Using delta * old_q twists characters with rotated parent hierarchies.
    """
    world = om.MMatrix(cmds.xform(node, q=True, ws=True, m=True))
    transform = om.MTransformationMatrix(world)
    old_q = transform.rotation(asQuaternion=True)
    new_q = old_q * delta
    euler = new_q.asEulerRotation()
    _apply_world_rotation(node, [math.degrees(euler.x), math.degrees(euler.y), math.degrees(euler.z)])


def align_world_bone(node, child, desired_position):
    """Rotate node so the node->child direction points at desired_position."""
    origin = om.MVector(*world_position(node))
    current = om.MVector(*world_position(child)) - origin
    desired = om.MVector(*desired_position) - origin
    if current.length() < 0.0001 or desired.length() < 0.0001:
        raise ValueError("Cannot align a zero-length bone or zero-length target direction")
    current.normalize()
    desired.normalize()
    dot = max(-1.0, min(1.0, current * desired))
    if dot > 0.999999999:
        return
    # This two-vector constructor works in the tested Maya 2024 OpenMaya API.
    delta = om.MQuaternion(current, desired)
    rotate_world_delta(node, delta)


def solve_two_bone_world(start, middle, end, target, pole, iterations=3,
                         preserve_end_rotation=True, tolerance=0.01,
                         raise_on_error=False):
    """Solve a two-bone chain analytically in world space and bake rotations.

    Explicitly provide start/middle/end to avoid confusing twist bones with elbows.
    The target is clamped to the reachable annulus. The returned error is measured
    from the evaluated end position, never from an IK handle position.

    No IK handle is left behind. Temporary constraints and locators are removed.
    """
    for node in (start, middle, end):
        _long(node)
    if len({_long(start), _long(middle), _long(end)}) != 3:
        raise ValueError("start, middle and end must be different joints")
    if not _is_descendant(middle, start) or not _is_descendant(end, middle):
        raise ValueError("Expected start -> ... -> middle -> ... -> end hierarchy")

    source = om.MVector(*world_position(start))
    requested = om.MVector(*target)
    pole_v = om.MVector(*pole)
    l1 = distance(world_position(start), world_position(middle))
    l2 = distance(world_position(middle), world_position(end))
    if l1 < 0.0001 or l2 < 0.0001:
        raise ValueError("Two-bone lengths must be nonzero: %s" % [l1, l2])

    ray = requested - source
    raw_distance = ray.length()
    if raw_distance < 0.0001:
        raise ValueError("IK target overlaps the start joint")
    ray.normalize()
    epsilon = max(0.001, min(0.01, (l1 + l2) * 0.001))
    min_distance = abs(l1 - l2) + epsilon
    max_distance = l1 + l2 - epsilon
    solved_distance = min(max(raw_distance, min_distance), max_distance)
    effective_target = source + ray * solved_distance

    pole_ray = pole_v - source
    pole_ray = pole_ray - ray * (pole_ray * ray)
    if pole_ray.length() < 0.0001:
        raise ValueError("Pole is collinear with the start->target axis")
    pole_ray.normalize()

    along = (l1 * l1 + solved_distance * solved_distance - l2 * l2) / (2.0 * solved_distance)
    height_squared = l1 * l1 - along * along
    if height_squared < -0.0001:
        raise RuntimeError("No valid middle-joint solution; check bone lengths and target")
    height = math.sqrt(max(height_squared, 0.0))
    middle_v = source + ray * along + pole_ray * height
    middle_target = [middle_v.x, middle_v.y, middle_v.z]
    effective = [effective_target.x, effective_target.y, effective_target.z]
    end_rest_rotation = world_rotation(end)

    for _ in range(max(1, int(iterations))):
        align_world_bone(start, middle, middle_target)
        align_world_bone(middle, end, effective)

    if preserve_end_rotation:
        _apply_world_rotation(end, end_rest_rotation)

    got = world_position(end)
    error = distance(effective, got)
    result = {
        "solver": "analytic_world_two_bone",
        "start": _long(start),
        "middle": _long(middle),
        "end": _long(end),
        "bone_lengths": [l1, l2],
        "requested_target": list(requested),
        "effective_target": effective,
        "middle_target": middle_target,
        "actual_end": got,
        "actual_middle": world_position(middle),
        "error": error,
        "target_was_clamped": abs(raw_distance - solved_distance) > 0.000001,
        "rotations": {
            node: list(cmds.getAttr(node + ".rotate")[0])
            for node in (start, middle, end)
        },
    }
    if raise_on_error and error > tolerance:
        raise RuntimeError("Two-bone result missed target: %.6f > %.6f; %s" % (error, tolerance, result))
    return result


def torso_angle_from_up(start, head, up=(0.0, 1.0, 0.0)):
    """Measure the actual world-space torso direction instead of local Euler X."""
    a = om.MVector(*world_position(start))
    b = om.MVector(*world_position(head))
    direction = b - a
    if direction.length() < 0.0001:
        raise ValueError("Torso start and head overlap")
    direction.normalize()
    up_v = om.MVector(*up).normal()
    dot = max(-1.0, min(1.0, direction * up_v))
    return math.degrees(math.acos(dot))


def _mesh_fn(mesh):
    shapes = cmds.listRelatives(mesh, shapes=True, ni=True, fullPath=True) or []
    if cmds.objectType(mesh, isAType="shape"):
        shapes = [_long(mesh)]
    if not shapes:
        raise ValueError("No non-intermediate mesh shape found: %s" % mesh)
    selection = om.MSelectionList()
    selection.add(shapes[0])
    return shapes[0], om.MFnMesh(selection.getDagPath(0))


def mesh_bounding_metrics(mesh):
    """Return evaluated mesh parent, bbox, size, visibility and skin information."""
    shape, fn = _mesh_fn(mesh)
    transform = cmds.listRelatives(shape, parent=True, fullPath=True)[0]
    bbox = list(cmds.xform(transform, q=True, ws=True, bb=True))
    return {
        "shape": shape,
        "transform": transform,
        "parent": cmds.listRelatives(transform, parent=True, fullPath=True) or [],
        "visible": cmds.getAttr(transform + ".visibility"),
        "bbox": bbox,
        "size": [bbox[3] - bbox[0], bbox[4] - bbox[1], bbox[5] - bbox[2]],
        "lowest_y": bbox[1],
        "vertices": fn.numVertices,
        "skin_clusters": cmds.listConnections(shape, type="skinCluster") or [],
    }


def count_vertices_in_box(mesh, bbox_min, bbox_max, shrink=0.0):
    """Count world-space vertices strictly inside an axis-aligned box."""
    _shape, fn = _mesh_fn(mesh)
    count = 0
    for point in fn.getPoints(om.MSpace.kWorld):
        if (bbox_min[0] + shrink < point.x < bbox_max[0] - shrink and
                bbox_min[1] + shrink < point.y < bbox_max[1] - shrink and
                bbox_min[2] + shrink < point.z < bbox_max[2] - shrink):
            count += 1
    return count


def count_vertices_in_vertical_cylinder(mesh, center_x, center_z, radius, y_min, y_max):
    """Count world-space vertices inside a vertical cylinder, useful for tables."""
    _shape, fn = _mesh_fn(mesh)
    count = 0
    radius_squared = radius * radius
    for point in fn.getPoints(om.MSpace.kWorld):
        dx = point.x - center_x
        dz = point.z - center_z
        if y_min < point.y < y_max and dx * dx + dz * dz < radius_squared:
            count += 1
    return count


def scene_integrity():
    """Collect non-visual integrity facts; do not treat them as visual proof."""
    cameras = cmds.ls(type="camera", long=True) or []
    return {
        "scene": cmds.file(q=True, sceneName=True),
        "modified": cmds.file(q=True, modified=True),
        "linear_unit": cmds.currentUnit(q=True, linear=True),
        "time_unit": cmds.currentUnit(q=True, time=True),
        "references": cmds.file(q=True, reference=True) or [],
        "file_texture_nodes": cmds.ls(type="file") or [],
        "unknown_nodes": cmds.ls(type="unknown") or [],
        "blend_shapes": cmds.ls(type="blendShape") or [],
        "animation_curves": cmds.ls(type="animCurve") or [],
        "ik_handles": cmds.ls(type="ikHandle") or [],
        "delta_mush": cmds.ls(type="deltaMush") or [],
        "camera_shapes": cameras,
    }


__all__ = [
    "world_position",
    "world_rotation",
    "distance",
    "rotate_world_delta",
    "align_world_bone",
    "solve_two_bone_world",
    "torso_angle_from_up",
    "mesh_bounding_metrics",
    "count_vertices_in_box",
    "count_vertices_in_vertical_cylinder",
    "scene_integrity",
]
