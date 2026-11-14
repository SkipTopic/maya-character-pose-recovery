# Maya Character Pose Recovery / Maya 人物模型姿态修复

[中文说明](#中文快速开始) · [English Quick Start](#english-quick-start) · [Failure Catalog / 故障目录](#failure-catalog--真实故障目录) · [Validation / 验证](#validation--验证与跨-ai-可运行性)

A procedural Skill for diagnosing and repairing imported Maya characters whose bodies, seated poses, arms, legs, skin, or validation images have gone wrong.

一套用于诊断和修复 Maya 导入人物的工作流程 Skill：处理身体扭曲、坐姿错误、四肢 IK 异常、袖口/蒙皮破裂，以及“场景数值正常但渲染画面错误”的假成功。

**Skill ID:** `maya-character-pose-recovery`  
**Tested environment / 实测环境:** Autodesk Maya 2024, Windows  
**Core requirement / 核心前提:** The character already has a usable skeleton and skin binding. / 人物已有可用骨架和蒙皮；本仓库不是通用一键自动绑定器。

---

## 1. What this repository provides / 本仓库提供什么

- A strict diagnostic and recovery workflow. / 一套先诊断、再修复、再验收的流程。
- A Maya 2024-tested analytic two-bone IK implementation. / 经 Maya 2024 实测的解析两段 IK。
- Read-only scene inspection and mesh/collision measurements. / 只读场景检查、网格和碰撞测量。
- Four-view, saved-scene-reopen, and image-cache validation rules. / 四视图、保存后回读和图像缓存验证规则。
- A real failure-to-recovery case study with rejected approaches. / 真实修复案例，包括被否定的错误路线。

This is not a collection of universal joint angles.  
本仓库不是一套可以套到所有人物身上的固定关节角度。

---

## 中文快速开始

### 1. 获取仓库

```bash
git clone https://github.com/SkipTopic/maya-character-pose-recovery.git
```

### 2. 准备输入

向 AI 提供：

1. 当前出问题的 Maya 场景。
2. 同一人物的原始 FBX/PMX 或最近稳定场景。
3. 目标姿态参考图/视频。
4. Maya 可执行文件路径和版本。
5. 哪些部位允许动画，哪些禁止。
6. 桌椅、地面、道具和接触要求。

不要只给一张坏姿态截图，然后要求 AI 猜欧拉角。

### 3. 在 Maya 内加载工具

以下命令应在**正在运行的 Maya Python 环境**中执行，不是在普通系统 Python 中执行：

```python
import sys
sys.path.insert(0, r"<替换为仓库实际路径>/scripts")

from inspect_character_scene import inspect_scene

report = inspect_scene(
    joints=[
        "Bip001Spine",
        "Bip001Head",
        "Bip001LThigh",
        "Bip001LCalf",
        "Bip001LFoot",
    ],
    output_path="<替换为项目路径>/logs/character_audit.json",
)
```

将骨名替换为实际模型骨名。没有 `Bip001` 的模型不能原样使用上述名称。

### 4. 先跑临时骨链自测

```python
from test_maya_pose_tools import run_test

result = run_test(
    output_path="<替换为项目路径>/logs/two_bone_smoke_test.json"
)
assert result["ok"], result
```

该测试创建临时骨骼和临时约束，结束后清理，不打开或保存正式场景。仍应先保存重要工作。

### 5. 执行显式两段 IK

```python
from maya_pose_tools import solve_two_bone_world

result = solve_two_bone_world(
    start="Bip001LThigh",
    middle="Bip001LCalf",
    end="Bip001LFoot",
    target=measured_target,  # 由当前项目参考、骨长和接触面计算
    pole=measured_pole,      # 由当前项目膝盖/手肘弯曲方向计算
    preserve_end_rotation=True,
    tolerance=0.01,
    raise_on_error=True,
)
```

必须检查：

- `result["error"]`：实际末端误差。
- `result["target_was_clamped"]`：目标是否因不可达被钳制。
- `result["actual_middle"]`：膝盖/手肘实际位置。
- 真实渲染中的网格、脚底、袖口和接触区域。

### 6. 按完整流程修复

```text
保存现场
→ 只读审计
→ 从同一原始模型恢复中立姿态
→ 世界空间两段 IK
→ 四视图与碰撞检查
→ 另存新版本
→ 重新打开并重算
→ 用户验收后才进入动画
```

详细步骤见 `references/pose-recovery-workflow.md`。

---

## English Quick Start

### 1. Clone

```bash
git clone https://github.com/SkipTopic/maya-character-pose-recovery.git
```

### 2. Provide evidence

Give the AI:

1. The broken Maya scene.
2. The original FBX/PMX or a known-good scene of the same character.
3. Reference images or video for the target pose.
4. The Maya executable path and version.
5. Allowed and forbidden animation channels.
6. Furniture, floor, props, and contact requirements.

Do not ask the AI to infer joint angles from a single broken screenshot.

### 3. Load the tools inside Maya

Run the following in the **running Maya Python environment**, not in system Python:

```python
import sys
sys.path.insert(0, r"<actual-repository-path>/scripts")

from inspect_character_scene import inspect_scene

report = inspect_scene(
    joints=["Bip001Spine", "Bip001Head"],
    output_path="<project-path>/logs/character_audit.json",
)
```

Replace joint names with the actual rig. The example names are not universal.

### 4. Run the temporary-chain smoke test

```python
from test_maya_pose_tools import run_test

result = run_test(output_path="<project-path>/logs/two_bone_smoke_test.json")
assert result["ok"], result
```

The test creates and removes temporary joints and helpers. It does not open or save a production scene. Save important work before running it.

### 5. Solve an explicit two-bone chain

```python
from maya_pose_tools import solve_two_bone_world

result = solve_two_bone_world(
    start="Bip001LThigh",
    middle="Bip001LCalf",
    end="Bip001LFoot",
    target=measured_target,  # Measure from the current project's reference and contacts.
    pole=measured_pole,      # Compute the intended knee/elbow bend direction.
    preserve_end_rotation=True,
    tolerance=0.01,
    raise_on_error=True,
)
```

Always inspect the actual end effector, clamped-target flag, middle joint, mesh, cuffs, floor, and contact surfaces. A mathematically valid result can still look wrong.

---

## Repository map / 仓库结构

```text
SKILL.md
scripts/
  inspect_character_scene.py   # Read-only scene audit / 只读场景审计
  maya_pose_tools.py           # IK, pose, mesh and collision tools / 核心工具
  test_maya_pose_tools.py      # Temporary-rig smoke test / 临时骨链自测
references/
  failure-diagnosis.md
  pose-recovery-workflow.md
  animation-and-camera-safety.md
  case-study-let-bullets-fly.md
  validation-checklist.md
tests/
  maya_two_bone_test.json      # Actual Maya test evidence / Maya 实测报告
```

---

## Failure Catalog / 真实故障目录

下表同时保留中文和英文，便于不同 AI 接续。每一行都来自实际项目或真实工具测试，不是想象的问题。  
Each row is bilingual and comes from an actual project or tool test.

| 问题 / Problem | 如何遇到与证据 / How it was found | 根因 / Root cause | 解决与预防 / Fix and prevention |
|---|---|---|---|
| **MCP 有连接但无回传**<br>MCP connected but returned nothing | 命令执行了，客户端却等不到结果。<br>Commands executed without a response. | `echoOutput=False` 关闭了结果回传。<br>Output echo was disabled. | 核对 commandPort 和启动钩子；先用只读查询验证。<br>Verify commandPort/startup hooks with read-only calls. |
| **SafeMode 拦截文件和 Python**<br>SafeMode blocked I/O and Python | `open/eval/exec/io.open` 失效，脚本无法读写。<br>File I/O and exec failed. | Maya 安全配置阻止了自动化所需操作。<br>Maya security settings blocked automation. | 不盲目全局放开；审核代码和来源，使用可信本地通道。<br>Audit code and use a trusted local channel instead of blindly disabling security. |
| **客户端终止符识别错误**<br>Client missed the response terminator | 结果已经返回，但客户端仍等待。<br>The client waited after receiving data. | 回传以 `\n\x00` 结束，旧客户端只检查 `\n`。<br>The response ended in `\n\x00`, not only `\n`. | 修正读取逻辑；不要把协议问题当成模型问题。<br>Fix protocol handling before debugging the scene. |
| **第一次允许后仍有第二个警告**<br>A second warning appeared after Allow | 一次 MCP 操作分为执行和读取结果两次连接。<br>One operation used execute and result-read connections. | 第二个请求也被模态对话框阻塞。<br>The second request was blocked too. | 检查所有模态窗口；不连续重试堆积请求。<br>Inspect every modal dialog and avoid retry stacking. |
| **Connection refused**<br>连接被拒绝 | 出现 `WinError 10061`，poller 也不执行。<br>Port 10061 and no file execution. | 实际是 Maya 进程已退出，不是 Python 语法问题。<br>Maya was not running. | 检查进程，重启，做轻量只读测试，再恢复工作版本。<br>Check the process, restart, test read-only, then reopen the work scene. |
| **mayabatch/mayapy 崩溃**<br>Batch interpreters crashed | 多次尝试非 GUI 自动化失败。<br>Non-GUI automation repeatedly failed. | 本机环境不稳定。<br>The local batch setup was unstable. | 使用已启动的 Maya GUI 和可信执行通道。<br>Use the running Maya GUI with a trusted execution channel. |
| **重命名/重父级后蒙皮破坏**<br>Renaming/reparenting broke skinning | 转换后人物比例和姿态异常。<br>Characters broke after conversion edits. | 导入后的层级、名称和变换被不安全地改写。<br>Import hierarchy and transforms were rewritten unsafely. | 从干净 FBX 重导；保留骨架与网格关系。<br>Reimport cleanly and preserve rig/mesh relationships. |
| **网格被撑到几千单位**<br>Mesh expanded to thousands of units | 尝试给带缩放蒙皮网格换父级。<br>A scaled skinned mesh was reparented. | 重复叠加了父级变换和缩放。<br>Parent transforms and scale were applied twice. | 不改变蒙皮网格父级；移动人物骨架组。<br>Keep the mesh parent and move the character rig group. |
| **把关节全部清零后更扭曲**<br>Zeroing every joint made distortion worse | 将 Spine/Neck/Head 等直接设为 0。<br>Multiple joints were set to zero. | FBX 中立姿态本来就有非零旋转和坐标转换。<br>The rest rig contained non-zero rotations and coordinate conversions. | 从同一原始模型读取中立局部变换。<br>Restore rest transforms from the same original model. |
| **Spine 局部很小，身体却前倾约 45°**<br>Local Spine was small while the torso leaned about 45 degrees | 实测局部 `1.5°`、世界约 `42.29°`；另一处 `6°` 对 `46.6°`。<br>Measured local/world values contradicted the visual diagnosis. | 把局部欧拉角误当成世界空间姿态，忽略父级叠加。<br>Local Euler angles were mistaken for world orientation. | 用 Spine→Head 世界向量计算躯干角度。<br>Measure the world-space spine-to-head vector. |
| **root 摇摆不是真正的表演**<br>Root sway was not real performance | 旧流程给 root 反复叠加轻微旋转。<br>The old pipeline repeatedly modified root rotation. | 没有按视线和手势设计动作，且会累积错误。<br>No gaze/gesture design; errors accumulated. | 以验收姿态为基准制作头部/手部动作。<br>Animate from the accepted pose using explicit gaze and hand targets. |
| **腿部被拆成单段 IK**<br>Legs were treated as single segments | 膝盖和脚踝无法形成正常坐姿。<br>Knees and ankles could not form a valid seated pose. | 没有使用完整大腿→膝盖→脚踝两段链。<br>The full two-bone chain was not solved. | 显式提供 start/middle/end 和膝盖极点。<br>Provide explicit start, middle, end, and pole. |
| **IK 手柄到了，末端没到**<br>IK handle reached the target but the foot did not | 手柄位置正确，脚踝仍在旧位置，膝盖不弯。<br>The handle matched the target while the foot remained elsewhere. | 在这套导入骨链上，求解器状态不能作为末端证据。<br>Solver/handle state did not prove chain evaluation. | 使用解析两段 IK，并读取实际末端位置。<br>Use analytic two-bone IK and measure the evaluated end joint. |
| **twist 骨被当成肘部**<br>Twist joints were mistaken for elbows | 旧模型手臂含 ArmTwist/HandTwist。<br>The old rig contained twist joints. | 自动按父子关系猜中间关节不可靠。<br>Blind hierarchy inference is unreliable. | 显式指定 ForeArm/Forearm 为中间关节。<br>Explicitly select the main forearm joint. |
| **解析 IK 仍然严重偏侧**<br>Analytic IK initially twisted sideways | v2/v3 的腿部和手臂误差反而巨大。<br>v2/v3 produced large target errors. | 世界增量四元数使用了 `delta * old_q`。<br>The world delta was left-multiplied. | 按 Maya 行向量约定改为 `old_q * delta`，并用非单位父级测试。<br>Use right multiplication and test with rotated parents. |
| **旧模型大角度弯臂袖口翻开**<br>Old MMD cuffs tore during large bends | 同条件渲染显示袖壳/手臂分层穿插、变黑。<br>Rendered cuffs and arm shells intersected. | SDEF 辅助结构和分层蒙皮无法承受目标动作。<br>The old SDEF/skin structure could not support the target bend. | 减少旧模型动作或更换已验证新模型。<br>Simplify old-rig motion or use a validated replacement. |
| **Delta Mush 没有根治破袖**<br>Delta Mush did not fix the cuffs | 多种参数尝试无效，高迭代还带来约 2GB 内存峰值。<br>Parameters did not help; high iterations consumed memory. | 用平滑变形器掩盖结构问题。<br>A smoother was being used to hide a structural issue. | 停止盲目加参数，修动作范围或模型结构。<br>Stop hiding the issue; fix motion scope or model structure. |
| **新模型完整导入卡死**<br>Full new-model import stalled Maya | 约 149 份 morph、合计约 426 万顶点，机器约 8GB 内存。<br>About 149 morphs and 4.26M vertices on an 8GB machine. | 每轮都导入完整表情数据。<br>The full morph set was imported repeatedly. | 使用清理过表情的单身体网格副本。<br>Use a validated body-only scene with unneeded morphs removed. |
| **修髋部后手又穿桌**<br>Raising the hips created new table intersections | v4 桌面内部顶点为 0；v5 改髋部后马县长出现 78 个。<br>Raising the hip changed the arm path. | 只验收被修改的部位，没有重新检查全身接触。<br>Only the edited body part was revalidated. | 每次改肩部高度后重新检查肘、腕和小臂路径。<br>Recheck the entire arm path after changing body height. |
| **抬高极点反而更糟**<br>Raising the elbow pole made things worse | v6 桌面内部顶点从 78 增至 322。<br>The v6 pole change increased interior vertices to 322. | 凭直觉猜极点，没有依据实际碰撞路径。<br>The pole was guessed without checking the collision path. | 收近手腕、保持肘部外侧并降低极点，v7 回到 0。<br>Move the wrist nearer the edge and lower the outward pole; verify again. |
| **四视图头顶被裁切**<br>Review cameras clipped the heads | 单人取景错误使用了含落座补偿的组 Y 作为目标。<br>The camera target used the compensated group Y. | 把组平移当作人物实际中心。<br>The group transform was mistaken for the body center. | 从实际人物/骨骼计算取景中心。<br>Frame the evaluated character, not the compensated group origin. |
| **图片生成了但全部相同**<br>Different filenames contained identical images | 多机位图片哈希一致，甚至是重复旧视口。<br>Different shots had identical hashes. | 相机实际名称带后缀，后续仍使用旧名称；视口没有切换。<br>The actual camera name differed and the panel stayed on the old view. | 使用创建返回值、可见面板和 `lookThru`，并核对哈希。<br>Use returned names, a visible panel, lookThru, and image hashes. |
| **71 台相机不等于 71 次有效切换**<br>Seventy-one cameras did not mean seventy-one working shots | 旧场景按位置/朝向只有 12 种，最大重复组 18 次。<br>Only 12 unique transforms existed. | 生成逻辑只看主体和景别，没有处理剧情承接。<br>The generator ignored narrative and camera continuity. | 按原片逐镜设计，并记录实际渲染使用的相机。<br>Design each shot from the reference and log the camera actually rendered. |
| **旧报告的 PASS 是假通过**<br>Old PASS reports were misleading | 只检查相机数、文件数、节点数，漏掉静止、穿模、闪面。<br>Reports omitted visual failure modes. | 把“存在”当成“生效”，把“脚本成功”当成“画面正确”。<br>Existence was mistaken for visual correctness. | 保存后回读、四视图、短段、碰撞和图像哈希共同验收。<br>Require saved-scene reopening, images, clips, collision checks, and hashes. |
| **旧文档中的组 Y=0 被误用**<br>An obsolete "group Y must be zero" rule was reused | v7 的组 Y 实际承担落座补偿。<br>v7 used group Y for seat compensation. | 把旧版本说明误当成当前版本事实。<br>An old version note was treated as current truth. | 以当前保存后回读数据为准，不归零补偿。<br>Trust current scene evidence and preserve compensation. |

完整技术细节见 `references/failure-diagnosis.md` 和 `references/case-study-let-bullets-fly.md`。  
See the references for the full technical notes and iteration evidence.

---

### Additional audit findings / 后续审计补充

| 问题 / Problem | 如何遇到 / How it was found | 解决与预防 / Fix and prevention |
|---|---|---|
| **执行通道 `ok:true` 只是传输成功**<br>A transport-level `ok:true` was not business success | 本地 poller 执行了文件，但脚本自己的 `OUT["ok"]` 仍可能为 false。<br>The command file ran while the script's own result could still fail. | 同时检查 poller 结果、业务日志、输出文件和视觉证据。<br>Check transport, business logs, outputs, and visual evidence separately. |
| **转一个角色的关节，看的却是另一个角色**<br>The team rotated one character while viewing another | 顶点在动，但画面变化来自不同网格；历史修复报告明确记录了这一误判。<br>A historical report proved that the watched mesh differed from the edited rig. | 同时记录编辑对象、渲染对象、相机和网格名称。<br>Log the edited rig, rendered mesh, and camera together. |
| **材质槽名称不能证明真实贴图/UV**<br>Material-slot names did not prove texture or UV correctness | 裙甲 UV 被错误分类，后续又出现按材质槽猜测贴图的错误。<br>Armor UV was misclassified and material slots were misread as texture evidence. | 用 shader 图、贴图路径、UV 和真实渲染共同判断。<br>Inspect shader links, texture paths, UVs, and rendered output. |
| **辅助结构存在不等于原生 SDEF 可恢复**<br>Helper nodes did not prove recoverable native SDEF | 场景保留了 `_mmd_sdef_*` 结构，但没有证据表明 Maya 中原生 SDEF 算法仍可用。<br>Helper names existed without proof of a working native SDEF deformer. | 将其作为绑定风险记录，不声称“可恢复原生 SDEF”。<br>Document the risk without claiming native SDEF recovery. |
| **旧结论把局部可行写成普遍规律**<br>Old notes overgeneralized local results | 曾出现“手永远够不到桌面”“只能 root 动画”“组 Y 必须为 0”等说法；后续场景均推翻了这些绝对结论。<br>Later scenes disproved these absolute claims. | 所有旧规则必须绑定场景版本和验证条件。<br>Scope every rule to a scene version and tested conditions. |
| **备份和验收只对某个时点有效**<br>Backups and approvals were time-specific | v7 备份只包含到当时交接为止的状态，不能代表之后的 DS 版本。<br>The v7 backup predates later DS scenes. | 每次新阶段重新生成版本、备份和校验清单。<br>Create fresh backups and manifests for later stages. |

---

## Actual recovery result / 实际修复结果

在真实项目的 v7 场景中，保存后重新打开并计算：

| Character / 人物 | Torso angle / 躯干夹角 | Table interior vertices / 桌面内部顶点 | Max leg error / 最大腿部误差 | Max hand error / 最大手部误差 |
|---|---:|---:|---:|---:|
| Ma / 马县长 | 3.081° | 0 | 0.000022 cm | 0.000004 cm |
| Huang / 黄四郎 | 0.014° | 0 | 0.000002 cm | 0.000004 cm |
| Shiye / 师爷 | 0.914° | 0 | 0.000005 cm | 0.000011 cm |

These numbers are case evidence, not targets for a different model.  
这些是案例证据，不是新模型必须复制的数值。

The final review included four views per character, 16 distinct source images, saved-scene reopening, and explicit remaining-contact notes.  
最终验收包括每人四视图、16 张不同原图、保存后回读和剩余接触风险说明。

---

## Validation / 验证与跨 AI 可运行性

### 已实际验证 / Actually tested

- Python syntax checks passed. / Python 语法检查通过。
- The analytic two-bone solver passed in Maya 2024 with rotated and scaled parents. / 解析 IK 已在带旋转和缩放父级的 Maya 2024 临时骨链上通过。
- Actual end-effector error was approximately `1.95e-14`. / 实际末端误差约 `1.95e-14`。
- A locked rotation channel was rejected before modification, and the start joint remained unchanged. / 锁定旋转通道在修改前被拒绝，起始关节未发生变化。
- No temporary constraints or locators remained. / 无临时约束或 locator 残留。
- Official Skill validation and ZIP packaging passed. / 官方 Skill 校验和打包通过。

证据：`tests/maya_two_bone_test.json`。

### 换另一个 AI 后如何跑通 / What another AI must do

另一个 AI 可以按本仓库执行，但必须完成以下事项，不能只读 README 标题：

1. 在 Maya 内运行 Maya 脚本，并把 `scripts/` 加入 `sys.path`。
2. 提供同一人物的干净原始模型或中立变换来源。
3. 将示例骨名和目标坐标替换为新项目的实际值。
4. 先跑临时骨链测试，再修改正式人物。
5. 从世界空间验证姿态和实际末端，不看 IK 手柄代替。
6. 生成真实四视图并检查接触区域。
7. 保存后重开场景，再次计算和出图。
8. 未经用户确认，不把修复结果直接扩大成全身动画或全片渲染。

### 不能保证的部分 / What is not guaranteed

- 不会自动为任意静态模型生成完美骨架和权重。<br>It does not automatically produce a perfect rig for arbitrary static meshes.
- 不保证旧 MMD 模型在所有大角度动作下都不破袖。<br>It cannot guarantee that every old MMD rig supports extreme bends.
- 不把当前案例的骨名、桌面高度和人物坐标硬编码到新项目。<br>Case-specific names and coordinates are not portable.
- 不把数学误差为零等同于视觉完美。<br>Numerical accuracy does not replace visual review.
- 不包含 Maya 或 MCP 本体。<br>Maya and MCP software are not bundled.

需要完整 Maya MCP、分镜、动画和交付流程时，使用配套仓库：  
For the full MCP-to-animation workflow, use:

https://github.com/SkipTopic/maya-sheng-animation

---

## Security and handoff / 安全与交接

- 不在项目中保存访问令牌、账号密码或 MCP 凭据。<br>Never store access tokens, passwords, or MCP credentials in the repository.
- 不自动点击“全部允许”，不开放公共网络 commandPort。<br>Do not blindly select Allow All or expose commandPort publicly.
- 所有修改另存新版本，原始场景和模型保持可恢复。<br>Keep original scenes and models recoverable through versioned files.
- 交接时记录失败路线、当前唯一有效版本、验证证据和剩余问题。<br>Handoff notes must include rejected approaches, the current valid version, evidence, and unresolved issues.

**Read `SKILL.md` for the executable procedure, then use the references only as needed. / 先读 `SKILL.md` 获取执行流程，再按需加载 references。**
