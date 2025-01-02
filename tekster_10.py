import tkinter as tk
from tkinter.ttk import Progressbar, Style, Combobox
from tkinter import filedialog, messagebox
from transformers import MarianMTModel, MarianTokenizer
import whisper
import threading
import re
from datetime import timedelta
import multiprocessing

class SubtitleApp:
    def __init__(self, master):
        self.master = master
        self.master.title("Subtitle Processing")
        self.master.geometry("800x600")

        self.style = Style()
        self.style.theme_use("default")
        self.style.configure("green.Horizontal.TProgressbar", thickness=20)

        self.translating = False
        self.available_languages = {
            "English": "en",
            "Danish": "da",
            "German": "de",
            "French": "fr",
            "Spanish": "es",
            "Italian": "it",
            "Dutch": "nl",
            "Polish": "pl",
            "Finnish": "fi",
            "Swedish": "sv",
            "Norwegian": "no",
            "Portuguese": "pt",
            "Russian": "ru",
            "Chinese": "zh",
            "Japanese": "ja",
            "Korean": "ko",
            "Arabic": "ar",
            "Turkish": "tr",
            "Greek": "el",
            "Czech": "cs",
            "Hungarian": "hu",
            "Bulgarian": "bg",
            "Hindi": "hi",
            "Thai": "th",
            "Vietnamese": "vi",
            "Indonesian": "id",
            "Malay": "ms"
        }

        self.source_language_var = tk.StringVar(value="English")
        self.target_language_var = tk.StringVar(value="Danish")

        self.setup_gui()

    def setup_gui(self):
        main_frame = tk.Frame(self.master)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)

        left_frame = tk.Frame(main_frame)
        left_frame.pack(side="left", fill="y", padx=10, pady=10)

        tk.Button(left_frame, text="Audio to Text", command=self.threaded(self.audio_to_text), width=25, height=2).pack(pady=5)
        tk.Button(left_frame, text="Translate", command=self.threaded(self.translate), width=25, height=2).pack(pady=5)
        tk.Button(left_frame, text="Remove Hearing Impaired Text", command=self.threaded(self.remove_hearing_impaired_and_validate), width=25, height=2).pack(pady=5)
        tk.Button(left_frame, text="Validate and Correct", command=self.threaded(self.validate_and_correct), width=25, height=2).pack(pady=5)

        right_frame = tk.Frame(main_frame)
        right_frame.pack(side="right", fill="y", padx=10, pady=10)

        tk.Label(right_frame, text="Source Language").pack(pady=5)
        Combobox(right_frame, textvariable=self.source_language_var, values=list(self.available_languages.keys()), state="readonly", width=20).pack(pady=5)

        tk.Label(right_frame, text="Target Language").pack(pady=5)
        Combobox(right_frame, textvariable=self.target_language_var, values=list(self.available_languages.keys()), state="readonly", width=20).pack(pady=5)

        self.status_label = tk.Label(self.master, text="Status: Ready", anchor="w")
        self.status_label.pack(fill="x", padx=10, pady=10)

        self.progressbar = Progressbar(self.master, orient="horizontal", style="green.Horizontal.TProgressbar", mode="determinate")
        self.progressbar.pack(fill="x", padx=10, pady=10)

    def threaded(self, func):
        def wrapper():
            threading.Thread(target=func).start()
        return wrapper

    def update_status(self, message):
        self.master.after(0, lambda: self.status_label.config(text=message))

    def update_progress(self, current, total, message=""):
        if total == 0:
            self.master.after(0, lambda: self.progressbar.config(mode="indeterminate"))
            self.progressbar.start(10)
            self.master.after(0, lambda: self.status_label.config(text=message))
        else:
            self.progressbar.stop()
            self.master.after(0, lambda: self.progressbar.config(mode="determinate"))
            progress = int((current / total) * 100)
            self.master.after(0, lambda: self.progressbar.config(value=progress))
            self.master.after(0, lambda: self.status_label.config(text=f"{message} {progress}% færdig"))

    def audio_to_text(self):
        input_file = filedialog.askopenfilename(filetypes=[("Audio Files", "*.wav;*.mp3;*.mkv")])
        if not input_file:
            self.update_status("No file selected for Audio to Text")
            return

        output_file = filedialog.asksaveasfilename(defaultextension=".srt", filetypes=[("SRT Files", "*.srt")])
        if not output_file:
            self.update_status("No location selected to save Audio to Text output")
            return

        try:
            self.update_progress(0, 0, "Processing audio file...")
            model = whisper.load_model("medium")
            result = model.transcribe(input_file, language="en")

            total_segments = len(result['segments'])
            with open(output_file, "w", encoding="utf-8") as f:
                for i, segment in enumerate(result['segments'], start=1):
                    start = str(timedelta(seconds=segment['start'])).zfill(8)
                    end = str(timedelta(seconds=segment['end'])).zfill(8)
                    f.write(f"{i}\n{start},000 --> {end},000\n{segment['text']}\n\n")
                    self.update_progress(i, total_segments, "Processing audio file...")

            self.update_status(f"Audio to Text completed! Saved as: {output_file}")

        except Exception as e:
            self.update_status(f"Error during Audio to Text: {e}")
            self.progressbar.stop()

    def remove_hearing_impaired_and_validate(self):
        input_file = filedialog.askopenfilename(filetypes=[("SRT Files", "*.srt")])
        if not input_file:
            self.update_status("No file selected.")
            return

        output_file = filedialog.asksaveasfilename(defaultextension=".srt", filetypes=[("SRT Files", "*.srt")])
        if not output_file:
            self.update_status("No output file specified.")
            return

        try:
            with open(input_file, "r", encoding="utf-8") as infile:
                content = infile.read()

            # Regex til at fjerne hørehæmmet tekst
            content = re.sub(r"\(.*?\)|\[.*?\]|^[A-ZÆØÅ ]+ ?: ?", "", content, flags=re.MULTILINE)

            # Split blokke og rekonstruer
            blocks = content.strip().split("\n\n")
            cleaned_blocks = []
            block_number = 1

            for block in blocks:
                lines = block.strip().split("\n")
                if len(lines) < 2 or "-->" not in lines[1]:
                    continue  # Spring over blokke uden tidsstempler
                text_lines = [line.strip() for line in lines[2:] if line.strip()]
                if text_lines:
                    cleaned_block = [str(block_number), lines[1]] + text_lines
                    cleaned_blocks.append("\n".join(cleaned_block))
                    block_number += 1

            # Validering af kontinuerlige bloknumre
            validated_blocks = []
            for idx, block in enumerate(cleaned_blocks, start=1):
                lines = block.split("\n")
                lines[0] = str(idx)  # Sørg for kontinuerlig nummerering
                validated_blocks.append("\n".join(lines))

            # Skriv resultatet til fil
            final_content = "\n\n".join(validated_blocks)
            with open(output_file, "w", encoding="utf-8") as outfile:
                outfile.write(final_content)

            self.update_status(f"Processed and validated file saved to: {output_file}")

        except Exception as e:
            self.update_status(f"Error: {e}")

    def validate_and_correct(self):
        input_file = filedialog.askopenfilename(filetypes=[("SRT Files", "*.srt")])
        if not input_file:
            self.update_status("No file selected for Validation")
            return

        output_file = filedialog.asksaveasfilename(defaultextension=".srt", filetypes=[("SRT Files", "*.srt")])
        if not output_file:
            self.update_status("No location selected to save output")
            return

        try:
            with open(input_file, "r", encoding="utf-8") as infile:
                lines = infile.readlines()

            self.update_progress(0, len(lines), "Validating and correcting...")

            def is_valid_block(block):
                return len(block) >= 3 and "-->" in block[1] and any(block[2:])

            def separate_lines(block):
                separated = []
                for line in block:
                    if re.search(r'(?<!\.)\.(?=\S)', line):
                        parts = re.split(r'(?<!\.)\.(?=\S)', line)
                        separated.extend([part.strip() for part in parts if part.strip()])
                    else:
                        separated.append(line.strip())
                return separated

            corrected_lines = []
            current_block = []
            block_number = 1

            for line in lines:
                line = line.strip()
                if re.match(r"^\d+$", line):
                    if current_block and is_valid_block(current_block):
                        corrected_lines.append(f"{block_number}\n")
                        corrected_lines.append(current_block[1] + "\n")
                        corrected_lines.extend(separate_lines(current_block[2:]))
                        corrected_lines.append("\n")
                        block_number += 1
                    current_block = [line]
                else:
                    current_block.append(line)

            if current_block and is_valid_block(current_block):
                corrected_lines.append(f"{block_number}\n")
                corrected_lines.append(current_block[1] + "\n")
                corrected_lines.extend(separate_lines(current_block[2:]))
                corrected_lines.append("\n")

            with open(output_file, "w", encoding="utf-8") as outfile:
                outfile.writelines([line + "\n" for line in corrected_lines])

            self.update_status(f"Validation and correction completed! Saved as: {output_file}")

        except Exception as e:
            self.update_status(f"Error during validation: {e}")
            self.progressbar.stop()

    def translate(self):
        if self.translating:
            self.update_status("Translation already in progress.")
            return

        self.translating = True
        try:
            input_file = filedialog.askopenfilename(parent=self.master, filetypes=[("SRT Files", "*.srt")])
            if not input_file:
                self.update_status("No file selected for translation")
                self.translating = False
                return

            output_file = filedialog.asksaveasfilename(parent=self.master, defaultextension=".srt", filetypes=[("SRT Files", "*.srt")])
            if not output_file:
                self.update_status("No location selected to save translation output")
                self.translating = False
                return

            source_language = self.available_languages[self.source_language_var.get()]
            target_language = self.available_languages[self.target_language_var.get()]
            model_name = f"Helsinki-NLP/opus-mt-{source_language}-{target_language}"

            self.update_status("Loading model and translating...")
            model = MarianMTModel.from_pretrained(model_name)
            tokenizer = MarianTokenizer.from_pretrained(model_name)

            with open(input_file, "r", encoding="utf-8") as infile:
                lines = infile.readlines()

            text_lines = [line.strip() for line in lines if line.strip() and "-->" not in line and not line.strip().isdigit()]
            total_lines = len(text_lines)

            translated_lines = []
            for idx, line in enumerate(text_lines, start=1):
                inputs = tokenizer([line], return_tensors="pt", padding=True, truncation=True)
                outputs = model.generate(**inputs)
                translated = tokenizer.decode(outputs[0], skip_special_tokens=True)
                translated_lines.append(translated)
                self.update_progress(idx, total_lines, "Translating text...")

            with open(output_file, "w", encoding="utf-8") as outfile:
                idx = 0
                for line in lines:
                    if line.strip() and "-->" not in line and not line.strip().isdigit():
                        outfile.write(translated_lines[idx] + "\n")
                        idx += 1
                    else:
                        outfile.write(line)

            self.update_status(f"Translation completed! Saved as: {output_file}")

        except Exception as e:
            self.update_status(f"Error during Translate: {e}")

        finally:
            self.translating = False

if __name__ == "__main__":
    import sys
    if getattr(sys, 'frozen', False):  # Handle frozen executable
        multiprocessing.freeze_support()
    root = tk.Tk()
    app = SubtitleApp(root)
    root.mainloop()