"""Conservative, local hints from sampled preview images, not a video verdict."""

class FrameHealth:
    def __init__(self, max_gap=30):
        self.max_gap = max_gap
        self.reset()

    def reset(self):
        self._previous = None
        self._last_at = None
        self._still_since = None
        self._still_samples = 0
        self._dark_since = None
        self._dark_samples = 0

    def observe(self, image, timestamp):
        if self._last_at is not None and (timestamp <= self._last_at or timestamp - self._last_at > self.max_gap):
            self.reset()
        # Small luminance samples avoid retaining or logging the user's frame.
        pixels = image.convert('L').resize((32, 18)).tobytes()
        if self._previous is None:
            self._still_since, self._still_samples = timestamp, 1
        else:
            difference = sum(abs(a - b) for a, b in zip(pixels, self._previous)) / len(pixels)
            if difference <= 1.5:
                self._still_samples += 1
            else:
                self._still_since, self._still_samples = timestamp, 1
        dark = sum(value <= 8 for value in pixels) / len(pixels) >= .98
        if dark:
            if self._dark_since is None:
                self._dark_since, self._dark_samples = timestamp, 1
            else:
                self._dark_samples += 1
        else:
            self._dark_since, self._dark_samples = None, 0
        self._previous, self._last_at = pixels, timestamp
        hints = []
        if self._dark_samples >= 3 and timestamp - self._dark_since >= 20:
            hints.append('预览持续较暗，加载过程中也可能出现')
        if self._still_samples >= 4 and timestamp - self._still_since >= 60:
            hints.append('预览长时间未变化，静止界面也可能如此')
        return hints
