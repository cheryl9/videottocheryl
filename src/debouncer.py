"""
Speaker ID debouncing for stable camera tracking.

Removes rapid speaker-ID bounces that cause jarring crop window snaps.
"""


def debounce_speaker_ids(speaker_track_ids, min_hold_frames=15):
    """
    Remove rapid speaker-ID bounces shorter than min_hold_frames.

    Speaker detection sometimes flickers the active-speaker label during
    crosstalk or brief classification uncertainty, producing 1-10 frame
    segments that cause jarring rapid-fire crop snaps. This pre-filter
    replaces those short segments with the surrounding stable speaker ID
    so the downstream dead-zone tracker never sees them.

    Algorithm:
      1. Run-length encode the raw IDs into (track_id, start, length) runs.
      2. For any run shorter than min_hold_frames, replace it with the
         previous stable run's ID (or the next stable run if it's the first).
      3. Expand back to a per-frame list.

    Args:
        speaker_track_ids: Per-frame list of speaker IDs (int or None).
            None means no speaker detected at that frame.
        min_hold_frames: Minimum frames a speaker must hold to be "stable".

    Returns:
        Same-length list with short flicker runs replaced by nearest stable ID.
        None segments are never modified.
    """
    if not speaker_track_ids:
        return speaker_track_ids

    # Run-length encode raw IDs into runs of [track_id, start, length]
    runs = []
    i = 0
    while i < len(speaker_track_ids):
        current = speaker_track_ids[i]
        length = 1
        while i + length < len(speaker_track_ids) and speaker_track_ids[i + length] == current:
            length += 1
        runs.append([current, i, length])
        i += length

    # Replace short non-None runs with surrounding stable ID
    # Multiple passes handle cascading short segments
    changed = True
    while changed:
        changed = False
        for idx in range(len(runs)):
            track_id, start, length = runs[idx]
            if track_id is None:
                continue  
            if length >= min_hold_frames:
                continue  

            # Look backward for nearest non-None predecessor
            prev_id = None
            for p in range(idx - 1, -1, -1):
                if runs[p][0] is not None:
                    prev_id = runs[p][0]
                    break

            # Look forward for nearest stable non-None successor
            next_id = None
            for n in range(idx + 1, len(runs)):
                if runs[n][0] is not None and runs[n][2] >= min_hold_frames:
                    next_id = runs[n][0]
                    break

            replace_id = prev_id if prev_id is not None else next_id

            if replace_id is not None and replace_id != track_id:
                runs[idx][0] = replace_id
                changed = True

    # Merge adjacent runs that now have the same ID
    merged = [runs[0]]
    for run in runs[1:]:
        if run[0] == merged[-1][0]:
            merged[-1][2] += run[2]
        else:
            merged.append(run)

    # Expand back to per-frame list
    result = []
    for track_id, start, length in merged:
        result.extend([track_id] * length)

    return result