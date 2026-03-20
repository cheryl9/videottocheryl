from src.debouncer import debounce_speaker_ids

def test_short_flicker():
    ids = [0] * 50 + [1] * 3 + [0] * 50
    result = debounce_speaker_ids(ids, min_hold_frames=10)
    assert result == [0] * 103


def test_stable_segment_unchanged():
    ids = [0] * 50 + [1] * 50
    result = debounce_speaker_ids(ids, min_hold_frames=10)
    assert result == ids


def test_none_segments_untouched():
    ids = [None] * 10 + [0] * 50
    result = debounce_speaker_ids(ids, min_hold_frames=15)
    assert result == ids


def test_short_segment_at_start_uses_next():
    ids = [1] * 3 + [0] * 50
    result = debounce_speaker_ids(ids, min_hold_frames=10)
    assert result == [0] * 53