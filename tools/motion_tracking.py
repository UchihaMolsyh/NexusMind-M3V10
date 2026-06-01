"""
Motion Tracking — detect and track motion in video using OpenCV.
"""
import json
from pathlib import Path
from typing import Dict, Any, List
from core.tool_registry import registry, ToolParam


@registry.tool(
    name="motion_track",
    description="Detect and track motion in video files using OpenCV. Returns motion regions and frame-by-frame tracking data.",
    category="Image & Video",
    parameters=[
        ToolParam("path", "string", "Input video file path"),
        ToolParam("action", "string", "Action: detect (motion detection), track (object tracking), info (video info)"),
        ToolParam("params", "string", "JSON params: threshold, min_area, max_frames, etc.", required=False, default="{}"),
    ],
)
def motion_track(path: str, action: str, params: str = "{}"):
    p = json.loads(params) if isinstance(params, str) else params

    try:
        import cv2
        import numpy as np
    except ImportError:
        return {"error": "OpenCV not installed. pip install opencv-python-headless"}

    video_path = Path(path).resolve()
    if not video_path.exists():
        return {"error": f"File not found: {path}"}

    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        return {"error": f"Cannot open video: {path}"}

    try:
        if action == "info":
            return {
                "width": int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
                "height": int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)),
                "fps": cap.get(cv2.CAP_PROP_FPS),
                "total_frames": int(cap.get(cv2.CAP_PROP_FRAME_COUNT)),
                "duration_s": round(cap.get(cv2.CAP_PROP_FRAME_COUNT) / max(cap.get(cv2.CAP_PROP_FPS), 1), 2),
                "codec": int(cap.get(cv2.CAP_PROP_FOURCC)),
            }

        elif action == "detect":
            threshold = p.get("threshold", 25)
            min_area = p.get("min_area", 500)
            max_frames = p.get("max_frames", 300)
            sample_every = p.get("sample_every", 5)

            bg_sub = cv2.createBackgroundSubtractorMOG2(detectShadows=True)
            motion_frames = []
            frame_idx = 0

            while frame_idx < max_frames:
                ret, frame = cap.read()
                if not ret:
                    break

                if frame_idx % sample_every == 0:
                    mask = bg_sub.apply(frame)
                    _, thresh = cv2.threshold(mask, threshold, 255, cv2.THRESH_BINARY)
                    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

                    regions = []
                    for c in contours:
                        area = cv2.contourArea(c)
                        if area > min_area:
                            x, y, w, h = cv2.boundingRect(c)
                            regions.append({"x": int(x), "y": int(y), "w": int(w), "h": int(h), "area": int(area)})

                    if regions:
                        motion_frames.append({
                            "frame": frame_idx,
                            "time_s": round(frame_idx / max(cap.get(cv2.CAP_PROP_FPS), 1), 2),
                            "regions": regions,
                        })

                frame_idx += 1

            cap.release()
            return {
                "total_frames_processed": frame_idx,
                "frames_with_motion": len(motion_frames),
                "motion_data": motion_frames[:100],
            }

        elif action == "track":
            max_frames = p.get("max_frames", 200)
            ret, frame = cap.read()
            if not ret:
                cap.release()
                return {"error": "Cannot read first frame"}

            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            features = cv2.goodFeaturesToTrack(gray, maxCorners=100, qualityLevel=0.3, minDistance=7)

            if features is None:
                cap.release()
                return {"error": "No trackable features found"}

            tracking = [{"frame": 0, "points": [[float(p[0][0]), float(p[0][1])] for p in features]}]
            prev_gray = gray

            frame_idx = 1
            while frame_idx < max_frames:
                ret, frame = cap.read()
                if not ret:
                    break
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                next_pts, status, _ = cv2.calcOpticalFlowPyrLK(prev_gray, gray, features, None)

                if next_pts is not None:
                    good_new = next_pts[status.flatten() == 1]
                    if len(good_new) > 0 and frame_idx % 10 == 0:
                        tracking.append({
                            "frame": frame_idx,
                            "points": [[float(p[0]), float(p[1])] for p in good_new[:20]],
                        })
                    features = good_new.reshape(-1, 1, 2)

                prev_gray = gray
                frame_idx += 1

            cap.release()
            return {
                "total_frames": frame_idx,
                "initial_features": len(features),
                "tracking_data": tracking[:50],
            }

        cap.release()
        return {"error": f"Unknown action: {action}"}

    except Exception as e:
        cap.release()
        return {"error": str(e)}
