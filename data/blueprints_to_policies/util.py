import os

total = 0
exec_directory = os.getcwd()
refactor_dir = exec_directory + "/refactor"
for root, dirs, files in os.walk(refactor_dir):
    total += len(files)

pass
