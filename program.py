import re
import sys
import os
from PIL import Image, ImageTk
import tkinter as tk
from tkinter import messagebox

# This updated code:
# 1. Reads raw question text from "source.txt".
# 2. Distinguishes between four types of questions:
#    - Normal questions (no "Refer to ..." line)
#    - "Refer to Figure X-Y" questions: display figure image before the question.
#    - "Refer to Table X-Y" questions: display table image before the question.
#    - "Refer to Scenario X-Y" questions: display scenario text from "scenarios-ps6.txt" before the question.
#
# Assumptions:
# - Figures are stored in: /images-ps6/figures/figureX-Y.png
# - Tables are stored in: /images-ps6/tables/tableX-Y.png
# - Scenarios are stored in "scenarios-ps6.txt" in the format:
#   ***Scenario 5-1***
#   [Scenario text... possibly multiple lines]
#
#   Each scenario starts with "***Scenario X-Y***" on its own line.
#   We will parse this file to store scenarios in a dictionary keyed by "X-Y".
#
# Steps:
# 1. Parse scenarios from "scenarios-ps6.txt".
# 2. Parse questions from "source.txt".
# 3. Determine question type by checking if the question text contains:
#    - "Refer to Figure X-Y."
#    - "Refer to Table X-Y."
#    - "Refer to Scenario X-Y."
# 4. For each question, show a Tkinter window with:
#    - If figure/table: the corresponding image
#    - If scenario: the scenario text
#    - Then the question text and multiple-choice answers as radio buttons.
# 5. After selecting an answer, user can submit and get feedback (correct/incorrect).
#
# Note: You may need to adjust image file names and paths as per your actual naming convention.
# Also ensure that images and scenario file exist and are accessible.

#############################################
# Configuration
#############################################
SOURCE_FILE = "source.txt"
SCENARIO_FILE = "scenarios-ps6.txt"
FIGURE_DIR = "images-ps6/figures"
TABLE_DIR = "images-ps6/tables"

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
                # new scenario start
                # store old scenario if exists
                if current_scenario_key:
                    scenario_dict[current_scenario_key] = "\n".join(current_scenario_text).strip()
                current_scenario_key = scenario_match.group(1)
                current_scenario_text = []
            else:
                # part of scenario text
                if current_scenario_key:
                    current_scenario_text.append(line)

        # store the last scenario if any
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
    # Look for answer line anywhere in this line
    ans_match = re.search(r"ANS:\s*([A-Da-d])", line)
    if ans_match:
        # Extract answer
        correct_answer = ans_match.group(1).lower()
        # Now we need to finalize the question here
        if current_question and current_choices:
            questions.append({
                "question": current_question,
                "choices": current_choices,
                "answer": correct_answer
            })
        # Reset for next question
        current_question = None
        current_choices = {}
        continue
    
    # Check if line starts with a choice
    choice_match = re.match(r"([a-d])\.\s*(.*)", line, re.IGNORECASE)
    if choice_match:
        choice_letter = choice_match.group(1).lower()
        choice_text = choice_match.group(2).strip()
        current_choices[choice_letter] = choice_text
    else:
        # Part of the question text
        if current_question:
            current_question += " " + line
        else:
            current_question = line

#############################################
# Determine question type (figure/table/scenario/normal)
#############################################
def identify_question_type(question_text):
    # Check figure
    fig_match = re.search(r"Refer to Figure\s+(\d+-\d+)\.", question_text, re.IGNORECASE)
    if fig_match:
        return ("figure", fig_match.group(1))
    # Check table
    table_match = re.search(r"Refer to Table\s+(\d+-\d+)\.", question_text, re.IGNORECASE)
    if table_match:
        return ("table", table_match.group(1))
    # Check scenario
    scenario_match = re.search(r"Refer to Scenario\s+(\d+-\d+)\.", question_text, re.IGNORECASE)
    if scenario_match:
        return ("scenario", scenario_match.group(1))

    return ("normal", None)


#############################################
# GUI Quiz Application
#############################################
class QuizApp:
    def __init__(self, master, questions, scenarios, figure_dir, table_dir):
        self.master = master
        self.questions = questions
        self.scenarios = scenarios
        self.figure_dir = figure_dir
        self.table_dir = table_dir
        self.index = 0
        self.score = 0

        master.title("Quiz App")

        # Frame for content
        self.frame = tk.Frame(master)
        self.frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        self.image_label = tk.Label(self.frame)
        self.image_label.pack(pady=10)

        self.scenario_label = tk.Label(self.frame, text="", font=("Arial", 12), justify=tk.LEFT, wraplength=500)
        self.scenario_label.pack(pady=5)

        self.question_label = tk.Label(self.frame, text="", font=("Arial", 14), wraplength=500, justify=tk.LEFT)
        self.question_label.pack(pady=10)

        self.var = tk.StringVar()
        self.choice_buttons = []
        for i in range(4):
            rb = tk.Radiobutton(self.frame, text="", variable=self.var, value="", font=("Arial", 12), wraplength=500, justify=tk.LEFT)
            rb.pack(anchor='w')
            self.choice_buttons.append(rb)

        self.submit_button = tk.Button(self.frame, text="Submit", command=self.check_answer)
        self.submit_button.pack(pady=10)

        self.result_label = tk.Label(self.frame, text="", font=("Arial", 12))
        self.result_label.pack(pady=10)

        self.next_button = tk.Button(self.frame, text="Next", command=self.next_question, state="disabled")
        self.next_button.pack(pady=10)

        self.load_question(self.index)

    def load_image(self, path):
        # Load and display image if exists
        if os.path.exists(path):
            img = Image.open(path)
            img = img.resize((300, 300), Image.ANTIALIAS)
            self.photo = ImageTk.PhotoImage(img)
            self.image_label.config(image=self.photo)
        else:
            self.image_label.config(image="", text="(Image not found)")

    def load_question(self, idx):
        if idx >= len(self.questions):
            # No more questions
            self.show_score()
            return

        q = self.questions[idx]
        q_type, q_ref = identify_question_type(q["question"])

        # Clear previous displays
        self.image_label.config(image="", text="")
        self.scenario_label.config(text="")
        self.result_label.config(text="", fg="black")
        self.var.set("")

        # Show scenario or image if needed
        if q_type == "figure":
            # q_ref is something like '5-17'
            figure_path = os.path.join(self.figure_dir, f"figure{q_ref}.png")
            self.load_image(figure_path)
        elif q_type == "table":
            # q_ref like '5-1'
            table_path = os.path.join(self.table_dir, f"table{q_ref}.png")
            self.load_image(table_path)
        elif q_type == "scenario":
            # q_ref like '5-1'
            scenario_text = self.scenarios.get(q_ref, "(Scenario not found)")
            self.scenario_label.config(text=scenario_text)
        # Normal: do nothing special

        # Show question text and choices
        # Remove "Refer to ..." text from the displayed question if desired
        # Or just display as-is:
        self.question_label.config(text=q["question"])

        # Update choices
        keys = list(q["choices"].keys())
        for i, rb in enumerate(self.choice_buttons):
            if i < len(keys):
                rb.config(text=f"{keys[i]}) {q['choices'][keys[i]]}", value=keys[i])
            else:
                rb.config(text="", value="")

        self.submit_button.config(state="normal")
        self.next_button.config(state="disabled")

    def check_answer(self):
        q = self.questions[self.index]
        selected = self.var.get()
        if selected == q["answer"]:
            self.result_label.config(text="Correct!", fg="green")
            self.score += 1
        else:
            correct_choice = q["choices"][q["answer"]]
            self.result_label.config(text=f"Incorrect! Correct answer: {q['answer']}) {correct_choice}", fg="red")

        self.submit_button.config(state="disabled")
        self.next_button.config(state="normal")

    def next_question(self):
        self.index += 1
        self.load_question(self.index)

    def show_score(self):
        messagebox.showinfo("Quiz Complete", f"You answered {self.score} out of {len(self.questions)} questions correctly.")
        self.master.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    app = QuizApp(root, questions, scenario_dict, FIGURE_DIR, TABLE_DIR)
    root.mainloop()
