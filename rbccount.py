import tkinter as tk
from tkinter import filedialog, messagebox
import cv2
import numpy as np
import os
import sqlite3
from datetime import datetime

# === Initialize local storage ===
os.makedirs('stored_patterns', exist_ok=True)
conn = sqlite3.connect('rbc_results.db')
c = conn.cursor()
c.execute('''CREATE TABLE IF NOT EXISTS rbc_data (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              filename TEXT,
              raw_count INTEGER,
              rbc_per_uL INTEGER,
              interpretation TEXT,
              timestamp TEXT
)''')
conn.commit()

# === Constants for haemocytometer calculation ===
DILUTION_FACTOR = 200
CHAMBER_VOLUME_uL = 0.1  # mm³ = μL
CONVERSION_FACTOR = DILUTION_FACTOR / CHAMBER_VOLUME_uL  # 200 / 0.1 = 2000

# === Biomedical reference ranges (cells/μL) ===
LOW_THRESHOLD = 4_000_000
HIGH_THRESHOLD = 6_000_000

# === RBC Counting Function (Enhanced version) ===
def count_rbc_adaptive(image_path):
    image = cv2.imread(image_path)
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    # Step 1: Adaptive Threshold (robust to lighting)
    thresh = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_MEAN_C,
                                    cv2.THRESH_BINARY_INV, 35, 5)

    # Step 2: Morphological Opening (remove tiny noise)
    kernel = np.ones((3, 3), np.uint8)
    clean = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, kernel, iterations=2)

    # Step 3: Contour detection
    contours, _ = cv2.findContours(clean, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    # Step 4: Filter contours based on area (typical RBC size)
    valid_contours = []
    for cnt in contours:
        area = cv2.contourArea(cnt)
        if 50 < area < 300:  # Adjust as per your microscope (worked on your sample image)
            valid_contours.append(cnt)

    raw_rbc_count = len(valid_contours)

    # Draw detected cells
    output_img = image.copy()
    for cnt in valid_contours:
        (x, y), radius = cv2.minEnclosingCircle(cnt)
        center = (int(x), int(y))
        radius = int(radius)
        cv2.circle(output_img, center, radius, (0, 255, 0), 2)

    # Display count text on image
    text = f'Counted RBCs: {raw_rbc_count}'
    cv2.putText(output_img, text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)

    rbc_per_uL = raw_rbc_count * int(CONVERSION_FACTOR)

    # Step 5: Interpretation
    if rbc_per_uL < LOW_THRESHOLD:
        interpretation = "LOW RBC COUNT (Anemia)"
    elif rbc_per_uL > HIGH_THRESHOLD:
        interpretation = "HIGH RBC COUNT (Polycythemia)"
    else:
        interpretation = "NORMAL RBC COUNT"

    return raw_rbc_count, rbc_per_uL, interpretation, output_img

# === GUI App ===
def upload_image():
    file_path = filedialog.askopenfilename(filetypes=[("Image files", "*.jpg *.png *.jpeg")])
    if not file_path:
        return

    try:
        raw_count, rbc_per_uL, interpretation, processed_img = count_rbc_adaptive(file_path)

        # Show result to user
        result_msg = (
            f"Raw RBC Count (in Image): {raw_count}\n"
            f"Estimated RBC Count: {rbc_per_uL} cells/μL\n"
            f"Interpretation: {interpretation}"
        )
        messagebox.showinfo("RBC Count Result", result_msg)

        # Save processed image with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = os.path.basename(file_path).split('.')[0]
        save_path = f'stored_patterns/{filename}_{timestamp}.png'
        cv2.imwrite(save_path, processed_img)

        # Save result to DB
        c.execute("INSERT INTO rbc_data (filename, raw_count, rbc_per_uL, interpretation, timestamp) VALUES (?, ?, ?, ?, ?)",
                  (save_path, raw_count, rbc_per_uL, interpretation, timestamp))
        conn.commit()

        messagebox.showinfo("Saved", f"Processed image and result saved locally!")

    except Exception as e:
        messagebox.showerror("Error", f"Failed to process image: {e}")

# === Main App Window ===
root = tk.Tk()
root.title("Haemocytometer RBC Analyzer")
root.geometry("500x300")
root.configure(bg='#e6f2ff')

title = tk.Label(root, text="Biomedical RBC Counter (Enhanced)", font=("Helvetica", 16, "bold"), bg='#e6f2ff')
title.pack(pady=20)

desc = tk.Label(root, text="Upload haemocytometer image\nSystem will auto-detect cells and compute RBC count",
                font=("Helvetica", 11), bg='#e6f2ff')
desc.pack(pady=5)

upload_btn = tk.Button(root, text="Upload Image", command=upload_image,
                       font=("Helvetica", 13), bg='#008CBA', fg='white', padx=10, pady=5)
upload_btn.pack(pady=20)

footer = tk.Label(root, text="Developed for Secure Biomedical IoT Project", font=("Helvetica", 9), bg='#e6f2ff')
footer.pack(side='bottom', pady=10)

root.mainloop()

# Close DB on exit
conn.close()
