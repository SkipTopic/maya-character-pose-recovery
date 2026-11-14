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
    previous_selection = cmds.ls(selection=True, long=True) or []
    report = {"ok": False, "maya_version": cmds.about(version=True), "scene": cmds.file(q=True, sceneName=True)}
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

        locked_channel_rejected = False
        start_before_rejected = list(cmds.getAttr(start + ".rotate")[0])
        cmds.setAttr(middle + ".rotateX", lock=True)
        try:
            try:
                solve_two_bone_world(start, middle, end, target, pole, raise_on_error=True)
            except RuntimeError:
                locked_channel_rejected = True
        finally:
            cmds.setAttr(middle + ".rotateX", lock=False)
        start_after_rejected = list(cmds.getAttr(start + ".rotate")[0])
        locked_channel_rejected = locked_channel_rejected and start_before_rejected == start_after_rejected

        report.update(result)
        report["locked_channel_preflight_rejected_without_changes"] = locked_channel_rejected
        report["temporary_rotation_helpers_left"] = sorted(after_rot_helpers - before_rot_helpers)
        report["ok"] = result["error"] <= 0.05 and locked_channel_rejected and not report["temporary_rotation_helpers_left"]
        if not report["ok"]:
            raise RuntimeError("Two-bone smoke test failed: %s" % report)
    except Exception as exc:
        report["error_message"] = repr(exc)
    finally:
        if group and cmds.objExists(group):
            cmds.delete(group)
        existing_selection = [node for node in previous_selection if cmds.objExists(node)]
        if existing_selection:
            cmds.select(existing_selection, replace=True)
        else:
            cmds.select(clear=True)
        cmds.refresh(force=True)

    if output_path:
        parent = os.path.dirname(output_path)
        if parent and not os.path.isdir(parent):
            os.makedirs(parent)
        with open(output_path, "w", encoding="utf-8") as fh:
            json.dump(report, fh, ensure_ascii=False, indent=1)
    return report


def main(output_path=None):
    result = run_test(output_path=output_path)
    print(json.dumps({"ok": result.get("ok"), "report": output_path}, ensure_ascii=False))
    if not result.get("ok"):
        raise RuntimeError("Maya pose recovery smoke test failed; inspect %s" % output_path)
    return result


if __name__ in ("__main__", "__maya_cmd__"):
    main()
