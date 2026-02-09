import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import threading
import os

from gtts import gTTS
try:
    from PyPDF2 import PdfReader
    USE_NEW_API = True
except ImportError:
    import PyPDF2
    USE_NEW_API = False

# For audio playback
try:
    import pygame
    pygame.mixer.init()
    HAS_PYGAME = True
except ImportError:
    HAS_PYGAME = False


class AudioBookApp:
    def __init__(self, root):
        self.root = root
        self.root.title("PDF to Audio Book Converter")
        self.root.geometry("500x350")
        self.root.resizable(False, False)
        
        self.pdf_path = None
        self.audio_path = None
        self.is_playing = False
        
        self.setup_ui()
    
    def setup_ui(self):
        # Main frame
        main_frame = ttk.Frame(self.root, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Title
        title_label = ttk.Label(main_frame, text="PDF to Audio Book", font=("Helvetica", 16, "bold"))
        title_label.pack(pady=(0, 20))
        
        # File selection frame
        file_frame = ttk.LabelFrame(main_frame, text="PDF File", padding="10")
        file_frame.pack(fill=tk.X, pady=(0, 15))
        
        self.file_label = ttk.Label(file_frame, text="No file selected", width=50)
        self.file_label.pack(side=tk.LEFT, padx=(0, 10))
        
        browse_btn = ttk.Button(file_frame, text="Browse", command=self.browse_file)
        browse_btn.pack(side=tk.RIGHT)
        
        # Convert button
        self.convert_btn = ttk.Button(main_frame, text="Convert to Audio", command=self.convert_to_audio, state=tk.DISABLED)
        self.convert_btn.pack(pady=10)
        
        # Progress bar
        self.progress = ttk.Progressbar(main_frame, mode='indeterminate', length=300)
        self.progress.pack(pady=10)
        
        # Status label
        self.status_label = ttk.Label(main_frame, text="", foreground="gray")
        self.status_label.pack(pady=5)
        
        # Audio controls frame
        self.audio_frame = ttk.LabelFrame(main_frame, text="Audio Player", padding="10")
        self.audio_frame.pack(fill=tk.X, pady=(15, 0))
        
        btn_frame = ttk.Frame(self.audio_frame)
        btn_frame.pack()
        
        self.play_btn = ttk.Button(btn_frame, text="▶ Play", command=self.play_audio, state=tk.DISABLED, width=10)
        self.play_btn.pack(side=tk.LEFT, padx=5)
        
        self.stop_btn = ttk.Button(btn_frame, text="■ Stop", command=self.stop_audio, state=tk.DISABLED, width=10)
        self.stop_btn.pack(side=tk.LEFT, padx=5)
        
        self.save_btn = ttk.Button(btn_frame, text="💾 Save As", command=self.save_audio, state=tk.DISABLED, width=10)
        self.save_btn.pack(side=tk.LEFT, padx=5)
    
    def browse_file(self):
        file_path = filedialog.askopenfilename(
            title="Select PDF File",
            filetypes=[("PDF Files", "*.pdf"), ("All Files", "*.*")]
        )
        if file_path:
            self.pdf_path = file_path
            filename = os.path.basename(file_path)
            self.file_label.config(text=filename if len(filename) < 45 else filename[:42] + "...")
            self.convert_btn.config(state=tk.NORMAL)
            self.status_label.config(text="Ready to convert", foreground="gray")
            self.disable_audio_controls()
    
    def extract_text_from_pdf(self, pdf_path):
        text_list = []
        
        if USE_NEW_API:
            reader = PdfReader(pdf_path)
            for page in reader.pages:
                text = page.extract_text()
                if text:
                    text_list.append(text)
        else:
            with open(pdf_path, 'rb') as f:
                reader = PyPDF2.PdfFileReader(f)
                for i in range(reader.numPages):
                    text = reader.getPage(i).extractText()
                    if text:
                        text_list.append(text)
        
        return " ".join(text_list)
    
    def convert_to_audio(self):
        self.convert_btn.config(state=tk.DISABLED)
        self.disable_audio_controls()
        self.progress.start(10)
        self.status_label.config(text="Converting... Please wait", foreground="blue")
        
        thread = threading.Thread(target=self._convert_thread)
        thread.daemon = True
        thread.start()
    
    def _convert_thread(self):
        try:
            # Extract text
            text = self.extract_text_from_pdf(self.pdf_path)
            
            if not text.strip():
                self.root.after(0, lambda: self._conversion_error("No text could be extracted from the PDF"))
                return
            
            # Generate audio
            audio = gTTS(text=text, lang='en', slow=False)
            
            # Save to temp file
            base_name = os.path.splitext(os.path.basename(self.pdf_path))[0]
            self.audio_path = os.path.join(os.path.dirname(self.pdf_path), f"{base_name}_audio.mp3")
            audio.save(self.audio_path)
            
            self.root.after(0, self._conversion_complete)
            
        except Exception as e:
            self.root.after(0, lambda: self._conversion_error(str(e)))
    
    def _conversion_complete(self):
        self.progress.stop()
        self.convert_btn.config(state=tk.NORMAL)
        self.status_label.config(text=f"Conversion complete! Saved to: {os.path.basename(self.audio_path)}", foreground="green")
        self.enable_audio_controls()
    
    def _conversion_error(self, error_msg):
        self.progress.stop()
        self.convert_btn.config(state=tk.NORMAL)
        self.status_label.config(text="Conversion failed", foreground="red")
        messagebox.showerror("Error", f"Conversion failed:\n{error_msg}")
    
    def play_audio(self):
        if not self.audio_path or not os.path.exists(self.audio_path):
            messagebox.showerror("Error", "Audio file not found")
            return
        
        if HAS_PYGAME:
            try:
                if self.is_playing:
                    pygame.mixer.music.unpause()
                else:
                    pygame.mixer.music.load(self.audio_path)
                    pygame.mixer.music.play()
                self.is_playing = True
                self.play_btn.config(text="⏸ Pause", command=self.pause_audio)
                self.status_label.config(text="Playing audio...", foreground="blue")
            except Exception as e:
                messagebox.showerror("Error", f"Could not play audio: {e}")
        else:
            # Fallback: open with system default player
            try:
                import subprocess
                import sys
                if sys.platform == 'win32':
                    os.startfile(self.audio_path)
                elif sys.platform == 'darwin':
                    subprocess.run(['open', self.audio_path])
                else:
                    subprocess.run(['xdg-open', self.audio_path])
                self.status_label.config(text="Opened in default player", foreground="blue")
            except Exception as e:
                messagebox.showerror("Error", f"Could not open audio: {e}")
    
    def pause_audio(self):
        if HAS_PYGAME and self.is_playing:
            pygame.mixer.music.pause()
            self.play_btn.config(text="▶ Play", command=self.play_audio)
            self.status_label.config(text="Paused", foreground="gray")
    
    def stop_audio(self):
        if HAS_PYGAME:
            pygame.mixer.music.stop()
            self.is_playing = False
            self.play_btn.config(text="▶ Play", command=self.play_audio)
            self.status_label.config(text="Stopped", foreground="gray")
    
    def save_audio(self):
        if not self.audio_path or not os.path.exists(self.audio_path):
            messagebox.showerror("Error", "Audio file not found")
            return
        
        save_path = filedialog.asksaveasfilename(
            title="Save Audio File",
            defaultextension=".mp3",
            filetypes=[("MP3 Files", "*.mp3")],
            initialfile=os.path.basename(self.audio_path)
        )
        
        if save_path:
            import shutil
            try:
                shutil.copy2(self.audio_path, save_path)
                messagebox.showinfo("Success", f"Audio saved to:\n{save_path}")
            except Exception as e:
                messagebox.showerror("Error", f"Could not save file: {e}")
    
    def enable_audio_controls(self):
        self.play_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.NORMAL)
        self.save_btn.config(state=tk.NORMAL)
    
    def disable_audio_controls(self):
        self.play_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.DISABLED)
        self.save_btn.config(state=tk.DISABLED)
        if HAS_PYGAME:
            pygame.mixer.music.stop()
        self.is_playing = False
        self.play_btn.config(text="▶ Play", command=self.play_audio)


if __name__ == "__main__":
    root = tk.Tk()
    app = AudioBookApp(root)
    root.mainloop()
