import livekit.plugins.turn_detector
print("Turn Detector dir:", dir(livekit.plugins.turn_detector))
for x in dir(livekit.plugins.turn_detector):
    if not x.startswith("_"):
        attr = getattr(livekit.plugins.turn_detector, x)
        print(f"{x}: {type(attr)}")
