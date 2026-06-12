# 1. No need to install venv separately on Windows (it comes bundled with Python)

# 2. Remove any leftover broken venv
rmdir /s /q venv

# 3. Create a fresh venv
python -m venv venv

# 4. Activate it
venv\Scripts\activate


# 1. Install the venv package (if you haven't already)
sudo apt install python3.12-venv

# 2. Remove any leftover broken venv
rm -rf venv

# 3. Create a fresh venv
python3 -m venv venv

# 4. Activate it
source venv/bin/activate

