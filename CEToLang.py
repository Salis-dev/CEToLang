import os
import sys
import subprocess
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import xml.etree.ElementTree as ET

# Function to check and install missing dependencies
def check_and_install_dependencies():
    try:
        import pip
    except ImportError:
        messagebox.showerror("Error", "pip is not installed. Please install pip manually.")
        sys.exit(1)

    # List of required libraries
    required_libraries = ['tkinter', 'xml.etree.ElementTree']

    # Optional, if additional packages are needed
    optional_libraries = ['pymem']  # Example, not used in this specific script

    # Check if packages are installed, and install them if missing
    for lib in optional_libraries:
        try:
            __import__(lib)
        except ImportError:
            install_package(lib)


def install_package(package):
    """Automatically install a Python package."""
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", package])
        messagebox.showinfo("Success", f"{package} has been installed.")
    except Exception as e:
        messagebox.showerror("Error", f"Failed to install {package}: {e}")
        sys.exit(1)


# Function to select a file using a file dialog
def select_file():
    file_path = filedialog.askopenfilename(filetypes=[("Cheat Engine Table", "*.CT")])
    return file_path


# Function to parse the XML file
def parse_xml(file_path):
    tree = ET.parse(file_path)
    root = tree.getroot()

    cheat_entries = []
    modules_declared = set()  # Keep track of declared modules

    for cheat in root.iter("CheatEntry"):
        entry = {}
        description = cheat.find("Description")
        if description is not None:
            entry["name"] = description.text.strip("\"")
        else:
            entry["name"] = "Unknown"

        variable_type = cheat.find("VariableType")
        if variable_type is not None and variable_type.text != "Auto Assembler Script":
            entry["variable_type"] = variable_type.text
        else:
            entry["variable_type"] = None

        address = cheat.find("Address")
        if address is not None:
            entry["address"] = address.text

            # Handle offsets and pointers
            if cheat.find("Offsets") is not None:
                entry["type"] = "pointer"
                offsets = [offset.text for offset in cheat.findall("Offsets/Offset")]
                entry["offsets"] = offsets
                # Extract module name if present in the address
                if "exe" in entry["address"]:
                    module = entry["address"].split("+")[0]
                    entry["module"] = module
                    modules_declared.add(module)
            elif entry["address"].startswith('+'):
                entry["type"] = "offset"
                entry["offsets"] = [entry["address"]]
            else:
                entry["type"] = "direct"
        else:
            entry["type"] = None  # In case there's no address found, we set type as None

        cheat_entries.append(entry)

    return cheat_entries, modules_declared


# Function to convert parsed data to the chosen language format
def convert_to_language(cheat_entries, language):
    output = ""
    module_bases = ""
    modules_used = set()

    for cheat in cheat_entries:
        if cheat["type"] == "pointer" and "module" in cheat:
            module = cheat["module"].replace('"','')
            if module not in modules_used:
                if language == "Python":
                    module_bases += f"{module.split('.')[0]}base = utility.GetModuleBaseAddress(pid, \"{module}\")\n"
                elif language == "C++":
                    module_bases += f"uintptr_t {module.split('.')[0]}base = GetModuleBaseAddress(procId, \"{module}\");\n"
                elif language == "C#":
                    module_bases += f"IntPtr {module.split('.')[0]}base = yourlib.GetModuleBase(\"{module}\");\n"
                modules_used.add(module)

    if language == "Python":
        output += """Converted to Python with CEToLang 0.8
        Github Link:
        https://github.com/Salis-dev/CEToLang/"""
        output += "# Module base addresses\n" + module_bases + "\n# Parsed Cheats in Python\n"
        for cheat in cheat_entries:
            if cheat["type"] == "pointer" and "module" in cheat:
                cheat['module'] = cheat['module'].replace('"','')
                output += f"{cheat['name']} = {cheat['module'].split('.')[0]}base + 0x{cheat['address'].split('+')[1]}\n"
                output += f"{cheat['name']}_offsets = [{', '.join(f'0x{offset}' for offset in cheat['offsets'])}]\n"
            elif cheat["type"] == "offset":
                output += f"{cheat['name']} = base_address + {cheat['offsets'][0]}\n"
            elif cheat["type"] == "direct":
                output += f"{cheat['name']} = {cheat['address']}\n"
            output += "\n"

    elif language == "C++":
        output += """Converted to C++ with CEToLang 0.8
        Github Link:
        https://github.com/Salis-dev/CEToLang/"""
        output += "// Module base addresses\n" + module_bases + "\n// Parsed Cheats in C++\n"
        for cheat in cheat_entries:           
            if cheat["type"] == "pointer" and "module" in cheat:
                cheat['module'] = cheat['module'].replace('"','')
                output += f"uintptr_t {cheat['name']} = {cheat['module'].split('.')[0]}base + 0x{cheat['address'].split('+')[1]};\n"
                output += f"std::vector<unsigned int> {cheat['name']}Offsets = {{{', '.join(f'0x{offset}' for offset in cheat['offsets'])}}};\n"
            elif cheat["type"] == "offset":
                output += f"uintptr_t {cheat['name']} = base_address + {cheat['offsets'][0]};\n"
            elif cheat["type"] == "direct":
                output += f"uintptr_t {cheat['name']} = {cheat['address']};\n"
            output += "\n"

    elif language == "C#":
        output += """Converted to C# with CEToLang 0.8
        Github Link:
        https://github.com/Salis-dev/CEToLang/"""
        output += "// Module base addresses\n" + module_bases + "\n// Parsed Cheats in C#\n"
        for cheat in cheat_entries:
            if cheat["type"] == "pointer" and "module" in cheat:
                cheat['module'] = cheat['module'].replace('"','')
                output += f"IntPtr {cheat['name']} = new IntPtr({cheat['module'].split('.')[0]}base + 0x{cheat['address'].split('+')[1]});\n"
                output += f"int[] {cheat['name']}Offsets = {{{', '.join(f'0x{offset}' for offset in cheat['offsets'])}}};\n"
            elif cheat["type"] == "offset":
                output += f"IntPtr {cheat['name']} = baseAddress + {cheat['offsets'][0]};\n"
            elif cheat["type"] == "direct":
                output += f"IntPtr {cheat['name']} = new IntPtr({cheat['address']});\n"
            output += "\n"

    return output


# Function to save the output to a file
def save_output(output, language):
    file_ext = {"Python": ".py", "C++": ".cpp", "C#": ".cs"}
    if language not in file_ext:
        messagebox.showerror("Error", "Invalid language choice.")
        return

    output_file = filedialog.asksaveasfilename(defaultextension=file_ext[language], filetypes=[(language, file_ext[language])])
    if output_file:
        with open(output_file, "w") as file:
            file.write(output)
        messagebox.showinfo("Success", f"File saved as {output_file}")


# GUI Class for the cheat application
class CheatApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Cheat Engine Converter")
        self.root.resizable(False, False)  # Make window non-resizable
        self.root.geometry("250x150")  # Set default window size

        # Remove minimize and maximize buttons
        self.root.overrideredirect(False)  # Keep top bar but remove min/max buttons
        #self.root.attributes("-toolwindow", 1)  # Remove minimize/maximize but show in taskbar

        # File selection button
        self.file_button = ttk.Button(self.root, text="Select Cheat Table", command=self.open_file)
        self.file_button.grid(row=0, column=0, padx=50, pady=10)

        # Dropdown for language selection
        self.language_label = ttk.Label(self.root, text="Choose Output Language:")
        self.language_label.grid(row=1, column=0, padx=50, pady=5, sticky="w")

        self.language_var = tk.StringVar()
        self.language_dropdown = ttk.Combobox(self.root, textvariable=self.language_var, state="readonly")
        self.language_dropdown['values'] = ("Python", "C++", "C#")
        self.language_dropdown.grid(row=2, column=0, padx=50, pady=5)
        self.language_dropdown.current(0)  # Default to Python

        # Convert button
        self.convert_button = ttk.Button(self.root, text="Convert", command=self.convert)
        self.convert_button.grid(row=3, column=0, padx=50, pady=10)

    def open_file(self):
        self.file_path = select_file()
        if not self.file_path:
            messagebox.showerror("Error", "No file selected.")
            return
        messagebox.showinfo("File Selected", f"Selected: {self.file_path}")

    def convert(self):
        if not hasattr(self, 'file_path') or not self.file_path:
            messagebox.showerror("Error", "No file selected.")
            return

        # Ensure a language is selected
        language = self.language_var.get()
        if not language:
            messagebox.showerror("Error", "No language selected.")
            return

        # Parse XML
        cheat_entries, modules_declared = parse_xml(self.file_path)

        # Convert to the selected language format
        output = convert_to_language(cheat_entries, language)

        # Save the output
        save_output(output, language)


# Main Function
def main():
    # Check and install any dependencies
    check_and_install_dependencies()

    # Start the main Tkinter GUI
    root = tk.Tk()
    app = CheatApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
