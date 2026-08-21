import math
import re
import csv
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

import matplotlib
matplotlib.use('TkAgg')
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk

APP_TITLE = 'Hill Curve Estimator — Single Stage'


def parse_number(text: str) -> float:
    s = text.strip().replace('%', '').replace(' ', '')
    if ',' in s and '.' in s:
        if s.rfind(',') > s.rfind('.'):
            s = s.replace('.', '').replace(',', '.')
        else:
            s = s.replace(',', '')
    elif ',' in s:
        s = s.replace(',', '.')
    return float(s)


def parse_elongation(text: str) -> float:
    val = parse_number(text)
    return val / 100.0 if '%' in text or val > 1.0 else val


def hill_n(E, fy, fu, eps_max):
    if E <= 0 or fy <= 0 or fu <= fy:
        raise ValueError('Require E > 0 and UTS > yield > 0.')
    z = (eps_max - fu / E) / 0.002
    if z <= 0:
        raise ValueError('Maximum elongation must be greater than fu/E.')
    return math.log(z) / math.log(fu / fy)


def hill_curve(E, fy, fu, eps_max, n, points=200):
    if points < 20:
        raise ValueError('Use at least 20 curve points.')
    eng_stress = [fu * i / (points - 1) for i in range(points)]
    eng_strain = [s / E + 0.002 * (s / fy) ** n for s in eng_stress]
    true_stress = [s * (1.0 + e) for s, e in zip(eng_stress, eng_strain)]
    true_strain = [math.log(1.0 + e) for e in eng_strain]
    true_plastic = [et - ts / E for et, ts in zip(true_strain, true_stress)]
    return eng_stress, eng_strain, true_stress, true_strain, true_plastic, n


def parse_test_data(text):
    data = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        parts = re.split(r'\t|;', line)
        if len(parts) < 2:
            parts = re.split(r'\s+', line)
        if len(parts) < 2:
            continue
        try:
            data.append((parse_number(parts[0]), parse_number(parts[1])))
        except ValueError:
            pass
    return data


def fmt(x):
    return f'{x:.12g}'


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(APP_TITLE)
        self.geometry('1400x850')
        self.minsize(1150, 720)
        self.test_data = []
        self.curve = None
        self._build_ui()
        self._defaults()
        self.calculate()

    def _build_ui(self):
        self.columnconfigure(0, weight=0)
        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=1)

        left = ttk.Frame(self, padding=12)
        left.grid(row=0, column=0, sticky='nsw')
        right = ttk.Frame(self, padding=(0, 12, 12, 12))
        right.grid(row=0, column=1, sticky='nsew')
        right.rowconfigure(1, weight=1)
        right.columnconfigure(0, weight=1)

        ttk.Label(left, text='Hill Single-Stage Model', font=('Segoe UI', 16, 'bold')).grid(row=0, column=0, columnspan=2, sticky='w', pady=(0, 12))
        ttk.Label(left, text='Material inputs', font=('Segoe UI', 11, 'bold')).grid(row=1, column=0, columnspan=2, sticky='w')

        self.entries = {}
        fields = [
            ('E', "Young's modulus [MPa]"),
            ('fy', 'Yield / 0.2% proof [MPa]'),
            ('fu', 'UTS [MPa]'),
            ('elong', 'Maximum elongation [0.02 or 2%]'),
            ('points', 'Estimated curve points'),
        ]
        for i, (key, label) in enumerate(fields, start=2):
            ttk.Label(left, text=label).grid(row=i, column=0, sticky='w', pady=4)
            entry = ttk.Entry(left, width=18)
            entry.grid(row=i, column=1, sticky='ew', padx=(10, 0), pady=4)
            self.entries[key] = entry

        ttk.Label(left, text='Calculated parameters', font=('Segoe UI', 11, 'bold')).grid(row=8, column=0, columnspan=2, sticky='w', pady=(10, 4))
        self.n_var = tk.StringVar(value='—')
        self.status_var = tk.StringVar(value='Ready')
        ttk.Label(left, text='Hill exponent n').grid(row=9, column=0, sticky='w', pady=3)
        ttk.Label(left, textvariable=self.n_var, font=('Segoe UI', 10, 'bold')).grid(row=9, column=1, sticky='e')
        ttk.Label(left, text='Status').grid(row=10, column=0, sticky='w', pady=3)
        ttk.Label(left, textvariable=self.status_var).grid(row=10, column=1, sticky='e')

        ttk.Button(left, text='Calculate / Update Plot', command=self.calculate).grid(row=11, column=0, columnspan=2, sticky='ew', pady=(8, 3))
        ttk.Button(left, text='Save Plot', command=self.save_plot).grid(row=12, column=0, columnspan=2, sticky='ew', pady=3)
        ttk.Button(left, text='Export Estimated Curve CSV', command=self.export_curve).grid(row=13, column=0, columnspan=2, sticky='ew', pady=3)

        ttk.Separator(left).grid(row=14, column=0, columnspan=2, sticky='ew', pady=10)
        ttk.Label(left, text='Test data', font=('Segoe UI', 11, 'bold')).grid(row=15, column=0, columnspan=2, sticky='w')
        ttk.Label(left, text='Paste: True Strain [mm/mm]  |  True Stress [MPa]').grid(row=16, column=0, columnspan=2, sticky='w', pady=4)
        self.test_text = tk.Text(left, width=42, height=14, font=('Consolas', 9), wrap='none')
        self.test_text.grid(row=17, column=0, columnspan=2)
        ttk.Button(left, text='Plot Test Data', command=self.load_test).grid(row=18, column=0, columnspan=2, sticky='ew', pady=5)
        ttk.Button(left, text='Clear Test Data', command=self.clear_test).grid(row=19, column=0, columnspan=2, sticky='ew')

        ttk.Label(right, text='True Stress–Strain Comparison', font=('Segoe UI', 13, 'bold')).grid(row=0, column=0, sticky='w', pady=(0, 6))
        self.fig = Figure(figsize=(8.5, 6), dpi=100)
        self.ax = self.fig.add_subplot(111)
        self.canvas = FigureCanvasTkAgg(self.fig, master=right)
        self.canvas.get_tk_widget().grid(row=1, column=0, sticky='nsew')
        toolbar = NavigationToolbar2Tk(self.canvas, right, pack_toolbar=False)
        toolbar.update()
        toolbar.grid(row=2, column=0, sticky='ew')
        ttk.Label(right, text='Hill: ε = σ/E + 0.002(σ/fy)^n   |   Test data: True Strain / True Stress').grid(row=3, column=0, sticky='w', pady=(6, 0))

        # Material card tab in right panel
        self.tabs = ttk.Notebook(right)
        self.tabs.grid(row=4, column=0, sticky='nsew', pady=(10, 0))
        right.rowconfigure(4, weight=0)
        card_frame = ttk.Frame(self.tabs, padding=8)
        self.tabs.add(card_frame, text='Abaqus Material Card')
        card_frame.columnconfigure(0, weight=1)
        card_frame.rowconfigure(1, weight=1)
        top = ttk.Frame(card_frame)
        top.grid(row=0, column=0, sticky='ew', pady=(0, 5))
        ttk.Label(top, text='Material name:').pack(side='left')
        self.material_name = ttk.Entry(top, width=28)
        self.material_name.pack(side='left', padx=6)
        self.material_name.insert(0, 'HILL_MATERIAL')
        ttk.Button(top, text='Update from Inputs', command=self.update_card).pack(side='left', padx=4)
        ttk.Button(top, text='Export .inp', command=self.export_inp).pack(side='left', padx=4)
        ttk.Button(top, text='Copy Card', command=self.copy_card).pack(side='left', padx=4)
        self.card_text = tk.Text(card_frame, height=12, font=('Consolas', 9), wrap='none', undo=True)
        self.card_text.grid(row=1, column=0, sticky='nsew')
        ttk.Label(card_frame, text='Editable. The exported file contains the material definition exactly as shown here.').grid(row=2, column=0, sticky='w', pady=(5, 0))

    def _defaults(self):
        for key, value in {'E': '72900', 'fy': '117', 'fu': '265', 'elong': '0.02', 'points': '200'}.items():
            self.entries[key].insert(0, value)

    def get_inputs(self):
        E = parse_number(self.entries['E'].get())
        fy = parse_number(self.entries['fy'].get())
        fu = parse_number(self.entries['fu'].get())
        eps_max = parse_elongation(self.entries['elong'].get())
        points = int(parse_number(self.entries['points'].get()))
        return E, fy, fu, eps_max, points

    def calculate(self):
        try:
            E, fy, fu, eps_max, points = self.get_inputs()
            n = hill_n(E, fy, fu, eps_max)
            self.curve = hill_curve(E, fy, fu, eps_max, n, points)
            self.n_var.set(f'{n:.5f}')
            self.status_var.set('Calculated')
            self.redraw()
            self.update_card()
        except Exception as exc:
            self.status_var.set('Input error')
            messagebox.showerror('Calculation error', str(exc))

    def redraw(self):
        self.ax.clear()
        self.ax.grid(True, alpha=0.25)
        self.ax.set_xlabel('True Strain')
        self.ax.set_ylabel('True Stress [MPa]')
        if self.curve:
            _, _, ts, te, _, n = self.curve
            self.ax.plot(te, ts, linewidth=2.5, label=f'Hill estimate (n = {n:.3f})')
        if self.test_data:
            x = [p[0] for p in self.test_data]
            y = [p[1] for p in self.test_data]
            self.ax.plot(x, y, linewidth=1.8, marker='o', markersize=3, markevery=max(1, len(x)//80), label=f'Test data ({len(x)} pts)')
        if self.curve or self.test_data:
            self.ax.legend()
        self.fig.tight_layout()
        self.canvas.draw_idle()

    def load_test(self):
        data = parse_test_data(self.test_text.get('1.0', 'end'))
        if len(data) < 2:
            messagebox.showwarning('Test data', 'Paste at least two numeric rows with True Strain in column 1 and True Stress in column 2.')
            return
        self.test_data = data
        self.status_var.set(f'Test data loaded: {len(data)} points')
        self.redraw()

    def clear_test(self):
        self.test_data = []
        self.test_text.delete('1.0', 'end')
        self.status_var.set('Test data cleared')
        self.redraw()

    def update_card(self):
        if not self.curve:
            return
        try:
            E, fy, fu, eps_max, points = self.get_inputs()
            n = self.curve[4]
            # Abaqus *PLASTIC expects true stress and true plastic strain.
            # Start with a small positive plastic strain at yield, then generated points.
            ts = self.curve[2]
            tp = self.curve[4]
            rows = []
            # Use points from yield onward, avoiding the zero row and duplicate/negative plastic values.
            for stress, plastic in zip(ts, tp):
                if stress + 1e-10 >= fy and plastic >= -1e-12:
                    rows.append((stress, max(0.0, plastic)))
            # Ensure yield point is present and monotonic plastic strain.
            if not rows or abs(rows[0][0] - fy) > max(1e-6, fy*1e-5):
                eng_strain_y = fy / E + 0.002
                true_stress_y = fy * (1 + eng_strain_y)
                true_strain_y = math.log(1 + eng_strain_y)
                true_plastic_y = max(0.0, true_strain_y - true_stress_y / E)
                rows.insert(0, (true_stress_y, true_plastic_y))
            clean = []
            last_p = -1e100
            for s, p in rows:
                if p + 1e-12 >= last_p:
                    clean.append((s, p)); last_p = p
            name = self.material_name.get().strip() or 'HILL_MATERIAL'
            card = [f'*MATERIAL, NAME={name}', '**', '** Hill single-stage approximation', f'** E = {fmt(E)} MPa, Yield = {fmt(fy)} MPa, UTS = {fmt(fu)} MPa, Elongation = {fmt(eps_max)}', f'** Hill exponent n = {fmt(n)}', '** Units must be consistent with the Abaqus model.', '*ELASTIC', f'{fmt(E)}, 0.3', '*PLASTIC']
            card += [f'{fmt(s)}, {fmt(p)}' for s, p in clean]
            self.card_text.delete('1.0', 'end')
            self.card_text.insert('1.0', '\n'.join(card) + '\n')
        except Exception:
            pass

    def get_card(self):
        return self.card_text.get('1.0', 'end-1c')

    def export_inp(self):
        content = self.get_card().strip()
        if not content:
            messagebox.showwarning('Abaqus material card', 'The material card is empty.')
            return
        path = filedialog.asksaveasfilename(defaultextension='.inp', filetypes=[('Abaqus input file', '*.inp'), ('Text file', '*.txt')], initialfile=(self.material_name.get().strip() or 'HILL_MATERIAL') + '.inp')
        if path:
            try:
                with open(path, 'w', encoding='utf-8', newline='') as f:
                    f.write(content + '\n')
                messagebox.showinfo('Export complete', f'Material definition exported to:\n{path}')
            except OSError as exc:
                messagebox.showerror('Export error', str(exc))

    def copy_card(self):
        content = self.get_card()
        self.clipboard_clear()
        self.clipboard_append(content)
        self.update()
        messagebox.showinfo('Copied', 'Material card copied to the clipboard.')

    def save_plot(self):
        path = filedialog.asksaveasfilename(defaultextension='.png', filetypes=[('PNG image', '*.png'), ('PDF', '*.pdf'), ('SVG', '*.svg')])
        if path:
            self.fig.savefig(path, dpi=250, bbox_inches='tight')

    def export_curve(self):
        if not self.curve:
            return
        path = filedialog.asksaveasfilename(defaultextension='.csv', filetypes=[('CSV', '*.csv')])
        if not path:
            return
        eng_s, eng_e, true_s, true_e, true_p, _ = self.curve
        with open(path, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.writer(f)
            writer.writerow(['Engineering Strain', 'Engineering Stress [MPa]', 'True Strain', 'True Stress [MPa]', 'True Plastic Strain'])
            writer.writerows(zip(eng_e, eng_s, true_e, true_s, true_p))
        messagebox.showinfo('Export complete', f'Estimated curve saved to:\n{path}')


if __name__ == '__main__':
    App().mainloop()
