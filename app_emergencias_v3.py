import serial
import serial.tools.list_ports
import mysql.connector
import time
import threading
import customtkinter as ctk
from tkinter import messagebox  

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

BAUD_RATE = 115200

DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': '12345',
    'database': 'emergencias_nfc'
}

class SistemaEmergenciasApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Sistema de Gestión de Emergencias Médicas")
        self.geometry("650x600")
        self.resizable(False, False)

        self.conexion_db = self.conectar_bd()
        self.ser = None
        self.ejecutando_serial = False
        
        self.uid_actual = None
        self.paciente_actual = None
        self.modo_edicion = False

        self.configurar_interfaz()

    def conectar_bd(self):
        try:
            return mysql.connector.connect(**DB_CONFIG)
        except mysql.connector.Error as err:
            messagebox.showerror("Error de Base de Datos", f"No se pudo conectar: {err}")
            return None

    def obtener_puertos(self):
        puertos = serial.tools.list_ports.comports()
        lista_puertos = [puerto.device for puerto in puertos]
        return lista_puertos if lista_puertos else ["Sin puertos"]

    def configurar_interfaz(self):
        self.lbl_titulo = ctk.CTkLabel(self, text="Control de Acceso Médico", font=ctk.CTkFont(size=24, weight="bold"))
        self.lbl_titulo.pack(pady=(15, 5))

        self.frame_conexion = ctk.CTkFrame(self)
        self.frame_conexion.pack(fill="x", padx=20, pady=5)

        ctk.CTkLabel(self.frame_conexion, text="Puerto Serial:").pack(side="left", padx=(10, 5), pady=10)

        self.combo_puertos = ctk.CTkOptionMenu(self.frame_conexion, values=self.obtener_puertos())
        self.combo_puertos.pack(side="left", padx=5, pady=10)

        self.btn_actualizar_puertos = ctk.CTkButton(self.frame_conexion, text="↻ Actualizar", width=80, fg_color="gray", command=self.actualizar_puertos)
        self.btn_actualizar_puertos.pack(side="left", padx=5, pady=10)

        self.btn_conectar = ctk.CTkButton(self.frame_conexion, text="Conectar", width=100, command=self.toggle_conexion)
        self.btn_conectar.pack(side="right", padx=10, pady=10)

        self.lbl_estado = ctk.CTkLabel(self, text="Sistema en pausa. Por favor, conecte un lector NFC.", text_color="gray")
        self.lbl_estado.pack(pady=(5, 10))

        self.contenedor = ctk.CTkFrame(self)
        self.contenedor.pack(fill="both", expand=True, padx=20, pady=(0, 20))

        self.frame_espera = ctk.CTkFrame(self.contenedor, fg_color="transparent")
        self.lbl_espera_texto = ctk.CTkLabel(self.frame_espera, text="Esperando conexión...", font=ctk.CTkFont(size=18))
        self.lbl_espera_texto.pack(expand=True)

        self.frame_datos = ctk.CTkFrame(self.contenedor, fg_color="transparent")
        self.datos_labels = {}
        campos = ["Nombre Completo", "Tipo de Sangre", "Alergias", "Condiciones", "Contacto de Emergencia"]
        
        for campo in campos:
            lbl_tit = ctk.CTkLabel(self.frame_datos, text=campo + ":", font=ctk.CTkFont(weight="bold"))
            lbl_tit.pack(anchor="w", pady=(5, 0), padx=20)
            
            lbl_val = ctk.CTkLabel(self.frame_datos, text="-", font=ctk.CTkFont(size=14))
            lbl_val.pack(anchor="w", padx=20)
            self.datos_labels[campo] = lbl_val

        self.frame_acciones = ctk.CTkFrame(self.frame_datos, fg_color="transparent")
        self.frame_acciones.pack(pady=20)

        self.btn_cerrar = ctk.CTkButton(self.frame_acciones, text="Cerrar", fg_color="gray", width=120, command=self.mostrar_espera)
        self.btn_cerrar.pack(side="left", padx=10)

        self.btn_editar = ctk.CTkButton(self.frame_acciones, text="Editar", width=120, command=self.preparar_edicion)
        self.btn_editar.pack(side="left", padx=10)

        self.btn_eliminar = ctk.CTkButton(self.frame_acciones, text="Eliminar", fg_color="#8B0000", hover_color="#5C0000", width=120, command=self.eliminar_paciente)
        self.btn_eliminar.pack(side="left", padx=10)

        self.frame_registro = ctk.CTkFrame(self.contenedor, fg_color="transparent")
        self.lbl_titulo_registro = ctk.CTkLabel(self.frame_registro, text="Registrar Nuevo Paciente", font=ctk.CTkFont(size=18, weight="bold"))
        self.lbl_titulo_registro.pack(pady=10)

        self.entradas = {}
        campos_reg = ["Nombre Completo", "Tipo de Sangre", "Alergias", "Condiciones Médicas", "Contacto Emergencia"]
        
        for campo in campos_reg:
            entry = ctk.CTkEntry(self.frame_registro, placeholder_text=campo, width=400)
            entry.pack(pady=5)
            self.entradas[campo] = entry

        self.btn_guardar = ctk.CTkButton(self.frame_registro, text="Guardar Información", command=self.guardar_registro)
        self.btn_guardar.pack(pady=15)
        
        self.btn_cancelar = ctk.CTkButton(self.frame_registro, text="Cancelar", fg_color="gray", command=self.mostrar_espera)
        self.btn_cancelar.pack()

        self.mostrar_espera()

    def actualizar_puertos(self):
        puertos = self.obtener_puertos()
        self.combo_puertos.configure(values=puertos)
        if puertos and puertos[0] != "Sin puertos":
            self.combo_puertos.set(puertos[0])
        else:
            self.combo_puertos.set("Sin puertos")

    def toggle_conexion(self):
        if self.ejecutando_serial:
            self.desconectar_serial()
        else:
            self.conectar_serial()

    def conectar_serial(self):
        puerto_seleccionado = self.combo_puertos.get()
        if puerto_seleccionado == "Sin puertos" or not puerto_seleccionado:
            messagebox.showwarning("Advertencia", "No hay puertos disponibles seleccionados.")
            return

        try:
            self.ser = serial.Serial(puerto_seleccionado, BAUD_RATE, timeout=1)
            self.ser.flushInput()
            self.ejecutando_serial = True
            
            self.btn_conectar.configure(text="Desconectar", fg_color="#8B0000", hover_color="#5C0000")
            self.combo_puertos.configure(state="disabled")
            self.btn_actualizar_puertos.configure(state="disabled")
            
            self.mostrar_espera()
            
            threading.Thread(target=self.leer_serial, daemon=True).start()
            
        except serial.SerialException as e:
            messagebox.showerror("Error de Conexión", f"No se pudo abrir el puerto {puerto_seleccionado}.\nVerifique que no esté en uso por otro programa (ej. Arduino IDE).")
            self.desconectar_serial()

    def desconectar_serial(self):
        self.ejecutando_serial = False
        if self.ser and self.ser.is_open:
            self.ser.close()
            
        self.btn_conectar.configure(text="Conectar", fg_color=["#3a7ebf", "#1f538d"], hover_color=["#325882", "#14375e"])
        self.combo_puertos.configure(state="normal")
        self.btn_actualizar_puertos.configure(state="normal")
        
        self.mostrar_espera()

    def leer_serial(self):
        while self.ejecutando_serial:
            try:
                if self.ser and self.ser.in_waiting > 0:
                    linea = self.ser.readline().decode('utf-8', errors='ignore').strip()
                    if linea.startswith("UID:"):
                        uid = linea.split(":")[1].strip()
                        self.after(0, self.procesar_uid, uid)
            except serial.SerialException:
                self.after(0, self.desconectar_serial)
                self.after(0, lambda: messagebox.showerror("Desconexión", "El dispositivo fue desconectado inesperadamente."))
                break
            time.sleep(0.1)

    def mostrar_espera(self):
        self.frame_datos.pack_forget()
        self.frame_registro.pack_forget()
        self.frame_espera.pack(fill="both", expand=True)
        
        self.uid_actual = None
        self.paciente_actual = None
        self.modo_edicion = False

        if self.ejecutando_serial:
            self.lbl_estado.configure(text=f"Escuchando en {self.combo_puertos.get()}...", text_color="green")
            self.lbl_espera_texto.configure(text="Acerque la tarjeta NFC al lector")
        else:
            self.lbl_estado.configure(text="Sistema en pausa. Por favor, conecte un lector NFC.", text_color="gray")
            self.lbl_espera_texto.configure(text="Seleccione un puerto y haga clic en Conectar")

    def mostrar_datos(self, paciente):
        self.paciente_actual = paciente
        self.frame_espera.pack_forget()
        self.frame_registro.pack_forget()
        
        self.datos_labels["Nombre Completo"].configure(text=paciente['nombre_completo'])
        self.datos_labels["Tipo de Sangre"].configure(text=paciente['tipo_sangre'])
        self.datos_labels["Alergias"].configure(text=paciente['alergias'])
        self.datos_labels["Condiciones"].configure(text=paciente['condiciones_medicas'])
        self.datos_labels["Contacto de Emergencia"].configure(text=paciente['contacto_emergencia'])

        self.lbl_estado.configure(text="Alerta Médica Activa", text_color="red")
        self.frame_datos.pack(fill="both", expand=True)

    def mostrar_registro(self, uid):
        self.uid_actual = uid
        self.modo_edicion = False
        self.lbl_titulo_registro.configure(text="Registrar Nuevo Paciente")
        self.frame_espera.pack_forget()
        self.frame_datos.pack_forget()
        
        for entry in self.entradas.values():
            entry.delete(0, 'end')
            
        self.lbl_estado.configure(text=f"UID No Registrado: {uid}", text_color="orange")
        self.frame_registro.pack(fill="both", expand=True)

    def preparar_edicion(self):
        self.modo_edicion = True
        self.lbl_titulo_registro.configure(text="Editar Datos del Paciente")
        self.frame_datos.pack_forget()
        
        for entry in self.entradas.values():
            entry.delete(0, 'end')
            
        self.entradas["Nombre Completo"].insert(0, self.paciente_actual['nombre_completo'])
        self.entradas["Tipo de Sangre"].insert(0, self.paciente_actual['tipo_sangre'])
        self.entradas["Alergias"].insert(0, self.paciente_actual['alergias'])
        self.entradas["Condiciones Médicas"].insert(0, self.paciente_actual['condiciones_medicas'])
        self.entradas["Contacto Emergencia"].insert(0, self.paciente_actual['contacto_emergencia'])

        self.lbl_estado.configure(text="Modo Edición", text_color="cyan")
        self.frame_registro.pack(fill="both", expand=True)

    def eliminar_paciente(self):
        respuesta = messagebox.askyesno("Confirmar Eliminación", f"¿Está seguro que desea eliminar a {self.paciente_actual['nombre_completo']}?\n\nEsta acción liberará la tarjeta NFC.")
        if respuesta:
            try:
                cursor = self.conexion_db.cursor()
                cursor.execute("DELETE FROM pacientes WHERE rfid_uid = %s", (self.uid_actual,))
                self.conexion_db.commit()
                cursor.close()
                
                messagebox.showinfo("Eliminado", "El paciente ha sido eliminado. La tarjeta está lista para un nuevo registro.")
                self.mostrar_espera()
            except mysql.connector.Error as err:
                messagebox.showerror("Error", f"No se pudo eliminar: {err}")

    def guardar_registro(self):
        if not self.conexion_db or not self.conexion_db.is_connected():
            messagebox.showerror("Error", "No hay conexión a la base de datos.")
            return

        valores = (
            self.entradas["Nombre Completo"].get(),
            self.entradas["Tipo de Sangre"].get(),
            self.entradas["Alergias"].get(),
            self.entradas["Condiciones Médicas"].get(),
            self.entradas["Contacto Emergencia"].get(),
            self.uid_actual
        )

        if not all(valores):
            messagebox.showwarning("Advertencia", "Por favor, llene todos los campos.")
            return

        try:
            cursor = self.conexion_db.cursor()
            
            if self.modo_edicion:
                query = """
                    UPDATE pacientes 
                    SET nombre_completo = %s, tipo_sangre = %s, alergias = %s, condiciones_medicas = %s, contacto_emergencia = %s
                    WHERE rfid_uid = %s
                """
                mensaje_exito = "Datos actualizados correctamente."
            else:
                valores_insert = (self.uid_actual, valores[0], valores[1], valores[2], valores[3], valores[4])
                query = """
                    INSERT INTO pacientes (rfid_uid, nombre_completo, tipo_sangre, alergias, condiciones_medicas, contacto_emergencia)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """
                valores = valores_insert
                mensaje_exito = "Paciente registrado correctamente."

            cursor.execute(query, valores)
            self.conexion_db.commit()
            cursor.close()
            
            messagebox.showinfo("Éxito", mensaje_exito)
            self.mostrar_espera()
            
        except mysql.connector.Error as err:
            messagebox.showerror("Error", f"Fallo en la base de datos: {err}")

    def procesar_uid(self, uid):
        if not self.conexion_db or not self.conexion_db.is_connected():
            self.conexion_db = self.conectar_bd()

        if self.conexion_db:
            try:
                self.uid_actual = uid 
                cursor = self.conexion_db.cursor(dictionary=True)
                cursor.execute("SELECT * FROM pacientes WHERE rfid_uid = %s", (uid,))
                paciente = cursor.fetchone()
                cursor.close()

                if paciente:
                    self.mostrar_datos(paciente)
                else:
                    self.mostrar_registro(uid)
            except mysql.connector.Error as err:
                print(f"Error consultando BD: {err}")

    def on_closing(self):
        self.desconectar_serial()
        if self.conexion_db and self.conexion_db.is_connected():
            self.conexion_db.close()
        self.destroy()

if __name__ == "__main__":
    app = SistemaEmergenciasApp()
    app.protocol("WM_DELETE_WINDOW", app.on_closing)
    app.mainloop()