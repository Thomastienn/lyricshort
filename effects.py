import os
import logging
import tempfile
from typing import Sequence

import ffmpeg
import srt

from utils import StreamUtils
from structures import (
    Effect,
    TrimEffect,
    TextOverlayEffect,
    TextOverlayProperties,
    FillOverlayEffect,
    TextPosition,
    UserPrompts,
)


class EditorEffects:
    def __init__(
        self, file_path: str, subtitle_path: str, logger: logging.Logger, metadata=None
    ):
        self.file_path = file_path
        self.subtitle_path = subtitle_path
        self.logger = logger
        self.metadata = metadata
        self.start_time = 25
        self.duration = 20

    def apply_effects_individual(self, effects: Sequence[Effect]):
        """
        Apply a single effect to the video.
        :param effect: Effect instance
        """
        for effect in effects:
            try:
                logging.info(f"Applying effect: {effect.__class__.__name__}")
                effect.apply(self.file_path)
            except ffmpeg.Error as e:
                self.logger.error(
                    f"Error applying effect {effect.__class__.__name__}: {e}"
                )
                self.logger.error(
                    e.stdout.decode("utf-8") if e.stdout else "No ffmpeg stdout"
                )
                self.logger.error(
                    e.stderr.decode("utf-8") if e.stderr else "No ffmpeg stderr"
                )
                raise
            self.logger.info(
                f"Effect {effect.__class__.__name__} applied successfully."
            )

    def apply_effects(self, effects: Sequence[Effect]):
        """
        Apply a list of effects to the video.
        :param effects: List of Effect instances
        """
        # self.apply_effects_individual(effects)
        # return
        cnt = 0
        trim_idx = len(effects)
        for i, effect in enumerate(effects):
            cnt += isinstance(effect, TrimEffect)
            if isinstance(effect, TrimEffect):
                trim_idx = i

        if cnt > 1:
            self.apply_effects_individual(effects)
            return

        def apply_without_trim(local_effects):
            if not local_effects:
                return
            self.logger.info(
                f"Applying effects without trim: {[effect.__class__.__name__ for effect in local_effects]}"
            )
            input_stream = ffmpeg.input(self.file_path)
            video_node: ffmpeg.nodes.FilterableStream = input_stream.video
            audio_node = input_stream.audio

            for effect in local_effects:
                video_node: ffmpeg.nodes.FilterableStream = effect.video_node(
                    video_node, self.file_path
                )

            try:
                audio_codec = StreamUtils.get_audio_codec(self.file_path)
                acodec = "copy" if audio_codec == "aac" else "aac"

                with tempfile.NamedTemporaryFile(
                    suffix=".mp4", delete=False
                ) as temp_file:
                    (
                        ffmpeg.output(
                            video_node,
                            audio_node,
                            temp_file.name,
                            vcodec="libx264",
                            acodec=acodec,
                        )
                        .overwrite_output()
                        .global_args(
                            "-hide_banner",
                            "-loglevel",
                            "error",  # Suppress ffmpeg output
                            "-stats",  # Show progress stats
                        )
                        .run()
                    )
                    os.replace(temp_file.name, self.file_path)

                self.logger.info(f"Effects applied successfully without trim.")
            except ffmpeg.Error as e:
                self.logger.error(f"Error applying effects : {e}")
                self.logger.error(
                    e.stdout.decode("utf-8") if e.stdout else "No ffmpeg stdout"
                )
                self.logger.error(
                    e.stderr.decode("utf-8") if e.stderr else "No ffmpeg stderr"
                )
                raise

        apply_without_trim(effects[:trim_idx])
        if trim_idx < len(effects):
            self.logger.info("Found a trim effect, applying it.")
            self.apply_effects_individual([effects[trim_idx]])
        else:
            self.logger.info("No trim effect to apply.")
        apply_without_trim(effects[trim_idx + 1 :])

        self.logger.info("Effects applied successfully.")

    def effects_vid(
        self,
        user_prompts: UserPrompts,
    ):
        trim = TrimEffect(
            start_time=self.start_time, end_time=self.start_time + self.duration
        )
        fill_overlay = FillOverlayEffect(color="black", opacity=0.4)
        text_overlay = TextOverlayEffect(
            texts=[
                TextOverlayProperties(
                    text=f"{user_prompts.title} by {user_prompts.author}",
                    position=TextPosition(
                        vertical="top",
                        horizontal="center",
                    ),
                    font_size=50,
                    color="white",
                    duration=self.duration,
                    offset=(0, 20),  # Offset for top margin
                )
            ]
        )

        try:
            self.apply_effects([trim, fill_overlay, text_overlay])
            self.logger.info(f"Applied all effects to {self.file_path}")
        except ffmpeg.Error as e:
            self.logger.error(f"Error applying effects: {e}")
            raise

    def add_subtitles(self):
        """
        Add subtitles to the video.
        """
        if not os.path.exists(self.subtitle_path):
            self.logger.error(f"Subtitle file {self.subtitle_path} does not exist.")
            return

        with open(self.subtitle_path, "r", encoding="utf-8") as file:
            subtitles = srt.parse(file.read())

        subtitle_props: list[TextOverlayProperties] = []
        for subtitle in subtitles:
            text: str = subtitle.content
            start_time: float = subtitle.start.total_seconds() - self.start_time
            end_time: float = subtitle.end.total_seconds() - self.start_time

            self.logger.info(
                f"Adding subtitle: {subtitle.index}, '{text}' from {start_time} to {end_time}"
            )

            subtitle_prop = TextOverlayProperties(
                text=text,
                position=TextPosition(
                    vertical="center",
                    horizontal="center",
                ),
                font_size=24,
                color="white",
                start_time=start_time,
                duration=int(end_time - start_time),
                offset=(0, 20),
            )
            subtitle_props.append(subtitle_prop)

        subtitle_effect = TextOverlayEffect(texts=subtitle_props)
        self.apply_effects([subtitle_effect])
