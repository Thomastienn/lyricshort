from structures import Effect


class EditorEffects:
    def __init__(self, file_path, logger=None):
        self.file_path = file_path
        self.logger = logger

    def apply_effects(self, effects: list[Effect]):
        """
        Apply a list of effects to the video.
        :param effects: List of Effect instances
        """
        for effect in effects:
            if self.logger:
                self.logger.info(f"Applying effect: {effect.__class__.__name__}")
            effect.apply(self.file_path)
            if self.logger:
                self.logger.info(
                    f"Effect {effect.__class__.__name__} applied successfully."
                )
