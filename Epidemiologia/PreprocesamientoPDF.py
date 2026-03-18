import fitz 

# ARCHIVO_ENTRADA = "66221_ch01_5398.pdf"
# ARCHIVO_SALIDA = "Libro1.pdf"
# PAGINAS_A_QUITAR = [1,"19-22"] 

# ARCHIVO_ENTRADA = "9241547073_eng.pdf"
# ARCHIVO_SALIDA = "Libro2.pdf"
# PAGINAS_A_QUITAR = ["1-13","25-27","49-51","73-75",82,"110-111","127-129","144-145","156-157","174-177","189-226"]

ARCHIVO_ENTRADA = "cdc_13178_DS1.pdf"
ARCHIVO_SALIDA = "Libro3.pdf"
PAGINAS_A_QUITAR = ["1-12",18,26,32,"40-41",57,63,68,81,86,91,"93-108",114,118,128,132,135,141,143,151,155,160,"164-165","167-179",188,198,205,208,211,216,223,226,"231-244","254-255",259,266,271,280,284,295,306,"313-335",343,354,357,368,"371-372","392-411",418,424,"429-430","434-435",443,"459-461","470-511"]  

def obtener_lista_paginas(lista_mixta):
    paginas_finales = set()
    for item in lista_mixta:
        if isinstance(item, int):
            paginas_finales.add(item)
        elif isinstance(item, str) and "-" in item:
            partes = item.split("-")
            inicio = int(partes[0])
            fin = int(partes[1])
            for i in range(inicio, fin + 1):
                paginas_finales.add(i)
        elif isinstance(item, str):
            paginas_finales.add(int(item))
            
    return sorted(list(paginas_finales), reverse=True)

def eliminar_paginas():
    try:
        doc = fitz.open(ARCHIVO_ENTRADA)
        total_paginas = len(doc)
        
        lista_a_borrar = obtener_lista_paginas(PAGINAS_A_QUITAR)
        
        contador = 0
        for num_pag in lista_a_borrar:
            indice = num_pag - 1 
            if 0 <= indice < total_paginas:
                doc.delete_page(indice)
                contador += 1
            else:
                print(f"Omitiendo página {num_pag}: no existe en el PDF.")

        doc.save(ARCHIVO_SALIDA, garbage=3, deflate=True)
        doc.close()
        
        print(f"--- Proceso finalizado ---")
        print(f"Páginas eliminadas: {contador}")
        print(f"Archivo guardado: {ARCHIVO_SALIDA}")

    except Exception as e:
        print(f"Ocurrió un error: {e}")

if __name__ == "__main__":
    eliminar_paginas()