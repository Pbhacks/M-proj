import customtkinter as ctk
from tkinter import filedialog, messagebox
from PIL import Image
import cv2
import numpy as np
import sqlite3
import os
from datetime import datetime

# ========== Initialize DB and folders ==========
os.makedirs('stored_results', exist_ok=True)
conn = sqlite3.connect('lab_results.db')
c = conn.cursor()
c.execute('''CREATE TABLE IF NOT EXISTS blood_analysis (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    filename TEXT,
    rbc_count INTEGER,
    wbc_estimate INTEGER,
    abnormal_count INTEGER,
    interpretation TEXT,
    timestamp TEXT
)''')
conn.commit()

# === Biomedical Reference Ranges ===
LOW_RBC = 4_000_000
HIGH_RBC = 6_000_000

# === CustomTkinter Theme ===
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

# === RBC Detection Function ===
def analyze_image(image_path):
    image = cv2.imread(image_path)
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    # Preprocess
    blurred = cv2.medianBlur(gray, 5)

    # RBC Detection: Circle detection (HoughCircles works better here)
    circles = cv2.HoughCircles(blurred, cv2.HOUGH_GRADIENT, dp=1.2, minDist=15,
                                param1=50, param2=30, minRadius=5, maxRadius=15)

    rbc_count = 0
    abnormal_count = 0

    output_img = image.copy()

    if circles is not None:
        circles = np.uint16(np.around(circles))
        rbc_count = len(circles[0, :])
        for i in circles[0, :]:
            x, y, r = i
            cv2.circle(output_img, (x, y), r, (0, 255, 0), 2)

            # Basic abnormality check (very small or large radius)
            if r < 6 or r > 14:
                abnormal_count += 1
                cv2.circle(output_img, (x, y), r, (0, 0, 255), 2)

    # WBC Estimate: Rough assumption (~1% of RBC)
    wbc_estimate = int(rbc_count * 0.01)

    # Interpretation
    estimated_rbc_ul = rbc_count * 2000  # using same conversion
    if estimated_rbc_ul < LOW_RBC:
        interpretation = "LOW RBC COUNT (Possible Anemia)"
    elif estimated_rbc_ul > HIGH_RBC:
        interpretation = "HIGH RBC COUNT (Possible Polycythemia)"
    else:
        interpretation = "NORMAL RBC COUNT"

    return rbc_count, wbc_estimate, abnormal_count, interpretation, output_img

# === App Functions ===
def upload_image():
    file_path = filedialog.askopenfilename(filetypes=[("Image files", "*.jpg *.jpeg *.png")])
    if not file_path:
        return

    try:
        rbc_count, wbc_estimate, abnormal_count, interpretation, output_img = analyze_image(file_path)

        # Save processed image
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = os.path.basename(file_path).split('.')[0]
        save_path = f'stored_results/{filename}_{timestamp}.png'
        cv2.imwrite(save_path, output_img)

        # Store results
        c.execute('INSERT INTO blood_analysis (filename, rbc_count, wbc_estimate, abnormal_count, interpretation, timestamp) VALUES (?, ?, ?, ?, ?, ?)',
                  (save_path, rbc_count, wbc_estimate, abnormal_count, interpretation, timestamp))
        conn.commit()

        # Display result
        pil_img = Image.fromarray(cv2.cvtColor(output_img, cv2.COLOR_BGR2RGB))
        pil_img.thumbnail((400, 400))

        img_ctk = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=pil_img.size)
        image_label.configure(image=img_ctk)
        image_label.image = img_ctk

        result_text.set(f"RBC Count: {rbc_count}\nWBC Estimate: {wbc_estimate}\nAbnormal Cells: {abnormal_count}\n\n{interpretation}")

        messagebox.showinfo("Success", f"Analysis complete and saved!\n\nResults saved as: {save_path}")

    except Exception as e:
        messagebox.showerror("Error", f"Failed to process image:\n{e}")

# === App Window ===
app = ctk.CTk()
app.title("Biomedical Multi-Analysis Lab App")
app.geometry("800x600")

title_label = ctk.CTkLabel(app, text="🔬 Biomedical RBC Multi-Analyzer", font=("Helvetica", 24, "bold"))
title_label.pack(pady=20)

upload_btn = ctk.CTkButton(app, text="Upload Haemocytometer Image", command=upload_image, font=("Helvetica", 16), width=200, height=40)
upload_btn.pack(pady=10)

result_text = ctk.StringVar()
result_label = ctk.CTkLabel(app, textvariable=result_text, font=("Helvetica", 16), justify="left")
result_label.pack(pady=10)

image_label = ctk.CTkLabel(app, text="")
image_label.pack(pady=10)

footer = ctk.CTkLabel(app, text="Developed for Secure Biomedical IoT Project\nAdvanced Multi-Analysis Platform", font=("Helvetica", 10))
footer.pack(side="bottom", pady=10)

app.mainloop()

# === Close DB connection on exit ===
conn.close()
