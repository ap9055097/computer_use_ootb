# Runtime hook to patch Gradio for PyInstaller frozen apps
# Gradio's ComponentMeta tries to read .py source files to generate .pyi stubs
# This fails in frozen apps because source files aren't bundled (only .pyc)
#
# Error: FileNotFoundError: gradio\blocks_events.py
# Cause: gradio/component_meta.py line 108: source_file.read_text()

import sys


def patch_gradio_component_meta():
    """
    Patch Gradio's create_or_modify_pyi to be a no-op in frozen apps.

    This must run BEFORE gradio is imported, because the metaclass
    ComponentMeta calls create_or_modify_pyi during class creation.
    """
    if not getattr(sys, 'frozen', False):
        return  # Only patch in frozen apps

    # We need to patch before gradio.component_meta is imported
    # Use importlib to intercept the module
    import importlib.abc
    import importlib.machinery

    class GradioComponentMetaPatcher(importlib.abc.Loader):
        """Custom loader that patches component_meta after loading."""

        def __init__(self, original_loader):
            self.original_loader = original_loader

        def create_module(self, spec):
            return None  # Use default module creation

        def exec_module(self, module):
            # Execute the original module first
            self.original_loader.exec_module(module)

            # Now patch the function
            original_func = getattr(module, 'create_or_modify_pyi', None)
            if original_func:
                def noop_create_or_modify_pyi(*args, **kwargs):
                    pass  # Skip .pyi generation in frozen apps

                module.create_or_modify_pyi = noop_create_or_modify_pyi

    class GradioMetaPathFinder(importlib.abc.MetaPathFinder):
        """Meta path finder to intercept gradio.component_meta imports."""

        def find_spec(self, fullname, path, target=None):
            if fullname == 'gradio.component_meta':
                # Find the original spec
                for finder in sys.meta_path:
                    if finder is self:
                        continue
                    spec = finder.find_spec(fullname, path, target)
                    if spec is not None:
                        # Wrap the loader
                        spec.loader = GradioComponentMetaPatcher(spec.loader)
                        return spec
            return None

    # Install our finder at the beginning of meta_path
    sys.meta_path.insert(0, GradioMetaPathFinder())


# Alternative simpler approach: just suppress the error
def patch_gradio_simple():
    """
    Simpler patch: monkey-patch Path.read_text to handle missing .py files gracefully.
    """
    if not getattr(sys, 'frozen', False):
        return

    from pathlib import Path
    original_read_text = Path.read_text

    def patched_read_text(self, encoding=None, errors=None):
        try:
            return original_read_text(self, encoding=encoding, errors=errors)
        except FileNotFoundError:
            # If file doesn't exist (common in frozen apps), return empty
            if str(self).endswith('.py'):
                return ""  # Return empty source code
            raise  # Re-raise for other files

    Path.read_text = patched_read_text


# Use the simple patch - it's more robust
patch_gradio_simple()
