import sys
import os
import sqlite3
from PyQt5.QtWidgets import (
    QApplication, QWidget, QLabel, QLineEdit, QComboBox, QPushButton,
    QVBoxLayout, QHBoxLayout, QTableView, QHeaderView, QScrollArea, QMenu, QInputDialog, QAction  
)
from PyQt5.QtCore import Qt, QAbstractTableModel, QVariant, QModelIndex
from PyQt5.QtGui import QIcon
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib

matplotlib.use('Agg')  # Required for PyInstaller
import numpy as np
from collections import defaultdict


class CustomTableModel(QAbstractTableModel):
    def __init__(self, data, headers):
        super().__init__()
        self._data = data
        self.headers = headers

    def rowCount(self, parent=QModelIndex()):
        return len(self._data)

    def columnCount(self, parent=QModelIndex()):
        return len(self.headers)

    def data(self, index, role=Qt.DisplayRole):
        if role == Qt.DisplayRole:
            row = self._data[index.row()]
            return str(row[index.column()])
        return QVariant()

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if role == Qt.DisplayRole:
            if orientation == Qt.Horizontal:
                return str(self.headers[section])
            if orientation == Qt.Vertical:
                return str(section + 1)
        return QVariant()


class TransactionEntryApp(QWidget):
    def __init__(self):
        super().__init__()

        # Database setup
        self.db_path = self.get_db_path()
        self.db = self.connect_database()
        self.initialize_database()

        # UI setup
        self.subcategory_map = {
            'Despesas Gerais': ['Supermercado', 'Refeições Escolares', 'Telecomunicações', 'Vestuário', 'Impostos',
                                'Banco'],
            'Deslocação': ['Viatura 1', 'Viatura 2', 'Viatura 3', 'Transportes Públicos'],
            'Estética': ['Cabeleireiro', 'Depilação', 'Unhas'],
            'Formação': ['Actividades Extra-curriculares', 'Curos e Workshoops', 'Material Didático/ Equipamentos'],
            'Habitação': ['Seguros', 'Prestação', 'Impostos', 'Manutenção', 'Energia e Recursos', 'Condominio',
                          'Melhorias e Manutenção'],
            'Lazer': ['Restauração e Cafetaria', 'Férias', 'Hobbies', 'Actividades Lúdicas', 'Eventos Festivos'],
            'Saúde e Bem-estar': ['Consultas e Exames', 'Seguros', 'Farmácia', 'Equipamentos', 'Ginásio', 'Saúde Oral'],
            'Receitas': ['Ordenado', 'Comissões', 'Seguros', 'Aplicações Bancárias', 'Actividades Extra-profissionais']
        }

        self.subsubcategory_map = {
            'Viatura 1': ['Combustível', 'Seguro', 'Inspecção', 'Manutenção', 'Portagens', 'Impostos',
                                  'Multas', 'Estacionamento', 'Outra'],
            'Viatura 2': ['Combustível', 'Seguro', 'Inspecção', 'Manutenção', 'Portagens', 'Impostos',
                                   'Multas', 'Estacionamento', 'Outra'],
            'Viatura 3': ['Combustível', 'Seguro', 'Inspecção', 'Manutenção', 'Portagens', 'Impostos',
                                   'Multas', 'Estacionamento', 'Outra'],
            'Transportes Públicos': ['Autocarro', 'Comboio', 'Taxi/Uber', 'Metro', 'Barco', 'Outra'],
            'Outra': []
        }
        
        self.subsubcategory_map.update({
            'Seguros': ['Quarteira', 'Sobral'],
            'Prestação': ['Quarteira', 'Sobral'],
            'Impostos': ['Quarteira', 'Sobral'],
            'Manutenção': ['Quarteira', 'Sobral'],
            'Energia e Recursos': ['Quarteira', 'Sobral'],
            'Condominio': ['Quarteira', 'Sobral'],
            'Melhorias e Manutenção': ['Quarteira', 'Sobral'],
        })
        

        self.headers = ['data', 'valor', 'tipo', 'fornecedor', 'fundos', 'categoria', 'subcategoria', 'subsubcategoria']
        self.full_data = []

        self.init_ui()
        self.load_data()

    def get_db_path(self):
        """Get the correct database path for both development and executable"""
        if getattr(sys, 'frozen', False):
            # Use a safe, writable directory in user profile
            appdata_dir = os.path.join(os.path.expanduser("~"), ".budget_app")
            os.makedirs(appdata_dir, exist_ok=True)
            return os.path.join(appdata_dir, "budget.db")
        else:
            return "budget.db"
            
    def handle_type_change(self, text):
        if text == "Crédito":
            self.cmb_category.setCurrentText("Receitas")
            self.cmb_category.setDisabled(True)
            self.update_subcategory_items("Receitas")
        else:
            self.cmb_category.setDisabled(False)


    def connect_database(self):
        """Connect to SQLite database"""
        try:
            db = sqlite3.connect(self.db_path)
            print(f"Connected to database at: {self.db_path}")
            return db
        except Exception as e:
            print(f"Database connection failed: {e}")
            return None

    def initialize_database(self):
        """Create the table if it doesn't exist"""
        if self.db is not None:
            try:
                cursor = self.db.cursor()
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS Transactions (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        date TEXT,
                        value REAL,
                        type TEXT,
                        supplier TEXT,
                        funds TEXT,
                        category TEXT,
                        subcategory TEXT,
                        subsubcategory TEXT
                    )
                ''')
                self.db.commit()
                print("Database table initialized")
            except Exception as e:
                print(f"Error initializing database: {e}")

    def init_ui(self):
        self.setWindowIcon(QIcon("lili.ico"))

        # Inputs
        self.le_date = QLineEdit()
        self.le_date.setPlaceholderText("ex: 2505")
        self.le_value = QLineEdit()
        self.le_value.setPlaceholderText("valor sem a anotação do €")
        self.cmb_type = QComboBox()
        self.cmb_type.addItems(['Débito', 'Crédito'])
        self.cmb_type.currentTextChanged.connect(self.handle_type_change)
        self.le_supplier = QLineEdit()
        self.le_supplier.setPlaceholderText("Pingo Doce")
        self.cmb_funds = QComboBox()
        self.cmb_funds.addItems(
            ['Dinheiro', 'Conta Bancária 1', 'Conta Bancária 2', 'Conta Bancária 3', 'Conta Bancária 4', 'Conta Bancária 5',
             'Other'])
        self.cmb_category = QComboBox()
        self.cmb_category.addItems(list(self.subcategory_map.keys()))
        self.cmb_category.currentTextChanged.connect(self.update_subcategory_items)

        self.cmb_subcategory = QComboBox()
        self.update_subcategory_items(self.cmb_category.currentText())
        self.cmb_subcategory.currentTextChanged.connect(self.handle_subcategory_change)

        self.cmb_subsubcategory = QComboBox()

        self.btn_submit = QPushButton('Submeter')
        font = self.btn_submit.font()
        font.setBold(True)
        self.btn_submit.setFont(font)
        self.btn_submit.setStyleSheet("background-color: darkcyan;")
        self.btn_submit.clicked.connect(self.submit_data)

        self.lbl_message = QLabel('')
        self.lbl_message.setAlignment(Qt.AlignCenter)

        self.search_boxes = [QLineEdit() for _ in self.headers]
        for i, box in enumerate(self.search_boxes):
            box.setPlaceholderText(f'Search {self.headers[i]}')

        self.btn_search = QPushButton("Procurar")
        self.btn_search.clicked.connect(self.search_data)
        self.btn_reset = QPushButton("Reiniciar")
        self.btn_reset.clicked.connect(self.reset_search)

        self.lbl_sum = QLabel("Sum: 0.00")
        font = self.lbl_sum.font()
        font.setBold(True)
        self.lbl_sum.setFont(font)

        # Graph setup — initialize BEFORE using graph_canvas
        self.graph_canvas = FigureCanvas(Figure(figsize=(6, 3)))
        self.ax = self.graph_canvas.figure.add_subplot(111)

        # Set context menu for graph_canvas
        self.graph_canvas.setContextMenuPolicy(Qt.CustomContextMenu)
        self.graph_canvas.customContextMenuRequested.connect(self.show_legend_menu)
        self.legend_visible = False  # track legend state

        self.model = CustomTableModel([], self.headers)
        self.table_view = QTableView()
        self.table_view.setModel(self.model)
        self.table_view.setSortingEnabled(True)
        self.table_view.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table_view.customContextMenuRequested.connect(self.show_context_menu)
        header = self.table_view.horizontalHeader()
        header.setStretchLastSection(True)
        header.setSectionResizeMode(QHeaderView.Stretch)

        # Wrap canvas in scroll area
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidget(self.graph_canvas)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll_area.setMinimumHeight(200)

        # Define consistent colors for categories
        self.category_colors = {
            'Despesas Gerais': '#d399ff',
            'Deslocação': '#66B2FF',
            'Estética': '#FFCC99',
            'Formação': '#99FF99',
            'Habitação': '#c7c9c5',
            'Lazer': '#ffc099',
            'Saúde e Bem-estar': '#99FFFF',
            'Receitas': '#5fb83e'
        }

        # Layouts
        layout = QVBoxLayout()

        entry_layout = QHBoxLayout()
        entry_layout.addWidget(QLabel('Data:'))
        entry_layout.addWidget(self.le_date)
        entry_layout.addWidget(QLabel('Valor:'))
        entry_layout.addWidget(self.le_value)
        entry_layout.addWidget(QLabel('Fornecedor:'))
        entry_layout.addWidget(self.le_supplier)
        layout.addLayout(entry_layout)

        combo_layout = QHBoxLayout()
        combo_layout.addWidget(self.cmb_type)
        combo_layout.addWidget(self.cmb_funds)
        combo_layout.addWidget(self.cmb_category)
        combo_layout.addWidget(self.cmb_subcategory)
        layout.addLayout(combo_layout)

        subsub_layout = QHBoxLayout()
        subsub_layout.addWidget(QLabel(''))
        subsub_layout.addWidget(self.cmb_subsubcategory)
        layout.addLayout(subsub_layout)

        submit_layout = QHBoxLayout()
        submit_layout.addWidget(self.btn_submit)
        layout.addLayout(submit_layout)

        layout.addWidget(self.lbl_message)

        search_layout = QHBoxLayout()
        for box in self.search_boxes:
            search_layout.addWidget(box)
        layout.addLayout(search_layout)

        btn_layout = QHBoxLayout()
        btn_layout.addWidget(self.btn_search)
        btn_layout.addWidget(self.btn_reset)
        btn_layout.addStretch()
        btn_layout.addWidget(self.lbl_sum)
        layout.addLayout(btn_layout)

        layout.addWidget(self.table_view)
        layout.addWidget(self.scroll_area)

        self.setLayout(layout)
        self.setWindowTitle('Budget das contas certas')
        self.setGeometry(400, 50, 1000, 940)
        self.show()


    def update_subcategory_items(self, category):
        self.cmb_subcategory.clear()
        if category in self.subcategory_map:
            items = self.subcategory_map[category] + ['Outra']
            self.cmb_subcategory.addItems(items)

    def update_subsubcategory_items(self, subcategory):
        self.cmb_subsubcategory.clear()
        items = self.subsubcategory_map.get(subcategory, [])
        self.cmb_subsubcategory.addItems(items if items else ['N/A'])
        
    def handle_subcategory_change(self, subcategory):
        if subcategory == 'Outra':
            category = self.cmb_category.currentText()
            text, ok = QInputDialog.getText(self, 'Nova Subcategoria', 'Digite o nome da nova subcategoria:')
            if ok and text.strip():
                new_sub = text.strip()
                # Update internal map
                if category in self.subcategory_map:
                    self.subcategory_map[category].append(new_sub)
                    # Refresh the items
                    self.update_subcategory_items(category)
                    self.cmb_subcategory.setCurrentText(new_sub)
        else:
            self.update_subsubcategory_items(subcategory)

    def submit_data(self):
        if not self.db:
            self.lbl_message.setText("No DB connection")
            return
        try:
            value = float(self.le_value.text())
        except ValueError:
            self.lbl_message.setText("Invalid value")
            return

        data = (
            self.le_date.text().strip(),
            value,
            self.cmb_type.currentText(),
            self.le_supplier.text().strip(),
            self.cmb_funds.currentText(),
            self.cmb_category.currentText(),
            self.cmb_subcategory.currentText(),
            self.cmb_subsubcategory.currentText()
        )

        try:
            cursor = self.db.cursor()
            cursor.execute("""
                INSERT INTO Transactions 
                (date, value, type, supplier, funds, category, subcategory, subsubcategory)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, data)
            self.db.commit()
            self.lbl_message.setText("Transaction submitted.")
            self.le_date.clear()
            self.le_value.clear()
            self.le_supplier.clear()
            self.load_data()
        except Exception as e:
            self.lbl_message.setText(f"Error: {e}")

    def load_data(self):
        if not self.db:
            self.lbl_message.setText("No database connection")
            return
        try:
            cursor = self.db.cursor()
            cursor.execute(
                "SELECT date, value, type, supplier, funds, category, subcategory, subsubcategory FROM Transactions ORDER BY id DESC")
            data = cursor.fetchall()
            self.full_data = [tuple(item) for item in data]
            self.apply_filter()
            self.plot_graph()
        except Exception as e:
            self.lbl_message.setText(f"Error loading data: {str(e)}")
            print(f"Database error: {str(e)}")

    
    def show_context_menu(self, position):
        index = self.table_view.indexAt(position)
        if index.isValid():
            menu = QMenu()
            delete_action = menu.addAction("Delete Row")
            action = menu.exec_(self.table_view.mapToGlobal(position))
            if action == delete_action:
                self.delete_row(index.row())


    def delete_row(self, row):
        id_query = "SELECT id FROM Transactions ORDER BY id DESC LIMIT 1 OFFSET ?"
        cursor = self.db.cursor()
        cursor.execute(id_query, (row,))
        row_id = cursor.fetchone()
        if row_id:
            cursor.execute("DELETE FROM Transactions WHERE id=?", (row_id[0],))
            self.db.commit()
            self.load_data()
    
    
    def apply_filter(self):
        filters = [box.text().strip().lower() for box in self.search_boxes]
        filtered = [row for row in self.full_data if all(f in str(row[i]).lower() for i, f in enumerate(filters) if f)]
        self.model._data = filtered
        self.model.layoutChanged.emit()
        self.update_sum(filtered)

    def search_data(self):
        self.apply_filter()

    def reset_search(self):
        for box in self.search_boxes:
            box.clear()
        self.apply_filter()

    def update_sum(self, data):
        total = 0
        for row in data:
            try:
                val = float(row[1])
                ttype = row[2].lower()
                total += val if ttype == 'credit' else -val
            except:
                pass
        self.lbl_sum.setText(f"TOTAL: {total:.2f}")

    def plot_graph(self):
        monthly_data = defaultdict(lambda: defaultdict(float))
        for row in self.full_data:
            try:
                month = row[0][:7]
                value = float(row[1])
                category = row[5]
                monthly_data[month][category] += value
            except:
                continue

        months = sorted(monthly_data.keys())
        all_categories = set()
        for month_data in monthly_data.values():
            all_categories.update(month_data.keys())
        all_categories.discard('Receitas')

        categories = sorted(all_categories)
        expenses_data = {cat: [] for cat in categories}
        receitas_data = []

        for month in months:
            receitas_data.append(monthly_data[month].get('Receitas', 0))
            for cat in categories:
                expenses_data[cat].append(monthly_data[month].get(cat, 0))

        self.ax.clear()
        x = np.arange(len(months))
        fixed_bar_width = 0.4

        min_fig_width = 6
        inch_per_month = 0.6
        fig_width = max(min_fig_width, inch_per_month * len(months))
        self.graph_canvas.figure.set_size_inches(fig_width, 3)
        dpi = self.graph_canvas.figure.get_dpi()
        self.graph_canvas.resize(int(fig_width * dpi), int(3 * dpi))

        # Plot credit (Receitas) bars
        self.ax.bar(x - fixed_bar_width / 2, receitas_data, fixed_bar_width,
                    color=self.category_colors.get('Receitas', '#77DA99'), label='Receitas')

        # Plot stacked debit (Despesas) bars
        bottom = np.zeros(len(months))
        total_debits = np.zeros(len(months))
        for cat in categories:
            values = expenses_data[cat]
            if sum(values) > 0:
                self.ax.bar(x + fixed_bar_width / 2, values, fixed_bar_width,
                            bottom=bottom,
                            color=self.category_colors.get(cat, '#CCCCCC'),
                            label=cat)
                bottom += np.array(values)
                total_debits += np.array(values)

        self.ax.set_xticks(x)
        # Add sum labels on top of stacked debits
        for i, val in enumerate(total_debits):
            if val > 0:
                self.ax.text(x[i] + fixed_bar_width / 2, val + 2, f"{val:.0f}",
                             ha='center', va='bottom', fontsize=8, color='black')
                             
        # Add sum labels on top of stacked credits
        for i, val in enumerate(receitas_data):
            if val > 0:
                self.ax.text(x[i] - fixed_bar_width / 2, val + 2, f"{val:.0f}",
                             ha='center', va='bottom', fontsize=8, color='black')


        self.ax.set_xticks(x)
        self.ax.set_xticklabels(months, rotation=20)
        self.ax.set_title("Gráfico Receitas vs Despesas")
        self.ax.set_xlabel("Data")
        self.ax.set_ylabel("Soma")
        self.ax.legend(loc='upper center', bbox_to_anchor=(0.5, -0.15),
               fontsize='x-small', ncol=3, frameon=False)
        self.ax.grid(True, axis='y', linestyle='--', alpha=0.8)

        # Adjust y-axis limit to add headroom
        max_receita = max(receitas_data) if receitas_data else 0
        max_debito = max(total_debits) if total_debits.any() else 0
        self.ax.set_ylim(0, max(max_receita, max_debito) * 1.2)

        self.graph_canvas.draw()
        
    def show_legend_menu(self, pos):
        menu = QMenu()
        action_toggle_legend = QAction("Toggle Legend", self)
        action_toggle_legend.triggered.connect(self.toggle_legend)
        menu.addAction(action_toggle_legend)
        menu.exec_(self.graph_canvas.mapToGlobal(pos))

    def toggle_legend(self):
        # If legend visible, remove it
        if self.legend_visible:
            leg = self.ax.get_legend()
            if leg:
                leg.remove()
            self.legend_visible = False
        else:
            # Show legend at the top center inside the plot
            self.ax.legend(loc='upper center', bbox_to_anchor=(0.5, 1.05), ncol=3, fancybox=True, shadow=True)
            self.legend_visible = True

        self.graph_canvas.draw_idle()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = TransactionEntryApp()
    sys.exit(app.exec_())