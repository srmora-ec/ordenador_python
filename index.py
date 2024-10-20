import os
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext
import sqlite3
import requests
import json
import shutil
from tkinter import ttk
import traceback
# Función para seleccionar carpeta
def seleccionar_carpeta():
    carpeta = filedialog.askdirectory()
    if carpeta:
        entry_carpeta.delete(0, tk.END)
        entry_carpeta.insert(0, carpeta)


def mostrar_confirmacion(mensaje):
    return messagebox.askyesno("Confirmación", mensaje)

def ordenar_archivos_por_json(ruta_base, json_data, actualizar_vista):
    if not os.path.exists(ruta_base):
        actualizar_vista(f"Error: La ruta base '{ruta_base}' no existe. \n")
        return
    
    for carpeta, archivos in json_data["orden"].items():
        ruta_carpeta = os.path.join(ruta_base, carpeta)
        
        if not os.path.exists(ruta_carpeta):
            os.makedirs(ruta_carpeta)
            actualizar_vista(f"Carpeta creada: {ruta_carpeta} \n")
        
        for archivo in archivos:
            nombre_archivo = archivo['nombre']
            ruta_origen = os.path.join(ruta_base, nombre_archivo)
            ruta_destino = os.path.join(ruta_carpeta, nombre_archivo)
            
            if os.path.exists(ruta_origen):
                try:
                    shutil.move(ruta_origen, ruta_destino)
                    actualizar_vista(f"Movido: {nombre_archivo} a {ruta_carpeta} \n")
                except PermissionError:
                    respuesta = mostrar_confirmacion(f"No se puede mover '{nombre_archivo}'. ¿Quieres omitir este archivo y continuar?")
                    if respuesta: 
                        actualizar_vista(f"Omitido: {nombre_archivo} \n")
                    else:  
                        actualizar_vista("Operación cancelada. \n")
                        return
                except Exception as e:
                    respuesta = mostrar_confirmacion(f"No se puede mover '{nombre_archivo}'. ¿Quieres omitir este archivo y continuar?")
                    if respuesta:  
                        actualizar_vista(f"Omitido: {nombre_archivo} \n")
                    else:
                        actualizar_vista("Operación cancelada. \n")
                        return
            else:
                actualizar_vista(f"Advertencia: {nombre_archivo} no encontrado en {ruta_base} \n")
    mostrar_alerta("Se ordenaron los archivos")

def calcular_tamano(ruta):
    if os.path.isfile(ruta):
        return os.path.getsize(ruta)
    else:
        total_size = 0
        for dirpath, dirnames, filenames in os.walk(ruta):
            for f in filenames:
                fp = os.path.join(dirpath, f)
                total_size += os.path.getsize(fp)
        return total_size


def obtener_tipo(nombre):
    _, extension = os.path.splitext(nombre)
    if extension in ['.txt']:
        return 'archivo de texto'
    elif os.path.isdir(nombre):
        return 'carpeta'
    else:
        return 'archivo'

def generar_json(carpeta,actualizar_vista):
    lista_archivos = []
    actualizar_vista('Leyendo archivos...  \n')
    for nombre in os.listdir(carpeta):
        ruta = os.path.join(carpeta, nombre)
        tipo = obtener_tipo(ruta)
        tamano = calcular_tamano(ruta)
        peso = convertir_tamano(tamano)

        archivo = {
            "nombre": nombre,
            "tipo": tipo,
            "peso": peso
        }
        lista_archivos.append(archivo)
    
    archivos_json = {
        "archivos": lista_archivos
    }
    
    return archivos_json

def convertir_tamano(tamano):
    for unidad in ['B', 'KB', 'MB', 'GB', 'TB']:
        if tamano < 1024:
            return f"{tamano:.2f} {unidad}"
        tamano /= 1024

def solicitar_organizacion(json_archivos, descripcion):
    print('Solicitando orden')
    api_key = obtener_api_key() 
    if not api_key:
        messagebox.showwarning("Advertencia", "Por favor, configure la API antes de continuar.")
        return None
    
    url = f'https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash-latest:generateContent?key={api_key}'
    
    # Crear el prompt para la API
    prompt = (
        f'Quiero que organices estos archivos {json.dumps(json_archivos)} y me los devuelvas ordenados en carpetas de la siguiente manera: {descripcion}. '
        'Recuerda solo responder con el json.'
        'Recuerda que si ya hay una carpeta con el nombre que solicité no tienes porque meterla dentro de otra carpeta, o porque crearla, simplemente usa esa carpeta para organizar.'
        'No me devuelvas caracteres especiales como el salto de linea /n'
        'Devuélveme un JSON con el siguiente formato:\n'
        '{'
        '  "orden": {'
        '    {"programa": "esteprogramaquedaenelescritorio.txt", "tipo": "archivo de texto", "peso": "1GB"},\n'
        '    "Carpeta1": ['
        '      {"nombre": "archivo.txt", "tipo": "archivo de texto", "peso": "1GB"},'
        '      {"nombre": "Documentos de la U", "tipo": "carpeta", "peso": "10GB"}'
        '    ],'
        '    "Carpeta2": ['
        '      {"nombre": "archivo2.txt", "tipo": "archivo de texto", "peso": "2GB"},'
        '      {"nombre": "Fotos", "tipo": "carpeta", "peso": "5GB"}'
        '    ]'
        '  }'
        '}'
    )

    headers = {
        'Content-Type': 'application/json'
    }
    data = {
        'contents': [
            {
                'parts': [
                    {'text': prompt}
                ]
            }
        ]
    }

    try:
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()
        result = response.json()
        if 'candidates' in result and len(result['candidates']) > 0:
            candidate = result['candidates'][0]
            if 'content' in candidate and 'parts' in candidate['content'] and len(candidate['content']['parts']) > 0:
                text = candidate['content']['parts'][0].get('text', '')
                
                try:
                    
                    text = text.replace("```json", '').replace("```", '').strip() 
                    text = text.strip('```') 
                    text = text.replace("\n", '')
                    

                    json_organizado = json.loads(text)
                    print(f"json limpio: {json_organizado}")
                    return json_organizado
                
                except json.JSONDecodeError as e:

                    messagebox.showwarning("Error", f"Error al interpretar la respuesta como JSON: {str(e)}")
                    print(f"Error al interpretar la respuesta como JSON: {str(e)}")
                except Exception as e:
                    messagebox.showwarning("Error", f"Error: {str(e)}")
                    print(f"Error detallado:\n{traceback.format_exc()}")

    except requests.exceptions.RequestException as e:
        messagebox.showerror("Error", f"Error al hacer la solicitud a la API: {e}")
        return None

def mostrar_json(json_data):
    modal_json = tk.Toplevel(root)
    modal_json.title("Resultados del cálculo")
    text_area = scrolledtext.ScrolledText(modal_json, width=80, height=20)
    text_area.pack(padx=10, pady=10)

    json_formateado = json.dumps(json_data, indent=4)
    
    text_area.insert(tk.END, json_formateado)
    text_area.configure(state='disabled') 

def mostrar_alerta(mensaje):
    messagebox.showinfo("Información", mensaje)

def dividir_json_en_bloques(json_archivos, tamaño_bloque=30):
    lista_archivos = json_archivos["archivos"]  
    for i in range(0, len(lista_archivos), tamaño_bloque):
        yield {"archivos": lista_archivos[i:i + tamaño_bloque]}

def ordenar(actualizar_vista):
    carpeta = entry_carpeta.get()
    descripcion = text_descripcion.get("1.0", tk.END).strip()

    if carpeta and descripcion:
        json_archivos = generar_json(carpeta, actualizar_vista)
        bloques_json = dividir_json_en_bloques(json_archivos, 30)

        for bloque in bloques_json:
            json_organizado = solicitar_organizacion(bloque, descripcion)
            
            if json_organizado:
                ordenar_archivos_por_json(carpeta, json_organizado, actualizar_vista)
    else:
        messagebox.showwarning("Advertencia", "Por favor selecciona una carpeta y añade una descripción.")


def guardar_api_key(api_key):
    conn = sqlite3.connect('gemini.db')
    cursor = conn.cursor()

    cursor.execute('''CREATE TABLE IF NOT EXISTS gemini (api TEXT)''')


    cursor.execute('''DELETE FROM gemini''')

    cursor.execute('''INSERT INTO gemini (api) VALUES (?)''', (api_key,))

    conn.commit()
    conn.close()


def obtener_api_key():
    conn = sqlite3.connect('gemini.db')
    cursor = conn.cursor()


    cursor.execute('''CREATE TABLE IF NOT EXISTS gemini (api TEXT)''')
    cursor.execute('''SELECT api FROM gemini LIMIT 1''')
    result = cursor.fetchone()

    conn.close()
    if result:
        return result[0]
    return ""

def abrir_modal():

    modal = tk.Toplevel(root)
    modal.title("Configurar API")
    modal.transient(root)
    modal.grab_set() 

    label_api = tk.Label(modal, text="Ingrese la API Key:")
    label_api.pack(pady=10)

    entry_api = tk.Entry(modal, width=50)
    entry_api.pack(padx=10, pady=5)


    api_guardada = obtener_api_key()
    if api_guardada:
        entry_api.insert(0, api_guardada) 

    # Botón para guardar la API
    btn_guardar_api = tk.Button(modal, text="Guardar", command=lambda: guardar_y_cerrar_modal(modal, entry_api))
    btn_guardar_api.pack(pady=10)

    modal.mainloop()
def cerrar_modal_y_ordenar(modal, actualizar_vista):
    ordenar(actualizar_vista) 
    modal.destroy() 

def cargar():

    modal = tk.Toplevel(root)
    modal.title("Ordenando")
    modal.transient(root)
    modal.grab_set() 


    text_area = scrolledtext.ScrolledText(modal, wrap=tk.WORD, width=80, height=10)
    text_area.pack(padx=10, pady=10)


    def actualizar_vista(mensaje):
        text_area.insert(tk.END, mensaje) 
        text_area.see(tk.END) 
        root.update_idletasks() 

    root.after(100, lambda: cerrar_modal_y_ordenar(modal, actualizar_vista))


def guardar_y_cerrar_modal(modal, entry_api):
    api_key = entry_api.get().strip()
    if api_key:
        guardar_api_key(api_key)
        messagebox.showinfo("Éxito", "API Key guardada correctamente.")
        modal.destroy()
    else:
        messagebox.showwarning("Advertencia", "Por favor ingrese una API Key.")

root = tk.Tk()
root.title("Ordenar Carpetas")


label_carpeta = tk.Label(root, text="Seleccionar carpeta:")
label_carpeta.pack(pady=5)

entry_carpeta = tk.Entry(root, width=50)
entry_carpeta.pack(padx=10, pady=5)

btn_seleccionar = tk.Button(root, text="Seleccionar", command=seleccionar_carpeta)
btn_seleccionar.pack(pady=5)

label_descripcion = tk.Label(root, text="Descripción:")
label_descripcion.pack(pady=5)

text_descripcion = tk.Text(root, height=5, width=50)
text_descripcion.pack(padx=10, pady=5)

btn_ordenar = tk.Button(root, text="Ordenar", command=cargar)
btn_ordenar.pack(pady=10)

btn_configurar = tk.Button(root, text="Configurar API", command=abrir_modal)
btn_configurar.pack(pady=5)

root.mainloop()
