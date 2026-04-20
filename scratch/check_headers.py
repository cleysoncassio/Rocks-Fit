import os
import openpyxl

folder = 'temp'
for filename in os.listdir(folder):
    if filename.endswith('.xlsx'):
        path = os.path.join(folder, filename)
        try:
            wb = openpyxl.load_workbook(path, data_only=True)
            ws = wb.active
            headers = [str(c.value) for c in next(ws.iter_rows())]
            print(f"File: {filename}")
            print(f"Headers: {headers}")
            print("-" * 20)
        except Exception as e:
            print(f"Error reading {filename}: {e}")
