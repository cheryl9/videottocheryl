What I found (root cause of each bug):

Bug 1: Dead zone is never used.
I read through the function. I noticed dz_half_w was calculated early on but I could not find it being used anywhere later, which suggested it was dead code. I then searched for where the dead zone check actually happened and found abs(dx) > 0 which would be true for any movement at all. The dead zone ratio (deadzone_ratio=0.10) and the computed dz_half_w or dz_half_h variables are computed but never compared against. This meant the dead zone had no effect. The crop window chased every tiny face movement, producing constant jitter instead of stable output.

What I fixed:
need_move_x = abs(dx) > dz_half_w
need_move_y = abs(dy) > dz_half_h

instead of 
need_move_x = abs(dx) > 0
need_move_y = abs(dy) > 0

Bug 2: Scene cut or speaker switch does not snap.
Reading the code, I traced what happens when should_snap is True and noticed there was no continue or early exit. should_snap sets a flag and appends to a list. But there's no continue, early return, or else branch to prevent the smoothing block from executing. The snap is recorded but never applied. Hence I realised that when should_snap is True (scene boundary or speaker switch), the code records the frame in scene_cut_frames but then falls through to the same EMA smoothing path as normal movement. 

What I fixed:
// Added a hard snap
if should_snap:
    scene_cut_frames.append(frame_idx)
    crop_cx, crop_cy = clamp_crop(face_x, face_y)
    per_frame.append((crop_cx, crop_cy))
    continue

instead of 
if should_snap:
    scene_cut_frames.append(frame_idx)


Debouncer design decisions:
- Mutable lists instead of tuples for runs. Each run is stored as [track_id, start, length] rather than a tuple so the replacement pass can mutate track_id in-place without rebuilding the list. This keeps the logic straightforward.

- Multi-pass replacement loop. The outer while changed loop re-runs until no more substitutions occur. This handles cascading cases, e.g. two adjacent short runs where the first can only be resolved after the second is replaced. A single forward pass would miss these.

- Prefer previous over next. When a short run has both a predecessor and a stable successor, the predecessor wins. In a live tracking context, what just happened is more reliable context than what is coming next. It also means the debouncer is causal, it never looks further forward than necessary.

- None segments are fully inert. None runs are skipped during replacement and are never used as a replacement source. A None gap between two speakers does not donate an ID to either side, and a short non-None run surrounded by None on both sides stays unchanged (no valid replacement exists).

- Merge after all replacements complete. The adjacent-run merge happens once after the full replacement loop, not inside it. This avoids index drift mid-pass and keeps the loop logic simple.

Anything else I noticed:
- face_scenes overlapping ranges are not validated. If two scene ranges overlap (e.g. (0, 15) and (10, 25)), both start frames are added to scene_starts and both trigger a snap. There is no error or warning, it just silently does the wrong thing. A guard or at least a sort-and-check would make this more robust.

- RLE compression uses a different tolerance semantic in tracker.py vs compression.py. compress_crop_coordinates uses a pixel tolerance to merge similar coordinates, which is fuzzy. The inline RLE in tracker.py uses coords_close with the same logic. These are two implementations of the same idea, which thus is worth consolidating into a shared utility if the codebase grows.

- The start field in RLE runs is computed but never used. Each run stores [track_id, start, length] but start is only ever unpacked with _start during expansion. It could be dropped to [track_id, length], though keeping it makes debugging easier since I can immediately see where a run begins in the original timeline.

- Given more time, I would add property-based tests to verify invariants. For example, output length always equals input length, None positions are never mutated, and total frame counts are preserved across compression. These catch edge cases that hand-written example tests tend to miss.