import jwt
from fastapi import FastAPI, HTTPException, status, Depends
from pydantic import BaseModel
from database import conn
from pwdlib import PasswordHash
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from datetime import datetime, timedelta, timezone

app = FastAPI()
password_hash = PasswordHash.recommended()

SECRET_KEY = "your-super-secret-key"
ALGORITHM = "HS256"

security = HTTPBearer()

class Student(BaseModel):
    name: str
    email: str
    age: int

class StudentResponse(BaseModel):
    id:int
    name: str
    email: str
    age: int

class StudentCreateResponse(BaseModel):
    message: str
    student: StudentResponse

class StudentUpdate(BaseModel):
    name: str | None = None
    email: str | None = None
    age: int | None = None

class UserCreate(BaseModel):
    username: str
    email: str
    password: str

class UserResponse(BaseModel):
    id: int
    username: str
    email: str

class Userlogin(BaseModel):
    username: str
    password: str

def verify_token(token:str):
    try:
        payload = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM]
        )
        return payload
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code= status.HTTP_401_UNAUTHORIZED,
            detail= "Invalid or expired token"
        )

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    payload = verify_token(token)
    return payload

def require_admin(current_user = Depends(get_current_user)):
    if current_user["role"] != 'admin':
        raise HTTPException(
            status_code= status.HTTP_403_FORBIDDEN,
            detail= "Admin Access Required.!"
        )

    return current_user

@app.post("/students", response_model= StudentCreateResponse, status_code=status.HTTP_201_CREATED)
def create_students(student:Student, current_user = Depends(get_current_user)):
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO students(name, email, age)
        VALUES(%s,%s,%s)
        RETURNING id, name, email, age
        """,
        (student.name, student.email, student.age)
    )
    new_student = cur.fetchone()
    conn.commit()
    cur.close()

    return{
        "message":"Student created Successfully.!",
        "student":{
            "id":new_student[0],
            "name":new_student[1],
            "email":new_student[2],
            "age": new_student[3]
        }
    }

@app.get("/students", response_model= list [StudentResponse])
def get_all_students(current_user = Depends(get_current_user)):
    cur = conn.cursor()
    cur.execute("""
        SELECT id, name, email, age
        FROM students
""")
    students = cur.fetchall()
    cur.close()
    return[
        {
            "id": student[0],
            "name": student[1],
            "email": student[2],
            "age": student[3]
        }
        for student in students
    ]


@app.get("/students/{student_id}", response_model=StudentResponse)
def get_student(student_id:int, current_user = Depends(get_current_user)):
    cur = conn.cursor()
    cur.execute("""
        SELECT id, name, email, age 
        FROM students
        WHERE id = %s
    """,(student_id,)
    )
    student = cur.fetchone()
    cur.close()

    if student is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail= "Student Not Found.!"
        )

    return{
        "id": student[0],
        "name": student[1],
        "email": student[2],
        "age": student[3]
    }

@app.delete("/students/{student_id}", status_code= status.HTTP_204_NO_CONTENT)
def delete_student(student_id, current_user = Depends(require_admin)):
    cur = conn.cursor()
    cur.execute("""
        DELETE FROM students 
        WHERE id = %s
        RETURNING id
    """,(student_id,))
    deleted_student = cur.fetchone()
    conn.commit()
    cur.close()

    if deleted_student is None:
        raise HTTPException(
            status_code= status.HTTP_404_NOT_FOUND,
            detail= "Student Not Found.!"
        )

    return None


@app.put("/student/{student_id}", response_model= StudentCreateResponse)
def update_student(student_id, updated_student:Student, current_user = Depends(get_current_user)):
    cur = conn.cursor()
    cur.execute("""
        UPDATE students
        SET
            name = %s,
            email = %s,
            age = %s
        WHERE id = %s
        RETURNING id, name, email, age
    """,(
            updated_student.name,
            updated_student.email,
            updated_student.age,
            student_id
        )
    )

    update = cur.fetchone()
    conn.commit()
    cur.close()

    if update is None:
        raise HTTPException(
            status_code= status.HTTP_404_NOT_FOUND,
            detail= "Student Not Found.!"
        )

    return{
        "message":"Student Updated.!",
        "student":{
            "id":update[0],
            "name":update[1],
            "email":update[2],
            "age":update[3]
        }
    }

@app.patch("/students/{student_id}", response_model= StudentResponse)
def patch_student(student_id:int, student:StudentUpdate, current_user = Depends(get_current_user)):
    update_data = student.model_dump(exclude_unset= True)

    if not update_data:
        raise HTTPException(
            status_code= status.HTTP_400_BAD_REQUEST,
            detail= "No Fields provided to update.! "
        )
    
    cur = conn.cursor()
    
    cur.execute("""
        SELECT id, name, email, age
        FROM students
        WHERE id = %s
    """, (student_id,))

    existing_data = cur.fetchone()
    if existing_data is None:

        cur.close()
        raise HTTPException(
            status_code= status.HTTP_404_NOT_FOUND,
            detail= "Student not Found.!"
        )

    name= update_data.get("name", existing_data[1])
    email= update_data.get("email", existing_data[2])
    age= update_data.get("age", existing_data[3])

    cur.execute("""
        UPDATE students
        SET 
            name= %s,
            email= %s,
            age= %s
        WHERE id = %s
        RETURNING id, name, email, age
    """,(name, email, age, student_id)
    )

    update = cur.fetchone()
    conn.commit()
    cur.close()

    return{
        "id": update[0],
        "name": update[1],
        "email": update[2],
        "age": update[3]
    }


@app.post("/register", response_model= UserResponse, status_code=status.HTTP_201_CREATED)
def create_user(user: UserCreate):
    cur = conn.cursor()
    
    hash_password = password_hash.hash(user.password)

    cur.execute("""
        INSERT INTO users(username, email, password_hash)
        VALUES(%s, %s, %s)
        RETURNING id, username, email
    """,(user.username, user.email, hash_password)
    )

    new_user = cur.fetchone()
    conn.commit()
    cur.close()

    return{
        "id":new_user[0],
        "username":new_user[1],
        "email": new_user[2]
    }


@app.post("/login")
def user_login(user:Userlogin):
    cur = conn.cursor()
    cur.execute("""
        SELECT * FROM users
        WHERE username = %s
    """,(user.username,)
    )

    db_user = cur.fetchone()
    conn.commit()
    cur.close()

    if db_user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail= "Invalid Username or Password"
        )

    valid_user = password_hash.verify(user.password, db_user[3])

    if not valid_user:
        raise HTTPException(
            status_code= status.HTTP_401_UNAUTHORIZED,
            detail= "Invalid username or password"
        )

    access_token_expire = timedelta(minutes=30)
    token = jwt.encode(
        {
            "sub":str(db_user[0]),
            "role": str(db_user[4]),
            "exp": datetime.now(timezone.utc) + access_token_expire
        },
        SECRET_KEY,
        algorithm=ALGORITHM
    )

    return{
        "access_token": token,
        "token_type": "bearer"
    }