import os
import sys
import shutil

import yt_dlp
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer, util

from logger import MyLogger
from structures import UserPrompts
from effects import EditorEffects
from utils import FontUtils

load_dotenv()

my_prompt = UserPrompts(
    title=os.getenv("TITLE", "Never gonna give you up"),
    author=os.getenv("AUTHOR", "Rick Astley"),
    language=os.getenv("LANGUAGE", "en"),
)

sys.stderr = open("error.log", "w")

logger = MyLogger.get_logger("main")
logger.info("Loading SentenceTransformer model...")
model = SentenceTransformer("all-MiniLM-L6-v2")
embedding1 = model.encode(
    f"The original video music video called {my_prompt.title} by {my_prompt.author}."
)
logger.info("Model loaded successfully.")

ydl_opts = {
    "skip_download": True,
    "extract_flat": "in_playlist",
    "logger": logger,
}

download_opts = {
    "http_headers": {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/138.0.0.0 Safari/537.36"
        ),
        "Referer": "https://www.youtube.com/",
    },
    "outtmpl": "downloads/%(title)s.%(ext)s",
    "geo_bypass": True,
    "logger": logger,
    "subtitleslangs": [my_prompt.language],
    "subtitlesformat": "srt",
    "writesubtitles": True,
    "writeautomaticsub": True,
    # "verbose": True,
}


with yt_dlp.YoutubeDL(ydl_opts) as ydl:
    logger.info("Searching for videos...")
    results = ydl.extract_info(
        f"ytsearch5:{my_prompt.title} {my_prompt.author}", download=False
    )
    logger.info("Search completed.")

    max_entry = None
    max_metric = -1
    max_cosine_similarity = -1
    if results is None:
        logger.error("No results found.")
        exit(1)

    max_view = max(entry.get("view_count", 0) for entry in results["entries"])
    min_view = min(entry.get("view_count", 0) for entry in results["entries"])

    logger.info(f"Max view count: {max_view}, Min view count: {min_view}")
    for entry in results["entries"]:
        description = (
            "Title Video: "
            + entry.get("title", "No title")
            + " from channel: "
            + entry.get("channel", "No uploader")
            + " with total views: "
            + str(entry.get("view_count", "Not available"))
        )
        embedding2 = model.encode(description)

        # Compute cosine similarity between the embeddings
        cos_sim = util.cos_sim(embedding1, embedding2)

        # Normalize view_count to a range of 0 to 1
        current_view_count = entry.get("view_count", 0)
        normalized_view_count = (current_view_count - min_view) / (max_view - min_view)

        logger.info(
            f"Video: {entry.get('title', 'No title')}, Channel: {
                entry.get('channel', 'No uploader')
            }, Total Views: {
                entry.get('view_count', 'Not available')
            }, Normalize View Count : {normalized_view_count:.4f}, Cosine similarity: {
                cos_sim.item():.4f}"
        )

        weird_metric = cos_sim.item() * 0.7 + normalized_view_count * 0.3
        if weird_metric > max_metric:
            max_metric = weird_metric
            max_entry = entry
            max_cosine_similarity = cos_sim.item()

    # Download the video
    if max_entry:
        logger.info(
            f"Best match found: {max_entry.get('title', 'No title')} with cosine similarity {max_cosine_similarity:.4f}, with views: {max_entry.get('view_count', 'Not available')}"
        )
        with yt_dlp.YoutubeDL(download_opts) as download_ydl:
            logger.info(f"Downloading {max_entry['url']}")
            ret_code = download_ydl.download([max_entry["url"]])
            if ret_code != 0:
                logger.error(
                    f"Failed to download video: {max_entry['url']}, return code: {ret_code}"
                )
                exit(1)

            metadata = download_ydl.extract_info(max_entry["url"], download=False)
            if not metadata:
                logger.error("Failed to extract metadata from the downloaded video.")
                exit(1)
            # Get subtitles
            # If there is a manual subtitle, use it, discard the automatic one
            if "subtitles" in metadata and my_prompt.language in metadata["subtitles"]:
                logger.info(
                    f"Using manual subtitles for language: {my_prompt.language}"
                )
            elif (
                "automatic_captions" in metadata
                and my_prompt.language in metadata["automatic_captions"]
            ):
                logger.info(
                    f"Using automatic subtitles for language: {my_prompt.language}"
                )
            else:
                logger.error(
                    f"No subtitles found for language: {my_prompt.language}. Exiting."
                )
                exit(1)

            file_name = download_ydl.prepare_filename(metadata)
            base_name = os.path.splitext(file_name)[0]
            subtitle_file = f"{base_name}.{my_prompt.language}.srt"

            logger.info(f"Downloaded to {file_name}")

            edited_filename = os.path.splitext(file_name)[0] + "_edited.mp4"
            shutil.copy(file_name, edited_filename)

            editor = EditorEffects(
                file_path=edited_filename,
                subtitle_path=subtitle_file,
                metadata=metadata,
            )
            logger.info(f"Using font: {FontUtils.CURRENT_FONT}")
            editor.effects_vid(user_prompts=my_prompt)
            editor.add_subtitles()

    else:
        logger.warning("No suitable video found.")

logger.info("Finished")
