import os, sys, subprocess, re
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
    context = ET.iterparse(file_path, events=("start", "end"))
    context = iter(context)
    event, root = next(context)

    cheat_entries = []
    modules_declared = set()

    for event, elem in context:
        if event == "end" and elem.tag == "CheatEntry":
            entry = {}
            description = elem.find("Description")
            if description is not None:
                entry["name"] = description.text.strip("\"")
            else:
                entry["name"] = "Unknown"

            variable_type = elem.find("VariableType")
            if variable_type is not None and variable_type.text != "Auto Assembler Script":
                entry["variable_type"] = variable_type.text
            else:
                entry["variable_type"] = None

            address = elem.find("Address")
            if address is not None:
                entry["address"] = address.text

                offsets = [offset.text for offset in elem.findall("Offsets/Offset")]
                if offsets:
                    entry["type"] = "offset"
                    entry["offsets"] = offsets
                elif elem.find("CheatEntries") is not None:
                    entry["type"] = "namespace"
                    entry["CheatEntries"] = []
                    for subcheat in elem.findall("CheatEntries/CheatEntry"):
                        subentry = {
                            "name": subcheat.find("Description").text.strip("\""),
                            "address": subcheat.find("Address").text.strip("+")
                        }
                        entry["CheatEntries"].append(subentry)
                else:
                    entry["type"] = "direct"
            else:
                entry["type"] = None

            cheat_entries.append(entry)
            root.clear()  # Clear root to free up memory

    return cheat_entries, modules_declared
    
def clean_name(name):
    """Cleans up the name by removing leading numbers/spaces and unwanted characters."""
    name = re.sub(r'^[0-9\s]+', '', name)  # Remove leading numbers or spaces
    name = name.replace(" ", "_")
    name = re.sub(r'[",.<>/?\-+()]+', '', name)  # Remove special characters
    return name

def convert_to_language(cheat_entries, language):
    module_bases = ""
    pointers = ""
    structures = ""
    rest = ""
    modules_used = set()  # To track which module bases were declared
    
    if language == "C++":
        output = "//Module Bases\n"
        
        for cheat in cheat_entries:
            if cheat["type"] == "pointer" or cheat["type"] == "offset":
                # Handle module base detection and declaration
                if "exe" in cheat['address'] or "dll" in cheat['address']:
                    module_name = cheat['address'].split('+')[0].replace('"', '')
                    base_name = clean_name(module_name)
                    if base_name not in modules_used:
                        module_bases += f"uintptr_t {base_name}Base = GetModuleBaseAddress(procId, \"{module_name}\");\n"
                        modules_used.add(base_name)
                    addr = f"{base_name}Base + 0x{cheat['address'].split('+')[1]}"
                else:
                    addr = f"base_address + 0x{cheat['address'].strip('+')}"
                
                # Clean name and ensure only valid addresses are added
                name = clean_name(cheat['name'])
                pointers += f"uintptr_t {name} = {addr};\n"
                if cheat.get('offsets'):
                    pointers += f"std::vector<unsigned int> {name}Offsets = {{{', '.join(f'0x{offset}' for offset in cheat['offsets'])}}};\n"

            elif cheat["type"] == "namespace":
                # Handle nested structures
                namespace_name = clean_name(cheat['name']) if cheat['name'] != "Unknown" else "UnnamedStruct"
                struct_output = f"namespace {namespace_name} {{\n"
                for subcheat in cheat["CheatEntries"]:
                    subname = clean_name(subcheat['name'])
                    subaddress = f"0x{subcheat['address'].strip('+')}"
                    struct_output += f"    constexpr auto {subname} = {subaddress};\n"
                struct_output += "}\n\n"
                structures += struct_output

            elif cheat["type"] == "direct":
                # Add loose cheats under "rest"
                name = clean_name(cheat['name'])
                rest += f"uintptr_t {name} = {cheat['address']};\n"
            
        # Group the output into sections
        output += module_bases
        output += "\n//Pointers\n" + pointers
        output += "\n//Structures\n" + structures
        output += "\n//Rest\n" + rest
        return output
    
    # Logic for Python output
    elif language == "Python":
        output = "#Module Bases\n"
        
        for cheat in cheat_entries:
            if cheat["type"] == "pointer" or cheat["type"] == "offset":
                if "exe" in cheat['address'] or "dll" in cheat['address']:
                    module_name = cheat['address'].split('+')[0].replace('"', '')
                    base_name = clean_name(module_name)
                    if base_name not in modules_used:
                        module_bases += f"{base_name}Base = utility.GetModuleBaseAddress(pid, \"{module_name}\")\n"
                        modules_used.add(base_name)
                    addr = f"{base_name}Base + 0x{cheat['address'].split('+')[1]}"
                else:
                    addr = f"base_address + 0x{cheat['address'].strip('+')}"
                
                name = clean_name(cheat['name'])
                pointers += f"{name} = {addr}\n"
                if cheat.get('offsets'):
                    pointers += f"{name}_offsets = [{', '.join(f'0x{offset}' for offset in cheat['offsets'])}]\n"

            elif cheat["type"] == "namespace":
                class_name = clean_name(cheat['name']) if cheat['name'] != "Unknown" else "UnnamedStruct"
                struct_output = f"class {class_name}:\n"
                for subcheat in cheat["CheatEntries"]:
                    subname = clean_name(subcheat['name'])
                    subaddress = f"0x{subcheat['address'].strip('+')}"
                    struct_output += f"    {subname} = {subaddress}\n"
                struct_output += "\n"
                structures += struct_output

            elif cheat["type"] == "direct":
                name = clean_name(cheat['name'])
                rest += f"{name} = {cheat['address']}\n"

        # Group the output into sections
        output += module_bases
        output += "\n#Pointers\n" + pointers
        output += "\n#Structures\n" + structures
        output += "\n#Rest\n" + rest
        return output

    # Logic for C# output
    elif language == "C#":
        output = "//Module Bases\n"
        
        for cheat in cheat_entries:
            if cheat["type"] == "pointer" or cheat["type"] == "offset":
                if "exe" in cheat['address'] or "dll" in cheat['address']:
                    module_name = cheat['address'].split('+')[0].replace('"', '')
                    base_name = clean_name(module_name)
                    if base_name not in modules_used:
                        module_bases += f"IntPtr {base_name}Base = yourlib.GetModuleBase(\"{module_name}\");\n"
                        modules_used.add(base_name)
                    addr = f"{base_name}Base + 0x{cheat['address'].split('+')[1]}"
                else:
                    addr = f"baseAddress + 0x{cheat['address'].strip('+')}"
                
                name = clean_name(cheat['name'])
                pointers += f"IntPtr {name} = {addr};\n"
                if cheat.get('offsets'):
                    pointers += f"int[] {name}Offsets = {{{', '.join(f'0x{offset}' for offset in cheat['offsets'])}}};\n"

            elif cheat["type"] == "namespace":
                namespace_name = clean_name(cheat['name']) if cheat['name'] != "Unknown" else "UnnamedStruct"
                struct_output = f"namespace {namespace_name} {{\n"
                for subcheat in cheat["CheatEntries"]:
                    subname = clean_name(subcheat['name'])
                    subaddress = f"0x{subcheat['address'].strip('+')}"
                    struct_output += f"    public const int {subname} = {subaddress};\n"
                struct_output += "}\n\n"
                structures += struct_output

            elif cheat["type"] == "direct":
                name = clean_name(cheat['name'])
                rest += f"IntPtr {name} = new IntPtr({cheat['address']});\n"

        # Group the output into sections
        output += module_bases
        output += "\n//Pointers\n" + pointers
        output += "\n//Structures\n" + structures
        output += "\n//Rest\n" + rest
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
