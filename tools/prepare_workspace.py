"""Compatibility entry point for the portable independent editor configuration."""
from pathlib import Path
import runpy
if __name__=='__main__':runpy.run_path(str(Path(__file__).with_name('configure_editor.py')),run_name='__main__')
