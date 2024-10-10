import os

# Project root directory
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))

# Data directory
DATA_DIR = os.path.join(ROOT_DIR, 'data')

# Constraints directory
CONSTRAINTS_DIR = os.path.join(DATA_DIR, 'constraints')

# Default constraints file
DEFAULT_CONSTRAINTS_FILE = os.path.join(CONSTRAINTS_DIR, 'default_constraints.json')
