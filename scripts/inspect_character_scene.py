"""Read-only Maya character scene inspection.

Example inside Maya:
    from inspect_character_scene import inspect_scene
    report = inspect_scene(
        joints=["Bip001Spine", "Bip001Head"],
        output_path="D:/project/qa/character_scene.json",
    )

No scene is opened, saved, closed, or modified by this script.
"""

import json
import os
import maya.cmds as cmds
from maya_pose_tools import mesh_bounding_metrics, scene_integrity


def _vector(node, attr):
    try:
        return list(cmds.getAttr(node + "." + attr)[0])
    except Exception:
        return None


def inspect_joint(node):
    if not cmds.objExists(node):
        return {"missing": True}
    return {
        "parent": cmds.listRelatives(node, parent=True, fullPath=True) or [],
        "children": cmds.listRelatives(node, children=True, fullPath=True) or [],
        "local_translate": _vector(node, "translate"),
        "local_rotate": _vector(node, "rotate"),
        "local_scale": _vector(node, "scale"),
        "joint_orient": _vector(node, "jointOrient"),
        "world_translate": list(cmds.xform(node, q=True, ws=True, t=True)),
        "world_rotate": list(cmds.xform(node, q=True, ws=True, ro=True)),
        "world_matrix": cmds.xform(node, q=True, ws=True, m=True),
        "rotate_connections": cmds.listConnections(node + ".rotate", s=True, d=False) or [],
        "locked_channels": {
            axis: cmds.getAttr(node + ".rotate" + axis, lock=True)
            for axis in ("X", "Y", "Z")
        },
    }


def inspect_scene(joints=None, output_path=None):
    """Return a scene report and optionally write UTF-8 JSON to output_path."""
    report = scene_integrity()
    report["maya_version"] = cmds.about(version=True)
    report["playback"] = {
        "min": cmds.playbackOptions(q=True, min=True),
        "max": cmds.playbackOptions(q=True, max=True),
        "animation_start": cmds.playbackOptions(q=True, animationStartTime=True),
        "animation_end": cmds.playbackOptions(q=True, animationEndTime=True),
    }
    report["assemblies"] = cmds.ls(assemblies=True) or []
    report["meshes"] = []
    for shape in cmds.ls(type="mesh", long=True) or []:
        if cmds.getAttr(shape + ".intermediateObject"):
            continue
        report["meshes"].append(mesh_bounding_metrics(shape))
    all_joints = cmds.ls(type="joint", long=True) or []
    report["joint_count"] = len(all_joints)
    report["joint_names"] = all_joints
    report["requested_joints"] = {
        node: inspect_joint(node) for node in (joints or [])
    }
    report["note"] = "These are scene facts only. Visual acceptance still requires rendered images and saved-scene reopening."

    if output_path:
        parent = os.path.dirname(output_path)
        if parent and not os.path.isdir(parent):
            os.makedirs(parent)
        with open(output_path, "w", encoding="utf-8") as fh:
            json.dump(report, fh, ensure_ascii=False, indent=1)
    return report
