# Runtime hook to patch Gradio for PyInstaller frozen apps
# Gradio's ComponentMeta tries to read .py source files to generate .pyi stubs
# This fails in frozen apps because source files aren't bundled (only .pyc)
#
# Error: FileNotFoundError: gradio\blocks_events.py
# Then: ValueError: Couldn't find class source code
#
# Solution: Intercept gradio.component_meta import and replace
# create_or_modify_pyi with a no-op BEFORE any components load

import sys


def patch_gradio_component_meta():
    """
    Patch Gradio's create_or_modify_pyi via import interception.

    This must run BEFORE gradio is imported. The metaclass ComponentMeta
    calls create_or_modify_pyi during class creation, so we need to
    patch it before any Gradio component classes are defined.
    """
    if not getattr(sys, 'frozen', False):
        return  # Only patch in frozen apps

    import importlib.abc

    class GradioComponentMetaPatcher(importlib.abc.Loader):
        """Custom loader that patches component_meta after loading."""

        def __init__(self, original_loader):
            self.original_loader = original_loader

        def create_module(self, spec):
            return None  # Use default module creation

        def exec_module(self, module):
            # Execute the original module first
            self.original_loader.exec_module(module)

            # Patch AFTER module loads but BEFORE components use it
            # Replace create_or_modify_pyi with a no-op
            def noop_create_or_modify_pyi(*args, **kwargs):
                pass  # Skip .pyi generation in frozen apps

            module.create_or_modify_pyi = noop_create_or_modify_pyi

    class GradioMetaPathFinder(importlib.abc.MetaPathFinder):
        """Meta path finder to intercept gradio.component_meta imports."""

        def find_spec(self, fullname, path, target=None):
            if fullname == 'gradio.component_meta':
                # Find the original spec using other finders
                for finder in sys.meta_path:
                    if finder is self:
                        continue
                    try:
                        spec = finder.find_spec(fullname, path, target)
                        if spec is not None:
                            # Wrap the loader with our patcher
                            spec.loader = GradioComponentMetaPatcher(spec.loader)
                            return spec
                    except (AttributeError, TypeError):
                        continue
            return None

    # Install our finder at the beginning of meta_path
    sys.meta_path.insert(0, GradioMetaPathFinder())


# Run the patch immediately when this hook loads
patch_gradio_component_meta()
