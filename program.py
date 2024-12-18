import re
import sys
import os
import json
from PIL import Image, ImageTk
import tkinter as tk
from tkinter import messagebox

#############################################
# Configuration
#############################################
SOURCE_FILE = "source.txt"
SCENARIO_FILE = "scenarios-ps6.txt"
FIGURE_DIR = "images-ps6/figures"
TABLE_DIR = "images-ps6/tables"
SESSION_FILE = "session.json"
LEFT_AD_IMAGE = "left_ad.png"
RIGHT_AD_IMAGE = "right_ad.png"

#############################################
# Parse Scenarios
#############################################
scenario_dict = {}

if os.path.exists(SCENARIO_FILE):
    with open(SCENARIO_FILE, "r", encoding="utf-8") as sf:
        lines = [line.rstrip('\n') for line in sf]
        current_scenario_key = None
        current_scenario_text = []

        for line in lines:
            scenario_match = re.match(r"\*\*\*Scenario\s+(\d+-\d+)\*\*\*", line, re.IGNORECASE)
            if scenario_match:
                if current_scenario_key:
                    scenario_dict[current_scenario_key] = "\n".join(current_scenario_text).strip()
                current_scenario_key = scenario_match.group(1)
                current_scenario_text = []
            else:
                if current_scenario_key:
                    current_scenario_text.append(line)

        # Store the last scenario if any
        if current_scenario_key:
            scenario_dict[current_scenario_key] = "\n".join(current_scenario_text).strip()
else:
    print(f"Warning: Scenario file '{SCENARIO_FILE}' not found. Scenario questions won't have scenario text.")
    scenario_dict = {}

#############################################
# Parse Questions
#############################################
all_text = ""
try:
    with open(SOURCE_FILE, "r", encoding="utf-8") as f:
        all_text = f.read()
except FileNotFoundError:
    print(f"Error: File {SOURCE_FILE} not found.")
    sys.exit(1)

lines = [line.strip() for line in all_text.split('\n') if line.strip()]

questions = []
current_question = None
current_choices = {}

for line in lines:
    ans_match = re.search(r"ANS:\s*([A-Da-d])", line)
    if ans_match:
        correct_answer = ans_match.group(1).lower()
        if current_question and current_choices:
            questions.append({
                "question": current_question,
                "choices": current_choices,
                "answer": correct_answer
            })
        current_question = None
        current_choices = {}
        continue

    choice_match = re.match(r"([a-d])\.\s*(.*)", line, re.IGNORECASE)
    if choice_match:
        choice_letter = choice_match.group(1).lower()
        choice_text = choice_match.group(2).strip()
        current_choices[choice_letter] = choice_text
    else:
        if current_question:
            current_question += " " + line
        else:
            current_question = line

#############################################
# Determine question type (figure/table/scenario/normal)
#############################################
def identify_question_type(question_text):
    fig_match = re.search(r"Refer to Figure\s+(\d+-\d+)\.", question_text, re.IGNORECASE)
    if fig_match:
        return ("figure", fig_match.group(1))
    table_match = re.search(r"Refer to Table\s+(\d+-\d+)\.", question_text, re.IGNORECASE)
    if table_match:
        return ("table", table_match.group(1))
    scenario_match = re.search(r"Refer to Scenario\s+(\d+-\d+)\.", question_text, re.IGNORECASE)
    if scenario_match:
        return ("scenario", scenario_match.group(1))

    return ("normal", None)

#############################################
# Session Handling
#############################################
def load_session():
    if os.path.exists(SESSION_FILE):
        with open(SESSION_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data.get("current_index", 0)
    return 0

def save_session(index):
    with open(SESSION_FILE, "w", encoding="utf-8") as f:
        json.dump({"current_index": index}, f)

#############################################
# Helper to load and tile ad images
#############################################
def load_ad_image(path):
    if os.path.exists(path):
        img = Image.open(path)
        img = img.resize((200, 400), Image.Resampling.LANCZOS)
        return img
    return None

def tile_image_vertically(base_img, height):
    if not base_img:
        return None
    w, h = base_img.size
    times = (height // h) + 1
    new_img = Image.new('RGB', (w, max(h, height)), color=(255, 255, 255))
    y_offset = 0
    for _ in range(times):
        new_img.paste(base_img, (0, y_offset))
        y_offset += h
        if y_offset >= height:
            break
    if new_img.size[1] > height:
        new_img = new_img.crop((0, 0, w, height))
    return ImageTk.PhotoImage(new_img)

#############################################
# GUI Quiz Application
#############################################
class QuizApp:
    def __init__(self, master, questions, scenarios, figure_dir, table_dir, start_index=0):
        self.master = master
        self.questions = questions
        self.scenarios = scenarios
        self.figure_dir = figure_dir
        self.table_dir = table_dir
        self.index = start_index if 0 <= start_index < len(self.questions) else 0
        self.score = 0
        self.num_questions = len(self.questions)

        self.master.attributes('-fullscreen', True)

        self.main_frame = tk.Frame(master)
        self.main_frame.pack(fill=tk.BOTH, expand=True)

        self.left_ad_frame = tk.Frame(self.main_frame, width=200)
        self.left_ad_frame.pack(side=tk.LEFT, fill=tk.BOTH)

        self.center_frame = tk.Frame(self.main_frame)
        self.center_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.right_ad_frame = tk.Frame(self.main_frame, width=200)
        self.right_ad_frame.pack(side=tk.LEFT, fill=tk.BOTH)

        self.left_ad_img = load_ad_image(LEFT_AD_IMAGE)
        self.right_ad_img = load_ad_image(RIGHT_AD_IMAGE)

        self.left_ad_label = tk.Label(self.left_ad_frame, bg="white")
        self.left_ad_label.pack(fill=tk.BOTH, expand=True)

        self.right_ad_label = tk.Label(self.right_ad_frame, bg="white")
        self.right_ad_label.pack(fill=tk.BOTH, expand=True)

        self.left_ad_frame.bind("<Configure>", self.update_left_ad)
        self.right_ad_frame.bind("<Configure>", self.update_right_ad)

        question_font = ("Arial", 24, "bold")
        scenario_font = ("Arial", 20)
        choice_font = ("Arial", 20)
        button_font = ("Arial", 20, "bold")

        self.content_frame = tk.Frame(self.center_frame)
        self.content_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        self.image_label = tk.Label(self.content_frame)
        self.image_label.pack(pady=10)

        self.scenario_label = tk.Label(self.content_frame, text="", font=scenario_font, justify=tk.LEFT, wraplength=700)
        self.scenario_label.pack(pady=5)

        self.question_label = tk.Label(self.content_frame, text="", font=question_font, wraplength=700, justify=tk.LEFT)
        self.question_label.pack(pady=10)

        self.var = tk.StringVar(value='')

        self.choice_frame = tk.Frame(self.content_frame)
        self.choice_frame.pack(pady=10)

        self.choice_buttons = []
        for i in range(4):
            rb = tk.Radiobutton(self.choice_frame, text="", variable=self.var, value="", font=choice_font, wraplength=700, justify=tk.LEFT, anchor='w')
            rb.pack(anchor='w', pady=5)
            self.choice_buttons.append(rb)

        self.button_frame = tk.Frame(self.content_frame)
        self.button_frame.pack(pady=10)

        # For next and previous use arrows, submit in the middle
        self.prev_button = tk.Button(self.button_frame, text="←", command=self.prev_question, font=button_font, bg="lightblue", fg="black")
        self.prev_button.grid(row=0, column=0, padx=10)

        self.submit_button = tk.Button(self.button_frame, text="Submit", command=self.check_answer, font=button_font, bg="lightblue", fg="black")
        self.submit_button.grid(row=0, column=1, padx=10)

        self.next_button = tk.Button(self.button_frame, text="→", command=self.next_question, font=button_font, bg="lightblue", fg="black")
        self.next_button.grid(row=0, column=2, padx=10)

        self.result_label = tk.Label(self.content_frame, text="", font=("Arial", 20))
        self.result_label.pack(pady=10)

        self.question_rank_label = tk.Label(self.content_frame, text="", font=("Arial", 18))
        self.question_rank_label.pack(pady=5)

        # Scoreboard frame to show dynamic subset of questions
        self.scoreboard_frame = tk.Frame(self.center_frame)
        self.scoreboard_frame.pack(side=tk.BOTTOM, pady=10)

        # Create labels for each question (status)
        self.question_status = []
        for i in range(self.num_questions):
            # Initially all gray
            lbl = tk.Label(self.scoreboard_frame, text=str(i+1), width=4, height=2, bg="gray", font=("Arial", 14, "bold"))
            # We'll pack dynamically later, not now
            self.question_status.append(lbl)

        self.load_question(self.index)
        self.master.bind("<Escape>", self.exit_fullscreen)

    def exit_fullscreen(self, event=None):
        self.master.attributes('-fullscreen', False)

    def update_left_ad(self, event):
        if self.left_ad_img:
            tiled = tile_image_vertically(self.left_ad_img, event.height)
            if tiled:
                self.left_ad_label.config(image=tiled)
                self.left_ad_label.image = tiled
            else:
                self.left_ad_label.config(text="Ads Here")
        else:
            self.left_ad_label.config(text="Ads Here")

    def update_right_ad(self, event):
        if self.right_ad_img:
            tiled = tile_image_vertically(self.right_ad_img, event.height)
            if tiled:
                self.right_ad_label.config(image=tiled)
                self.right_ad_label.image = tiled
            else:
                self.right_ad_label.config(text="Ads Here")
        else:
            self.right_ad_label.config(text="Ads Here")

    def load_image(self, path):
        if os.path.exists(path):
            img = Image.open(path)
            img = img.resize((300, 300), Image.Resampling.LANCZOS)
            self.photo = ImageTk.PhotoImage(img)
            self.image_label.config(image=self.photo, text="")
            self.image_label.image = self.photo
        else:
            self.image_label.config(image="", text="(Image not found)")

    def load_question(self, idx):
        if idx < 0:
            self.index = 0
        if idx >= len(self.questions):
            self.show_score()
            return

        self.var.set('')
        q = self.questions[idx]
        q_type, q_ref = identify_question_type(q["question"])

        self.image_label.config(image="", text="")
        self.result_label.config(text="", fg="black")
        self.scenario_label.config(text="")
        self.question_label.config(text="")

        if q_type == "figure":
            figure_path = os.path.join(self.figure_dir, f"figure{q_ref}.png")
            self.load_image(figure_path)
        elif q_type == "table":
            table_path = os.path.join(self.table_dir, f"table{q_ref}.png")
            self.load_image(table_path)
        elif q_type == "scenario":
            scenario_text = self.scenarios.get(q_ref, "(Scenario not found)")
            self.scenario_label.config(text=scenario_text)

        self.question_label.config(text=q["question"])

        keys = list(q["choices"].keys())
        for i, rb in enumerate(self.choice_buttons):
            if i < len(keys):
                rb.config(text=f"{keys[i]}) {q['choices'][keys[i]]}", value=keys[i], state="normal")
                rb.deselect()
            else:
                rb.config(text="", value="", state="disabled")
                rb.deselect()

        self.question_rank_label.config(text=f"Question {self.index+1} of {self.num_questions}")

        # Make next button always enabled
        self.submit_button.config(state="normal")
        self.next_button.config(state="normal")

        # Previous button disabled if at first question
        if self.index == 0:
            self.prev_button.config(state="disabled")
        else:
            self.prev_button.config(state="normal")

        # Update scoreboard to show only q +/- 5
        self.update_scoreboard()

    def update_scoreboard(self):
        # Clear all current packing
        for lbl in self.question_status:
            lbl.pack_forget()

        start = max(0, self.index - 5)
        end = min(self.num_questions, self.index + 5 + 1)  # +1 because range end is exclusive
        for i in range(start, end):
            self.question_status[i].pack(side=tk.LEFT, padx=5)

    def check_answer(self):
        if self.index < len(self.questions):
            q = self.questions[self.index]
            selected = self.var.get()
            if selected == q["answer"]:
                self.result_label.config(text="Correct!", fg="green")
                self.score += 1
                self.question_status[self.index].config(bg="green")
            else:
                correct_choice = q["choices"][q["answer"]]
                self.result_label.config(text=f"Incorrect! Correct answer: {q['answer']}) {correct_choice}", fg="red")
                self.question_status[self.index].config(bg="red")

            self.submit_button.config(state="disabled")
            # Next button should remain enabled now
            self.next_button.config(state="normal")

    def next_question(self):
        if self.index < self.num_questions - 1:
            self.index += 1
            self.save_current_index()
            self.load_question(self.index)
        else:
            self.show_score()

    def prev_question(self):
        if self.index > 0:
            self.index -= 1
            self.save_current_index()
            self.load_question(self.index)

    def show_score(self):
        messagebox.showinfo("Quiz Complete", f"You answered {self.score} out of {len(self.questions)} questions correctly.")
        self.save_current_index()
        self.master.destroy()

    def save_current_index(self):
        save_session(self.index)


if __name__ == "__main__":
    start_index = load_session()
    root = tk.Tk()
    app = QuizApp(root, questions, scenario_dict, FIGURE_DIR, TABLE_DIR, start_index=start_index)
    root.mainloop()
