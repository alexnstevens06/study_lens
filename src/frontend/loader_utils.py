import importlib
import importlib.util
import inspect
import os
import sys
from typing import List, Type, Any

def load_classes_from_path(file_path: str, base_class: Type) -> List[Type]:
    """
    Loads classes from a given file path that are subclasses of base_class.
    
    Args:
        file_path: Relative or absolute path to the python file.
        base_class: The class that loaded classes must inherit from.
        
    Returns:
        List of class objects found in the file.
    """
    # Resolve absolute path
    if not os.path.isabs(file_path):
        file_path = os.path.abspath(file_path)

    if not os.path.exists(file_path):
        print(f"File not found: {file_path}")
        return []

    # Try to resolve module path relative to CWD (Project Root)
    cwd = os.getcwd()
    if file_path.startswith(cwd):
        # It's inside the project, try to load as a proper module
        rel_path = os.path.relpath(file_path, cwd)
        module_name = rel_path.replace(os.sep, '.').replace('.py', '')
        
        try:
            module = importlib.import_module(module_name)
            
            found_classes = []
            for name, obj in inspect.getmembers(module):
                if (inspect.isclass(obj) and 
                    issubclass(obj, base_class) and 
                    obj is not base_class):
                    found_classes.append(obj)
            return found_classes
            
        except Exception as e:
            print(f"Failed to import module {module_name}: {e}")
            # Fallback to direct file loading if import fails (e.g. for external files)

    # Fallback: Load as standalone file (won't support relative imports)
    module_name = os.path.basename(file_path).replace('.py', '')
    
    try:
        spec = importlib.util.spec_from_file_location(module_name, file_path)
        if spec and spec.loader:
            module = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = module
            spec.loader.exec_module(module)
            
            found_classes = []
            for name, obj in inspect.getmembers(module):
                if (inspect.isclass(obj) and 
                    issubclass(obj, base_class) and 
                    obj is not base_class):
                    found_classes.append(obj)
            
            return found_classes
    except Exception as e:
        print(f"Failed to load module from {file_path}: {e}")
        return []
    
    return []
