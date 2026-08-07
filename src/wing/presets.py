from enum import Enum

class Presets(Enum):
    FLUTTER = 0

class Preset:

    def __init__(self, preset, port, *args, **kwargs):
        self.preset = preset
        self.port = port