"""Compatibility entry point for the aggregate-only source audit."""
from pathlib import Path
import argparse
from source_audit_contract import audit, profile

if __name__ == '__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--source-root',type=Path,required=True)
    args=parser.parse_args()
    audit(args.source_root)
