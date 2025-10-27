"""
Project-level Configuration Module

This module centralizes project-wide settings. It currently defines the
primary source of truth for the downloads directory used by the app.

Loading order (highest to lowest precedence):
1. Environment variables
2. .env file in project root
3. Default values in this file (None)

If this module is missing or `download_dir` is not set, modules should
fall back to their own configuration defaults as documented locally.
"""

import os
from dataclasses import dataclass
from typing import Optional, List

from .utils.file_sys_utils import get_script_directory


@dataclass
class ProjectConfig:
    download_dir: Optional[str]
    processed_download_dir: Optional[str]
    enable_dl_from_gdrive: bool
    enable_dl_from_gmail: bool
    enable_extract_audio: bool
    extract_audio_blacklist: List[str]
    enable_audio_rm_silence: bool
    audio_rm_silence_blacklist: List[str]
    enable_transcribe_audio: bool
    transcribe_audio_blacklist: List[str]
    enable_docx_to_txt: bool
    docx_to_txt_blacklist: List[str]
    enable_text_processor: bool
    text_processor_blacklist: List[str]
    enable_data_ingest: bool

    @classmethod
    def load(cls) -> "ProjectConfig":
        """
        Load project-level configuration with precedence env > .env > defaults.
        Configures `download_dir`, `enable_dl_from_gdrive`, `enable_dl_from_gmail`, 
        `enable_extract_audio`, `extract_audio_blacklist`, `enable_audio_rm_silence`, 
        `audio_rm_silence_blacklist`, `enable_transcribe_audio`, `transcribe_audio_blacklist`, 
        `enable_docx_to_txt`, `docx_to_txt_blacklist`, `enable_text_processor`, 
        `text_processor_blacklist`, and `enable_data_ingest` pipeline control.
        """
        # Default values
        download_dir: Optional[str] = r"C:\Users\pmpmt\Scripts_Cursor\z_tests\downloads"
        processed_download_dir: Optional[str] = r"C:\Users\pmpmt\Scripts_Cursor\z_tests\processed_downloads"
        enable_dl_from_gdrive: bool = True
        enable_dl_from_gmail: bool = True
        enable_extract_audio: bool = True
        extract_audio_blacklist: List[str] = ["text", "other", "spreadsheets", "gmail_attachments"]
        enable_audio_rm_silence: bool = True
        audio_rm_silence_blacklist: List[str] = ["text", "other", "spreadsheets", "gmail_attachments", "video"]
        enable_transcribe_audio: bool = True
        transcribe_audio_blacklist: List[str] = ["text", "other", "spreadsheets", "gmail_attachments", "video"]
        enable_docx_to_txt: bool = True
        docx_to_txt_blacklist: List[str] = ["video"]
        enable_text_processor: bool = True
        text_processor_blacklist: List[str] = ["video"]
        enable_data_ingest: bool = True

        # Try to load from .env if present (without overriding env vars)
        env_file = get_script_directory() / ".env"
        if env_file.exists():
            try:
                with open(env_file, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith("#") and "=" in line:
                            key, value = line.split("=", 1)
                            key = key.strip()
                            value = value.strip().strip("'\"")
                            if key == "DOWNLOAD_DIR" and "DOWNLOAD_DIR" not in os.environ:
                                download_dir = value
                            elif key == "ENABLE_DL_FROM_GDRIVE" and "ENABLE_DL_FROM_GDRIVE" not in os.environ:
                                enable_dl_from_gdrive = value.lower() in ("true", "1", "yes", "on")
                            elif key == "ENABLE_DL_FROM_GMAIL" and "ENABLE_DL_FROM_GMAIL" not in os.environ:
                                enable_dl_from_gmail = value.lower() in ("true", "1", "yes", "on")
                            elif key == "ENABLE_EXTRACT_AUDIO" and "ENABLE_EXTRACT_AUDIO" not in os.environ:
                                enable_extract_audio = value.lower() in ("true", "1", "yes", "on")
                            elif key == "EXTRACT_AUDIO_BLACKLIST" and "EXTRACT_AUDIO_BLACKLIST" not in os.environ:
                                extract_audio_blacklist = [item.strip() for item in value.split(",") if item.strip()]
                            elif key == "ENABLE_AUDIO_RM_SILENCE" and "ENABLE_AUDIO_RM_SILENCE" not in os.environ:
                                enable_audio_rm_silence = value.lower() in ("true", "1", "yes", "on")
                            elif key == "AUDIO_RM_SILENCE_BLACKLIST" and "AUDIO_RM_SILENCE_BLACKLIST" not in os.environ:
                                audio_rm_silence_blacklist = [item.strip() for item in value.split(",") if item.strip()]
                            elif key == "ENABLE_TRANSCRIBE_AUDIO" and "ENABLE_TRANSCRIBE_AUDIO" not in os.environ:
                                enable_transcribe_audio = value.lower() in ("true", "1", "yes", "on")
                            elif key == "TRANSCRIBE_AUDIO_BLACKLIST" and "TRANSCRIBE_AUDIO_BLACKLIST" not in os.environ:
                                transcribe_audio_blacklist = [item.strip() for item in value.split(",") if item.strip()]
                            elif key == "ENABLE_DOCX_TO_TXT" and "ENABLE_DOCX_TO_TXT" not in os.environ:
                                enable_docx_to_txt = value.lower() in ("true", "1", "yes", "on")
                            elif key == "DOCX_TO_TXT_BLACKLIST" and "DOCX_TO_TXT_BLACKLIST" not in os.environ:
                                docx_to_txt_blacklist = [item.strip() for item in value.split(",") if item.strip()]
                            elif key == "ENABLE_TEXT_PROCESSOR" and "ENABLE_TEXT_PROCESSOR" not in os.environ:
                                enable_text_processor = value.lower() in ("true", "1", "yes", "on")
                            elif key == "TEXT_PROCESSOR_BLACKLIST" and "TEXT_PROCESSOR_BLACKLIST" not in os.environ:
                                text_processor_blacklist = [item.strip() for item in value.split(",") if item.strip()]
                            elif key == "ENABLE_DATA_INGEST" and "ENABLE_DATA_INGEST" not in os.environ:
                                enable_data_ingest = value.lower() in ("true", "1", "yes", "on")
            except Exception:
                # Avoid raising on optional .env read for robustness
                pass

        # Environment variable overrides .env/default
        download_dir = os.getenv("DOWNLOAD_DIR", download_dir)
        enable_dl_from_gdrive_env = os.getenv("ENABLE_DL_FROM_GDRIVE")
        if enable_dl_from_gdrive_env is not None:
            enable_dl_from_gdrive = enable_dl_from_gdrive_env.lower() in ("true", "1", "yes", "on")
        
        enable_dl_from_gmail_env = os.getenv("ENABLE_DL_FROM_GMAIL")
        if enable_dl_from_gmail_env is not None:
            enable_dl_from_gmail = enable_dl_from_gmail_env.lower() in ("true", "1", "yes", "on")
        
        enable_extract_audio_env = os.getenv("ENABLE_EXTRACT_AUDIO")
        if enable_extract_audio_env is not None:
            enable_extract_audio = enable_extract_audio_env.lower() in ("true", "1", "yes", "on")
        
        extract_audio_blacklist_env = os.getenv("EXTRACT_AUDIO_BLACKLIST")
        if extract_audio_blacklist_env is not None:
            extract_audio_blacklist = [item.strip() for item in extract_audio_blacklist_env.split(",") if item.strip()]
        
        enable_audio_rm_silence_env = os.getenv("ENABLE_AUDIO_RM_SILENCE")
        if enable_audio_rm_silence_env is not None:
            enable_audio_rm_silence = enable_audio_rm_silence_env.lower() in ("true", "1", "yes", "on")
        
        audio_rm_silence_blacklist_env = os.getenv("AUDIO_RM_SILENCE_BLACKLIST")
        if audio_rm_silence_blacklist_env is not None:
            audio_rm_silence_blacklist = [item.strip() for item in audio_rm_silence_blacklist_env.split(",") if item.strip()]
        
        enable_transcribe_audio_env = os.getenv("ENABLE_TRANSCRIBE_AUDIO")
        if enable_transcribe_audio_env is not None:
            enable_transcribe_audio = enable_transcribe_audio_env.lower() in ("true", "1", "yes", "on")
        
        transcribe_audio_blacklist_env = os.getenv("TRANSCRIBE_AUDIO_BLACKLIST")
        if transcribe_audio_blacklist_env is not None:
            transcribe_audio_blacklist = [item.strip() for item in transcribe_audio_blacklist_env.split(",") if item.strip()]
        
        enable_docx_to_txt_env = os.getenv("ENABLE_DOCX_TO_TXT")
        if enable_docx_to_txt_env is not None:
            enable_docx_to_txt = enable_docx_to_txt_env.lower() in ("true", "1", "yes", "on")
        
        docx_to_txt_blacklist_env = os.getenv("DOCX_TO_TXT_BLACKLIST")
        if docx_to_txt_blacklist_env is not None:
            docx_to_txt_blacklist = [item.strip() for item in docx_to_txt_blacklist_env.split(",") if item.strip()]
        
        enable_text_processor_env = os.getenv("ENABLE_TEXT_PROCESSOR")
        if enable_text_processor_env is not None:
            enable_text_processor = enable_text_processor_env.lower() in ("true", "1", "yes", "on")
        
        text_processor_blacklist_env = os.getenv("TEXT_PROCESSOR_BLACKLIST")
        if text_processor_blacklist_env is not None:
            text_processor_blacklist = [item.strip() for item in text_processor_blacklist_env.split(",") if item.strip()]
        
        enable_data_ingest_env = os.getenv("ENABLE_DATA_INGEST")
        if enable_data_ingest_env is not None:
            enable_data_ingest = enable_data_ingest_env.lower() in ("true", "1", "yes", "on")

        return cls(
            download_dir=download_dir, 
            processed_download_dir=processed_download_dir,
            enable_dl_from_gdrive=enable_dl_from_gdrive, 
            enable_dl_from_gmail=enable_dl_from_gmail,
            enable_extract_audio=enable_extract_audio,
            extract_audio_blacklist=extract_audio_blacklist,
            enable_audio_rm_silence=enable_audio_rm_silence,
            audio_rm_silence_blacklist=audio_rm_silence_blacklist,
            enable_transcribe_audio=enable_transcribe_audio,
            transcribe_audio_blacklist=transcribe_audio_blacklist,
            enable_docx_to_txt=enable_docx_to_txt,
            docx_to_txt_blacklist=docx_to_txt_blacklist,
            enable_text_processor=enable_text_processor,
            text_processor_blacklist=text_processor_blacklist,
            enable_data_ingest=enable_data_ingest
        )


# Global config instance
project_config = ProjectConfig.load()


