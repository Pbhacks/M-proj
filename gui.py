import tkinter as tk
from tkinter import ttk, messagebox
import ttkbootstrap as tb
from ttkbootstrap.constants import *
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

# ---------- Data Storage ----------
patient_data = pd.DataFrame(columns=[
    'Patient ID', 'Name', 'Age', 'Sex',
    'Hemoglobin', 'RBC', 'WBC', 'Platelets'
])

# ---------- Functions ----------

def validate_and_submit():
    global patient_data
    try:
        patient_id = entry_id.get().strip()
        name = entry_name.get().strip()
        age = int(entry_age.get())
        sex = combo_sex.get()
        hb = float(entry_hb.get())
        rbc = float(entry_rbc.get())
        wbc = float(entry_wbc.get())
        platelets = int(entry_platelets.get())

        # Validation
        if not patient_id or not name or not sex:
            messagebox.showwarning("Missing Data", "Fill all fields properly.")
            return
        if patient_id in patient_data['Patient ID'].values:
            messagebox.showerror("Duplicate ID", "Patient ID already exists.")
            return

        new_row = {
            'Patient ID': patient_id, 'Name': name, 'Age': age, 'Sex': sex,
            'Hemoglobin': hb, 'RBC': rbc, 'WBC': wbc, 'Platelets': platelets
        }
        patient_data = pd.concat([patient_data, pd.DataFrame([new_row])], ignore_index=True)
        list_patients.insert('end', f"{patient_id} - {name}")
        clear_entries()

    except ValueError:
        messagebox.showerror("Invalid Input", "Check numeric values!")

def clear_entries():
    for entry in [entry_id, entry_name, entry_age, entry_hb, entry_rbc, entry_wbc, entry_platelets]:
        entry.delete(0, 'end')
    combo_sex.set('')

def generate_report():
    selected = list_patients.curselection()
    if not selected:
        messagebox.showwarning("Select Patient", "Choose a patient first.")
        return
    index = selected[0]
    pid = list_patients.get(index).split(' - ')[0]
    record = patient_data[patient_data['Patient ID'] == pid].iloc[0]

    label_patientinfo.config(text=f"ID: {record['Patient ID']}\nName: {record['Name']}\nAge: {record['Age']}\nSex: {record['Sex']}")
    label_statsinfo.config(text=f"""
Hemoglobin: {record['Hemoglobin']} g/dL
RBC Count: {record['RBC']} million/uL
WBC Count: {record['WBC']} /uL
Platelets: {record['Platelets']} /uL
""".strip())

    # Store globally for charts
    app.selected_record = record

    # Auto trigger chart refresh
    update_chart()

def update_chart(*args):
    for widget in frame_chart.winfo_children():
        widget.destroy()

    record = app.selected_record
    chart_type = combo_chart.get()

    fig, ax = plt.subplots(figsize=(5.5, 4))
    plt.subplots_adjust(left=0.2, right=0.8)

    if chart_type == "Donut Chart":
        values = [record['Hemoglobin'], record['RBC'], record['WBC']/1000, record['Platelets']/100000]
        labels = ['Hemoglobin', 'RBC', 'WBC(x1000)', 'Platelets(x100k)']
        wedges, _ = ax.pie(values, wedgeprops=dict(width=0.4), startangle=140)
        ax.legend(wedges, labels, loc='center left', bbox_to_anchor=(1.2, 0.5))
        ax.set_title('Blood Composition')

    elif chart_type == "Bar Chart":
        metrics = ['Hemoglobin', 'RBC', 'WBC', 'Platelets']
        values = [record['Hemoglobin'], record['RBC'], record['WBC'], record['Platelets']]
        ax.bar(metrics, values, color=['blue', 'green', 'orange', 'red'])
        ax.set_ylabel('Value')
        ax.set_title('Cell Counts Comparison')

    elif chart_type == "Line Chart (Dummy Trend)":
        days = np.arange(1, 8)
        hb_trend = record['Hemoglobin'] + np.random.normal(0, 0.5, size=7)
        ax.plot(days, hb_trend, marker='o', color='purple')
        ax.set_xticks(days)
        ax.set_xlabel('Last 7 Days')
        ax.set_ylabel('Hemoglobin g/dL')
        ax.set_title('Hemoglobin Trend')

    elif chart_type == "Hemoglobin Gauge":
        target = 15
        percent = min(record['Hemoglobin']/target, 1)
        wedges, _ = ax.pie([percent, 1 - percent], startangle=90, colors=['limegreen', 'gray'],
                            wedgeprops=dict(width=0.3))
        ax.text(0, 0, f"{int(percent*100)}%", ha='center', va='center', fontsize=14, weight='bold')
        ax.set_title('Hemoglobin Target %')

    canvas = FigureCanvasTkAgg(fig, master=frame_chart)
    canvas.draw()
    canvas.get_tk_widget().pack(fill='both', expand=True)

# ---------- GUI Layout ----------
app = tb.Window(themename="superhero")
app.title("Ultra-Advanced Power BI-style Haemoanalysis Dashboard")
app.geometry("1600x900")
app.selected_record = None

# Layout
app.columnconfigure((0, 1, 2), weight=1)
app.rowconfigure(0, weight=1)

# Patient Entry Panel
frame_entry = tb.Labelframe(app, text="Enter Patient Record", bootstyle="warning", padding=15)
frame_entry.grid(row=0, column=0, sticky='nsew', padx=5, pady=5)

fields = ["Patient ID", "Name", "Age", "Sex", "Hemoglobin", "RBC", "WBC", "Platelets"]
entries = {}

for i, fld in enumerate(fields):
    lbl = tb.Label(frame_entry, text=fld + ":")
    lbl.grid(row=i, column=0, sticky='w', pady=3)
    if fld == "Sex":
        ent = tb.Combobox(frame_entry, values=["Male", "Female", "Other"])
    else:
        ent = tb.Entry(frame_entry)
    ent.grid(row=i, column=1, sticky='ew', pady=3)
    entries[fld] = ent

frame_entry.columnconfigure(1, weight=1)

entry_id = entries["Patient ID"]
entry_name = entries["Name"]
entry_age = entries["Age"]
combo_sex = entries["Sex"]
entry_hb = entries["Hemoglobin"]
entry_rbc = entries["RBC"]
entry_wbc = entries["WBC"]
entry_platelets = entries["Platelets"]

btn_submit = tb.Button(frame_entry, text="Add Patient Record", bootstyle="success", command=validate_and_submit)
btn_submit.grid(row=len(fields), column=0, columnspan=2, pady=10)

# Patient List Panel
frame_list = tb.Labelframe(app, text="Patients List", bootstyle="info", padding=15)
frame_list.grid(row=0, column=1, sticky='nsew', padx=5, pady=5)

list_patients = tk.Listbox(frame_list, height=20, font=('Segoe UI', 10))
list_patients.pack(fill='both', expand=True)

btn_report = tb.Button(frame_list, text="Generate Report", bootstyle="primary", command=generate_report)
btn_report.pack(pady=10)

# Report Panel (Tabbed style mimic)
frame_report = tb.Labelframe(app, text="Patient Report & Analysis", bootstyle="danger", padding=15)
frame_report.grid(row=0, column=2, sticky='nsew', padx=5, pady=5)
frame_report.columnconfigure(0, weight=1)
frame_report.rowconfigure(2, weight=1)

# Info Cards
label_patientinfo = tb.Label(frame_report, text="No patient selected.", font=("Segoe UI", 11), bootstyle="info")
label_patientinfo.grid(row=0, column=0, sticky='ew', pady=5)

label_statsinfo = tb.Label(frame_report, text="", font=("Segoe UI", 10), bootstyle="light")
label_statsinfo.grid(row=1, column=0, sticky='ew', pady=5)

# Chart Selector
combo_chart = tb.Combobox(frame_report, values=["Donut Chart", "Bar Chart", "Line Chart (Dummy Trend)", "Hemoglobin Gauge"])
combo_chart.set("Donut Chart")
combo_chart.grid(row=2, column=0, sticky='ew', pady=5)
combo_chart.bind("<<ComboboxSelected>>", update_chart)

# Chart Frame
frame_chart = tb.Frame(frame_report)
frame_chart.grid(row=3, column=0, sticky='nsew', pady=5)
frame_report.rowconfigure(3, weight=1)

app.mainloop()
