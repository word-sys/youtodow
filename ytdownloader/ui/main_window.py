# YTDownloaderPro/ytdownloader/ui/main_window.py
import os
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QProgressBar, QStatusBar, QComboBox, QFileDialog, QMessageBox,
    QSpacerItem, QSizePolicy
)
from PyQt6.QtCore import QSize, Qt, QTimer # QTimer for delayed GUI updates if needed

# Relative imports
from ..core.download_worker import InfoFetcherThread, DownloadWorkerThread
from ..utils.file_helper import sanitize_filename

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("YT Downloader Pro")
        self.setMinimumSize(QSize(700, 550)) # Increased height a bit

        self.info_fetch_thread = None
        self.download_worker_thread = None
        self.current_pytube_object = None
        self.last_fetched_video_info = None # To store the raw info dict

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        self.main_layout = QVBoxLayout(central_widget)

        self._create_ui_elements()
        self._arrange_ui_elements()
        self._connect_signals()

        self.statusBar().showMessage("Ready. Please enter a YouTube URL.")
        self._load_initial_settings() # e.g., last download path


    def _load_initial_settings(self):
        # Placeholder for loading settings, e.g., last used download path
        # For now, you can set a default or leave it blank
        # self.path_input.setText(os.path.expanduser("~")) # Example: Home directory
        pass

    def _create_ui_elements(self):
        self.url_label = QLabel("YouTube URL:")
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("Enter YouTube video URL or ID here")

        self.fetch_button = QPushButton("Fetch Video Info")
        self.fetch_button.setFixedHeight(35)

        self.title_label_header = QLabel("Video Title:")
        self.video_title_label = QLabel("N/A")
        self.video_title_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        self.video_title_label.setWordWrap(True)

        self.format_label = QLabel("Select Format:")
        self.format_combobox = QComboBox()
        self.format_combobox.addItems(["MP4 (Video)", "MP3 (Audio Only)"])

        self.quality_label = QLabel("Select Quality:")
        self.quality_combobox = QComboBox()
        self.quality_combobox.setEnabled(False)
        self.quality_combobox.addItem("--- Fetch video first ---")

        self.path_label = QLabel("Download to:")
        self.path_input = QLineEdit()
        self.path_input.setPlaceholderText("Click 'Browse' to select download directory")
        self.path_input.setReadOnly(True)
        self.browse_button = QPushButton("Browse...")

        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFixedHeight(25)

        self.download_button = QPushButton("Download")
        self.download_button.setEnabled(False)
        self.download_button.setStyleSheet("font-size: 16px; padding: 8px 15px; background-color: #4CAF50; color: white; border-radius: 5px;")
        self.download_button.setFixedHeight(45)

        self.setStatusBar(QStatusBar(self))


    def _arrange_ui_elements(self):
        url_layout = QHBoxLayout()
        url_layout.addWidget(self.url_label)
        url_layout.addWidget(self.url_input, 1) # Stretch URL input
        self.main_layout.addLayout(url_layout)
        self.main_layout.addWidget(self.fetch_button)

        self.main_layout.addSpacing(10)
        line1 = QWidget()
        line1.setFixedHeight(1)
        line1.setStyleSheet("background-color: #c0c0c0;")
        self.main_layout.addWidget(line1)
        self.main_layout.addSpacing(10)

        self.main_layout.addWidget(self.title_label_header)
        self.main_layout.addWidget(self.video_title_label)

        self.main_layout.addSpacing(15)

        options_layout = QHBoxLayout()
        format_group_layout = QVBoxLayout()
        format_group_layout.addWidget(self.format_label)
        format_group_layout.addWidget(self.format_combobox)
        options_layout.addLayout(format_group_layout)

        quality_group_layout = QVBoxLayout()
        quality_group_layout.addWidget(self.quality_label)
        quality_group_layout.addWidget(self.quality_combobox)
        options_layout.addLayout(quality_group_layout)
        self.main_layout.addLayout(options_layout)

        self.main_layout.addSpacing(15)

        path_selection_layout = QHBoxLayout()
        path_selection_layout.addWidget(self.path_label)
        path_selection_layout.addWidget(self.path_input, 1) # Stretch path input
        path_selection_layout.addWidget(self.browse_button)
        self.main_layout.addLayout(path_selection_layout)

        self.main_layout.addStretch(1) # Pushes progress and download to bottom

        self.main_layout.addWidget(self.progress_bar)
        self.main_layout.addWidget(self.download_button)


    def _connect_signals(self):
        self.fetch_button.clicked.connect(self.on_fetch_info_clicked)
        self.browse_button.clicked.connect(self.on_browse_clicked)
        self.format_combobox.currentIndexChanged.connect(self.on_format_changed)
        self.download_button.clicked.connect(self.on_download_clicked)
        self.url_input.returnPressed.connect(self.fetch_button.click) # Convenience

    def _set_ui_busy_state(self, busy):
        """Enable/Disable UI elements when busy."""
        self.url_input.setEnabled(not busy)
        self.fetch_button.setEnabled(not busy)
        self.format_combobox.setEnabled(not busy)
        # Quality combobox state depends on other factors, handle separately or refresh
        self.browse_button.setEnabled(not busy)
        self.download_button.setEnabled(not busy and self._can_download()) # Re-check if download possible

    def _can_download(self):
        title_ok = self.video_title_label.text() not in ["N/A", "Fetching...", "Error fetching info."]
        path_ok = bool(self.path_input.text())
        quality_data = self.quality_combobox.currentData()
        quality_ok = (self.quality_combobox.isEnabled() and
                      self.quality_combobox.count() > 0 and
                      quality_data is not None and
                      "---" not in self.quality_combobox.currentText())
        return title_ok and path_ok and quality_ok

    def on_fetch_info_clicked(self):
        url = self.url_input.text().strip()
        if not url:
            QMessageBox.warning(self, "Input Error", "Please enter a YouTube URL or Video ID.")
            return

        self._set_ui_busy_state(True)
        self.statusBar().showMessage(f"Fetching info for: {url}...")
        self.video_title_label.setText("Fetching...")
        self.quality_combobox.clear()
        self.quality_combobox.addItem("--- Fetching ---")
        self.quality_combobox.setEnabled(False)
        self.current_pytube_object = None # Clear previous
        self.last_fetched_video_info = None

        self.info_fetch_thread = InfoFetcherThread(url)
        self.info_fetch_thread.info_ready.connect(self.on_info_ready)
        self.info_fetch_thread.error_occurred.connect(self.on_fetch_error)
        self.info_fetch_thread.finished.connect(self.on_fetch_worker_finished)
        self.info_fetch_thread.start()

    def on_info_ready(self, video_data):
        self.last_fetched_video_info = video_data # Store the raw info
        self.current_pytube_object = video_data.get("pytube_object")

        title = video_data.get("title", "N/A")
        self.video_title_label.setText(title)
        self.statusBar().showMessage(f"Video info loaded: {title[:50]}...")

        # Important: Call on_format_changed to populate quality based on new info
        self.on_format_changed(self.format_combobox.currentIndex())
        # self._check_enable_download_button() # on_format_changed will call this

    def on_fetch_error(self, error_message):
        self.statusBar().showMessage(f"Error: {error_message}")
        QMessageBox.critical(self, "Fetch Error", error_message)
        self.video_title_label.setText("Error fetching info.")
        self.quality_combobox.clear()
        self.quality_combobox.addItem("--- Error ---")
        self.quality_combobox.setEnabled(False)
        self.current_pytube_object = None
        self.last_fetched_video_info = None

    def on_fetch_worker_finished(self):
        self._set_ui_busy_state(False) # Re-enable UI
        self.info_fetch_thread = None
        self._check_enable_download_button()


    def on_browse_clicked(self):
        current_path = self.path_input.text() or os.path.expanduser("~")
        directory = QFileDialog.getExistingDirectory(
            self, "Select Download Directory", current_path
        )
        if directory:
            self.path_input.setText(directory)
            self.statusBar().showMessage(f"Download path: {directory}")
            self._check_enable_download_button()

    def on_format_changed(self, index):
        selected_format_text = self.format_combobox.currentText()
        self.quality_combobox.clear()
        self.quality_combobox.setEnabled(False) # Disable by default

        if not self.current_pytube_object or not self.last_fetched_video_info:
            self.quality_combobox.addItem("--- Fetch video first ---")
            self._check_enable_download_button()
            return

        if "MP3" in selected_format_text:
            self.quality_label.setText("Audio Quality:")
            audio_options = self.last_fetched_video_info['streams']['audio_only']
            if audio_options:
                self.quality_combobox.setEnabled(True)
                for audio_opt in audio_options: # {'desc': 'opus (160kbps)', 'itag': 251}
                    self.quality_combobox.addItem(audio_opt['desc'], audio_opt['itag'])
                if not self.quality_combobox.count(): # Should not happen if audio_options is not empty
                     self.quality_combobox.addItem("--- No audio found ---")
                     self.quality_combobox.setEnabled(False)
            else: # No specific audio options, offer a generic "best"
                # Fallback: get best audio directly if info structure was bad
                best_audio = self.current_pytube_object.streams.get_audio_only()
                if best_audio:
                    self.quality_combobox.setEnabled(True)
                    self.quality_combobox.addItem(f"Best Available ({best_audio.abr}, {best_audio.mime_type.split('/')[-1]})", best_audio.itag)
                else:
                    self.quality_combobox.addItem("--- No audio found ---")
        else: # MP4
            self.quality_label.setText("Video Quality (MP4):")
            # Use pytube_object directly to get streams for MP4
            added_resolutions_tags = {} # To store res_text -> itag to avoid near duplicates

            # Progressive MP4 streams (Video+Audio)
            for stream in self.current_pytube_object.streams.filter(progressive=True, file_extension='mp4').order_by('resolution').desc():
                if stream.resolution:
                    res_text = f"{stream.resolution} (Video+Audio)"
                    if res_text not in added_resolutions_tags:
                        added_resolutions_tags[res_text] = stream.itag

            # Adaptive MP4 video-only streams
            for stream in self.current_pytube_object.streams.filter(adaptive=True, only_video=True, file_extension='mp4').order_by('resolution').desc():
                if stream.resolution:
                    res_text_base = stream.resolution
                    full_res_text = res_text_base
                    if hasattr(stream, 'is_hdr') and stream.is_hdr: full_res_text += " HDR"
                    if hasattr(stream, 'fps') and stream.fps > 30: full_res_text += f" ({stream.fps}fps)"

                    # Add suffix to distinguish from progressive if same base resolution
                    display_text = f"{full_res_text} (Video-Only)"

                    # Avoid adding if a progressive stream of the same base resolution already exists,
                    # unless this adaptive stream is significantly better (e.g. higher FPS, HDR).
                    # This simple logic just adds it if the exact display_text isn't there yet.
                    if display_text not in added_resolutions_tags:
                         added_resolutions_tags[display_text] = stream.itag

            if added_resolutions_tags:
                self.quality_combobox.setEnabled(True)
                for text, itag in added_resolutions_tags.items():
                    self.quality_combobox.addItem(text, itag)
            else:
                self.quality_combobox.addItem("--- No MP4 streams found ---")

        if not self.quality_combobox.count(): # Final fallback
            self.quality_combobox.addItem("--- N/A ---")
            self.quality_combobox.setEnabled(False)

        self._check_enable_download_button()


    def on_download_clicked(self):
        if not self.current_pytube_object:
            QMessageBox.warning(self, "Error", "No video information loaded. Fetch video info first.")
            return
        if not self.path_input.text():
            QMessageBox.warning(self, "Error", "Please select a download directory.")
            return

        selected_quality_itag = self.quality_combobox.currentData()
        if selected_quality_itag is None or "---" in self.quality_combobox.currentText():
            QMessageBox.warning(self, "Error", "Please select a valid quality option.")
            return

        output_format = "MP3" if "MP3" in self.format_combobox.currentText() else "MP4"

        # If itag is 0 (our placeholder for "Best Available Audio" before population), resolve it now
        if output_format == "MP3" and selected_quality_itag == 0: # Should not happen if populated correctly
            best_audio_stream = self.current_pytube_object.streams.get_audio_only()
            if not best_audio_stream:
                QMessageBox.critical(self, "Error", "No audio stream available for MP3 conversion.")
                return
            selected_quality_itag = best_audio_stream.itag

        base_filename = sanitize_filename(self.video_title_label.text())
        if not base_filename: # Should be handled by sanitize_filename, but as a safeguard
            base_filename = "downloaded_video"

        self._set_ui_busy_state(True)
        self.progress_bar.setValue(0)

        self.download_worker_thread = DownloadWorkerThread(
            self.current_pytube_object,
            selected_quality_itag,
            self.path_input.text(),
            output_format,
            base_filename
        )
        self.download_worker_thread.progress_updated.connect(self.on_download_progress)
        self.download_worker_thread.status_updated.connect(self.on_download_status)
        self.download_worker_thread.download_finished.connect(self.on_download_complete)
        self.download_worker_thread.error_occurred.connect(self.on_download_error)
        self.download_worker_thread.finished.connect(self.on_download_worker_finished)
        self.download_worker_thread.start()

    def on_download_progress(self, percentage):
        self.progress_bar.setValue(percentage)

    def on_download_status(self, message):
        self.statusBar().showMessage(message)

    def on_download_complete(self, filepath, original_title_base):
        self.statusBar().showMessage(f"Success: '{original_title_base}' saved to '{filepath}'")
        QMessageBox.information(self, "Download Complete",
                                f"'{original_title_base}' downloaded successfully!\n\nLocation: {filepath}")
        self.progress_bar.setValue(100)

    def on_download_error(self, error_message):
        self.statusBar().showMessage(f"Failed: {error_message}")
        QMessageBox.critical(self, "Download Error", error_message)
        self.progress_bar.setValue(0) # Reset progress

    def on_download_worker_finished(self):
        self._set_ui_busy_state(False)
        # Re-evaluate quality combobox based on current video info
        if self.current_pytube_object and self.last_fetched_video_info:
            self.on_format_changed(self.format_combobox.currentIndex())
        else: # No video info, reset quality box
            self.quality_combobox.clear()
            self.quality_combobox.addItem("--- Fetch video first ---")
            self.quality_combobox.setEnabled(False)

        self.download_worker_thread = None
        self._check_enable_download_button()


    def _check_enable_download_button(self):
        self.download_button.setEnabled(self._can_download())


    def closeEvent(self, event):
        # Attempt to stop threads gracefully
        if self.info_fetch_thread and self.info_fetch_thread.isRunning():
            self.info_fetch_thread.stop()
            self.info_fetch_thread.wait(500)
        if self.download_worker_thread and self.download_worker_thread.isRunning():
            self.download_worker_thread.stop()
            self.download_worker_thread.wait(1000)
        super().closeEvent(event)

if __name__ == '__main__':
    import sys
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
