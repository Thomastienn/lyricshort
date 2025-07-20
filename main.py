import sys
import logging

import yt_dlp
import ffmpeg
from sentence_transformers import SentenceTransformer, util

from effects import EditorEffects
from structures import BlurEffect, TrimEffect, TextOverlayEffect

VIDEO_TITLE = "Lost"
AUTHOR = "Obito"

sys.stderr = open("error.log", "w")


# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

console_handler = logging.StreamHandler(sys.stdout)
console_handler.setFormatter(
    logging.Formatter(
        "%(asctime)s - %(levelname)s - %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
    )
)
file_handler = logging.FileHandler("output.log", mode="w")
file_handler.setFormatter(
    logging.Formatter(
        "%(asctime)s - %(levelname)s - %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
    )
)

logger.addHandler(console_handler)
logger.addHandler(file_handler)

logger.info("Loading SentenceTransformer model...")
model = SentenceTransformer("all-MiniLM-L6-v2")
embedding1 = model.encode(
    f"The original video music video called {VIDEO_TITLE} by {AUTHOR}."
)
logger.info("Model loaded successfully.")

ydl_opts = {
    "skip_download": True,
    "extract_flat": "in_playlist",
    "logger": logger,
}

download_opts = {
    "outtmpl": "downloads/%(title)s.%(ext)s",
    "logger": logger,
}


def effects_vid(filename: str, metadata=None):
    editor = EditorEffects(filename, logger=logger)

    start_time = 10
    duration = 20

    trim = TrimEffect(start_time=start_time, end_time=start_time + duration)
    blur = BlurEffect(radius=10)

    try:
        editor.apply_effects([trim, blur])
        logger.info(f"Applied all effects to {filename}")
    except ffmpeg.Error as e:
        logger.error(f"Error applying blur effect: {e}")
        logger.error(e.stdout.decode("utf-8"))
        logger.error(e.stderr.decode("utf-8"))
        raise


with yt_dlp.YoutubeDL(ydl_opts) as ydl:
    logger.info("Searching for videos...")
    results = ydl.extract_info("ytsearch5:obito lost", download=False)
    logger.info("Search completed.")

    max_entry = None
    max_cos_sim = -1
    if results is None:
        logger.error("No results found.")
        exit(1)

    for entry in results["entries"]:
        description = (
            "Title Video: "
            + entry.get("title", "No title")
            + " from channel: "
            + entry.get("channel", "No uploader")
        )
        embedding2 = model.encode(description)

        # Compute cosine similarity between the embeddings
        cos_sim = util.cos_sim(embedding1, embedding2)

        logger.info(
            f"Video: {entry.get('title', 'No title')}, Channel: {entry.get('channel', 'No uploader')}, Cosine similarity: {cos_sim.item():.4f}"
        )
        if cos_sim > max_cos_sim:
            max_cos_sim = cos_sim.item()
            max_entry = entry

    # Download the video
    if max_entry:
        logger.info(
            f"Best match found: {max_entry.get('title', 'No title')} with cosine similarity {max_cos_sim:.4f}"
        )
        with yt_dlp.YoutubeDL(download_opts) as download_ydl:
            logger.info(f"Downloading {max_entry['url']}")
            download_ydl.download([max_entry["url"]])

            metadata = download_ydl.extract_info(max_entry["url"], download=False)
            file_name = download_ydl.prepare_filename(metadata)
            logger.info(f"Downloaded to {file_name}")
            effects_vid(file_name, metadata=metadata)

    else:
        logger.warning("No suitable video found.")

logger.info("Finished")
