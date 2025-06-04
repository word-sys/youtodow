# YTDownloaderPro/ytdownloader/utils/file_helper.py
import re
import os

def sanitize_filename(filename_str):
    """
    Sanitizes a string to be a valid filename.
    Removes or replaces characters that are not allowed in filenames
    on most common operating systems.
    """
    if not filename_str:
        return "untitled_video"

    # Remove characters that are invalid in Windows filenames and often problematic elsewhere
    # \ / : * ? " < > |
    # Also remove control characters (0-31)
    sanitized = re.sub(r'[\\/*?:"<>|\x00-\x1f]', "", filename_str)

    # Replace multiple spaces with a single space, and strip leading/trailing spaces
    sanitized = re.sub(r'\s+', ' ', sanitized).strip()

    # Avoid names that are reserved on Windows (CON, PRN, AUX, NUL, COM1-9, LPT1-9)
    # Also avoid filenames starting or ending with a dot or space (problematic on Windows)
    if sanitized.upper() in ["CON", "PRN", "AUX", "NUL"] or \
       re.match(r"^(COM|LPT)[1-9]$", sanitized.upper()):
        sanitized = "_" + sanitized + "_"

    # Remove leading/trailing dots and spaces again after potential modifications
    sanitized = sanitized.strip('. ')

    # If the name becomes empty after sanitization, provide a default
    if not sanitized:
        sanitized = "downloaded_video"

    # Limit length (conservative limit to avoid issues with full path length)
    max_len = 180
    if len(sanitized) > max_len:
        # Try to cut at a space if possible
        cut_at = sanitized.rfind(' ', 0, max_len)
        if cut_at != -1:
            sanitized = sanitized[:cut_at]
        else:
            sanitized = sanitized[:max_len]

    return sanitized

if __name__ == '__main__':
    test_names = [
        "My Video: Awesome & Cool / EP. 1? \"Quotes\" * Stars < > |",
        "  leading and trailing spaces  ",
        "CON",
        "LPT1.mp4",
        "file.with.dots.txt",
        ".hiddenfile",
        "ver\tver\ny\nlong\rfilename" * 10,
        "",
        None
    ]
    for name in test_names:
        print(f"Original: '{name}' -> Sanitized: '{sanitize_filename(name)}'")
