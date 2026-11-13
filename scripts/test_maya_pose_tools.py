"""Temporary-joint smoke test for maya_pose_tools inside Maya.

Run after saving important work. The test creates only a temporary joint chain,
never opens or saves a scene, and removes its temporary nodes in finally.
"""

import json
import os
import maya.cmds as cmds
from maya_pose_tools import solve_two_bone_world, world_position


def run_test(output_path=None):
    group = None
    report = {"ok": False}
    try:
        before_rot_helpers = set(cmds.ls("TMP_POSE_RECOVERY_ROT*", long=True) or [])
        group = cmds.group(empty=True, name="TMP_POSE_RECOVERY_TEST_GROUP")
        cmds.select(clear=True)
        start = cmds.joint(p=[0.0, 50.0, 0.0], name="TMP_TEST_START")
        cmds.select(clear=True)
        middle = cmds.joint(p=[0.0, 50.0, 30.0], name="TMP_TEST_MIDDLE")
        cmds.select(clear=True)
        end = cmds.joint(p=[0.0, 10.0, 30.0], name="TMP_TEST_END")
        cmds.parent(middle, start)
        cmds.parent(end, middle)
        cmds.parent(start, group)
        cmds.setAttr(group + ".rotate", 20.0, 35.0, -10.0)
        cmds.setAttr(group + ".scale", 1.2, 1.2, 1.2)
        cmds.refresh(force=True)

        current_end = world_position(end)
        current_middle = world_position(middle)
        target = [current_end[0] + 5.0, current_end[1] + 3.0, current_end[2] - 4.0]
        pole = [current_middle[0], current_middle[1] + 20.0, current_middle[2] + 20.0]
        result = solve_two_bone_world(
            start=start,
            middle=middle,
            end=end,
            target=target,
            pole=pole,
            tolerance=0.05,
            raise_on_error=False,
            preserve_end_rotation=True,
        )
        after_rot_helpers = set(cmds.ls("TMP_POSE_RECOVERY_ROT*", long=True) or [])
        report.update(result)
        report["temporary_rotation_helpers_left"] = sorted(after_rot_helpers - before_rot_helpers)
        report["ok"] = result["error"] <= 0.05 and not report["temporary_rotation_helpers_left"]
        if not report["ok"]:
            raise RuntimeError("Two-bone smoke test failed: %s" % report)
    except Exception as exc:
        report["error_message"] = repr(exc)
    finally:
        if group and cmds.objExists(group):
            cmds.delete(group)
        cmds.select(clear=True)
        cmds.refresh(force=True)

    if output_path:
        parent = os.path.dirname(output_path)
        if parent and not os.path.isdir(parent):
            os.makedirs(parent)
        with open(output_path, "w", encoding="utf-8") as fh:
            json.dump(report, fh, ensure_ascii=False, indent=1)
    return report


if __name__ == "__maya_cmd__":
    run_test()
