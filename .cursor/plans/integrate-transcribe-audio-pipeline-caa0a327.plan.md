<!-- caa0a327-a1e6-409b-b036-ba43f42e43ec aab71e8c-2175-42bc-b862-aba989b4a4ef -->
# Integrate Transcribe Audio into Pipeline

## Overview

Integrate the `transcribe_audio` module into the pipeline orchestrator as the final processing step, refactor its configuration to match project conventions, and ensure it follows all established patterns.

## Implementation Steps

### 1. Refactor transcribe_audio Configuration

**File**: `src/transcribe_audio/config/config_transcribe_audio.py`

Convert from class-based config to dataclass pattern matching other modules:

- Change from `TranscriptionConfig` class to dataclass structure
- Implement precedence: env → .env → project_config → module defaults
- Add integration with `common/project_config.py`
- Maintain all existing settings (models, formats, API settings)

**Pattern to follow**: `src/dl_from_gdrive/config/config_dl_from_gdrive.py`

### 2. Add Project-Level Configuration

**File**: `common/project_config.py`

Add transcription settings to `ProjectConfig` dataclass:

- `enable_transcribe_audio: bool` (default: `True`)
- `transcribe_audio_blacklist: List[str]` (default: same as audio_rm_silence)
- Load from environment variables with fallbacks
- Support comma-separated env var parsing

### 3. Configure Centralized Logging

**File**: `common/logging_utils/logging_config.py`

Add logger configuration for transcribe_audio:

```python
"transcribe_audio": {
    "log_filename": "transcribe_audio.log",
    "console_output": True,
    "file_output": True
}
```

### 4. Refactor transcribe_audio Main Module

**File**: `src/transcribe_audio/main.py`

Update to support both CLI and pipeline integration:

- Keep existing CLI functionality intact
- Add `main()` function for pipeline orchestrator (no args)
- Integrate with project_config for directory/blacklist
- Use centralized logging (remove custom logging setup for pipeline mode)
- Process all audio files in download directory structure
- Respect blacklist patterns from project_config
- Save `.txt` files alongside audio files

### 5. Integrate into Pipeline Orchestrator

**File**: `pipeline_orchestrator.py`

Add transcribe_audio as final pipeline step:

- Import `from src.transcribe_audio.main import main as transcribe_audio_main`
- Add conditional execution based on `project_config.enable_transcribe_audio`
- Chain after `audio_rm_silence` step
- Add to pipeline_steps list with proper ordering
- Log enable/disable status
- Include in summary statistics

### 6. Update README Documentation

**File**: `README.md`

Document the new transcribe_audio module:

- Add to pipeline steps section
- Document configuration options
- Add environment variable examples
- Update module status table
- Document blacklist pattern usage

### 7. Update Module README

**File**: `src/transcribe_audio/README.md`

Ensure documentation covers:

- Pipeline integration usage
- Standalone CLI usage
- Configuration precedence
- Blacklist support
- OpenAI API key requirements

## Key Design Decisions

1. **Configuration Pattern**: Match existing dataclass pattern for consistency
2. **Pipeline Position**: Final step (after silence removal, before/alongside future database ingestion)
3. **Blacklist Default**: Same as `audio_rm_silence_blacklist` to avoid transcribing non-voice content
4. **File Output**: Save `.txt` files alongside source audio files for easy association
5. **Error Handling**: Continue processing on individual file errors (don't break pipeline)

## Files Modified

- `src/transcribe_audio/config/config_transcribe_audio.py` (refactor)
- `src/transcribe_audio/main.py` (enhance for pipeline)
- `common/project_config.py` (add settings)
- `common/logging_utils/logging_config.py` (add logger)
- `pipeline_orchestrator.py` (integrate module)
- `README.md` (document)
- `src/transcribe_audio/README.md` (update if needed)

## Testing Approach

After integration, test:

1. Pipeline runs with transcription enabled
2. Pipeline skips transcription when disabled
3. Blacklist patterns are respected
4. CLI mode still works independently
5. Logs appear in correct file
6. Configuration precedence works correctly

### To-dos

- [ ] Refactor transcribe_audio config from class-based to dataclass pattern matching project conventions
- [ ] Add transcribe_audio settings to common/project_config.py (enable flag, blacklist)
- [ ] Add transcribe_audio logger configuration to logging_config.py
- [ ] Enhance transcribe_audio/main.py to support pipeline integration (directory walking, blacklist support)
- [ ] Integrate transcribe_audio into pipeline_orchestrator.py as final step
- [ ] Update main README.md to document transcribe_audio module and configuration