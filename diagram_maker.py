import tkinter as tk
from tkinter import messagebox, filedialog
import customtkinter as ctk
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.ticker import MultipleLocator
import numpy as np

ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")

class PVPoint:
    def __init__(self, id, v, p, label=""):
        self.id = id
        self.v = v
        self.p = p
        self.label = label

class PVProcess:
    def __init__(self, id, type, point1, point2, label=""):
        self.id = id
        self.type = type
        self.p1 = point1
        self.p2 = point2
        self.label = label

class PVShading:
    def __init__(self, id, type, process_ids, label=""):
        self.id = id
        self.type = type
        self.process_ids = process_ids
        self.label = label

class PVTextLabel:
    def __init__(self, id, v, p, text):
        self.id = id
        self.v = v
        self.p = p
        self.text = text

class PVDiagram:
    def __init__(self):
        self.points = {}
        self.processes = {}
        self.shadings = {}
        self.text_labels = {}
        self.point_counter = 1
        self.process_counter = 1
        self.shading_counter = 1
        self.label_counter = 1
        self.unit_v = "L"
        self.unit_p = "atm"

    def add_point(self, v, p, label=""):
        # Check if point already exists
        for pt in self.points.values():
            if np.isclose(pt.v, v) and np.isclose(pt.p, p):
                if label and not pt.label:
                    pt.label = label
                return pt
        
        if not label:
            label = str(self.point_counter)
            
        pt = PVPoint(self.point_counter, v, p, label)
        self.points[self.point_counter] = pt
        self.point_counter += 1
        return pt

    def add_process(self, type, v1, p1, v2, p2, label=""):
        pt1 = self.add_point(v1, p1)
        pt2 = self.add_point(v2, p2)
        
        proc = PVProcess(self.process_counter, type, pt1, pt2, label)
        self.processes[self.process_counter] = proc
        self.process_counter += 1
        return proc

    def delete_point(self, pid):
        if pid in self.points:
            # removing point should probably remove processes associated with it
            to_remove_proc = [k for k, v in self.processes.items() if v.p1.id == pid or v.p2.id == pid]
            for k in to_remove_proc:
                self.delete_process(k)
            del self.points[pid]

    def delete_process(self, pid):
        if pid in self.processes:
            # Also removeshadings that use this process
            to_remove_shading = [k for k, v in self.shadings.items() if pid in v.process_ids]
            for k in to_remove_shading:
                self.delete_shading(k)
            del self.processes[pid]

    def add_shading(self, type, process_ids, label=""):
        shd = PVShading(self.shading_counter, type, process_ids, label)
        self.shadings[self.shading_counter] = shd
        self.shading_counter += 1
        return shd

    def delete_shading(self, sid):
        if sid in self.shadings:
            del self.shadings[sid]

    def add_text_label(self, v, p, text):
        tlbl = PVTextLabel(self.label_counter, v, p, text)
        self.text_labels[self.label_counter] = tlbl
        self.label_counter += 1
        return tlbl

    def delete_text_label(self, lid):
        if lid in self.text_labels:
            del self.text_labels[lid]

    def generate(self):
        lines = []
        lines.append(r"\begin{tikzpicture}")
        lines.append(r"\begin{axis}[")
        lines.append(r"axis lines = middle,")
        lines.append(rf"xlabel = $V\ (\mathrm{{{self.unit_v}}})$,")
        lines.append(rf"ylabel = $P\ (\mathrm{{{self.unit_p}}})$,")
        lines.append(r"grid=major,")
        x_min, x_max = 0, 10
        y_min, y_max = 0, 10
        if self.points:
            v_vals = [pt.v for pt in self.points.values()]
            p_vals = [pt.p for pt in self.points.values()]
            min_v, max_v = min(v_vals), max(v_vals)
            min_p, max_p = min(p_vals), max(p_vals)
            
            x_min = max(0, int(np.floor(min_v)) - 1)
            x_max = int(np.ceil(max_v)) + 1
            y_min = max(0, int(np.floor(min_p)) - 1)
            y_max = int(np.ceil(max_p)) + 1
            
            lines.append(rf"ymin={y_min}, ymax={y_max},")
            lines.append(rf"xmin={x_min}, xmax={x_max},")
        else:
            lines.append(r"ymin=0, xmin=0,")
            
        lines.append(r"xtick={" + ", ".join([str(i) for i in range(x_min, x_max)]) + "}, ytick={" + ", ".join([str(i) for i in range(y_min, y_max)]) + "},")
        lines.append(r"]")

        for shd in self.shadings.values():
            fill_coords_v = []
            fill_coords_p = []
            for pid in shd.process_ids:
                if pid in self.processes:
                    proc = self.processes[pid]
                    vs = np.linspace(proc.p1.v, proc.p2.v, 20)
                    if proc.type == "Isothermal":
                        c = proc.p1.v * proc.p1.p
                        ps = c / vs
                    elif proc.type == "Adiabatic":
                        gamma = 1.4
                        c = proc.p1.p * (proc.p1.v ** gamma)
                        ps = c / (vs ** gamma)
                    else:
                        ps = np.linspace(proc.p1.p, proc.p2.p, 20)
                    for x, y in zip(vs, ps):
                        fill_coords_v.append(x)
                        fill_coords_p.append(y)
            if fill_coords_v:
                cv, cp = fill_coords_v[:], fill_coords_p[:]
                if shd.type == "Under Curve":
                    cv.append(cv[-1])
                    cp.append(0)
                    cv.append(cv[0])
                    cp.append(0)
                
                coords_str = " -- ".join([f"(axis cs:{x:.3f},{y:.3f})" for x, y in zip(cv, cp)])
                lines.append(rf"\fill[gray, opacity=0.3] {coords_str} -- cycle;")
                
                if shd.label:
                    mid_v = sum(cv) / len(cv)
                    mid_p = sum(cp) / len(cp)
                    lines.append(rf"\node at (axis cs:{mid_v:.3f},{mid_p:.3f}) {{{shd.label}}};")

        for proc in self.processes.values():
            if proc.type in ["Isobaric", "Isochoric", "Linear"]:
                node_label = rf" node[midway, above] {{{proc.label}}}" if proc.label else ""
                lines.append(
                    rf"\addplot[thick, -latex] coordinates "
                    rf"{{({proc.p1.v},{proc.p1.p}) ({proc.p2.v},{proc.p2.p})}}{node_label};"
                )
            elif proc.type == "Isothermal":
                c = proc.p1.v * proc.p1.p
                v_min = min(proc.p1.v, proc.p2.v)
                v_max = max(proc.p1.v, proc.p2.v)
                
                direction = "->" if proc.p1.v < proc.p2.v else "<-"
                node_label = rf" node[midway, above right] {{{proc.label}}}" if proc.label else ""
                lines.append(rf"\addplot[thick, {direction}, domain={v_min}:{v_max}, samples=50] {{{c}/x}}{node_label};")
            elif proc.type == "Adiabatic":
                gamma = 1.4
                c = proc.p1.p * (proc.p1.v ** gamma)
                v_min = min(proc.p1.v, proc.p2.v)
                v_max = max(proc.p1.v, proc.p2.v)
                
                direction = "->" if proc.p1.v < proc.p2.v else "<-"
                node_label = rf" node[midway, above right] {{{proc.label}}}" if proc.label else ""
                lines.append(rf"\addplot[thick, {direction}, domain={v_min}:{v_max}, samples=50] {{{c}/(x^{{{gamma}}})}}{node_label};")

        if self.points:
            lines.append(r"\addplot[only marks, mark=*, mark size=1.5pt] coordinates {")
            for pt in self.points.values():
                lines.append(f"({pt.v},{pt.p})")
            lines.append("};")

        for pt in self.points.values():
            if pt.label:
                lines.append(rf"\node at (axis cs:{pt.v},{pt.p}) [above right] {{{pt.label}}};")

        for tlbl in self.text_labels.values():
            lines.append(rf"\node at (axis cs:{tlbl.v},{tlbl.p}) {{{tlbl.text}}};")

        lines.append(r"\end{axis}")
        lines.append(r"\end{tikzpicture}")

        return "\n".join(lines)


class CalculatorPanel(ctk.CTkFrame):
    def __init__(self, parent, diagram):
        super().__init__(parent)
        self.diagram = diagram
        
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        # Process Selection
        sel_frame = ctk.CTkFrame(self, fg_color="transparent")
        sel_frame.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        
        ctk.CTkLabel(sel_frame, text="Select Process:").pack(side="left", padx=5, pady=2)
        
        self.proc_var = ctk.StringVar()
        self.proc_menu = ctk.CTkOptionMenu(sel_frame, variable=self.proc_var, values=["None"])
        self.proc_menu.pack(side="left", padx=5, pady=2, fill="x", expand=True)

        # Parameters
        param_frame = ctk.CTkFrame(self, fg_color="transparent")
        param_frame.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)
        
        ctk.CTkLabel(param_frame, text="Degrees of Freedom (f):").grid(row=0, column=0, padx=5, pady=2, sticky="w")
        self.f_var = ctk.StringVar(value="3")
        self.f_entry = ctk.CTkEntry(param_frame, textvariable=self.f_var, width=50)
        self.f_entry.grid(row=0, column=1, padx=5, pady=2, sticky="w")
        
        ctk.CTkButton(param_frame, text="Calculate", command=self.calculate, width=80).grid(row=0, column=2, padx=5, pady=2)

        # Output
        out_frame = ctk.CTkFrame(self, fg_color="transparent")
        out_frame.grid(row=2, column=0, sticky="nsew", padx=5, pady=5)
        
        self.result_lbl = ctk.CTkLabel(out_frame, text="", justify="left", font=ctk.CTkFont(size=13))
        self.result_lbl.pack(padx=5, pady=5, anchor="nw")
        
        ctk.CTkLabel(out_frame, text="LaTeX Output (Work):").pack(padx=5, pady=(5, 0), anchor="w")
        self.latex_out = ctk.CTkTextbox(out_frame, height=100, font=ctk.CTkFont(family="Consolas", size=11))
        self.latex_out.pack(padx=5, pady=2, fill="both", expand=True)

        self.update_process_list()

    def update_process_list(self):
        proc_options = [f"Process {pid}: {p.type}" for pid, p in self.diagram.processes.items()]
        if not proc_options:
            proc_options = ["None"]
        self.proc_menu.configure(values=proc_options)
        if self.proc_var.get() not in proc_options:
            self.proc_var.set(proc_options[0])

    def calculate(self):
        sel_val = self.proc_var.get()
        if sel_val == "None" or not sel_val:
            return
            
        pid = int(sel_val.split(":")[0].replace("Process ", ""))
        proc = self.diagram.processes.get(pid)
        if not proc:
            return

        try:
            f = float(self.f_var.get())
        except ValueError:
            f = 3.0

        v1, p1 = proc.p1.v, proc.p1.p
        v2, p2 = proc.p2.v, proc.p2.p
        
        W = 0
        latex_eq = ""
        
        if proc.type == "Isochoric":
            W = 0
            latex_eq = r"W &= \int P \, dV = 0"
        elif proc.type == "Isobaric":
            W = p1 * (v2 - v1)
            latex_eq = rf"W &= P \Delta V = {p1:.2f} \times ({v2:.2f} - {v1:.2f}) = {W:.2f}"
        elif proc.type == "Isothermal":
            W = p1 * v1 * np.log(v2 / v1) if v1 != 0 else 0
            latex_eq = rf"W &= nRT \ln\left(\frac{{V_f}}{{V_i}}\right) = P_i V_i \ln\left(\frac{{V_f}}{{V_i}}\right) = {p1:.2f} \times {v1:.2f} \ln\left(\frac{{{v2:.2f}}}{{{v1:.2f}}}\right) = {W:.2f}"
        elif proc.type == "Adiabatic":
            gamma = 1.4
            W = (p2 * v2 - p1 * v1) / (1 - gamma)
            latex_eq = rf"W &= \frac{{P_f V_f - P_i V_i}}{{1 - \gamma}} = \frac{{{p2:.2f} \times {v2:.2f} - {p1:.2f} \times {v1:.2f}}}{{1 - 1.4}} = {W:.2f}"
        else: # Linear
            W = 0.5 * (p1 + p2) * (v2 - v1)
            latex_eq = rf"W &= \text{{Area under curve}} = \frac{{1}}{{2}}(P_i + P_f)(V_f - V_i) = \frac{{1}}{{2}}({p1:.2f} + {p2:.2f})({v2:.2f} - {v1:.2f}) = {W:.2f}"

        # dE_th
        delta_E = (f / 2) * (p2 * v2 - p1 * v1)
        Q = delta_E + W
        
        res_text = (f"Results for Process {pid}:\n\n"
                    f"Work Done (W): {W:.3f}\n"
                    f"Change in Thermal Energy (ΔE_th): {delta_E:.3f}\n"
                    f"Heat Added (Q): {Q:.3f}")
        
        self.result_lbl.configure(text=res_text)
        
        latex_str = (r"\begin{aligned}" + "\n"
                     rf"    {latex_eq}" + "\n"
                     r"\end{aligned}" + "\n"
                     rf"\boxed{{W = {W:.2f}}}")
        self.latex_out.delete("0.0", "end")
        self.latex_out.insert("0.0", latex_str)


class PVApp:
    def __init__(self, root):
        self.diagram = PVDiagram()
        self.root = root
        self.root.title("PV Diagram Maker Pro")
        self.root.geometry("1100x700")
        
        self.root.grid_columnconfigure(0, weight=1)
        self.root.grid_columnconfigure(1, weight=1)
        self.root.grid_columnconfigure(2, weight=2)
        self.root.grid_rowconfigure(0, weight=1)

        # left pane: inputs
        self.left_pane = ctk.CTkFrame(self.root)
        self.left_pane.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        
        # middle pane: lists
        self.mid_pane = ctk.CTkFrame(self.root)
        self.mid_pane.grid(row=0, column=1, sticky="nsew", padx=10, pady=10)

        # right pane: plot & output
        self.right_pane = ctk.CTkFrame(self.root)
        self.right_pane.grid(row=0, column=2, sticky="nsew", padx=10, pady=10)
        self.right_pane.grid_rowconfigure(0, weight=3)
        self.right_pane.grid_rowconfigure(1, weight=1)
        self.right_pane.grid_columnconfigure(0, weight=1)

        self._setup_left_pane()
        self._setup_mid_pane()
        self._setup_right_pane()

        self.update_ui()

    def _setup_left_pane(self):
        # Create a scrollable frame for left pane to fit all inputs
        self.left_scroll = ctk.CTkScrollableFrame(self.left_pane, fg_color="transparent")
        self.left_scroll.pack(fill="both", expand=True)

        ctk.CTkLabel(self.left_scroll, text="Controls", font=ctk.CTkFont(size=20, weight="bold")).pack(pady=5)
        
        # Add Process
        p_frame = ctk.CTkFrame(self.left_scroll)
        p_frame.pack(fill="x", padx=10, pady=5)
        ctk.CTkLabel(p_frame, text="Add Process").pack(anchor="w", padx=10, pady=(5,0))
        
        self.proc_type_var = ctk.StringVar(value="Linear")
        proc_menu = ctk.CTkOptionMenu(p_frame, variable=self.proc_type_var, values=["Linear", "Isobaric", "Isochoric", "Isothermal", "Adiabatic"])
        proc_menu.pack(fill="x", padx=10, pady=5)
        
        row1 = ctk.CTkFrame(p_frame, fg_color="transparent")
        row1.pack(fill="x", padx=5)
        self.v1_ent = ctk.CTkEntry(row1, width=70, placeholder_text="V1")
        self.v1_ent.pack(side="left", padx=5, pady=5)
        self.p1_ent = ctk.CTkEntry(row1, width=70, placeholder_text="P1")
        self.p1_ent.pack(side="left", padx=5, pady=5)

        row2 = ctk.CTkFrame(p_frame, fg_color="transparent")
        row2.pack(fill="x", padx=5)
        self.v2_ent = ctk.CTkEntry(row2, width=70, placeholder_text="V2")
        self.v2_ent.pack(side="left", padx=5, pady=5)
        self.p2_ent = ctk.CTkEntry(row2, width=70, placeholder_text="P2")
        self.p2_ent.pack(side="left", padx=5, pady=5)

        self.p_lbl_ent = ctk.CTkEntry(p_frame, placeholder_text="Process Label (optional)")
        self.p_lbl_ent.pack(fill="x", padx=10, pady=5)

        ctk.CTkButton(p_frame, text="Add Process", command=self.add_process).pack(fill="x", padx=10, pady=5)

        # Add Point manually
        pt_frame = ctk.CTkFrame(self.left_scroll)
        pt_frame.pack(fill="x", padx=10, pady=5)
        ctk.CTkLabel(pt_frame, text="Add Point").pack(anchor="w", padx=10, pady=(5,0))
        
        pt_row = ctk.CTkFrame(pt_frame, fg_color="transparent")
        pt_row.pack(fill="x", padx=5)
        self.pt_v_ent = ctk.CTkEntry(pt_row, width=50, placeholder_text="V")
        self.pt_v_ent.pack(side="left", padx=5, pady=5)
        self.pt_p_ent = ctk.CTkEntry(pt_row, width=50, placeholder_text="P")
        self.pt_p_ent.pack(side="left", padx=5, pady=5)
        self.pt_lbl_ent = ctk.CTkEntry(pt_row, width=60, placeholder_text="Lbl")
        self.pt_lbl_ent.pack(side="left", padx=5, pady=5)
        
        ctk.CTkButton(pt_frame, text="Add Point", command=self.add_point).pack(fill="x", padx=10, pady=5)

        # Add Shading manually
        shd_frame = ctk.CTkFrame(self.left_scroll)
        shd_frame.pack(fill="x", padx=10, pady=5)
        ctk.CTkLabel(shd_frame, text="Add Shading").pack(anchor="w", padx=10, pady=(5,0))
        
        self.shd_type_var = ctk.StringVar(value="Under Curve")
        shd_menu = ctk.CTkOptionMenu(shd_frame, variable=self.shd_type_var, values=["Under Curve", "Inside Cycle"])
        shd_menu.pack(fill="x", padx=10, pady=5)

        self.shd_ent = ctk.CTkEntry(shd_frame, placeholder_text="Process IDs (e.g. 1, 2)")
        self.shd_ent.pack(fill="x", padx=10, pady=5)

        self.shd_lbl_ent = ctk.CTkEntry(shd_frame, placeholder_text="Region Label (optional)")
        self.shd_lbl_ent.pack(fill="x", padx=10, pady=5)
        
        ctk.CTkButton(shd_frame, text="Shade Region", command=self.add_shading).pack(fill="x", padx=10, pady=5)

        # Arbitrary Label
        lbl_frame = ctk.CTkFrame(self.left_scroll)
        lbl_frame.pack(fill="x", padx=10, pady=5)
        ctk.CTkLabel(lbl_frame, text="Add Text Label").pack(anchor="w", padx=10, pady=(5,0))
        
        lbl_row = ctk.CTkFrame(lbl_frame, fg_color="transparent")
        lbl_row.pack(fill="x", padx=5)
        self.tl_v_ent = ctk.CTkEntry(lbl_row, width=50, placeholder_text="V")
        self.tl_v_ent.pack(side="left", padx=5, pady=5)
        self.tl_p_ent = ctk.CTkEntry(lbl_row, width=50, placeholder_text="P")
        self.tl_p_ent.pack(side="left", padx=5, pady=5)
        self.tl_txt_ent = ctk.CTkEntry(lbl_row, width=60, placeholder_text="Text")
        self.tl_txt_ent.pack(side="left", padx=5, pady=5)
        
        ctk.CTkButton(lbl_frame, text="Add Label", command=self.add_text_label).pack(fill="x", padx=10, pady=5)

        # Set Units
        units_frame = ctk.CTkFrame(self.left_scroll)
        units_frame.pack(fill="x", padx=10, pady=5)
        ctk.CTkLabel(units_frame, text="Units").pack(anchor="w", padx=10, pady=(5,0))
        
        units_row = ctk.CTkFrame(units_frame, fg_color="transparent")
        units_row.pack(fill="x", padx=5)
        self.unit_v_ent = ctk.CTkEntry(units_row, width=60, placeholder_text="Vol (L)")
        self.unit_v_ent.pack(side="left", padx=5, pady=5)
        self.unit_p_ent = ctk.CTkEntry(units_row, width=60, placeholder_text="Pr (atm)")
        self.unit_p_ent.pack(side="left", padx=5, pady=5)
        
        ctk.CTkButton(units_frame, text="Update Units", command=self.update_units).pack(fill="x", padx=10, pady=5)

    def _setup_mid_pane(self):
        ctk.CTkLabel(self.mid_pane, text="Active Items", font=ctk.CTkFont(size=20, weight="bold")).pack(pady=10)
        
        self.scroll_frame = ctk.CTkScrollableFrame(self.mid_pane)
        self.scroll_frame.pack(fill="both", expand=True, padx=10, pady=10)

        ctk.CTkLabel(self.mid_pane, text="Calculator", font=ctk.CTkFont(size=20, weight="bold")).pack(pady=(10, 0))
        self.calc_panel = CalculatorPanel(self.mid_pane, self.diagram)
        self.calc_panel.pack(fill="both", expand=True, padx=10, pady=10)

    def _setup_right_pane(self):
        self.fig, self.ax = plt.subplots(figsize=(5, 4))
        self.ax.set_xlabel("V (L)")
        self.ax.set_ylabel("P (atm)")
        self.ax.grid(True)
        self.fig.tight_layout()

        self.canvas = FigureCanvasTkAgg(self.fig, master=self.right_pane)
        self.canvas.get_tk_widget().grid(row=0, column=0, sticky="nsew", padx=5, pady=5)

        bottom_frame = ctk.CTkFrame(self.right_pane)
        bottom_frame.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)
        
        btn_frame = ctk.CTkFrame(bottom_frame, fg_color="transparent")
        btn_frame.pack(fill="x")
        ctk.CTkButton(btn_frame, text="Save .tex", command=self.save_file).pack(side="right", padx=10, pady=5)
        
        self.output = ctk.CTkTextbox(bottom_frame, font=ctk.CTkFont(family="Consolas", size=12))
        self.output.pack(fill="both", expand=True, padx=5, pady=5)

    def add_process(self):
        try:
            v1 = float(self.v1_ent.get())
            p1 = float(self.p1_ent.get())
            v2 = float(self.v2_ent.get())
            p2 = float(self.p2_ent.get())
            ptype = self.proc_type_var.get()
            lbl = self.p_lbl_ent.get()
            
            self.diagram.add_process(ptype, v1, p1, v2, p2, lbl)
            for widget in (self.v1_ent, self.p1_ent, self.v2_ent, self.p2_ent, self.p_lbl_ent):
                widget.delete(0, 'end')
            self.update_ui()
        except ValueError:
            messagebox.showerror("Error", "Invalid numbers for Process")

    def add_point(self):
        try:
            v = float(self.pt_v_ent.get())
            p = float(self.pt_p_ent.get())
            lbl = self.pt_lbl_ent.get()
            self.diagram.add_point(v, p, lbl)
            for widget in (self.pt_v_ent, self.pt_p_ent, self.pt_lbl_ent):
                widget.delete(0, 'end')
            self.update_ui()
        except ValueError:
            messagebox.showerror("Error", "Invalid numbers for Point")

    def add_shading(self):
        txt = self.shd_ent.get()
        if not txt:
            return
        stype = self.shd_type_var.get()
        slbl = self.shd_lbl_ent.get()
        try:
            pids = [int(x.strip()) for x in txt.replace(',', ' ').split()]
            valid_pids = [x for x in pids if x in self.diagram.processes]
            if valid_pids:
                self.diagram.add_shading(stype, valid_pids, slbl)
                for widget in (self.shd_ent, self.shd_lbl_ent):
                    widget.delete(0, 'end')
                self.update_ui()
            else:
                messagebox.showerror("Error", "No valid Process IDs found.")
        except Exception:
            messagebox.showerror("Error", "Invalid Process IDs format.")

    def add_text_label(self):
        try:
            v = float(self.tl_v_ent.get())
            p = float(self.tl_p_ent.get())
            txt = self.tl_txt_ent.get()
            if txt:
                self.diagram.add_text_label(v, p, txt)
                for widget in (self.tl_v_ent, self.tl_p_ent, self.tl_txt_ent):
                    widget.delete(0, 'end')
                self.update_ui()
        except ValueError:
            messagebox.showerror("Error", "Invalid numbers for Label location")

    def update_units(self):
        v_u = self.unit_v_ent.get()
        p_u = self.unit_p_ent.get()
        if v_u:
            self.diagram.unit_v = v_u
        if p_u:
            self.diagram.unit_p = p_u
        self.update_ui()

    def update_ui(self):
        # Refresh mid pane
        for widget in self.scroll_frame.winfo_children():
            widget.destroy()

        if self.diagram.points:
            ctk.CTkLabel(self.scroll_frame, text="Points", font=ctk.CTkFont(weight="bold")).pack(anchor="w", pady=(5,0))
            for pid, pt in self.diagram.points.items():
                f = ctk.CTkFrame(self.scroll_frame)
                f.pack(fill="x", pady=2)
                ctk.CTkLabel(f, text=f"Pt {pt.label}: ({pt.v}, {pt.p})").pack(side="left", padx=5)
                ctk.CTkButton(f, text="X", width=30, fg_color="red", hover_color="darkred", 
                              command=lambda p=pid: self.delete_point(p)).pack(side="right", padx=5, pady=2)

        if self.diagram.processes:
            ctk.CTkLabel(self.scroll_frame, text="Processes", font=ctk.CTkFont(weight="bold")).pack(anchor="w", pady=(10,0))
            for pid, proc in self.diagram.processes.items():
                f = ctk.CTkFrame(self.scroll_frame)
                f.pack(fill="x", pady=2)
                ctk.CTkLabel(f, text=f"({pid}) {proc.type}: {proc.p1.v}v->{proc.p2.v}v").pack(side="left", padx=5)
                ctk.CTkButton(f, text="X", width=30, fg_color="red", hover_color="darkred", 
                              command=lambda p=pid: self.delete_process(p)).pack(side="right", padx=5, pady=2)

        if hasattr(self.diagram, 'shadings') and self.diagram.shadings:
            ctk.CTkLabel(self.scroll_frame, text="Shadings", font=ctk.CTkFont(weight="bold")).pack(anchor="w", pady=(10,0))
            for sid, shd in self.diagram.shadings.items():
                f = ctk.CTkFrame(self.scroll_frame)
                f.pack(fill="x", pady=2)
                proc_str = ",".join(map(str, shd.process_ids))
                ctk.CTkLabel(f, text=f"[{shd.type}] Proc(s): {proc_str}").pack(side="left", padx=5)
                ctk.CTkButton(f, text="X", width=30, fg_color="red", hover_color="darkred", 
                              command=lambda s=sid: self.delete_shading(s)).pack(side="right", padx=5, pady=2)

        if hasattr(self.diagram, 'text_labels') and self.diagram.text_labels:
            ctk.CTkLabel(self.scroll_frame, text="Text Labels", font=ctk.CTkFont(weight="bold")).pack(anchor="w", pady=(10,0))
            for lid, tlbl in self.diagram.text_labels.items():
                f = ctk.CTkFrame(self.scroll_frame)
                f.pack(fill="x", pady=2)
                ctk.CTkLabel(f, text=f"'{tlbl.text}' at ({tlbl.v}, {tlbl.p})").pack(side="left", padx=5)
                ctk.CTkButton(f, text="X", width=30, fg_color="red", hover_color="darkred", 
                              command=lambda l=lid: self.delete_text_label(l)).pack(side="right", padx=5, pady=2)
                              
        # Update Calculator process list
        if hasattr(self, 'calc_panel'):
            self.calc_panel.update_process_list()

        self.update_plot()
        self.output.delete("0.0", "end")
        self.output.insert("end", self.diagram.generate())

    def delete_point(self, pid):
        self.diagram.delete_point(pid)
        self.update_ui()

    def delete_process(self, pid):
        self.diagram.delete_process(pid)
        self.update_ui()

    def delete_shading(self, sid):
        self.diagram.delete_shading(sid)
        self.update_ui()

    def delete_text_label(self, lid):
        self.diagram.delete_text_label(lid)
        self.update_ui()

    def update_plot(self):
        self.ax.clear()
        
        vu = self.diagram.unit_v if hasattr(self.diagram, 'unit_v') else "L"
        pu = self.diagram.unit_p if hasattr(self.diagram, 'unit_p') else "atm"
        self.ax.set_xlabel(f"V ({vu})")
        self.ax.set_ylabel(f"P ({pu})")
        self.ax.grid(True)
        
        self.ax.xaxis.set_major_locator(MultipleLocator(1))
        self.ax.yaxis.set_major_locator(MultipleLocator(1))

        if self.diagram.points:
            v_vals = [pt.v for pt in self.diagram.points.values()]
            p_vals = [pt.p for pt in self.diagram.points.values()]
            
            x_min = max(0, int(np.floor(min(v_vals))) - 1)
            x_max = int(np.ceil(max(v_vals))) + 1
            y_min = max(0, int(np.floor(min(p_vals))) - 1)
            y_max = int(np.ceil(max(p_vals))) + 1
            
            self.ax.set_xlim(left=x_min, right=x_max)
            self.ax.set_ylim(bottom=y_min, top=y_max)
        else:
            self.ax.set_xlim(left=0, right=10)
            self.ax.set_ylim(bottom=0, top=10)

        if hasattr(self.diagram, 'shadings'):
            for shd in self.diagram.shadings.values():
                xs, ys = [], []
                for pid in shd.process_ids:
                    if pid in self.diagram.processes:
                        proc = self.diagram.processes[pid]
                        vvals = np.linspace(proc.p1.v, proc.p2.v, 20)
                        if proc.type == "Isothermal":
                            c = proc.p1.v * proc.p1.p
                            pvals = c / vvals
                        elif proc.type == "Adiabatic":
                            gamma = 1.4
                            c = proc.p1.p * (proc.p1.v ** gamma)
                            pvals = c / (vvals ** gamma)
                        else:
                            pvals = np.linspace(proc.p1.p, proc.p2.p, 20)
                        xs.extend(vvals)
                        ys.extend(pvals)
                if xs and ys:
                    cv, cp = xs[:], ys[:]
                    if shd.type == "Under Curve":
                        cv.append(cv[-1])
                        cp.append(0)
                        cv.append(cv[0])
                        cp.append(0)
                    self.ax.fill(cv, cp, 'c', alpha=0.3, zorder=1)
                    if shd.label:
                        mid_v = sum(cv) / len(cv)
                        mid_p = sum(cp) / len(cp)
                        self.ax.text(mid_v, mid_p, f' {shd.label}', verticalalignment='center', horizontalalignment='center', zorder=6)

        for proc in self.diagram.processes.values():
            if proc.type in ["Isobaric", "Isochoric", "Linear"]:
                self.ax.plot([proc.p1.v, proc.p2.v], [proc.p1.p, proc.p2.p], 'b-', linewidth=2)
                
                # arrow
                mx = (proc.p1.v + proc.p2.v) / 2
                my = (proc.p1.p + proc.p2.p) / 2
                dx = proc.p2.v - proc.p1.v
                dy = proc.p2.p - proc.p1.p
                # normalize
                n = np.sqrt(dx**2 + dy**2)
                if n > 0:
                    dx, dy = dx/n, dy/n
                    self.ax.quiver(mx, my, dx, dy, color='b', scale=30, zorder=3)
            
            elif proc.type in ["Isothermal", "Adiabatic"]:
                v_min = min(proc.p1.v, proc.p2.v)
                v_max = max(proc.p1.v, proc.p2.v)
                vs = np.linspace(v_min, v_max, 100)
                
                if proc.type == "Isothermal":
                    c = proc.p1.v * proc.p1.p
                    ps = c / vs
                else:
                    gamma = 1.4
                    c = proc.p1.p * (proc.p1.v ** gamma)
                    ps = c / (vs ** gamma)
                
                self.ax.plot(vs, ps, 'b-', linewidth=2)
                
                idx = len(vs) // 2
                mx, my = vs[idx], ps[idx]
                
                if proc.p1.v < proc.p2.v:
                    dx = vs[idx+1] - vs[idx]
                    dy = ps[idx+1] - ps[idx]
                else:
                    dx = vs[idx-1] - vs[idx]
                    dy = ps[idx-1] - ps[idx]
                    
                n = np.sqrt(dx**2 + dy**2)
                if n > 0:
                    self.ax.quiver(mx, my, dx/n, dy/n, color='b', scale=30, zorder=3)

        for pt in self.diagram.points.values():
            self.ax.plot(pt.v, pt.p, 'ko', markersize=6, zorder=4)
            if pt.label:
                self.ax.text(pt.v, pt.p, f' {pt.label}', verticalalignment='bottom', horizontalalignment='left', zorder=5)

        if hasattr(self.diagram, 'text_labels'):
            for tlbl in self.diagram.text_labels.values():
                self.ax.text(tlbl.v, tlbl.p, tlbl.text, verticalalignment='center', horizontalalignment='center', zorder=6)

        self.fig.tight_layout()
        self.canvas.draw()

    def save_file(self):
        file = filedialog.asksaveasfilename(defaultextension=".tex", filetypes=[("LaTeX Files", "*.tex")])
        if file:
            with open(file, "w") as f:
                f.write(self.diagram.generate())
            messagebox.showinfo("Saved", f"Saved to {file}")

if __name__ == "__main__":
    root = ctk.CTk()
    app = PVApp(root)
    root.mainloop()