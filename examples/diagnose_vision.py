"""Diagnose why the detector is reporting nothing.

Runs the real camera and the real YOLO model, but with all filtering
switched off, then reports each stage separately so the failure can be
located precisely:

  1. Does the camera return a frame at all?
  2. Is the frame actually an image, or is it black (covered lens,
     privacy shutter, another app holding the camera)?
  3. Does YOLO see anything at all, at ANY confidence?
  4. Do any of those classes map to labels DeskOS understands?
  5. Do they clear the configured confidence threshold?

Run: python examples/diagnose_vision.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from deskos.config.settings import load_settings  # noqa: E402
from deskos.perception.object_detector import _COCO_LABEL_MAP  # noqa: E402

_SAVED_FRAME = Path("diagnose_frame.png")


def main() -> None:
    settings = load_settings()
    print("=" * 62)
    print(" DeskOS vision diagnostic")
    print("=" * 62)
    print(f"model_path           : {settings.perception.model_path}")
    print(f"confidence_threshold : {settings.perception.confidence_threshold}")
    print(f"camera device_index  : {settings.camera.device_index}")
    print()

    # --- 1. camera -----------------------------------------------------
    print("[1] Opening camera...")
    from deskos.camera.webcam_source import WebcamSource

    camera = WebcamSource(settings.camera)
    try:
        camera.start()
    except Exception as exc:
        print(f"    FAILED to start camera: {exc}")
        print("    -> Another app may be using the webcam, or Windows camera")
        print("       privacy settings are blocking it.")
        return

    frame = None
    for _attempt in range(10):  # first frames are often empty while it warms up
        frame = camera.read_frame()
        if frame is not None:
            break
    camera.stop()

    if frame is None:
        print("    FAILED: camera opened but returned no frame.")
        print("    -> Check Windows Settings > Privacy > Camera.")
        return
    print("    OK: got a frame.")

    # --- 2. is the frame a real image? ---------------------------------
    print("\n[2] Inspecting the frame...")
    image = frame.image
    try:
        import numpy as np

        arr = np.asarray(image)
        mean = float(arr.mean())
        print(f"    shape={arr.shape} dtype={arr.dtype}")
        print(f"    brightness: mean={mean:.1f} min={arr.min()} max={arr.max()}")
        if mean < 8:
            print("    WARNING: the frame is essentially black.")
            print("    -> Lens cover / privacy shutter closed, or the camera is")
            print("       held by another application. This alone explains")
            print("       zero detections.")
    except Exception as exc:
        print(f"    could not inspect pixels: {exc}")

    try:
        import cv2

        cv2.imwrite(str(_SAVED_FRAME), image)
        print(f"    saved a copy to: {_SAVED_FRAME.resolve()}")
        print("    -> Open it. If you cannot see your desk, the camera is the problem.")
    except Exception as exc:
        print(f"    could not save frame: {exc}")

    # --- 3. raw YOLO output --------------------------------------------
    print("\n[3] Running YOLO with NO confidence filter...")
    try:
        from ultralytics import YOLO
    except ImportError:
        print('    ultralytics not installed. Run: pip install -e ".[vision]"')
        return

    try:
        model = YOLO(settings.perception.model_path)
    except Exception as exc:
        print(f"    FAILED to load the model: {exc}")
        return

    results = model.predict(image, verbose=False, conf=0.01)[0]
    raw = []
    for box in results.boxes:
        raw.append((results.names[int(box.cls[0])], float(box.conf[0])))
    raw.sort(key=lambda pair: pair[1], reverse=True)

    if not raw:
        print("    YOLO detected NOTHING, even at 1% confidence.")
        print("    -> The frame almost certainly contains no recognisable")
        print("       objects. Check the saved image above.")
        return

    print(f"    YOLO found {len(raw)} object(s):")
    for name, conf in raw[:20]:
        mapped = _COCO_LABEL_MAP.get(name)
        passes = "yes" if conf >= settings.perception.confidence_threshold else "NO"
        note = f"-> DeskOS label '{mapped}'" if mapped else "-> ignored (not in label map)"
        print(f"      {name:<14} {conf:.2f}  clears threshold: {passes:<3}  {note}")

    # --- 4/5. what DeskOS would actually use ---------------------------
    usable = [
        (n, c)
        for n, c in raw
        if n in _COCO_LABEL_MAP and c >= settings.perception.confidence_threshold
    ]
    print(f"\n[4] Detections DeskOS would actually use: {len(usable)}")
    if usable:
        for name, conf in usable:
            print(f"      {_COCO_LABEL_MAP[name]} ({conf:.2f})")
        print("\n    Vision is working. If the app still shows 'det=-', the")
        print("    problem is elsewhere - send this output over.")
    else:
        recognised = [n for n, _ in raw]
        mappable = [n for n in recognised if n in _COCO_LABEL_MAP]
        if not mappable:
            print("    YOLO sees things, but none are in DeskOS's label map.")
            print(f"    It saw: {', '.join(sorted(set(recognised))[:12])}")
            print("    -> The label map may need widening for your desk.")
        else:
            print("    The right objects are visible but below the threshold.")
            print(f"    -> Lower perception.confidence_threshold (now "
                  f"{settings.perception.confidence_threshold}).")


if __name__ == "__main__":
    main()
