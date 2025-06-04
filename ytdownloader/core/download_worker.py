# YTDownloaderPro/ytdownloader/core/download_worker.py
import os
import time # For small delay
import re   # For extracting bitrate
from PyQt6.QtCore import QThread, pyqtSignal
from pytubefix import YouTube # For type hinting the pytube_object
from pytubefix.streams import Stream # For type hinting
from moviepy import AudioFileClip # For MP3 conversion


class InfoFetcherThread(QThread):
    info_ready = pyqtSignal(dict)
    error_occurred = pyqtSignal(str)

    def __init__(self, url, parent=None):
        super().__init__(parent)
        self.url = url
        self._is_running = True

    def run(self):
        if not self._is_running: return
        try:
            # Import get_video_info here to avoid circular dependency if download_worker
            # is imported by youtube_handler for some reason (it shouldn't be)
            from .youtube_handler import get_video_info
            video_data = get_video_info(self.url)
            if not self._is_running: return # Check again after potentially long operation

            if video_data.get("success"):
                self.info_ready.emit(video_data)
            else:
                self.error_occurred.emit(video_data.get("error", "Unknown error fetching info."))
        except Exception as e:
            if self._is_running: # Only emit if not stopped
                self.error_occurred.emit(f"Critical thread error: {str(e)}")

    def stop(self):
        self._is_running = False


class DownloadWorkerThread(QThread):
    progress_updated = pyqtSignal(int)
    status_updated = pyqtSignal(str)
    download_finished = pyqtSignal(str, str) # final_filepath, original_filename_base
    error_occurred = pyqtSignal(str)

    def __init__(self, pytube_object: YouTube, selected_itag: int, download_path: str, output_format: str, filename_base: str, parent=None):
        super().__init__(parent)
        self.pytube_object = pytube_object
        self.selected_itag = selected_itag
        self.download_path = download_path
        self.output_format = output_format.upper() # Ensure "MP4" or "MP3"
        self.filename_base = filename_base
        self._is_running = True
        self._download_cancelled_flag = False # For progress callback to check and raise error

    def run(self):
        if not self._is_running:
            return

        downloaded_filepath_intermediate = None # To store path for potential cleanup

        try:
            stream_to_download: Stream = self.pytube_object.streams.get_by_itag(self.selected_itag)
            if not stream_to_download:
                self.error_occurred.emit(f"Could not find stream with itag {self.selected_itag}.")
                return

            self.status_updated.emit(f"Starting download: {self.filename_base}...")

            # Ensure the download directory exists
            os.makedirs(self.download_path, exist_ok=True)

            def progress_function(stream, chunk, bytes_remaining):
                if not self._is_running or self._download_cancelled_flag:
                    raise InterruptedError("Download cancelled by user during progress.")

                total_size = stream.filesize
                if total_size > 0:
                    bytes_downloaded = total_size - bytes_remaining
                    percentage = int((bytes_downloaded / total_size) * 100)
                    self.progress_updated.emit(percentage)
                else:
                    self.progress_updated.emit(0)

            self.pytube_object.register_on_progress_callback(progress_function)

            self.status_updated.emit(f"Downloading {self.filename_base} (as {stream_to_download.subtype})...")

            # Construct the full intermediate filename pytubefix expects
            intermediate_filename_with_ext = f"{self.filename_base}.{stream_to_download.subtype}"

            downloaded_filepath_intermediate = stream_to_download.download(
                output_path=self.download_path,
                filename=intermediate_filename_with_ext
            )

            self.progress_updated.emit(100)
            self.pytube_object.register_on_progress_callback(None)

            if not self._is_running:
                self.status_updated.emit("Download process stopped post-download.")
                if downloaded_filepath_intermediate and os.path.exists(downloaded_filepath_intermediate):
                    os.remove(downloaded_filepath_intermediate)
                return

            final_filepath = downloaded_filepath_intermediate

            if self.output_format == "MP3":
                self.status_updated.emit(f"Converting {self.filename_base} to MP3...")
                self.progress_updated.emit(0)

                if not stream_to_download.includes_audio_track:
                     self.error_occurred.emit(f"Selected stream for MP3 ('{stream_to_download.mime_type}') has no audio track.")
                     if downloaded_filepath_intermediate and os.path.exists(downloaded_filepath_intermediate):
                         os.remove(downloaded_filepath_intermediate)
                     return

                mp3_filename_base = self.filename_base
                final_filepath = os.path.join(self.download_path, f"{mp3_filename_base}.mp3")

                time.sleep(0.1) # Small delay, sometimes helps with file locks

                target_bitrate = None
                if stream_to_download.abr: # e.g., "160kbps"
                    match = re.search(r'(\d+)', stream_to_download.abr)
                    if match:
                        numeric_bitrate = int(match.group(1))
                        if numeric_bitrate > 0: # Ensure valid bitrate
                            target_bitrate = f"{numeric_bitrate}k"
                            self.status_updated.emit(f"Converting to MP3 at approximately {target_bitrate}...")
                        else:
                            self.status_updated.emit("Warning: Invalid source bitrate detected. Using default for MP3.")
                    else:
                        self.status_updated.emit("Warning: Could not parse source bitrate. Using default for MP3.")
                else:
                    self.status_updated.emit("Warning: Source bitrate not available. Using default for MP3.")

                audio_clip = AudioFileClip(downloaded_filepath_intermediate)

                try:
                    if target_bitrate:
                        audio_clip.write_audiofile(final_filepath, bitrate=target_bitrate, logger=None)
                    else:
                        # Fallback to moviepy's default if no bitrate determined (often ~128k)
                        audio_clip.write_audiofile(final_filepath, logger=None)
                finally: # Ensure clip is closed even if write_audiofile fails
                    audio_clip.close()


                if os.path.exists(downloaded_filepath_intermediate) and downloaded_filepath_intermediate != final_filepath:
                    os.remove(downloaded_filepath_intermediate)

                self.status_updated.emit("MP3 conversion complete.")
                self.progress_updated.emit(100)

            self.download_finished.emit(final_filepath, self.filename_base)

        except InterruptedError:
            self.status_updated.emit("Download cancelled by user.")
            if downloaded_filepath_intermediate and os.path.exists(downloaded_filepath_intermediate):
                os.remove(downloaded_filepath_intermediate)
        except Exception as e:
            import traceback
            print("------ ERROR IN DOWNLOAD WORKER ------")
            traceback.print_exc()
            print("------------------------------------")
            error_msg = f"Download/Conversion Error: {type(e).__name__} - {str(e)}"
            self.error_occurred.emit(error_msg)
            if downloaded_filepath_intermediate and os.path.exists(downloaded_filepath_intermediate):
                try:
                    os.remove(downloaded_filepath_intermediate)
                except Exception as cleanup_e:
                    print(f"Error cleaning up intermediate file: {cleanup_e}")
        finally:
            if self.pytube_object:
                 self.pytube_object.register_on_progress_callback(None)

    def stop(self):
        self.status_updated.emit("Attempting to stop download/conversion...")
        self._is_running = False
        self._download_cancelled_flag = True # Signal to progress callback
