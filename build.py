import zipfile
import os

def create_addon_package(output_filename="ollamaTranslator.nvda-addon"):
    files_to_include = [
        "manifest.ini",
        "globalPlugins/ollama_translator.py"
    ]
    
    with zipfile.ZipFile(output_filename, 'w', zipfile.ZIP_DEFLATED) as addon_zip:
        for file_path in files_to_include:
            if os.path.exists(file_path):
                addon_zip.write(file_path)
                print(f"Added {file_path}")
            else:
                print(f"Warning: {file_path} not found!")
        
        # Add documentation
        if os.path.exists('doc'):
            for root, dirs, files in os.walk('doc'):
                for file in files:
                    file_path = os.path.join(root, file)
                    addon_zip.write(file_path)
                    print(f"Added {file_path}")

    print(f"Created {output_filename}")

if __name__ == "__main__":
    create_addon_package()
