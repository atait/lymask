import os

test_dir = os.path.realpath(os.path.dirname(__file__))
os.environ["KLAYOUT_HOME"] = test_dir
