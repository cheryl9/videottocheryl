"""Basic tests for the face tracking module."""

from itertools import count

from src.tracker import track_face_crop


class TestTrackFaceCropBasics:
    """Basic sanity tests for track_face_crop."""

    def test_empty_input(self):
        """Empty bbox list returns empty output."""
        compressed, scene_cuts = track_face_crop([])
        assert compressed == []
        assert scene_cuts == []

    def test_single_frame_with_face(self):
        """One frame with a face returns one crop position."""
        # Face centered at (320, 180) in a 640x360 frame
        bboxes = [(300, 160, 340, 200)]
        compressed, scene_cuts = track_face_crop(bboxes, video_width=640, video_height=360)

        assert len(compressed) == 1
        assert compressed[0][2] == 1  # frame count
        assert compressed[0][0] > 0   # valid x coordinate
        assert compressed[0][1] > 0   # valid y coordinate
        assert scene_cuts == []

    def test_no_face_before_first_detection(self):
        """Frames with None bbox before first face return (-1, -1) sentinel."""
        bboxes = [None, None, None, (300, 160, 340, 200), (300, 160, 340, 200)]
        compressed, scene_cuts = track_face_crop(bboxes, video_width=640, video_height=360)

        # First segment should be the no-face sentinel
        assert compressed[0][0] == -1
        assert compressed[0][1] == -1
        assert compressed[0][2] == 3  # 3 no-face frames

    def test_dead_zone(self):
        """Face inside dead zone should not move crop"""
        # Face starts centered, then moves slightly within dead zone
        center_bbox = (310, 170, 330, 190)
        tiny_shift = (312, 172, 332, 192) 

        bboxes = [center_bbox] * 10 + [tiny_shift] * 10
        compressed, scene_cuts = track_face_crop(bboxes, video_width = 640, video_height = 360, deadzone_ratio = 0.10)

        assert len(compressed) == 1  # Only one segment since no movement

    def test_scene_cut_snaps(self):
        """At a scene boundary the crop should snap instead of smooth"""
        # Face on left side, then immediately on right side 
        left_face = [(100, 160, 140, 200)] * 10
        right_face = [(500, 160, 540, 200)] * 10
        bboxes = left_face + right_face
        face_scenes = [(0, 9), (10, 19)]  # Scene cut between frame 9 and 10

        compressed, scene_cuts = track_face_crop(
            bboxes, video_width=640, video_height=360, face_scenes=face_scenes
        )

        # Scene cut should be detected at frame 10  
        assert 10 in scene_cuts 
        frame_osset = 0
        for seg in compressed:
            if frame_osset == 10:
                assert seg[0] > 400
                break
            frame_osset += seg[2]