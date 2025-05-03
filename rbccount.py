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

# === RBC Counting Function with grid rules ===
def count_rbc_with_grid(image_path):
    image = cv2.imread(image_path)
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    # Step 1: Pre-process to enhance grid
    blur = cv2.GaussianBlur(gray, (5, 5), 0)
    edges = cv2.Canny(blur, 50, 150, apertureSize=3)

    # Step 2: Detect lines to get grid
    lines = cv2.HoughLinesP(edges, 1, np.pi/180, threshold=100, minLineLength=50, maxLineGap=5)

    grid_mask = np.zeros_like(gray)
    if lines is not None:
        for line in lines:
            x1, y1, x2, y2 = line[0]
            cv2.line(grid_mask, (x1, y1), (x2, y2), 255, 2)

    # Step 3: Find bounding box of densest grid region (central square)
    contours, _ = cv2.findContours(grid_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    largest_contour = max(contours, key=cv2.contourArea)
    x, y, w, h = cv2.boundingRect(largest_contour)

    # Focus only on central square ROI
    roi = gray[y:y+h, x:x+w]

    # Step 4: Detect RBCs inside ROI
    blurred_roi = cv2.medianBlur(roi, 5)
    _, thresh = cv2.threshold(blurred_roi, 127, 255, cv2.THRESH_BINARY_INV)

    contours_rbc, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    min_area = 50
    filtered_contours = [cnt for cnt in contours_rbc if cv2.contourArea(cnt) > min_area]

    raw_rbc_count = len(filtered_contours)
    rbc_per_uL = raw_rbc_count * int(CONVERSION_FACTOR)

    # Step 5: Interpretation
    if rbc_per_uL < LOW_THRESHOLD:
        interpretation = "LOW RBC COUNT (Anemia)"
    elif rbc_per_uL > HIGH_THRESHOLD:
        interpretation = "HIGH RBC COUNT (Polycythemia)"
    else:
        interpretation = "NORMAL RBC COUNT"

    # Visualization
    output_img = image.copy()
    cv2.rectangle(output_img, (x, y), (x + w, y + h), (255, 0, 0), 3)  # Mark ROI
    for cnt in filtered_contours:
        cnt_shifted = cnt + [x, y]  # Shift contour to full image coords
        cv2.drawContours(output_img, [cnt_shifted], -1, (0, 255, 0), 2)

    return raw_rbc_count, rbc_per_uL, interpretation, output_img

# === GUI App ===
def upload_image():
    file_path = filedialog.askopenfilename(filetypes=[("Image files", "*.jpg *.png *.jpeg")])
    if not file_path:
        return

    try:
        raw_count, rbc_per_uL, interpretation, processed_img = count_rbc_with_grid(file_path)

        # Show result to user
        result_msg = (
            f"Raw RBC Count (in ROI): {raw_count}\n"
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

title = tk.Label(root, text="Biomedical RBC Counter (Haemocytometer)", font=("Helvetica", 16, "bold"), bg='#e6f2ff')
title.pack(pady=20)

desc = tk.Label(root, text="Upload blood smear haemocytometer image\nSystem will auto-detect grid and compute RBC count",
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
