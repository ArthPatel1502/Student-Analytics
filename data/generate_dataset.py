"""
generate_dataset.py
--------------------
Creates a synthetic dataset of students for the Data Science &
Visualization mini-project (Practicals 1-3).

Fields:
  name, gender, enrollment_no, mobile, city,
  sem1_DS, sem1_DBMS, sem1_OS, sem1_MATH, sem1_ENG,
  sem2_..., sem3_..., sem4_...  (5 subjects x 4 semesters)

A few marks and a few gender values are deliberately left blank
so Practical-3 (missing value treatment) has something real to do.
"""

import csv
import os
import random

random.seed(42)

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

FIRST_NAMES_M = ["Arjun", "Rohan", "Vivaan", "Karan", "Aditya", "Yash", "Kunal",
                  "Devansh", "Harsh", "Nikhil", "Parth", "Raj", "Sahil", "Tanish", "Vivek"]
FIRST_NAMES_F = ["Ananya", "Diya", "Isha", "Kavya", "Meera", "Nisha", "Priya",
                  "Riya", "Sneha", "Tanvi", "Vidhi", "Zoya", "Aarushi", "Bhavya", "Charvi"]
LAST_NAMES = ["Patel", "Shah", "Mehta", "Desai", "Joshi", "Trivedi", "Rana",
              "Chauhan", "Solanki", "Parmar", "Panchal", "Gohil", "Bhatt", "Naik", "Thakor"]
CITIES = ["Vapi", "Surat", "Vadodara", "Ahmedabad", "Anand", "Nadiad", "Valsad", "Navsari"]
SUBJECTS = ["DS", "DBMS", "OS", "MATH", "ENG"]
SEMESTERS = [1, 2, 3, 4]

N_STUDENTS = 60


def make_name(gender):
    first = random.choice(FIRST_NAMES_M if gender == "M" else FIRST_NAMES_F)
    last = random.choice(LAST_NAMES)
    return f"{first} {last}"


def make_mobile():
    return "9" + "".join(str(random.randint(0, 9)) for _ in range(9))


def make_marks(base_ability):
    """Marks out of 100, drifting slightly upward each semester."""
    m = int(random.gauss(base_ability, 12))
    return max(0, min(100, m))


def build_row(i):
    gender = random.choice(["M", "F"])
    row = {
        "enrollment_no": f"12302080{501000 + i}",
        "name": make_name(gender),
        "gender": gender,
        "mobile": make_mobile(),
        "city": random.choice(CITIES),
    }
    base_ability = random.gauss(65, 10)
    for sem in SEMESTERS:
        drift = (sem - 1) * random.uniform(0, 3)
        for sub in SUBJECTS:
            row[f"sem{sem}_{sub}"] = make_marks(base_ability + drift)
    return row


def inject_missing(rows, frac=0.05):
    """Randomly blank out some gender values and some mark cells."""
    mark_cols = [f"sem{s}_{sub}" for s in SEMESTERS for sub in SUBJECTS]
    n_missing_marks = int(len(rows) * len(mark_cols) * frac)
    for _ in range(n_missing_marks):
        r = random.choice(rows)
        c = random.choice(mark_cols)
        r[c] = ""
    n_missing_gender = max(1, int(len(rows) * 0.05))
    for r in random.sample(rows, n_missing_gender):
        r["gender"] = ""
    return rows


def main():
    rows = [build_row(i) for i in range(1, N_STUDENTS + 1)]
    rows = inject_missing(rows)

    fieldnames = ["enrollment_no", "name", "gender", "mobile", "city"] + \
                 [f"sem{s}_{sub}" for s in SEMESTERS for sub in SUBJECTS]

    out_path = os.path.join(SCRIPT_DIR, "students.csv")
    with open(out_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"Wrote {len(rows)} students to {out_path}")


if __name__ == "__main__":
    main()
