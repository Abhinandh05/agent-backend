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

15

in this i created a .env file for the need to store the  screct file into that section 

 then i created the main file called main.py 

 in this inculde the sample section of the server  in this file incudes like api doc file, test file and last normla home route page in this 


 in this the doc file incudes how may api is precent in this 

  below code is how to run the main server 

run the the main py in this 

uvicorn main:app --reload



DB_NAME=postgres
DB_USER=postgres
DB_PASSWORD=Abhi@123
DB_HOST=
DB_PORT=5432
DB_DIALECT=postgres

DATABASE_URL=postgresql://admin:secret@localhost:5432/ai_business_os
SECRET_KEY=your-super-secret-key-change-this-later
OPENAI_API_KEY=sk-put-your-key-here-later
DEBUG=True



# new
DATABASE_URL=postgresql://admin:secret@localhost:5432/ai_business_os
# JWT Settings
SECRET_KEY=7df29d5aa1a72a243c4e2753d0ee2a5541726a9e646e318e4b0db8d28b4c188a
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
OPENAI_API_KEY=sk-put-your-key-here-later
DEBUG=True

#Database
DB_NAME=postgres
DB_USER=postgres
DB_PASSWORD=Abhi@123
DB_HOST=localhost
DB_PORT=5432
DB_DIALECT=postgres