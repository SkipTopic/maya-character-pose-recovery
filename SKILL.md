---
name: maya-character-pose-recovery
description: "This skill should be used when repairing Maya characters imported from FBX/MMD/PMX with body distortion, incorrect seated poses, failed two-bone IK, skin or cuff breakage, unsafe animation baselines, or viewport/camera evidence that does not match the scene. 提供场景诊断、原始中立姿态恢复、世界空间解析两段 IK、四向验收、动画与相机安全检查。"
agent_created: true
---

# Maya 人物模型姿态修复与安全动画

## 目标

将“人物扭曲、坐姿异常、手臂破裂、骨骼目标不命中、动画后模型炸开”的问题拆成可验证的步骤，避免用固定欧拉角、网格硬搬、Delta Mush 或随机运镜掩盖根因。

适用于 Maya 2024 及兼容版本中的 FBX/MMD/PMX 转模型、带骨架人物、坐姿/手臂修复和后续头部/手部动画。不要把本 Skill 当作通用自动绑定器；缺少骨架或蒙皮时，先完成绑定和权重验收。

## 强制安全边界

- 保留原始场景，先另存新版本；不得覆盖用户确认过的基线。
- 先读取实际场景和原始模型，再决定修复方式；不得根据截图猜关节角度。
- 不得清零整套关节旋转；导入模型的中立姿态可能包含非零旋转。
- 不得改变蒙皮网格父级、缩放或旋转来补偿骨架问题。
- 不得将局部欧拉角当成世界空间前倾角。
- 不得把 IK 手柄到达目标当成末端关节到达目标。
- 不得用 Delta Mush、隐藏网格或删除角色掩盖未定位的蒙皮问题。
- 不得在用户未确认静帧和短段前批量渲染全片。
- 不得把“文件存在”“脚本无异常”或“节点存在”写成“视觉验收通过”。

## 所需输入

收集以下信息；缺失时先读取项目，仍不明确再询问用户：

1. 当前场景、原始 FBX/PMX/模型文件和最近的稳定基线。
2. 目标姿态或参考视频/图片，以及人物应该接触的地面的高度、椅面、桌面和道具。
3. 允许动画的身体部位、明确禁止的嘴型/手指/躯干动作，以及镜头帧范围。
4. 场景单位、Maya 版本、渲染方式、内存限制和交付规格。
5. 当前是否已有动画、约束、IK、SDEF、Delta Mush、blendShape 或外部 reference。

## 工作流

### 1. 诊断而非立即修改

读取 `references/failure-diagnosis.md`，按“变换层级 → 蒙皮 → 网格 → IK → 动画 → 视口”的顺序定位问题。

运行 `scripts/inspect_character_scene.py` 中的 `inspect_scene()`，保存场景报告。至少记录：

- 场景文件、单位、帧率、播放范围和修改状态。
- 主网格父级、包围盒、顶点数、可见性和 skinCluster。
- 关键关节的局部旋转、世界旋转、世界位置、父级和输入连接。
- morph/blendShape、SDEF、Delta Mush、约束、IK 和动画曲线。
- 外部 reference、贴图、未知节点和相机真实名称。

### 2. 恢复可信的中立基准

读取 `references/pose-recovery-workflow.md`。

优先从原始 FBX 或干净模型场景提取同一骨架的局部中立变换。保留骨骼命名空间、蒙皮网格父级和合法的角色落座补偿。清理多余 morph 时使用已经验证的清理副本，不要再次导入数百万顶点的完整表情数据。

### 3. 用世界空间求解姿态

使用 `scripts/maya_pose_tools.py` 中的 `solve_two_bone_world()`。显式传入起点、中间关节、末端、世界目标和极点，不依赖名称猜测：

```python
from maya_pose_tools import solve_two_bone_world

result = solve_two_bone_world(
    start="Bip001LThigh",
    middle="Bip001LCalf",
    end="Bip001LFoot",
    target=[6.78, 10.10, -67.28],
    pole=[6.78, 62.00, -35.00],
    preserve_end_rotation=True,
    tolerance=0.01,
    raise_on_error=True,
)
```

该函数采用解析两段 IK、Maya 行向量约定下的 `old_q * delta`，并在结束后返回实际末端误差。不要省略结果检查。

### 4. 做四向和碰撞验收

生成正面、左侧、右侧、俯视图；单人验收时隔离其他人物，但保留当前人物的桌椅和接触道具。检查：

- 躯干世界方向、人体尺度和脚底高度。
- 肩、肘、腕、膝盖、脚踝和袖口。
- 手、四肢、躯干与桌椅/道具的穿插。
- 网格是否翻转、破裂、变黑或异常拉伸。
- 图像是否来自不同相机，而非重复缓存。

使用 `references/validation-checklist.md` 作为交付门槛。保存后重新打开场景并重新计算关键指标。

### 5. 再制作动画和相机

读取 `references/animation-and-camera-safety.md`。

以验收姿态为动画基准，制作有剧情依据的头部/手部动作。不得套用统一转头模板、root 摇摆或随机手部动作。先确认动作范围；只有头部/手部许可时，不得自行加入站起、坐下或大幅躯干动画。

逐镜读取主体、听者、前景人物、动作和运镜。保持 180° 轴线，使用相机创建命令返回的真实名称，切换可见面板后出图，并核对图像哈希与实际内容。

### 6. 复盘并留痕

记录失败原因、使用的方法、实际输出、保存后回读结果和剩余风险。将新场景、脚本、参考图和验收数据放入项目备份，不把中间试验版标成完成品。

## 参考资源

- `references/failure-diagnosis.md`：失败症状、根因和诊断顺序。
- `references/pose-recovery-workflow.md`：完整修复流程和 Maya 2024 兼容注意事项。
- `references/animation-and-camera-safety.md`：头部、手部、道具、相机和渲染安全。
- `references/case-study-let-bullets-fly.md`：真实项目从严重扭曲到 v7 验收的迭代证据。
- `references/validation-checklist.md`：验收清单和报告模板。

## 完成定义

只有同时满足以下条件才报告“修复完成”：

1. 原始基线未被覆盖。
2. 末端实际位置达到目标或在报告中明确说明偏差。
3. 四视图与接触区域经过真实图像检查。
4. 保存后重开场景，关键姿态、网格和相机仍存在且一致。
5. 动画和渲染没有超出用户确认的范围。
6. 遗留问题被明确记录，没有用“看起来完成”掩盖。
